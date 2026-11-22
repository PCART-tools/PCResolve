## @package pcresolve.flow.proofs.classes._class_deferred
#  Bound declaration-time class effects.
#
#
#  Declaration-time effects of private source helpers and fresh function objects.
#  分析私有源码辅助函数与新建函数对象在声明阶段产生的效果。



import ast
import builtins
import copy
from string import Formatter

from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.facts.effect_facts import execution_nodes
from pcresolve.flow.proofs.callables._function_metadata import fresh_function_wraps
from pcresolve.flow.proofs.classes._class_function_reads import function_reads
from pcresolve.flow.proofs.classes.deferred._class_deferred_metadata import (
    store_metadata_member, update_metadata_write,
)
from pcresolve.flow.proofs.classes.deferred._class_deferred_state import merge_deferred_branch_state
from pcresolve.flow.proofs.classes.deferred._class_deferred_expression import rewrite_deferred_expression
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Check that a function has a closed declaration with supported parameters.
## 检查函数声明是否封闭且参数形态受支持。
#
#  @param node Candidate function AST node.
#  @param allow_decorators Whether the caller has separately validated decorators.
#  @return True when defaults, annotations, and return annotations are absent.
def _declaration(node, allow_decorators=False):
    args = node.args
    arguments = args.posonlyargs + args.args + args.kwonlyargs
    arguments += [arg for arg in (args.vararg, args.kwarg) if arg]
    return (isinstance(node, ast.FunctionDef) and (allow_decorators or not node.decorator_list)
            and not args.defaults and not any(value is not None for value in args.kw_defaults)
            and not any(arg.annotation is not None for arg in arguments) and node.returns is None)


## Return statements excluding an inert leading docstring expression.
## 返回移除无执行效果文档字符串后的函数体语句。
#
#  @param node Function-like AST node.
#  @return Body statements excluding string-expression docstrings.
def _body(node):
    return [statement for statement in node.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]


## Bound the declaration syntax and charge the optional run budget.
## 限制声明语法规模，并扣减可选的整次运行预算。
#
#  @param analyzer Flow analyzer owning the current run budget.
#  @param function Candidate declaration whose syntax will be inspected.
#  @return True when the function fits the local bound; otherwise False.
def _within_function_budget(analyzer, function):
    inspected = 0
    for _ in ast.walk(function):
        inspected += 1
        if inspected > 2000:
            return False
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
    return True


## Mutable state owned by one deferred-class proof attempt.
## 一次延后类证明尝试独占的可变状态。
class _DeferredClassProofState:
    ## Initialize one proof attempt with optional pre-supplied mutable state.
    ## 使用可选的外部可变状态初始化一次证明尝试。
    #
    #  @param declarations Evidence for deferred function declarations.
    #  @param invocations Evidence for factory invocations.
    #  @param stores Evidence for stores into the protected class namespace.
    #  @param metadata_writes Evidence for fresh function metadata writes.
    #  @param generated_members Records of members generated for the class.
    #  @param published_tokens Tokens already published for generated members.
    #  @param token_nodes Generated function nodes keyed by their token.
    #  @param class_write_sites Evidence for direct class-namespace writes.
    #  @param expression_helper_calls Evidence for inlined helper calls.
    #  @param expression_budget Remaining bounded expression rewrite budget.
    #  @param namespace_queries Native namespace read premises collected so far.
    #  @param namespace_guard Cached builtin-namespace stability result.
    #  @param exception_branches Evidence for native exception branches.
    #  @param module_native Cached module `__name__` stability result.
    #  @param class_aliases Names currently bound to the protected class.
    #  @param dirty_class_names Class attributes written during the proof.
    #  @return None
    def __init__(self, declarations=None, invocations=None, stores=None,
                 metadata_writes=None, generated_members=None, published_tokens=None,
                 token_nodes=None, class_write_sites=None, expression_helper_calls=None,
                 expression_budget=2000, namespace_queries=None, namespace_guard=None,
                 exception_branches=None, module_native=None, class_aliases=None,
                 dirty_class_names=None):
        self.declarations = list() if declarations is None else declarations
        self.invocations = list() if invocations is None else invocations
        self.stores = list() if stores is None else stores
        self.metadata_writes = list() if metadata_writes is None else metadata_writes
        self.generated_members = list() if generated_members is None else generated_members
        self.published_tokens = set() if published_tokens is None else published_tokens
        self.token_nodes = dict() if token_nodes is None else token_nodes
        self.class_write_sites = list() if class_write_sites is None else class_write_sites
        self.expression_helper_calls = list() if expression_helper_calls is None else expression_helper_calls
        self.expression_budget = expression_budget
        self.namespace_queries = list() if namespace_queries is None else namespace_queries
        self.namespace_guard = namespace_guard
        self.exception_branches = list() if exception_branches is None else exception_branches
        self.module_native = module_native
        self.class_aliases = set() if class_aliases is None else class_aliases
        self.dirty_class_names = set() if dirty_class_names is None else dirty_class_names


## Isolate fresh function-object construction from arbitrary future method bodies.
## 将新建函数对象构造与后续任意方法体效果隔离。
#
#  @param analyzer Fixed source snapshot and optional analysis budget.
#  @param target Source class-decorator function pair, possibly literal-specialized.
#  @param parameter Protected class parameter; other namespaces remain unproved.
#  @param class_target Optional exact class declaration for independent function reads.
#  @param decorations Inner class decorations already proved at this source prefix.
#  @return Effect-only source and supporting facts, or None for open helper effects.
def prepare(analyzer, target, parameter, class_target=None, decorations=()):
    ref, function = target
    if not _within_function_budget(analyzer, function):
        return None
    proof = _DeferredClassProofState(class_aliases={parameter})
    read_function = function_reads(analyzer, class_target, decorations)
    ## Capture a source location for deferred-effect evidence.
    ## 记录延后效果证据对应的源码位置。
    #
    #  @param node AST node whose source coordinates are recorded.
    #  @return File path and source-coordinate mapping.
    def span(node):
        return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
                'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}

    ## Replace a fresh function expression with a marker that carries no invariant.
    ## 将新建函数表达式替换为不携带值不变量的标记。
    #
    #  @param node Original expression whose source location is retained.
    #  @return Synthetic AST name at the original source location.
    def placeholder(node):
        # This effect-only marker must not acquire a literal-value invariant:
        # a stored closure can mutate the protected class when called later.
        # The synthetic name is deliberately outside Python source identifiers.
        return ast.copy_location(ast.Name(id='$deferred_class_function', ctx=ast.Load()), node)

    ## Check whether a local name refers to a fresh helper or function.
    ## 检查局部名称是否指向新建辅助函数或函数对象。
    #
    #  @param state Current helper/function binding state.
    #  @param name Local name to query.
    #  @return True when the binding is a supported fresh value.
    def fresh(state, name):
        return name in state and state[name][0] in ('helper', 'fresh')

    ## Build metadata-formation evidence for a fresh function object.
    ## 为新建函数对象构建元数据形成证据。
    #
    #  @param node Fresh function AST node.
    #  @param wrappers Validated metadata wrapper premises.
    #  @param call Factory invocation producing the function.
    #  @return Metadata formation fact, or None when module metadata is unstable.
    def formation(node, wrappers, call):
        if proof.module_native is None:
            bindings = analyzer.import_binding_facts.get(ref.module, [])
            proof.module_native = (len(bindings) == 1 and not bindings[0].get('__name__')
                                   and unmodified(analyzer, ref.module + '.__name__'))
        if not proof.module_native:
            return None
        shapes = {'documentation': ['NoneType' if ast.get_docstring(node, clean=False) is None else 'str'],
                  'module': ['str'], 'name': ['str'], 'qualname': ['str'],
                  'code': 'native_python_code', 'signature': 'native_source_function_signature'}
        for wrapper in wrappers:
            wrapped = wrapper.get('wrapped_lookup', {}).get('metadata_formation')
            if wrapped is None:
                return None
            for field in ('documentation', 'module', 'name', 'qualname'):
                shapes[field] = copy.deepcopy(wrapped['metadata_shapes'][field])
        return {'kind': 'source_generated_function_metadata_creation', 'status': 'source_bound',
            'phase': 'before_class_store', 'result_kind': 'native_python_function',
            'metadata_shapes': shapes, 'current_namespace_binding_confirmed': False,
            'runtime_function_binding_confirmed': False, 'future_method_effects': 'unmodeled',
            'completion': 'normal_return_only', 'factory_call_evidence': span(call),
            'function_evidence': span(node), 'metadata_wrappers': copy.deepcopy(wrappers),
            'metadata_writes': [],
            'source_hashes': dict(sorted({**analyzer.hashes, **analyzer._supporting_source_hashes}.items())),
            'assumptions': sorted(set(['source_snapshot_bindings_hold',
                'builtin_function_creation_and_metadata', 'standard_source_module_name_binding',
                'no_unmodeled_indirect_module_mutation', 'no_external_monkeypatch_or_import_hook',
                'no_external_frame_introspection']
                + [item for wrapper in wrappers for item in wrapper['assumptions']]))}

    ## Cache whether relevant builtin namespace bindings remain stable.
    ## 缓存相关内建命名空间绑定是否稳定的结论。
    #
    #  @return True when namespace operations are proven to use builtins.
    def native_namespace():
        if proof.namespace_guard is None:
            try:
                proof.namespace_guard = _stable_builtin_namespace(
                    analyzer, ref, ('vars', 'getattr', 'type', '__build_class__'))[0]
            except _ClassEffectLimit:
                proof.namespace_guard = False
        return proof.namespace_guard

    ## Charge the bounded expansion budget for one helper inline.
    ## 扣减一次辅助函数内联所需的有界展开预算。
    #
    #  @param helper Helper function whose AST nodes are charged to both budgets.
    #  @return None; raises ValueError when either remaining budget turns negative.
    def consume_helper_budget(helper):
        count = sum(1 for _ in ast.walk(helper))
        proof.expression_budget -= count
        analyzer._class_effect_fact_steps -= count
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
        if proof.expression_budget < 0 or analyzer._class_effect_fact_steps < 0:
            raise ValueError()

    ## Rewrite one expression and merge its local evidence into this proof.
    ## 改写单个表达式，并将该次改写证据并入本次证明。
    #
    #  @param node Expression to rewrite; None is returned unchanged.
    #  @param state Current helper/function binding state.
    #  @param values Known local string values.
    #  @return Rewritten expression, or None when the input is None.
    def expression(node, state, values=None):
        if node is None:
            return None
        rewritten, namespace_queries, helper_calls = rewrite_deferred_expression(
            node, state, values or {}, parameter,
            string_value=string,
            source_span=span,
            builtin_name_status=lambda name: analyzer._builtin_name_status(ref, function, name)
                == 'confirmed_builtin',
            native_namespace=native_namespace,
            namespace_read=lambda absent=None: (
                read_function.namespace(proof.dirty_class_names)
                if absent is None else read_function.namespace(
                    proof.dirty_class_names, absent=absent)),
            consume_helper_budget=consume_helper_budget)
        proof.namespace_queries.extend(namespace_queries)
        proof.expression_helper_calls.extend(helper_calls)
        return rewritten

    ## Evaluate a bounded string expression from known values and literals.
    ## 根据已知值和字面量求值有界字符串表达式。
    #
    #  @param node Candidate string expression.
    #  @param values Known local string values.
    #  @return String value within the limit, or None when unresolved.
    def string(node, values):
        if isinstance(node, ast.Name):
            return values.get(node.id)
        if isinstance(node, ast.Constant) and type(node.value) is str and len(node.value) <= 2000:
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = string(node.left, values), string(node.right, values)
            if left is not None and right is not None and len(left) + len(right) <= 2000:
                return left + right
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'format' and not node.keywords and len(node.args) <= 64):
            template = string(node.func.value, values)
            arguments = [string(value, values) for value in node.args]
            if template is None or any(value is None for value in arguments):
                return None
            pieces, position, length = [], 0, 0
            try:
                for literal, field, spec, conversion in Formatter().parse(template):
                    if field is not None:
                        if field != '' or spec or conversion or position >= len(arguments):
                            return None
                        literal += arguments[position]
                        position += 1
                    length += len(literal)
                    if length > 2000:
                        return None
                    pieces.append(literal)
            except ValueError:
                return None
            return ''.join(pieces)
        return None

    ## Record direct class-namespace writes in the current statement inputs.
    ## 记录当前语句输入中对类命名空间的直接写入。
    #
    #  @param statement Source statement being analyzed.
    #  @param values Known local string values.
    #  @return None; updates dirty attributes and write evidence in place.
    def writes(statement, values):
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Name):
            if statement.value.id in proof.class_aliases:
                proof.class_aliases.update(node.id for node in statement.targets
                                           if isinstance(node, ast.Name))
        # Inspect this statement's evaluated inputs, not later statements in an
        # if branch or deferred helper bodies. Each reached statement is visited
        # in order, after the finite-loop specializer has bound its local names.
        inputs = [child for child in ast.iter_child_nodes(statement) if isinstance(child, ast.expr)]
        for node in (node for value in inputs for node in execution_nodes(ast.Expr(value=value))):
            if (isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.value, ast.Name)
                    and node.value.id in proof.class_aliases):
                proof.dirty_class_names.add(node.attr)
                proof.class_write_sites.append({'attribute': node.attr,
                                                'statement_evidence': span(statement)})
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('setattr', 'delattr') and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in proof.class_aliases):
                name = string(node.args[1], values) or '*'
                proof.dirty_class_names.add(name)
                proof.class_write_sites.append({'attribute': name,
                                                'statement_evidence': span(statement)})

    ## Recognize a helper call that constructs and returns a fresh inner function.
    ## 识别会构造并返回新建内层函数的辅助函数调用。
    #
    #  @param call Factory helper invocation.
    #  @param state Current helper/function binding state.
    #  @param values Known local string values.
    #  @return Fresh function binding and argument-evaluation statements, or None.
    def created(call, state, values):
        if not isinstance(call.func, ast.Name) or not fresh(state, call.func.id):
            return None
        kind, factory = state[call.func.id][:2]
        if kind != 'helper' or not _declaration(factory):
            raise ValueError()
        body = _body(factory)
        if len(body) == 1 and isinstance(body[0], ast.Return):
            return None
        if (len(body) != 2 or not isinstance(body[0], ast.FunctionDef)
                or not _declaration(body[0], allow_decorators=True)
                or not isinstance(body[1], ast.Return) or not isinstance(body[1].value, ast.Name)
                or body[1].value.id != body[0].name or factory.args.vararg or factory.args.kwarg
                or any(isinstance(arg, ast.Starred) for arg in call.args)
                or any(kw.arg is None for kw in call.keywords)):
            raise ValueError()
        records, reasons = bind_ast_call(call, FunctionSignature.from_ast(factory.args))
        if reasons or any(record.get('status') != 'exact' for record in records):
            raise ValueError()
        arguments = [expression(arg, state, values) for arg in call.args]
        arguments += [expression(kw.value, state, values) for kw in call.keywords]
        bound = {record['parameter']: string(record['node'], values) for record in records}

        ## Prove a deferred getter reads one stable native class attribute.
        ## 证明延后 getter 读取一个稳定的原生类属性。
        #
        #  @param node Candidate getter expression.
        #  @return Class-read premise, or None when the read is not proven.
        def class_read(node):
            if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                    or node.func.id != 'getattr' or len(node.args) != 2 or node.keywords
                    or not isinstance(node.args[0], ast.Name) or node.args[0].id != parameter
                    or node.args[0].id in analyzer._scope_facts(factory).bound
                    or analyzer._builtin_name_status(ref, function, 'getattr') != 'confirmed_builtin'
                    or 'getattr' in analyzer._scope_facts(factory).bound):
                return None
            # Only exact native string arguments of this particular factory
            # call may specialize its deferred getter name.
            name = string(node.args[1], bound)
            premise = read_function(name, node, proof.dirty_class_names)
            if premise is not None:
                premise['lookup_evidence'] = span(node)
            return premise

        wrappers = []
        for decorator in body[0].decorator_list:
            premise = fresh_function_wraps(analyzer, ref, (function, factory), decorator,
                                            lambda name: fresh(state, name), class_read)
            if premise is None:
                raise ValueError()
            wrappers.append(premise)
        invocation = {'call_evidence': span(call), 'factory_evidence': span(factory),
                            'function_evidence': span(body[0]),
                            'completion': 'fresh_function_return_only'}
        if wrappers:
            invocation['metadata_wrappers'] = wrappers
        proof.invocations.append(invocation)
        payload = {'token': len(proof.invocations),
                   'formation': formation(body[0], wrappers, call)}
        proof.token_nodes[payload['token']] = body[0]
        return ('fresh', body[0], payload), [ast.copy_location(ast.Expr(value=value), call)
                                  for value in arguments]

    ## Interpret declaration-time statements and preserve bounded branch paths.
    ## 解释声明阶段语句并保留有界分支路径。
    #
    #  @param body Ordered statements to interpret.
    #  @param state Mutable helper/function bindings.
    #  @param values Mutable known literal values.
    #  @param depth Current nested-branch depth.
    #  @return Rewritten statements; raises ValueError when effects are open.
    def block(body, state, values, depth=0):
        if depth > 32:
            raise ValueError()
        output = []
        for statement in body:
            writes(statement, values)
            if isinstance(statement, ast.FunctionDef):
                if not _declaration(statement):
                    raise ValueError()
                proof.declarations.append(span(statement))
                state[statement.name] = ('helper', statement)
                values.pop(statement.name, None)
                output.append(ast.copy_location(ast.Assign(
                    targets=[ast.copy_location(ast.Name(id=statement.name, ctx=ast.Store()), statement)],
                    value=placeholder(statement)), statement))
            elif isinstance(statement, ast.If):
                branch = copy.copy(statement)
                branch.test = expression(statement.test, state, values)
                left, right = dict(state), dict(state)
                left_values, right_values = dict(values), dict(values)
                branch.body = block(statement.body, left, left_values, depth + 1)
                branch.orelse = block(statement.orelse, right, right_values, depth + 1)
                merge_deferred_branch_state(state, values, left, right,
                                            left_values, right_values)
                output.append(branch)
            elif isinstance(statement, ast.Raise):
                call = statement.exc
                if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                        or any(isinstance(value, ast.Starred) for value in call.args)
                        or any(item.arg is None for item in call.keywords)
                        or statement.cause is not None and not (
                            isinstance(statement.cause, ast.Constant) and statement.cause.value is None)):
                    raise ValueError()
                name = call.func.id
                exception = getattr(builtins, name, None)
                if (not isinstance(exception, type) or not issubclass(exception, BaseException)
                        or analyzer._builtin_name_status(ref, function, name) != 'confirmed_builtin'):
                    raise ValueError()
                try:
                    stable, _ = _stable_builtin_namespace(analyzer, ref, (name,))
                except _ClassEffectLimit:
                    stable = False
                if not stable:
                    raise ValueError()
                value = expression(call, state, values)
                # Bound effects on every branch; this overapproximates the
                # continuation after a terminating native raise. It does not
                # establish normal completion or suppress the source exception.
                # 每条分支都纳入效果上界；这不证明正常完成，也不会抑制源码异常。
                output.append(ast.copy_location(ast.Expr(value=value), statement))
                proof.exception_branches.append({'exception': name, 'evidence': span(statement),
                    'completion': 'source_exceptional_exit', 'runtime_exception_confirmed': False})
            elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                destination, value = statement.targets[0], statement.value
                result, before = None, []
                if isinstance(value, ast.Name) and fresh(state, value.id):
                    result = state[value.id]
                elif isinstance(value, ast.Call):
                    constructed = created(value, state, values)
                    if constructed is not None:
                        result, before = constructed
                if result is not None:
                    replacement = copy.copy(statement)
                    replacement.value = placeholder(value)
                    if isinstance(destination, ast.Name):
                        state[destination.id] = result
                        values.pop(destination.id, None)
                    elif (isinstance(destination, ast.Attribute)
                            and isinstance(destination.value, ast.Name)
                            and destination.value.id == parameter):
                        proof.stores.append(span(statement))
                        if isinstance(value, ast.Name):
                            store_metadata_member(destination.attr, value.id, state, statement,
                                                  proof.generated_members, proof.published_tokens, span)
                    else:
                        raise ValueError()
                    output.extend(before + [replacement])
                elif (isinstance(destination, ast.Attribute) and isinstance(destination.value, ast.Name)
                        and destination.value.id in state):
                    if not fresh(state, destination.value.id) or destination.attr not in (
                            '__doc__', '__name__', '__qualname__'):
                        raise ValueError()
                    evaluated = expression(value, state, values)
                    update_metadata_write(destination.value.id, destination.attr, value, state, values,
                                          statement, proof.generated_members, proof.published_tokens,
                                          proof.token_nodes, span, string)
                    proof.metadata_writes.append(span(statement))
                    output.append(ast.copy_location(ast.Expr(value=evaluated), statement))
                else:
                    replacement = copy.copy(statement)
                    replacement.value = expression(value, state, values)
                    if isinstance(destination, ast.Name):
                        state.pop(destination.id, None)
                        literal = string(value, values)
                        values.pop(destination.id, None)
                        if literal is not None:
                            values[destination.id] = literal
                    elif any(isinstance(node, ast.Name) and node.id in state
                             for node in ast.walk(destination)):
                        raise ValueError()
                    output.append(replacement)
            elif (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Name) and statement.value.func.id == 'setattr'
                    and len(statement.value.args) == 3 and not statement.value.keywords
                    and isinstance(statement.value.args[0], ast.Name)
                    and statement.value.args[0].id == parameter
                    and isinstance(statement.value.args[2], ast.Name)
                    and fresh(state, statement.value.args[2].id)):
                replacement = copy.deepcopy(statement)
                replacement.value.args[2] = placeholder(statement.value.args[2])
                expression(statement.value.args[1], state, values)
                proof.stores.append(span(statement))
                store_metadata_member(string(statement.value.args[1], values),
                               statement.value.args[2].id, state, statement,
                               proof.generated_members, proof.published_tokens, span)
                output.append(replacement)
            else:
                # Unknown uses of a helper/fresh function (including invocation,
                # reflection, escaping stores and unsupported control flow) do
                # not acquire a deferred-execution exemption.
                expression(statement, state, values)
                for name in statement_scope_facts([statement]).bound:
                    values.pop(name, None)
                output.append(copy.deepcopy(statement))
        return output

    try:
        body = block(function.body, {}, {})
    except (ValueError, TypeError, RecursionError):
        return None
    transformed = copy.copy(function)
    transformed.body = body
    assumptions = ['source_snapshot_bindings_hold', 'builtin_function_creation_and_metadata',
                   'builtin_type_attribute_writes', 'no_external_frame_introspection']
    for invocation in proof.invocations:
        for wrapper in invocation.get('metadata_wrappers', []):
            assumptions.extend(wrapper['assumptions'])
    hashes = dict(analyzer.hashes)
    for record in proof.generated_members:
        assumptions.extend(record['metadata_formation']['assumptions'])
        hashes.update(record['metadata_formation']['source_hashes'])
    for query in proof.namespace_queries:
        query['assumptions'] = sorted(set(query['assumptions'] + [
            'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation']))
        assumptions.extend(query['assumptions'])
        hashes.update(query['source_hashes'])
    if proof.exception_branches:
        assumptions.extend(['standard_builtin_namespace_preserved',
                            'no_unmodeled_indirect_builtin_mutation'])
    return transformed, {'kind': 'source_deferred_class_functions',
        'scope': 'class_decoration_only', 'status': 'declaration_effects_bounded',
        'runtime_bodies_executed': False, 'future_method_effects': 'unmodeled',
        'declarations': proof.declarations, 'factory_invocations': proof.invocations,
        'protected_class_stores': proof.stores,
        'fresh_function_metadata_writes': proof.metadata_writes,
        'generated_class_members': [
            {key: value for key, value in record.items() if key != '_token'}
            for record in proof.generated_members],
        'class_write_sites': proof.class_write_sites,
        'expression_helper_calls': proof.expression_helper_calls,
        'class_namespace_queries': proof.namespace_queries,
        'native_exception_branches': proof.exception_branches,
        'source_hashes': dict(sorted(hashes.items())),
        'assumptions': sorted(set(assumptions))}
