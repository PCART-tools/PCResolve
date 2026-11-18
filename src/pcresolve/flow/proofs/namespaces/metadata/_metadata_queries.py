## @package pcresolve.flow.proofs.namespaces.metadata._metadata_queries
#  Analyze callable metadata queries.
#
#
#  Conditional source effects for scalar queries of native callable metadata.
#  分析原生可调用对象元数据标量查询产生的条件源码效果。



import ast
import copy
from dataclasses import asdict, dataclass

from pcresolve.flow.proofs.callables._function_factory import _canonical
from pcresolve.flow.proofs.namespaces.metadata._metadata_creation import static_cache
from pcresolve.flow.proofs.namespaces.metadata._metadata_namespace import namespace, builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.scope_facts import statement_scope_facts


## Signal that metadata-query analysis reached an unsupported or open operation.
## 表示元数据查询分析遇到不支持或开放式操作。
class _OpenQuery(ValueError):
    pass


## Store a bounded abstract value used by scalar metadata analysis.
## 保存标量元数据分析使用的有界抽象值。
@dataclass(frozen=True)
class _Value:
    kind: str
    shapes: frozenset = frozenset()
    literal: object = None
    known: bool = False


## Construct an abstract scalar with optional known literal content.
## 构造可选带有已知字面量内容的抽象标量。
#
#  @param shapes Possible scalar type names.
#  @param literal Concrete literal value when known.
#  @param known Whether literal contains a proven concrete value.
#  @return Immutable scalar abstract value.
def _scalar(shapes, literal=None, known=False):
    return _Value('scalar', frozenset(shapes), literal, known)


## Capture source coordinates for metadata-query evidence.
## 记录元数据查询证据的源码坐标。
#
#  @param ref Source definition reference.
#  @param node AST node whose location is recorded.
#  @return Mapping with file path and source coordinates.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Analyze a metadata query using restricted scalar and callable abstractions.
## 使用受限的标量与可调用对象抽象分析元数据查询。
class _Query:
    ## Initialize query-local facts and conservative analysis budgets.
    ## 初始化查询局部事实与保守分析预算。
    #
    #  @param self Query proof state.
    #  @param analyzer Source analyzer providing definitions and budgets.
    #  @param target Exact source definition under analysis.
    #  @return None.
    def __init__(self, analyzer, target):
        self.analyzer, self.target = analyzer, target
        self.protocols, self.calls, self.inspect_names = set(), [], set()
        self.remaining, self.paths = 4000, 0

    ## Consume query and shared class-effect budgets.
    ## 消耗查询局部与共享类效果预算。
    #
    #  @param self Query proof state.
    #  @return None; raises _OpenQuery when a budget is exhausted.
    def charge(self):
        self.remaining -= 1
        self.analyzer._class_effect_fact_steps -= 1
        if self.remaining < 0 or self.analyzer._class_effect_fact_steps < 0:
            raise _OpenQuery()
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()

    ## Interpret a supported expression without executing user callbacks.
    ## 在不执行用户回调的前提下解释受支持的表达式。
    #
    #  @param self Query proof state collecting protocol evidence.
    #  @param node Expression to interpret.
    #  @param env Current abstract local environment.
    #  @return Abstract scalar, signature, parameter collection, or callable value.
    def expression(self, node, env):
        self.charge()
        if node is None:
            return _scalar({'NoneType'}, None, True)
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool, float, type(None)):
            return _scalar({type(node.value).__name__}, node.value, True)
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.Attribute):
            value = self.expression(node.value, env)
            if value.kind == 'signature' and node.attr == 'parameters':
                return _Value('parameters')
            raise _OpenQuery()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = self.expression(node.operand, env)
            if value.kind == 'scalar':
                return _scalar({'bool'}, not bool(value.literal), True) if value.known else _scalar({'bool'})
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = self.expression(node.left, env)
            right = self.expression(node.comparators[0], env)
            operation = node.ops[0]
            if isinstance(operation, (ast.Is, ast.IsNot)) and right.known and right.literal is None:
                if left.known or 'NoneType' not in left.shapes:
                    equal = left.known and left.literal is None
                    return _scalar({'bool'}, equal == isinstance(operation, ast.Is), True)
                return _scalar({'bool'})
            if (left.kind == right.kind == 'scalar'
                    and isinstance(operation, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE))):
                return _scalar({'bool'})
        if isinstance(node, ast.Call):
            ref, function = self.target
            canonical = _canonical(self.analyzer, ref, function, node.func)
            # Only recognized inspect entry points over a proven callable qualify.
            #  仅识别针对已证明可调用对象的 inspect 入口。
            if (canonical in ('inspect.getdoc', 'inspect.signature') and len(node.args) == 1
                    and not node.keywords and self.expression(node.args[0], env).kind == 'callable'):
                name = canonical.rsplit('.', 1)[1]
                self.inspect_names.add(name)
                self.protocols.add('native_documentation_resolution_without_user_callbacks'
                                   if name == 'getdoc' else 'native_signature_resolution_without_user_callbacks')
                self.calls.append({'protocol': canonical, 'evidence': _span(ref, node)})
                return (_scalar({'str', 'NoneType'}) if name == 'getdoc' else _Value('signature'))
            if (isinstance(node.func, ast.Name) and node.func.id == 'len'
                    and len(node.args) == 1 and not node.keywords
                    and self.analyzer._builtin_name_status(ref, function, 'len') == 'confirmed_builtin'):
                value = self.expression(node.args[0], env)
                if value.kind == 'parameters' or value.kind == 'scalar' and value.shapes == {'str'}:
                    self.calls.append({'protocol': 'native_metadata_length', 'evidence': _span(ref, node)})
                    return _scalar({'int'})
            if (isinstance(node.func, ast.Attribute) and node.func.attr == 'startswith'
                    and len(node.args) == 1 and not node.keywords
                    and isinstance(node.args[0], ast.Constant) and type(node.args[0].value) is str):
                value = self.expression(node.func.value, env)
                if value.kind == 'scalar' and value.shapes == {'str'}:
                    self.calls.append({'protocol': 'native_string_prefix', 'evidence': _span(ref, node)})
                    return _scalar({'bool'})
        raise _OpenQuery()

    ## Narrow a local scalar type along a supported None comparison branch.
    ## 根据受支持的 None 比较分支收窄局部标量类型。
    #
    #  @param self Query proof state.
    #  @param test Branch condition being refined.
    #  @param env Incoming abstract local environment.
    #  @param selected Whether the tested branch is selected.
    #  @return Refined environment, or None when the branch is impossible.
    def refine(self, test, env, selected):
        local = dict(env)
        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                and isinstance(test.left, ast.Name) and test.left.id in local
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None):
            value = local[test.left.id]
            if value.kind == 'scalar':
                is_none = selected == isinstance(test.ops[0], ast.Is)
                shapes = value.shapes & {'NoneType'} if is_none else value.shapes - {'NoneType'}
                if not shapes:
                    return None
                local[test.left.id] = _scalar(shapes, None, is_none)
        return local

    ## Analyze a bounded block and collect its normal return values.
    ## 分析有界语句块并收集其正常返回值。
    #
    #  @param self Query proof state tracking explored paths.
    #  @param statements Ordered statements in the current block.
    #  @param env Mutable abstract local environment.
    #  @param depth Current nested-block depth.
    #  @return Abstract values returned on normally completing paths.
    def block(self, statements, env, depth=0):
        if depth > 32:
            raise _OpenQuery()
        for index, node in enumerate(statements):
            self.charge()
            if isinstance(node, ast.Return):
                return [self.expression(node.value, env)]
            if isinstance(node, ast.Pass) or (isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant) and type(node.value.value) is str):
                continue
            if isinstance(node, ast.Assign):
                if not node.targets or any(not isinstance(target, ast.Name) for target in node.targets):
                    raise _OpenQuery()
                value = self.expression(node.value, env)
                env.update((target.id, value) for target in node.targets)
                continue
            if isinstance(node, ast.If):
                test = self.expression(node.test, env)
                if test.kind != 'scalar':
                    raise _OpenQuery()
                # Unknown conditions retain both paths; budget each explored path.
                # 条件未知时保留两条路径，并为每条路径计入预算。
                choices = [bool(test.literal)] if test.known else [True, False]
                result = []
                for selected in choices:
                    local = self.refine(node.test, env, selected)
                    if local is not None:
                        self.paths += 1
                        if self.paths > 32:
                            raise _OpenQuery()
                        branch = node.body if selected else node.orelse
                        result.extend(self.block(branch + statements[index + 1:], local, depth + 1))
                return result
            raise _OpenQuery()
        return [_scalar({'NoneType'}, None, True)]


## Summarize scalar source queries without granting arbitrary inputs native protocols.
## 汇总标量源码查询，但不把原生协议能力赋予任意输入。
#
#  @param analyzer Fixed source snapshot and query-local resource budget.
#  @param target Exact source definition; binding at an actual call is separate.
#  @return Conditional effect template, or None for open effects or unsupported syntax.
## Return a cached metadata-query summary for an exact source definition.
## 返回指定源码定义的缓存元数据查询摘要。
#
#  @param analyzer Source analyzer with query cache and snapshots.
#  @param target Exact source definition to summarize.
#  @return Deep-copied query effect template, or None when unsupported.
def metadata_query(analyzer, target):
    cache = analyzer._metadata_query_cache
    key = target[0], id(target[1])
    if key not in cache:
        cache[key] = None
        cache[key] = _metadata_query(analyzer, target)
    return copy.deepcopy(cache[key])


## Build a conservative metadata-query summary from supported source syntax.
## 根据受支持的源码语法构建保守的元数据查询摘要。
#
#  @param analyzer Source analyzer providing namespace and definition facts.
#  @param target Exact source definition to inspect.
#  @return Conditional effect template, or None when proof is incomplete.
def _metadata_query(analyzer, target):
    ref, function = target
    if not isinstance(function, ast.FunctionDef):
        return None
    args = function.args
    parameters = args.posonlyargs + args.args
    if (len(parameters) != 1 or args.defaults or args.kwonlyargs or args.vararg or args.kwarg
            or analyzer._scope_facts(function).globals or analyzer._scope_facts(function).nonlocals):
        return None
    # Most source functions are not metadata queries. Keep this optional summary
    # off their normal effect path and do not turn failed templates into boundaries.
    # 大多数源码函数并非元数据查询；失败的可选摘要不应成为常规效果边界。
    candidate = False
    count = 0
    for node in ast.walk(function):
        count += 1
        if count > 2000:
            return None
        if isinstance(node, ast.Call) and _canonical(analyzer, ref, function, node.func) in (
                'inspect.signature', 'inspect.getdoc'):
            candidate = True
    if not candidate:
        return None
    construction = None
    if function.decorator_list:
        owner_name = ref.qualname.rpartition('.')[0]
        owners = analyzer._definition_index.find(ref.module, owner_name, kind='class')
        if len(owners) != 1 or function not in owners[0][1].body:
            return None
        shadowed = set()
        for member in owners[0][1].body:
            if member is function:
                break
            shadowed.update(statement_scope_facts([member]).bound)
        construction = static_cache(analyzer, owners[0][0], function, shadowed)
        if construction is None:
            return None
    proof = _Query(analyzer, target)
    try:
        values = proof.block(function.body, {parameters[0].arg: _Value('callable')})
        if (not values or any(value.kind != 'scalar' for value in values)
                or not proof.inspect_names):
            return None
        paths = namespace(analyzer, 'inspect', proof.inspect_names)
        if paths is None:
            return None
        stable, builtin_paths = builtin_namespace(analyzer, ref)
        if not stable:
            return None
    except (_OpenQuery, _ClassEffectLimit):
        return None
    assumptions = ['source_snapshot_bindings_hold', 'standard_library_callable_metadata_protocols',
        'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
        'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_module_mutation',
        'no_unmodeled_indirect_function_mutation']
    if construction:
        assumptions.extend(construction['assumptions'])
        proof.protocols.add('native_callable_hash_equality_without_user_callbacks')
    result = {'kind': 'source_callable_metadata_query', 'status': 'requires_native_callable_metadata',
        'target': asdict(ref), 'completion': 'normal_return_only',
        'effect_scope': 'synchronous_query_only', 'runtime_execution_confirmed': False,
        'input_preconditions': {'parameter': parameters[0].arg,
            'kind': 'native_python_function_or_method', 'protocols': sorted(proof.protocols)},
        'input_effects': {'source_writes': [], 'source_exposures': [],
                          'native_cache_retention': construction is not None},
        'result_shapes': sorted(set().union(*(value.shapes for value in values))),
        'protocol_calls': proof.calls, 'definition_evidence': _span(ref, function),
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(set(paths) | set(builtin_paths))},
        'assumptions': sorted(set(assumptions))}
    if construction:
        result['construction'] = construction
    return result
