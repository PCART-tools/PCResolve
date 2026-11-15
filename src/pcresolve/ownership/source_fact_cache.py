## @package pcresolve.ownership.source_fact_cache
#  Detached ownership visitor facts, captured before any project propagation.
#  在项目级传播前捕获并隔离的归属访问器事实。

import ast
from copy import deepcopy
from dataclasses import dataclass, fields
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
## Explicit reusable facts collected by one source-file visitor.
## 单文件访问器收集并可复用的显式事实字段。
@dataclass(frozen=True)
class SingleFileVisitorFacts:
    return_sources: object
    return_element_sources: object
    call_graph_return_sources: object
    call_graph_return_values: object
    call_graph_yield_sources: object
    symbols: object
    api_calls: object
    comprehension_targets: object
    attr_accesses: object
    local: object
    defined_functions: object
    function_params: object
    _parameter_name_index: object
    parameter_sources: object
    _assigned_call_sources: object
    container_items: object
    homogeneous_container_items: object
    homogeneous_container_value_sources: object
    homogeneous_container_tuple_items: object
    container_lengths: object
    container_kinds: object
    container_item_kinds: object
    container_set_sources: object
    class_methods: object
    class_bases: object
    instance_attrs: object
    instance_attr_kinds: object
    instance_attr_item_kinds: object
    instance_attr_item_fields: object
    _constructor_kwargs_contracts: object
    _local_instance_field_sources: object
    _local_instance_field_shapes: object
    _local_instance_field_shadowed: object
    class_attr_kinds: object
    _container_item_kind_conflicts: object
    import_from_symbols: object
    wildcard_modules: object
    import_aliases: object
    _import_binding_sources: object
    call_sites: object
    call_assign_funcs: object
    _assignment_counter: object
    _global_names: object
    call_site_objects: object
    symbol_refs: object
    module_scope: object
    scope_stack: object
    module_cg: object
    _literal_values: object
    _pending_call_targets_by_node: object
    _argparse_parsers: object
    _argparse_destination_shapes: object
    _iterable_binding_sources: object
    _iterated_append_sources: object
    _iterated_append_tuple_sources: object
    _iterated_append_tuple_conflicts: object
    _attribute_append_tuple_sources: object
    _attribute_append_tuple_conflicts: object
    _subscripted_import_attribute_receivers: object
    external_method_overrides: object
    _mapping_edges: object
    _mapping_local_names: object
    _finite_namespace_stability: object
    _module_tree: object
    mapping_facts_literals: object


## Source version identity and detached ownership facts.
## 源码版本身份与分离后的归属事实。
#
#  @param module_name Import-qualified module identity.
#  @param is_package Whether the source represents a package initializer.
#  @param file_path Original source path.
#  @param visitor Declared source-derived visitor facts.
#  @param fact_structures Fact structures whose observer links are rebound per clone.
#  @param fact_edges Parent-child fact relationships.
#  @param versioned_edges Versioned-container callback relationships.
@dataclass(frozen=True)
class SingleFileFacts:
    module_name: str
    is_package: bool
    file_path: str
    visitor: SingleFileVisitorFacts
    fact_structures: tuple
    fact_edges: tuple
    versioned_edges: tuple


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

    pending = [(getattr(values, item.name), tracer)
               for item in fields(values)
               if type(getattr(values, item.name)) not in _ATOMIC_TYPES]
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
    visitor_values = {
        item.name: getattr(tracer, item.name)
        for item in fields(SingleFileVisitorFacts)
        if item.name != 'mapping_facts_literals'
    }
    visitor_values['mapping_facts_literals'] = tracer._mapping_facts.literals
    visitor = SingleFileVisitorFacts(**visitor_values)
    fact_structures, fact_edges, versioned_edges = _detach_visitor_callbacks(
        visitor, tracer, memo)
    visitor = deepcopy(visitor, memo)
    copied_structures = deepcopy(fact_structures, memo)
    copied_fact_edges = deepcopy(fact_edges, memo)
    copied_versioned_edges = deepcopy(versioned_edges, memo)
    _detach_fact_callbacks(copied_structures, copied_versioned_edges)
    if budget is not None:
        budget.checkpoint(force=True)
    return SingleFileFacts(tracer.module_name or '', tracer.is_package,
                           tracer._file_path, visitor, copied_structures,
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
    copied_visitor = deepcopy(source_facts.visitor, memo)
    copied = SingleFileAnalyzer(module_name=source_facts.module_name,
                                is_package=source_facts.is_package,
                                file_path=source_facts.file_path,
                                analysis_budget=budget)
    for item in fields(SingleFileVisitorFacts):
        if item.name != 'mapping_facts_literals':
            setattr(copied, item.name, getattr(copied_visitor, item.name))
    copied._mapping_facts.literals = copied_visitor.mapping_facts_literals
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
