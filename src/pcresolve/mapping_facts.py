## @package pcresolve.mapping_facts
#  Private literal-mapping facts for local callback edges, not owner sources.

import ast
from dataclasses import dataclass, field

from .call_graph import FunctionId


## Collect names bound in one lexical body, excluding nested namespaces.
#  @param statements Body statements.
#  @return Locally assigned names, excluding global/nonlocal declarations.
def bound_names(statements):
    names = set()
    outer = set()

    class Collector(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                names.add(node.id)

        def visit_FunctionDef(self, node):
            names.add(node.name)

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Lambda(self, node):
            pass

        def visit_Import(self, node):
            names.update(alias.asname or alias.name.split('.')[0]
                         for alias in node.names)

        def visit_ImportFrom(self, node):
            names.update(alias.asname or alias.name for alias in node.names)

        def visit_ExceptHandler(self, node):
            if node.name:
                names.add(node.name)
            self.generic_visit(node)

        def visit_Global(self, node):
            outer.update(node.names)

        visit_Nonlocal = visit_Global

        def visit_ListComp(self, node):
            for child in ast.walk(node):
                if isinstance(child, ast.NamedExpr):
                    self.visit(child.target)

        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

    collector = Collector()
    for statement in statements:
        collector.visit(statement)
    return names - outer


@dataclass(eq=False)
class _Origin:
    valid: bool = True


@dataclass(eq=False)
class _Table(_Origin):
    entries: dict = field(default_factory=dict)
    key_kind: str = ""
    keys_valid: bool = True


## A captured value and the mutable-object evidence supporting its identity.
@dataclass(frozen=True)
class MappingValue:
    values: tuple
    origins: tuple = ()
    selected: bool = False

    ## Return exact local targets and whether every alternative is known.
    #  @return (FunctionId tuple, complete flag).
    def targets(self):
        if not all(origin.valid for origin in self.origins):
            return (), False
        targets = tuple(dict.fromkeys(
            value for value in self.values if isinstance(value, FunctionId)))
        return targets, bool(self.values) and all(
            isinstance(value, FunctionId) for value in self.values)


## Scope-aware literal mapping evaluator sharing the analyzer's bindings.
#  Mutations or escapes invalidate shared cells, including already collected
#  call facts. This deliberately sacrifices earlier hits rather than retaining
#  stale identities in deferred function bodies or across aliases.
class MappingFacts:
    ## Initialize facts with the analyzer's lexical binding lookup.
    #  @param lookup Callable returning a Binding or None for a name.
    #  @param lambda_identity Callable returning an inline lambda FunctionId.
    #  @param mutable_lookup Lookup retaining enclosing-scope mutation targets.
    #  @param python_shape Independent expression protocol query.
    def __init__(self, lookup, lambda_identity, mutable_lookup, python_shape=None):
        self.lookup = lookup
        self.lambda_identity = lambda_identity
        self.mutable_lookup = mutable_lookup
        self.python_shape = python_shape or (lambda node: None)
        self.literals = {}

    ## Capture a local definition without reducing its identity to local.
    #  @param identity Module-qualified FunctionId.
    #  @return MappingValue with a rebind-invalidatable origin.
    def callable(self, identity):
        return MappingValue((identity,), (_Origin(),))

    ## Evaluate literals, aliases, subscripts and builtin dict.get selections.
    #  @param node Expression AST node.
    #  @return MappingValue or None for an unsupported expression.
    def value(self, node):
        if isinstance(node, ast.Lambda):
            return self.callable(self.lambda_identity(node))
        if isinstance(node, ast.Name):
            binding = self.lookup(node.id)
            return getattr(binding, 'mapping_value', None)
        if isinstance(node, ast.Dict):
            if node not in self.literals:
                table = _Table()
                self.literals[node] = MappingValue((table,), (table,))
                for key, item in zip(node.keys, node.values):
                    self._add_key(table, key)
                    if not isinstance(key, ast.Constant):
                        table.valid = False
                        continue
                    try:
                        hash(key.value)
                    except TypeError:
                        table.valid = False
                        continue
                    # Python literal dictionaries keep the last duplicate key.
                    table.entries[key.value] = (
                        self.value(item) or MappingValue((None,)))
            return self.literals[node]
        if isinstance(node, ast.Subscript):
            return self._select(self.value(node.value), node.slice, None)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'get'
                and 1 <= len(node.args) <= 2 and not node.keywords):
            default = self.value(node.args[1]) if len(node.args) == 2 else None
            return self._select(self.value(node.func.value), node.args[0], default)
        return None

    def _select(self, receiver, key, default):
        if receiver is None:
            return None
        tables = [value for value in receiver.values if isinstance(value, _Table)]
        if not tables:
            return None
        selected = []
        origins = list(receiver.origins)
        for table in tables:
            origins.append(table)
            if isinstance(key, ast.Constant):
                try:
                    selected.append(table.entries.get(key.value, default))
                except TypeError:
                    selected.append(None)
            else:
                selected.extend(table.entries.values())
                selected.append(default)
        values = []
        if len(tables) != len(receiver.values):
            values.append(None)
        for choice in selected:
            if choice is None:
                values.append(None)
            else:
                values.extend(choice.values)
                origins.extend(choice.origins)
        return MappingValue(tuple(values), tuple(dict.fromkeys(origins)), True)

    ## Invalidate containers reachable through an escaping or mutated value.
    #  @param value Captured value.
    #  @param rebind Also invalidate the identity of the binding itself.
    #  @param invalidate_keys Whether the mutation can change key kinds.
    def invalidate(self, value, rebind=False, invalidate_keys=True):
        if value is None:
            return
        if rebind:
            for origin in value.origins:
                origin.valid = False
        seen = set()

        def visit(current):
            for item in current.values:
                if not isinstance(item, _Table) or id(item) in seen:
                    continue
                seen.add(id(item))
                item.valid = False
                if invalidate_keys:
                    item.keys_valid = False
                for child in item.entries.values():
                    visit(child)

        visit(value)

    def _add_key(self, table, key):
        shape = self.python_shape(key) if key is not None else None
        if shape is None or (table.key_kind and table.key_kind != shape.kind):
            table.keys_valid = False
        elif table.keys_valid:
            table.key_kind = shape.kind

    ## Record a subscript write without confusing mapping keys and values.
    #  @param target Assignment subscript.
    def write(self, target):
        value = self.value(target.value)
        if value is None:
            self.escape(target.value)
            return
        for table in value.values:
            if isinstance(table, _Table):
                self._add_key(table, target.slice)
        self.invalidate(value, invalidate_keys=False)

    ## Return the uniform key kind of a proven literal mapping.
    #  @param node Mapping expression.
    #  @return Builtin type name or None for unknown/mixed keys.
    def key_kind(self, node):
        value = self.value(node)
        if value is None or not value.values:
            return None
        kinds = []
        for table in value.values:
            if not isinstance(table, _Table) or not table.keys_valid:
                return None
            kinds.append(table.key_kind)
        return kinds[0] if kinds[0] and len(set(kinds)) == 1 else None

    ## Reject container facts passed through unsupported expression shapes.
    #  @param node Escaping expression, including aggregate arguments.
    def escape(self, node):
        if isinstance(node, ast.Name):
            self.invalidate(getattr(
                self.mutable_lookup(node.id), 'mapping_value', None))
            return
        value = self.value(node)
        if value is not None:
            self.invalidate(value)
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self.escape(child)

    ## Invalidate a mutation receiver and escaping call arguments.
    #  @param node Call AST node.
    def call(self, node):
        if isinstance(node.func, ast.Attribute):
            receiver = self.value(node.func.value)
            readonly = (node.func.attr == 'get'
                        and 1 <= len(node.args) <= 2 and not node.keywords
                        and receiver is not None
                        and any(isinstance(value, _Table)
                                for value in receiver.values))
            if readonly:
                self.escape(node.args[0])
                return
            self.escape(node.func.value)
        for argument in node.args:
            self.escape(argument)
        for keyword in node.keywords:
            self.escape(keyword.value)
