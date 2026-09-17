## @package pcresolve.call_resolution
#  Internal candidate lookup and call-context facts over opaque adapter payloads.

from dataclasses import dataclass, field
from types import MappingProxyType


## One collected definition; repeated logical names remain separate records.
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
    #  @return Qualified name; not proof of a unique or importable API.
    @property
    def qualified_name(self):
        return self.module + '.' + self.qualname


## Immutable lookup structure for one adapter's collected definition generation.
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
    _scopes: object = field(init=False, repr=False, compare=False)

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
    #  @param module Adapter's module name.
    #  @param qualname Lexical name within the module.
    #  @param kind Definition category.
    #  @return Tuple of opaque payloads in collection order.
    def find(self, module, qualname, kind='function'):
        return tuple(self.records[i].payload
                     for i in self._scoped.get((kind, module, qualname), ()))

    ## Union qualified and optional module-local candidates without duplication.
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
    #  @param kind Definition category.
    #  @return Tuple of definition records in collection order.
    def records_for(self, kind='function'):
        return tuple(self.records[i] for i in self._kinds.get(kind, ()))

    ## Find lexical definition scopes in a module.
    #  @param module Adapter's module name.
    #  @param kind Definition category.
    #  @return Immutable set of collected lexical names.
    def scopes(self, module, kind='function'):
        return self._scopes.get((kind, module), frozenset())

    ## Find modules containing an exact lexical name.
    #  @param qualname Lexical name, not a last-component method-name guess.
    #  @param kind Definition category.
    #  @return Ordered unique module names.
    def defining_modules(self, qualname, kind='function'):
        return tuple(dict.fromkeys(self.records[i].module
                                   for i in self._names.get((kind, qualname), ())))

    ## Resolve a function name using nearest function scopes and import aliases.
    #  This is the flow adapter's existing name policy. Receiver dispatch and
    #  dynamic binding checks remain the caller's responsibility; ownership
    #  uses candidate lookup with its own source/receiver policy instead.
    #  @param module Calling module.
    #  @param scope Calling function's lexical qualified name.
    #  @param name Syntactic callable name.
    #  @param imports Module-to-alias lookup supplied by the adapter.
    #  @param max_alias_hops Maximum qualified candidate rounds.
    #  @return Unique opaque payload or None for absent/ambiguous candidates.
    def resolve_name(self, module, scope, name, imports, max_alias_hops=20):
        current = scope
        function_scopes = self.scopes(module)
        while current:
            if current in function_scopes:
                matches = self.find(module, current + '.' + name)
                if matches:
                    return matches[0] if len(matches) == 1 else None
            current = current.rpartition('.')[0]
        names = [module + '.' + name]
        parent = scope.rpartition('.')[0]
        if parent:
            names.insert(0, module + '.' + parent + '.' + name)
        alias, dot, rest = name.partition('.')
        imported = imports.get(module, {}).get(alias)
        if imported:
            names = [imported + (dot + rest if dot else '')]
        for _ in range(max_alias_hops):
            matches = self.find_qualified(names)
            if len(matches) == 1:
                return matches[0]
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
    #  @return Iterator from current context to entry.
    def chain(self):
        current = self
        while current is not None:
            yield current
            current = current.parent

    ## Read ancestor targets in traversal order, excluding this target.
    #  @return Tuple from entry to immediate parent, retaining repeated targets.
    @property
    def ancestors(self):
        if self.parent is None:
            return ()
        return tuple(reversed([context.target for context in self.parent.chain()]))

    ## Obtain the shared source-span identity without interpreting edge payloads.
    #  @return Snapshot-local call ID, or None for an entry/unlocated edge.
    @property
    def call_id(self):
        identity = getattr(self.edge, 'id', None)
        span = getattr(self.edge, 'source_span', None)
        return identity if identity is not None else span.key if span is not None else None
