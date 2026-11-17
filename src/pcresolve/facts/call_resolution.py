## @package pcresolve.facts.call_resolution
#  Organize candidate lookup and call contexts.
#
#
#  Keeps source definitions and call-context facts independent of adapter-specific payloads.
#  组织源码定义与调用上下文事实，候选查找不解释分析适配器持有的数据。



from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


## One collected definition; repeated logical names remain separate records.
## 单个已收集定义；重复的逻辑名称保留为独立记录。
@dataclass(frozen=True)
class DefinitionRecord:
    ## Module identity chosen by the source adapter.
    module: str
    ## Lexical qualified name within the module.
    qualname: str
    ## Adapter-owned summary or (reference, AST) pair; never interpreted here.
    payload: object
    ## Definition category, independent of ownership or flow classification.
    kind: str = 'function'
    ## Complete source location when available.
    source_span: object = None

    ## Join the module and lexical name for import-backed lookup.
    ## 拼接模块名和词法名称，供基于导入的查找使用。
    #
    #  @return Qualified name; not proof of a unique or importable API.
    @property
    def qualified_name(self):
        return self.module + '.' + self.qualname


## Immutable lookup structure for one adapter's collected definition generation.
## 某次适配器定义收集结果的不可变查找结构。
#  Candidate ordering follows collection order. Payloads remain owned by the
#  adapter; their return summaries can be refined without rebuilding names.
@dataclass(frozen=True)
class DefinitionIndex:
    ## Ordered records, including duplicate names and locations.
    records: tuple
    _scoped: object = field(init=False, repr=False, compare=False)
    _qualified: object = field(init=False, repr=False, compare=False)
    _kinds: object = field(init=False, repr=False, compare=False)
    _names: object = field(init=False, repr=False, compare=False)
    _scopes: Mapping[tuple[str, str], frozenset[str]] = field(init=False, repr=False, compare=False)

    ## Build immutable indexes while retaining duplicate definition records.
    ## 构建不可变索引，同时保留重复定义记录。
    #
    #  @return None
    def __post_init__(self):
        object.__setattr__(self, 'records', tuple(self.records))
        scoped, qualified, kinds, names, scopes = {}, {}, {}, {}, {}
        for ordinal, record in enumerate(self.records):
            scoped.setdefault((record.kind, record.module, record.qualname), []).append(ordinal)
            qualified.setdefault((record.kind, record.qualified_name), []).append(ordinal)
            kinds.setdefault(record.kind, []).append(ordinal)
            names.setdefault((record.kind, record.qualname), []).append(ordinal)
            scopes.setdefault((record.kind, record.module), set()).add(record.qualname)

        for attribute, lookup in (('_scoped', scoped), ('_qualified', qualified),
                                  ('_kinds', kinds), ('_names', names)):
            object.__setattr__(self, attribute, MappingProxyType(
                {key: tuple(values) for key, values in lookup.items()}))
        object.__setattr__(self, '_scopes', MappingProxyType(
            {key: frozenset(values) for key, values in scopes.items()}))

    ## Look up an exact logical name without choosing between duplicates.
    ## 按精确逻辑名称查找，不在重复项之间擅自选择。
    #
    #  @param module Adapter's module name.
    #  @param qualname Lexical name within the module.
    #  @param kind Definition category.
    #  @return Tuple of opaque payloads in collection order.
    def find(self, module, qualname, kind='function'):
        return tuple(self.records[i].payload
                     for i in self._scoped.get((kind, module, qualname), ()))

    ## Union qualified and optional module-local candidates without duplication.
    ## 合并限定名称和可选模块内候选项，并去除重复记录。
    #
    #  @param names Iterable of fully qualified names.
    #  @param kind Definition category.
    #  @param local_module Optional module for unqualified alternatives.
    #  @param local_names Iterable of lexical alternatives within that module.
    #  @return Tuple of opaque payloads in collection order.
    def find_qualified(self, names, kind='function', local_module=None, local_names=()):
        ordinals = set()
        for name in names:
            ordinals.update(self._qualified.get((kind, name), ()))
        if local_module is not None:
            for name in local_names:
                ordinals.update(self._scoped.get((kind, local_module, name), ()))
        return tuple(self.records[i].payload for i in sorted(ordinals))

    ## Enumerate candidates for adapter-specific dispatch checks.
    ## 枚举候选定义，供适配器执行各自的分派检查。
    #
    #  @param kind Definition category.
    #  @return Tuple of definition records in collection order.
    def records_for(self, kind='function'):
        return tuple(self.records[i] for i in self._kinds.get(kind, ()))

    ## Find lexical definition scopes in a module.
    ## 查找模块内已收集定义的词法名称。
    #
    #  @param module Adapter's module name.
    #  @param kind Definition category.
    #  @return Immutable set of collected lexical names.
    def scopes(self, module, kind = 'function'):
        return self._scopes.get((kind, module), frozenset())

    ## Find modules containing an exact lexical name.
    ## 查找包含精确词法名称的模块。
    #
    #  @param qualname Lexical name, not a last-component method-name guess.
    #  @param kind Definition category.
    #  @return Ordered unique module names.
    def defining_modules(self, qualname, kind='function'):
        return tuple(dict.fromkeys(self.records[i].module
                                   for i in self._names.get((kind, qualname), ())))

    ## Resolve a function name using nearest function scopes and import aliases.
    ## 结合最近函数作用域和导入别名解析函数名称。
    #  This is the flow adapter's existing name policy. Receiver dispatch and
    #  dynamic binding checks remain the caller's responsibility; ownership
    #  uses candidate lookup with its own source/receiver policy instead.
    #
    #  @param module Calling module.
    #  @param scope Calling function's lexical qualified name.
    #  @param name Syntactic callable name.
    #  @param imports Module-to-alias lookup supplied by the adapter.
    #  @param max_alias_hops Maximum qualified candidate rounds.
    #  @param kind Definition category to resolve.
    #  @return Unique opaque payload or None for absent/ambiguous candidates.
    def resolve_name(self, module, scope, name, imports, max_alias_hops=20,
                     kind='function'):
        current = scope
        function_scopes = self.scopes(module, kind=kind)
        while current:
            if current in function_scopes:
                matches = self.find(module, current + '.' + name, kind=kind)
                if matches:
                    return matches[0] if len(matches) == 1 else None
            current = current.rpartition('.')[0]

        # An established import binding replaces local qualified candidates.
        # 已知导入绑定会替换本地限定名称候选项。
        names = [module + '.' + name]
        parent = scope.rpartition('.')[0]
        if parent:
            names.insert(0, module + '.' + parent + '.' + name)
        alias, dot, rest = name.partition('.')
        imported = imports.get(module, {}).get(alias)
        if imported:
            names = [imported + (dot + rest if dot else '')]
        return self.resolve_qualified(names, imports, max_alias_hops, kind)

    ## Continue import-backed lookup from qualified names without lexical fallback.
    ## 从限定名称继续基于导入查找，不回退到词法查找。
    #
    #  @param names Fully qualified names from established import bindings.
    #  @param imports Module-to-alias lookup supplied by the adapter.
    #  @param max_alias_hops Maximum qualified candidate rounds.
    #  @param kind Definition category to resolve.
    #  @param qualified_guard Optional adapter predicate for binding stability.
    #  @return Unique opaque payload or None for absent/ambiguous/blocked names.
    def resolve_qualified(self, names, imports, max_alias_hops=20,
                          kind='function', qualified_guard=None):
        names = list(names)
        seen = set()
        for _ in range(max_alias_hops):
            state = tuple(names)
            # Cycles, unstable bindings, ambiguity and the hop budget stay unresolved.
            # 遇到循环、不稳定绑定、歧义或跳数上限时保持未解析。
            if state in seen or (qualified_guard is not None and any(
                    not qualified_guard(name) for name in names)):
                return None
            seen.add(state)
            matches = self.find_qualified(names, kind=kind)
            if len(matches) == 1:
                return matches[0]
            if matches:
                return None
            expanded = []
            for candidate in names:
                mod, _, symbol = candidate.rpartition('.')
                value = imports.get(mod, {}).get(symbol)
                if value:
                    expanded.append(value)
            if not expanded:
                break
            names = expanded
        return None


## One internal call occurrence and its enclosing forwarding/expansion context.
## 单个内部调用及其外层转发或展开上下文。
#  Target and edge are adapter-owned facts, not a public call-graph contract.
@dataclass(frozen=True)
class CallContext:
    ## Module containing the call expression.
    caller_module: str
    ## Target reference selected by the adapter.
    target: object
    ## Exact call edge, or None for an entry context.
    edge: object
    ## Enclosing context, or None at the entry.
    parent: object = None

    ## Iterate enclosing contexts starting at this call.
    ## 从当前调用开始迭代外层上下文。
    #
    #  @return Iterator from current context to entry.
    def chain(self):
        current = self
        while current is not None:
            yield current
            current = current.parent

    ## Read ancestor targets in traversal order, excluding this target.
    ## 按从入口到直接父级的顺序读取祖先目标，不包含当前目标。
    #
    #  @return Tuple from entry to immediate parent, retaining repeated targets.
    @property
    def ancestors(self):
        if self.parent is None:
            return ()
        return tuple(reversed([context.target for context in self.parent.chain()]))

    ## Obtain the shared source-span identity without interpreting edge payloads.
    ## 获取共享源码位置标识，不解释调用边的数据。
    #
    #  @return Snapshot-local call ID, or None for an entry/unlocated edge.
    @property
    def call_id(self):
        identity = getattr(self.edge, 'id', None)
        span = getattr(self.edge, 'source_span', None)
        return identity if identity is not None else span.key if span is not None else None
