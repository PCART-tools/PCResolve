## @package pcresolve.ownership.mapping_facts
#  Private literal-mapping facts for local callback edges, not owner sources.
#  为本地回调边记录私有字面量映射事实，不用于判定所有者来源。

import ast
from dataclasses import dataclass, field

from pcresolve.ownership.call_graph import FunctionId
from pcresolve.facts.effect_facts import container_method_effect
from pcresolve.facts.scope_facts import MAPPING_SCOPE, statement_scope_facts


## Collect names bound in one lexical body, excluding nested namespaces.
## 收集单个词法代码块中绑定的名称，并排除嵌套命名空间。
#
#  @param statements Body statements.
#  @return Locally assigned names, excluding global/nonlocal declarations.
def bound_names(statements):
    return set(statement_scope_facts(statements, MAPPING_SCOPE).bound)


## Track whether a captured callable identity remains valid.
## 跟踪捕获的可调用对象身份是否仍然有效。
@dataclass(eq=False)
class _Origin:
    valid: bool = True


## Store literal mapping entries and the validity of their key facts.
## 保存字面量映射项及其键事实的有效状态。
@dataclass(eq=False)
class _Table(_Origin):
    entries: dict = field(default_factory=dict)
    key_kind: str = ""
    keys_valid: bool = True


## A captured value and the mutable-object evidence supporting its identity.
## 表示捕获值及支撑其身份的可变对象证据。
@dataclass(frozen=True)
class MappingValue:
    values: tuple
    origins: tuple = ()
    selected: bool = False

    ## Return exact local targets and whether every alternative is known.
    ## 返回精确的本地目标，并说明所有候选是否均已知。
    #
    #  @return (FunctionId tuple, complete flag).
    def targets(self):
        if not all(origin.valid for origin in self.origins):
            return (), False
        targets = tuple(dict.fromkeys(
            value for value in self.values if isinstance(value, FunctionId)))
        return targets, bool(self.values) and all(
            isinstance(value, FunctionId) for value in self.values)


## Scope-aware literal mapping evaluator sharing the analyzer's bindings.
## 与分析器绑定共享状态的作用域感知字面量映射求值器。
#  Mutations or escapes invalidate shared cells, including already collected
#  call facts. This deliberately sacrifices earlier hits rather than retaining
#  stale identities in deferred function bodies or across aliases.
class MappingFacts:
    ## Initialize facts with the analyzer's lexical binding lookup.
    ## 使用分析器的词法绑定查找初始化映射事实。
    #
    #  @param lookup Callable returning a Binding or None for a name.
    #  @param lambda_identity Callable returning an inline lambda FunctionId.
    #  @param mutable_lookup Lookup retaining enclosing-scope mutation targets.
    #  @param python_shape Independent expression protocol query.
    #  @return None; lookup callbacks and literal cache are initialized.
    def __init__(self, lookup, lambda_identity, mutable_lookup, python_shape=None):
        self.lookup = lookup
        self.lambda_identity = lambda_identity
        self.mutable_lookup = mutable_lookup
        self.python_shape = python_shape or (lambda node: None)
        self.literals = {}

    ## Capture a local definition without reducing its identity to local.
    ## 捕获本地定义，同时保留其具体身份。
    #
    #  @param identity Module-qualified FunctionId.
    #  @return MappingValue with a rebind-invalidatable origin.
    def callable(self, identity):
        return MappingValue((identity,), (_Origin(),))

    ## Evaluate literals, aliases, subscripts and builtin dict.get selections.
    ## 求值字面量、别名、下标和内建 dict.get 选择。
    #
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

    ## Select mapping values for one key while retaining all mutable origins.
    ## 按给定键选择映射值，同时保留所有可变来源。
    #
    #  @param receiver Evaluated mapping receiver value.
    #  @param key Key expression used for selection.
    #  @param default Optional fallback value for absent keys.
    #  @return Selected MappingValue, or None when the receiver is unsupported.
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
    ## 使可逃逸值或已变更值可达的容器事实失效。
    #
    #  @param value Captured value.
    #  @param rebind Also invalidate the identity of the binding itself.
    #  @param invalidate_keys Whether the mutation can change key kinds.
    #  @return None; affected origins and nested tables are marked invalid.
    def invalidate(self, value, rebind=False, invalidate_keys=True):
        if value is None:
            return
        if rebind:
            for origin in value.origins:
                origin.valid = False
        seen = set()

        ## Invalidate each reachable mapping table once, including nested values.
        ## 逐个使可达映射表失效，包括嵌套值中的映射表。
        #
        #  @param current Value whose nested tables are traversed.
        #  @return None; reachable tables are marked invalid in place.
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

    ## Update a table's uniform key-kind fact from one key expression.
    ## 根据单个键表达式更新映射表统一键类型事实。
    #
    #  @param table Mapping table receiving the key.
    #  @param key Key expression to classify.
    #  @return None; mixed or unknown key kinds invalidate the fact.
    def _add_key(self, table, key):
        shape = self.python_shape(key) if key is not None else None
        if shape is None or (table.key_kind and table.key_kind != shape.kind):
            table.keys_valid = False
        elif table.keys_valid:
            table.key_kind = shape.kind

    ## Record a subscript write without confusing mapping keys and values.
    ## 记录下标写入，同时区分映射键和值。
    #
    #  @param target Assignment subscript.
    #  @return None; the target mapping is invalidated after key facts are updated.
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
    ## 返回已证明字面量映射的统一键类型。
    #
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
    ## 拒绝经不受支持的表达式形状传递的容器事实。
    #
    #  @param node Escaping expression, including aggregate arguments.
    #  @return None; every reachable mutable mapping fact is invalidated.
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
    ## 使变更接收者和逃逸调用参数对应的事实失效。
    #
    #  @param node Call AST node.
    #  @return None; mutable receiver and argument facts are invalidated as needed.
    def call(self, node):
        if isinstance(node.func, ast.Attribute):
            receiver = self.value(node.func.value)
            has_table = (receiver is not None
                         and any(isinstance(value, _Table)
                                 for value in receiver.values))
            effect = (container_method_effect(
                node.func.attr, ('dict',), len(node.args))
                if has_table else None)
            readonly = (effect is not None and effect.operation == 'get'
                        and not node.keywords)
            if readonly:
                self.escape(node.args[0])
                return
            self.escape(node.func.value)
        for argument in node.args:
            self.escape(argument)
        for keyword in node.keywords:
            self.escape(keyword.value)
