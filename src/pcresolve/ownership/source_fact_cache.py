## @package pcresolve.ownership.source_fact_cache
#  Detached ownership visitor facts, captured before any project propagation.
#  在项目级传播前捕获并隔离的归属访问器事实。

import ast
from copy import deepcopy
from dataclasses import dataclass
from types import CellType, FunctionType, MethodType

from pcresolve.ownership.call_graph import FunctionId
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer


## Detached source facts; no analyzer instance or run-local state is retained.
## 分离的源码事实记录；不保留分析器实例或单次运行状态。
#
#  @param module_name Import-qualified module identity.
#  @param is_package Whether the source represents a package initializer.
#  @param file_path Original source path.
#  @param values Deep-copied visitor facts with AST identities preserved.
#  @param fact_structures Fact structures whose observer links are rebound per clone.
#  @param fact_edges Parent-child fact relationships.
#  @param versioned_edges Versioned-container callback relationships.
@dataclass(frozen=True)
class SingleFileFacts:
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
# Exact built-in scalar types cannot hold fact structures or bound callbacks.
# Subclasses follow the existing visitor logic, including fact-edge registration.
_ATOMIC_TYPES = frozenset((type(None), str, bytes, int, float, bool))


## Preserve source AST identity during fact detachment and rehydration.
## 分离和重新载入事实时保留源 AST 节点身份。
#
#  @param document Read-only source version owning the AST nodes.
#  @param budget Optional analysis budget checked once per AST node.
#  @return Deepcopy memo mapping each source AST identity to the original node.
def _ast_memo(document, budget):
    memo = {}
    for node in ast.walk(document.tree):
        if budget is not None:
            budget.checkpoint()
        memo[id(node)] = node
    return memo


## Find fact observer links and remove references to the source visitor.
## 查找事实观察者关系并移除指向源访问器的引用。
#
#  @param values Collected visitor values to traverse.
#  @param tracer Visitor whose callbacks must not escape into the cache.
#  @param memo Deepcopy map preserving AST identities and detached callbacks.
#  @return Tuple of fact structures, fact edges and versioned-container edges.
def _detach_visitor_callbacks(values, tracer, memo):
    from pcresolve.ownership.fact_versions import FactStructure, VersionedDict, VersionedList

    pending = [(value, tracer) for value in values.values() if type(value) not in _ATOMIC_TYPES]
    seen = set()
    fact_structures, fact_edges, versioned_edges = [], [], []
    fact_structure_ids = set()
    while pending:
        value, owner = pending.pop()
        # Plain containers cannot have listeners of their own. Avoid the
        # versioned-container checks for these common traversal nodes.
        kind = type(value)
        if kind is dict:
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            pending.extend([(child, owner) for child in value.keys() if type(child) not in _ATOMIC_TYPES])
            pending.extend([(child, owner) for child in value.values() if type(child) not in _ATOMIC_TYPES])
            continue
        if kind in (list, tuple, set, frozenset):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            pending.extend([(child, owner) for child in value if type(child) not in _ATOMIC_TYPES])
            continue
        if isinstance(value, FactStructure):
            if id(value) not in fact_structure_ids:
                fact_structure_ids.add(id(value))
                fact_structures.append(value)
            if owner is tracer:
                fact_edges.append((True, None, value))
            elif isinstance(owner, FactStructure):
                fact_edges.append((False, owner, value))
        elif isinstance(value, (VersionedDict, VersionedList)):
            is_root = owner is tracer
            # Root ownership is represented by the flag, never by the visitor.
            parent = owner if not is_root and isinstance(owner, FactStructure) else None
            versioned_edges.append((value, is_root, parent))
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
            pending.extend([(child, owner) for child in value.keys() if type(child) not in _ATOMIC_TYPES])
            pending.extend([(child, owner) for child in value.values() if type(child) not in _ATOMIC_TYPES])
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend([(child, owner) for child in value if type(child) not in _ATOMIC_TYPES])
        elif hasattr(value, '__dict__') and not isinstance(value, type):
            child_owner = value if isinstance(value, FactStructure) else owner
            pending.extend([(child, child_owner) for child in value.__dict__.values()
                            if type(child) not in _ATOMIC_TYPES])
    return tuple(fact_structures), tuple(fact_edges), tuple(versioned_edges)


## Remove observers from a pristine cache copy before it is retained.
## 保留干净缓存副本前移除其中的观察者回调。
#
#  @param structures Copied fact structures whose listeners must be cleared.
#  @param versioned_edges Copied containers whose callbacks must be cleared.
#  @return None.
def _detach_fact_callbacks(structures, versioned_edges):
    for structure in structures:
        structure._listeners = []
    for container, _, _ in versioned_edges:
        container._changed = None
        container._adopt = None


## Restore callbacks so one clone observes only its own fact graph.
## 恢复回调，使每个克隆只观察自身事实图。
#
#  @param root Fresh visitor that owns root facts.
#  @param structures Cloned fact structures receiving local listeners.
#  @param fact_edges Parent-child fact relationships to restore.
#  @param versioned_edges Versioned containers and their recorded owners.
#  @return None.
def _reattach_fact_callbacks(root, structures, fact_edges, versioned_edges):
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
