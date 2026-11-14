## @package pcresolve.ownership.source_fact_cache
#  Detached ownership visitor facts, captured before any project propagation.
#  在项目级传播前捕获并隔离的归属访问器事实。

import ast
from copy import deepcopy
from dataclasses import dataclass
from types import CellType, FunctionType, MethodType

from pcresolve.ownership.call_graph import FunctionId
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer


@dataclass(frozen=True)
class SingleFileFacts:
    """Pristine source-derived visitor facts, without an analyzer instance."""
    module_name: str
    is_package: bool
    file_path: str
    values: dict
    fact_structures: tuple
    fact_edges: tuple
    versioned_edges: tuple


_RUN_STATE = frozenset((
    '_analysis_budget', '_func_stack', '_class_stack', '_super_base_path_stack',
    '_seen_api_call_ids', '_receiver_owner_guards', '_expression_query_cache',
    '_class_receiver_stack', '_caller_stack', '_mapping_blocked_names',
    '_finite_name_guards', '_listeners', '_version', '_mapping_facts',
))


def _ast_memo(document, budget):
    memo = {}
    for node in ast.walk(document.tree):
        if budget is not None:
            budget.checkpoint()
        memo[id(node)] = node
    return memo


def _detach_visitor_callbacks(values, tracer, memo):
    """Keep cached values from retaining the collector through bound callbacks."""
    from pcresolve.ownership.fact_versions import FactStructure, VersionedDict, VersionedList

    pending = [(value, tracer) for value in values.values()]
    seen = set()
    fact_structures, fact_edges, versioned_edges = [], [], []
    fact_structure_ids = set()
    while pending:
        value, owner = pending.pop()
        if isinstance(value, FactStructure):
            if id(value) not in fact_structure_ids:
                fact_structure_ids.add(id(value))
                fact_structures.append(value)
            if owner is tracer:
                fact_edges.append((True, None, value))
            elif isinstance(owner, FactStructure):
                fact_edges.append((False, owner, value))
        elif isinstance(value, (VersionedDict, VersionedList)):
            versioned_edges.append((value, owner is tracer,
                                    owner if isinstance(owner, FactStructure) else None))
        if value is tracer:
            continue
        if value is None or id(value) in seen or isinstance(value, (str, bytes, int, float, bool, ast.AST)):
            continue
        seen.add(id(value))
        if isinstance(value, MethodType):
            if value.__self__ is tracer:
                memo[id(value)] = None
            else:
                pending.append((value.__self__, None))
            continue
        if isinstance(value, FunctionType):
            for cell in value.__closure__ or ():
                try:
                    closed = cell.cell_contents
                except ValueError:
                    continue
                if closed is tracer:
                    memo[id(value)] = None
                    break
                pending.append((closed, None))
            continue
        if isinstance(value, CellType):
            try:
                pending.append((value.cell_contents, None))
            except ValueError:
                pass
            continue
        if isinstance(value, dict):
            pending.extend((child, owner) for child in value.keys())
            pending.extend((child, owner) for child in value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend((child, owner) for child in value)
        elif hasattr(value, '__dict__') and not isinstance(value, type):
            child_owner = value if isinstance(value, FactStructure) else owner
            pending.extend((child, child_owner) for child in value.__dict__.values())
    return tuple(fact_structures), tuple(fact_edges), tuple(versioned_edges)


def _detach_fact_callbacks(structures, versioned_edges):
    """Drop observer cycles from the pristine cache copy before retaining it."""
    for structure in structures:
        structure._listeners = []
    for container, _, _ in versioned_edges:
        container._changed = None
        container._adopt = None


def _reattach_fact_callbacks(root, structures, fact_edges, versioned_edges):
    """Restore listeners from the registered fact structures in one clone."""
    from pcresolve.ownership.fact_versions import FactStructure, VersionedDict, VersionedList

    root._listeners = []
    for value in structures:
        value._listeners = []
    for container, is_root, owner in versioned_edges:
        parent = root if is_root else owner
        if parent is None:
            continue
        if isinstance(container, (VersionedDict, VersionedList)):
            container._changed = parent._notify
            container._adopt = parent._adopt
    for is_root, owner, child in fact_edges:
        parent = root if is_root else owner
        if isinstance(parent, FactStructure):
            parent._adopt(child)


## Copy collected facts without copying ASTs or retaining callbacks to another run.
## 复制已收集事实，不复制 AST，也不保留指向其他运行的回调。
#
#  @param tracer Pristine single-file visitor state, never a propagated tracer.
#  @param document Read-only source version owning its AST identities.
#  @param budget Optional current analysis budget.
#  @return Independent visitor facts with callbacks rebound to the copy.
def capture_source_facts(tracer, document, budget=None):
    """Capture collected state as a detached facts record, never a visitor."""
    if budget is not None:
        budget.checkpoint(force=True)
    memo = _ast_memo(document, budget)
    if tracer._analysis_budget is not None:
        memo[id(tracer._analysis_budget)] = None
    values = {name: value for name, value in tracer.__dict__.items()
              if name not in _RUN_STATE and name not in (
                  'module_name', 'is_package', '_file_path')}
    fact_structures, fact_edges, versioned_edges = _detach_visitor_callbacks(
        values, tracer, memo)
    values['_mapping_facts_literals'] = deepcopy(tracer._mapping_facts.literals, memo)
    values = deepcopy(values, memo)
    copied_structures = deepcopy(fact_structures, memo)
    copied_fact_edges = deepcopy(fact_edges, memo)
    copied_versioned_edges = deepcopy(versioned_edges, memo)
    _detach_fact_callbacks(copied_structures, copied_versioned_edges)
    if budget is not None:
        budget.checkpoint(force=True)
    return SingleFileFacts(tracer.module_name or '', tracer.is_package,
                           tracer._file_path, values, copied_structures,
                           copied_fact_edges, copied_versioned_edges)


## Rehydrate detached facts into a fresh, run-local AST visitor.
## 将分离的事实重新载入全新的单次运行 AST 访问器。
#
#  @param source_facts Immutable source facts captured before project propagation.
#  @param document Read-only source version owning the AST identities.
#  @param budget Optional current analysis budget.
#  @return Fresh visitor with callbacks rebound to its own state.
def clone_source_facts(source_facts, document, budget=None):
    if budget is not None:
        budget.checkpoint(force=True)
    memo = _ast_memo(document, budget)
    memo[id(source_facts)] = None
    copied_values = deepcopy(source_facts.values, memo)
    copied = SingleFileAnalyzer(module_name=source_facts.module_name,
                                is_package=source_facts.is_package,
                                file_path=source_facts.file_path,
                                analysis_budget=budget)
    copied.__dict__.update(copied_values)
    copied._mapping_facts.literals = copied.__dict__.pop('_mapping_facts_literals')
    copied_structures = deepcopy(source_facts.fact_structures, memo)
    fact_edges = deepcopy(source_facts.fact_edges, memo)
    versioned_edges = deepcopy(source_facts.versioned_edges, memo)
    _reattach_fact_callbacks(copied, copied_structures, fact_edges, versioned_edges)

    # Rebind query callbacks to this fresh visitor.
    # 将查询回调重新绑定到当前新访问器。
    copied._analysis_budget = budget
    facts = copied._mapping_facts
    facts.lookup = copied._mapping_binding
    facts.lambda_identity = lambda node: FunctionId(
        copied.module_name or '', copied._local_lambda_key(node))
    facts.mutable_lookup = lambda name: copied.current_scope().lookup(
        name, skip_parent_classes=True)
    facts.python_shape = copied._expression_python_shape
    if budget is not None:
        budget.checkpoint(force=True)
    return copied
