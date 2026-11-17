## @package pcresolve.ownership.source_fact_cache
#  Capture and clone source facts.
#
#
#  Detached ownership visitor facts, captured before any project propagation.
#  在项目级传播前捕获并隔离的归属访问器事实。



from collections import namedtuple
import ast
from copy import deepcopy
from functools import partial
from types import FunctionType, MemberDescriptorType, MethodType

from pcresolve.ownership.call_graph import FunctionId
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer
from pcresolve.ownership.fact_versions import FactStructure, VersionedDict, VersionedList


## Explicit reusable facts collected by one source-file visitor.
## 单文件访问器收集并可复用的显式事实字段。
#  Only declared source facts are retained; query stacks and lookup caches are excluded.
#  仅保留显式声明的源码事实；查询栈和查找缓存不进入该记录。
class SingleFileVisitorFacts:
    # Fixed source-fact whitelist; visitor additions never enter the cache implicitly.
    __slots__ = (
        'return_sources',
        'return_element_sources',
        'call_graph_return_sources',
        'call_graph_return_values',
        'call_graph_yield_sources',
        'symbols',
        'api_calls',
        'comprehension_targets',
        'attr_accesses',
        'local',
        'defined_functions',
        'function_params',
        'parameter_sources',
        '_assigned_call_sources',
        'container_items',
        'homogeneous_container_items',
        'homogeneous_container_value_sources',
        'homogeneous_container_tuple_items',
        'container_lengths',
        'container_kinds',
        'container_item_kinds',
        'container_set_sources',
        'class_methods',
        'class_bases',
        'instance_attrs',
        'instance_attr_kinds',
        'instance_attr_item_kinds',
        'instance_attr_item_fields',
        '_constructor_kwargs_contracts',
        '_local_instance_field_sources',
        '_local_instance_field_shapes',
        '_local_instance_field_shadowed',
        'class_attr_kinds',
        '_container_item_kind_conflicts',
        'import_from_symbols',
        'wildcard_modules',
        'import_aliases',
        '_import_binding_sources',
        'call_sites',
        'call_assign_funcs',
        '_assignment_counter',
        '_global_names',
        'call_site_objects',
        'symbol_refs',
        'module_scope',
        'scope_stack',
        'module_cg',
        '_literal_values',
        '_argparse_parsers',
        '_argparse_destination_shapes',
        '_iterable_binding_sources',
        '_iterated_append_sources',
        '_iterated_append_tuple_sources',
        '_iterated_append_tuple_conflicts',
        '_attribute_append_tuple_sources',
        '_attribute_append_tuple_conflicts',
        '_subscripted_import_attribute_receivers',
        'external_method_overrides',
        '_mapping_edges',
        '_mapping_local_names',
        '_module_tree',
        'mapping_facts_literals',
    )

    def __init__(self, **values):
        if values.keys() != set(self.__slots__):
            raise TypeError('source facts must contain exactly the declared fields')
        for name in self.__slots__:
            object.__setattr__(self, name, values[name])

    def __setattr__(self, name, value):
        raise AttributeError('source fact fields cannot be reassigned')

    def __delattr__(self, name):
        raise AttributeError('source fact fields cannot be deleted')

    def __deepcopy__(self, memo):
        copied = object.__new__(type(self))
        memo[id(self)] = copied
        for name in self.__slots__:
            object.__setattr__(copied, name, deepcopy(getattr(self, name), memo))
        return copied


## Source version identity and detached ownership facts.
## 源码版本身份与分离后的归属事实。
#
#  This record contains no analyzer instance or run-local state.
#  该记录不包含分析器实例或单次运行状态。
#  @param module_name Import-qualified module identity.
#  @param is_package Whether the source represents a package initializer.
#  @param file_path Original source path.
#  @param document Exact source document whose AST identities occur in these facts.
#  @param visitor Declared source-derived visitor facts.
#  @param fact_structures Fact structures whose observer links are rebound per clone.
#  @param fact_edges Parent-child fact relationships.
#  @param versioned_edges Versioned-container callback relationships.
SingleFileFacts = namedtuple(
    'SingleFileFacts', ('module_name', 'is_package', 'file_path', 'document', 'visitor', 'fact_structures', 'fact_edges', 'versioned_edges'))


class SourceFactCacheEntry(namedtuple(
        'SourceFactCacheEntry', ('document', 'module_name', 'is_package', 'facts'))):
    __slots__ = ()

    def matches(self, document, module_name,
                is_package):
        return (self.document is document and self.module_name == module_name
                and self.is_package == is_package)


def find_source_fact_entry(cache, path,
                           document, module_name,
                           is_package):
    # Return a path and source-context match, or None on any cache miss.
    entry = cache.get(path)
    if entry is not None and entry.matches(document, module_name, is_package):
        if entry.facts.document is not document:
            raise ValueError('source facts belong to a different source document')
        if (entry.facts.file_path != path or entry.facts.module_name != module_name
                or entry.facts.is_package != is_package):
            raise ValueError('source facts have inconsistent module context')
        return entry
    return None


# Exact built-in scalar types cannot hold fact structures or bound callbacks.
# Subclasses follow the existing visitor logic, including fact-edge registration.
_ATOMIC_TYPES = frozenset((type(None), str, bytes, int, float, bool))


def _slot_values(value):
    # Member descriptors avoid executing arbitrary properties while traversing slots.
    for cls in type(value).__mro__:
        for descriptor in vars(cls).values():
            if isinstance(descriptor, MemberDescriptorType):
                try:
                    yield descriptor.__get__(value, type(value))
                except AttributeError:
                    pass


def _is_callback(value):
    # Arbitrary executable callbacks are not source facts. Known observer
    # callbacks are rebuilt from the recorded fact graph during cloning.
    return isinstance(value, (FunctionType, MethodType, partial))


def _ast_memo(document, budget):
    if not isinstance(document.tree, ast.AST):
        raise TypeError('source document must contain a parsed AST')
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
#  @param budget Optional resource budget for graph traversal.
#  @return Tuple of fact structures, fact edges and versioned-container edges.
def _detach_visitor_callbacks(
        values, tracer,
        memo, budget
        ):
    pending = [
        (getattr(values, name), tracer)
        for name in values.__slots__
        if type(getattr(values, name)) not in _ATOMIC_TYPES]
    seen = set()
    fact_structures = []
    fact_edges = []
    versioned_edges = []
    fact_structure_ids = set()
    while pending:
        if budget is not None:
            budget.checkpoint()
        value, owner = pending.pop()
        # Plain containers cannot have listeners of their own. Avoid the
        # versioned-container checks for these common traversal nodes.
        if type(value) is dict:
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            pending.extend([(child, owner) for child in value.keys() if type(child) not in _ATOMIC_TYPES])
            pending.extend([(child, owner) for child in value.values() if type(child) not in _ATOMIC_TYPES])
            continue
        children = None
        if type(value) is list:
            children = value
        elif type(value) is tuple:
            children = value
        elif type(value) is set:
            children = value
        elif type(value) is frozenset:
            children = value
        if children is not None:
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            pending.extend([(child, owner) for child in children
                            if type(child) not in _ATOMIC_TYPES])
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
            raise ValueError('source facts reference their collector')
        if value is None or id(value) in seen or isinstance(value, (str, bytes, int, float, bool, ast.AST)):
            continue
        seen.add(id(value))
        if _is_callback(value):
            memo[id(value)] = None
            continue
        if isinstance(value, dict):
            pending.extend([(child, owner) for child in value.keys() if type(child) not in _ATOMIC_TYPES])
            pending.extend([(child, owner) for child in value.values() if type(child) not in _ATOMIC_TYPES])
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend([(child, owner) for child in value if type(child) not in _ATOMIC_TYPES])
        if not isinstance(value, type):
            attributes = getattr(value, '__dict__', None)
            child_owner = value if isinstance(value, FactStructure) else owner
            if isinstance(attributes, dict):
                pending.extend([(child, child_owner) for child in attributes.values()
                                if type(child) not in _ATOMIC_TYPES])
            pending.extend((child, child_owner) for child in _slot_values(value)
                           if type(child) not in _ATOMIC_TYPES)
    return tuple(fact_structures), tuple(fact_edges), tuple(versioned_edges)


## Remove observers from a pristine cache copy before it is retained.
## 保留干净缓存副本前移除其中的观察者回调。
#
#  @param structures Copied fact structures whose listeners must be cleared.
#  @param versioned_edges Copied containers whose callbacks must be cleared.
#  @return None.
def _detach_fact_callbacks(structures,
                           versioned_edges):
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
def _reattach_fact_callbacks(root,
                             structures,
                             fact_edges,
                             versioned_edges):
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
def capture_source_facts(tracer, document,
                         budget = None):
    if tracer._module_tree is not document.tree:
        raise ValueError('visitor facts belong to a different source document')
    if budget is not None:
        budget.checkpoint(force=True)
    memo = _ast_memo(document, budget)
    if tracer._analysis_budget is not None:
        memo[id(tracer._analysis_budget)] = None
    visitor_values = {
        name: getattr(tracer, name)
        for name in SingleFileVisitorFacts.__slots__
        if name != 'mapping_facts_literals'
    }
    visitor_values['mapping_facts_literals'] = tracer._mapping_facts.literals
    visitor = SingleFileVisitorFacts(**visitor_values)
    fact_structures, fact_edges, versioned_edges = _detach_visitor_callbacks(
        visitor, tracer, memo, budget)
    visitor = deepcopy(visitor, memo)
    copied_structures = deepcopy(fact_structures, memo)
    copied_fact_edges = deepcopy(fact_edges, memo)
    copied_versioned_edges = deepcopy(versioned_edges, memo)
    _detach_fact_callbacks(copied_structures, copied_versioned_edges)
    if budget is not None:
        budget.checkpoint(force=True)
    return SingleFileFacts(tracer.module_name or '', tracer.is_package,
                           tracer._file_path, document, visitor, copied_structures,
                           copied_fact_edges, copied_versioned_edges)


## Rehydrate detached facts into a fresh, run-local AST visitor.
## 将分离的事实重新载入全新的单次运行 AST 访问器。
#
#  @param source_facts Immutable source facts captured before project propagation.
#  @param document Read-only source version owning the AST identities.
#  @param budget Optional current analysis budget.
#  @return Fresh visitor with callbacks rebound to its own state.
def clone_source_facts(source_facts, document,
                       budget = None):
    if source_facts.document is not document:
        raise ValueError('source facts belong to a different source document')
    if budget is not None:
        budget.checkpoint(force=True)
    memo = _ast_memo(document, budget)
    memo[id(source_facts)] = None
    copied_visitor = deepcopy(source_facts.visitor, memo)
    copied = SingleFileAnalyzer(module_name=source_facts.module_name,
                                           is_package=source_facts.is_package,
                                           file_path=source_facts.file_path,
                                           analysis_budget=budget)
    for name in SingleFileVisitorFacts.__slots__:
        if name != 'mapping_facts_literals':
            setattr(copied, name, getattr(copied_visitor, name))
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
