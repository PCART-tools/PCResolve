## @package pcresolve._class_deferred
#  Declaration-time effects of private source helpers and fresh function objects.

import ast
import builtins
import copy
from string import Formatter

from .program_facts import FunctionSignature, bind_ast_call
from .effect_facts import execution_nodes
from ._function_metadata import fresh_function_wraps
from ._class_function_reads import function_reads
from .scope_facts import statement_scope_facts
from ._runtime_namespace import unmodified
from ._property_namespace import _stable_builtin_namespace
from .class_attribute_effects import _ClassEffectLimit


def _declaration(node, allow_decorators=False):
    args = node.args
    arguments = args.posonlyargs + args.args + args.kwonlyargs
    arguments += [arg for arg in (args.vararg, args.kwarg) if arg]
    return (isinstance(node, ast.FunctionDef) and (allow_decorators or not node.decorator_list)
            and not args.defaults and not any(value is not None for value in args.kw_defaults)
            and not any(arg.annotation is not None for arg in arguments) and node.returns is None)


def _body(node):
    return [statement for statement in node.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]


## Isolate fresh function-object construction from arbitrary future method bodies.
#  @param analyzer Fixed source snapshot and optional analysis budget.
#  @param target Source class-decorator function pair, possibly literal-specialized.
#  @param parameter Protected class parameter; other namespaces remain unproved.
#  @param class_target Optional exact class declaration for independent function reads.
#  @param decorations Inner class decorations already proved at this source prefix.
#  @return Effect-only source and supporting facts, or None for open helper effects.
def prepare(analyzer, target, parameter, class_target=None, decorations=()):
    ref, function = target
    declarations, invocations, stores, metadata = [], [], [], []
    generated, published = [], set()
    token_nodes = {}
    write_sites = []
    expression_calls, expression_budget = [], [2000]
    namespace_queries, namespace_guard = [], [None]
    exception_branches = []
    module_native = [None]
    read_function = function_reads(analyzer, class_target, decorations)
    class_aliases, dirty = {parameter}, set()
    inspected = 0
    for _ in ast.walk(function):
        inspected += 1
        if inspected > 2000:
            return None
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()

    def span(node):
        return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
                'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}

    def placeholder(node):
        # This effect-only marker must not acquire a literal-value invariant:
        # a stored closure can mutate the protected class when called later.
        # The synthetic name is deliberately outside Python source identifiers.
        return ast.copy_location(ast.Name(id='$deferred_class_function', ctx=ast.Load()), node)

    def fresh(state, name):
        return name in state and state[name][0] in ('helper', 'fresh')

    def formation(node, wrappers, call):
        if module_native[0] is None:
            bindings = analyzer.import_binding_facts.get(ref.module, [])
            module_native[0] = (len(bindings) == 1 and not bindings[0].get('__name__')
                               and unmodified(analyzer, ref.module + '.__name__'))
        if not module_native[0]:
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

    def store_metadata(name, value, state, statement):
        payload = state[value][2] if len(state[value]) == 3 else None
        if payload is None or payload['formation'] is None or name is None:
            return
        fact = copy.deepcopy(payload['formation'])
        if any(fact['metadata_shapes'][key] is None for key in ('documentation', 'name', 'qualname')):
            return
        generated.append({'attribute': name, 'metadata_formation': fact,
                          'store_evidence': span(statement), '_token': payload['token']})
        published.add(payload['token'])

    def metadata_write(name, field, value, state, values, statement):
        current = state[name]
        payload = current[2] if len(current) == 3 else None
        if payload is None:
            # A branch join can lose metadata precision while retaining the
            # known native function. Invalidate any possibly aliased store too.
            generated[:] = [record for record in generated
                            if token_nodes.get(record['_token']) is not current[1]]
            return
        token = payload['token']
        # A later write through a retained local invalidates earlier snapshots.
        if token in published:
            generated[:] = [record for record in generated if record['_token'] != token]
        updated = copy.deepcopy(payload)
        fact = updated['formation']
        if fact is not None:
            shape = ['str'] if string(value, values) is not None else (
                ['NoneType'] if isinstance(value, ast.Constant) and value.value is None
                and field == '__doc__' else None)
            fact['metadata_shapes'][{'__doc__': 'documentation', '__name__': 'name',
                                     '__qualname__': 'qualname'}[field]] = shape
            fact['metadata_writes'].append(span(statement))
        for alias, item in list(state.items()):
            other = item[2] if len(item) == 3 else None
            if other is not None and other['token'] == token:
                state[alias] = (item[0], item[1], updated)

    def native_namespace():
        if namespace_guard[0] is None:
            try:
                namespace_guard[0] = _stable_builtin_namespace(
                    analyzer, ref, ('vars', 'getattr', 'type', '__build_class__'))[0]
            except _ClassEffectLimit:
                namespace_guard[0] = False
        return namespace_guard[0]

    def expression(node, state, values=None):
        if node is None:
            return None
        values = values or {}

        class Inline(ast.NodeTransformer):
            def __init__(self):
                self.active = set()

            def visit_Lambda(self, item):
                return item

            visit_GeneratorExp = visit_Lambda
            visit_ListComp = visit_Lambda
            visit_SetComp = visit_Lambda
            visit_DictComp = visit_Lambda

            def visit_Compare(self, item):
                if (len(item.ops) == 1 and isinstance(item.ops[0], (ast.In, ast.NotIn))
                        and len(item.comparators) == 1 and string(item.left, values) is not None):
                    right = item.comparators[0]
                    if (isinstance(right, ast.Call) and isinstance(right.func, ast.Name)
                            and right.func.id == 'vars' and len(right.args) == 1 and not right.keywords
                            and isinstance(right.args[0], ast.Name) and right.args[0].id == parameter
                            and analyzer._builtin_name_status(ref, function, 'vars') == 'confirmed_builtin'
                            and native_namespace()):
                        premise = read_function.namespace(dirty)
                        if premise is not None:
                            premise['lookup_evidence'] = span(item)
                            namespace_queries.append(premise)
                            return ast.copy_location(ast.Name(
                                id='$native_class_namespace_membership', ctx=ast.Load()), item)
                return self.generic_visit(item)

            def visit_Call(self, call):
                if (isinstance(call.func, ast.Name) and call.func.id == 'getattr'
                        and len(call.args) == 3 and not call.keywords
                        and isinstance(call.args[0], ast.Name) and call.args[0].id == parameter
                        and analyzer._builtin_name_status(ref, function, 'getattr') == 'confirmed_builtin'
                        and native_namespace()):
                    name = string(call.args[1], values)
                    fallback = call.args[2]
                    try:
                        if any(isinstance(item, ast.Call) for item in ast.walk(fallback)):
                            raise ValueError()
                        ast.literal_eval(fallback)
                        premise = read_function.namespace(dirty, absent=name) if name else None
                    except (ValueError, TypeError, RecursionError):
                        premise = None
                    if premise is not None:
                        premise['lookup_evidence'] = span(call)
                        namespace_queries.append(premise)
                        return copy.deepcopy(fallback)
                if not isinstance(call.func, ast.Name) or call.func.id not in state:
                    return self.generic_visit(call)
                name = call.func.id
                kind, helper = state[name][:2]
                body = _body(helper) if kind == 'helper' else []
                if (name in self.active or len(self.active) >= 16 or kind != 'helper'
                        or not _declaration(helper) or len(body) != 1 or not isinstance(body[0], ast.Return)
                        or body[0].value is None or helper.args.vararg or helper.args.kwarg
                        or any(isinstance(item, (ast.Lambda, ast.Yield, ast.YieldFrom, ast.Await,
                                                ast.NamedExpr)) for item in ast.walk(body[0]))):
                    raise ValueError()
                records, reasons = bind_ast_call(call, FunctionSignature.from_ast(helper.args))
                if reasons or any(record['status'] != 'exact' for record in records):
                    raise ValueError()
                count = sum(1 for _ in ast.walk(helper))
                expression_budget[0] -= count
                analyzer._class_effect_fact_steps -= count
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                if expression_budget[0] < 0 or analyzer._class_effect_fact_steps < 0:
                    raise ValueError()
                self.active.add(name)
                # An immediate lambda preserves argument snapshots, lexical
                # parameter binding and comprehension scope. Its full body is
                # still checked by the class-effect validator below.
                replacement = copy.copy(call)
                replacement.func = ast.copy_location(ast.Lambda(
                    args=copy.deepcopy(helper.args), body=copy.deepcopy(body[0].value)), call)
                # Keep the helper's own parameter scope intact. Nested private
                # helper references retain the ordinary unresolved-use guard.
                replacement.args = [self.visit(argument) for argument in replacement.args]
                replacement.keywords = [ast.keyword(arg=item.arg, value=self.visit(item.value))
                                        for item in replacement.keywords]
                self.active.remove(name)
                expression_calls.append({'call_evidence': span(call),
                    'helper_evidence': span(helper), 'effects': 'source_body_requires_validation',
                    'runtime_helper_executed': False})
                return replacement

        result = Inline().visit(copy.deepcopy(node))
        if any(isinstance(item, ast.Name) and item.id in state for item in ast.walk(result)):
            raise ValueError()
        return result

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

    def writes(statement, values):
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Name):
            if statement.value.id in class_aliases:
                class_aliases.update(node.id for node in statement.targets if isinstance(node, ast.Name))
        # Inspect this statement's evaluated inputs, not later statements in an
        # if branch or deferred helper bodies. Each reached statement is visited
        # in order, after the finite-loop specializer has bound its local names.
        inputs = [child for child in ast.iter_child_nodes(statement) if isinstance(child, ast.expr)]
        for node in (node for value in inputs for node in execution_nodes(ast.Expr(value=value))):
            if (isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and isinstance(node.value, ast.Name) and node.value.id in class_aliases):
                dirty.add(node.attr)
                write_sites.append({'attribute': node.attr, 'statement_evidence': span(statement)})
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('setattr', 'delattr') and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name) and node.args[0].id in class_aliases):
                name = string(node.args[1], values) or '*'
                dirty.add(name)
                write_sites.append({'attribute': name, 'statement_evidence': span(statement)})

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
            premise = read_function(name, node, dirty)
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
        invocations.append(invocation)
        payload = {'token': len(invocations), 'formation': formation(body[0], wrappers, call)}
        token_nodes[payload['token']] = body[0]
        return ('fresh', body[0], payload), [ast.copy_location(ast.Expr(value=value), call)
                                  for value in arguments]

    def merge(left, right):
        result = {}
        for name in set(left) | set(right):
            if name not in left or name not in right or left[name][:2] != right[name][:2]:
                result[name] = ('uncertain', None)
            else:
                result[name] = (left[name] if left[name] == right[name]
                                else (*left[name][:2], None))
        return result

    def block(body, state, values, depth=0):
        if depth > 32:
            raise ValueError()
        output = []
        for statement in body:
            writes(statement, values)
            if isinstance(statement, ast.FunctionDef):
                if not _declaration(statement):
                    raise ValueError()
                declarations.append(span(statement))
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
                state.clear()
                state.update(merge(left, right))
                values.clear()
                values.update({name: value for name, value in left_values.items()
                               if right_values.get(name) == value})
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
                output.append(ast.copy_location(ast.Expr(value=value), statement))
                exception_branches.append({'exception': name, 'evidence': span(statement),
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
                        stores.append(span(statement))
                        if isinstance(value, ast.Name):
                            store_metadata(destination.attr, value.id, state, statement)
                    else:
                        raise ValueError()
                    output.extend(before + [replacement])
                elif (isinstance(destination, ast.Attribute) and isinstance(destination.value, ast.Name)
                        and destination.value.id in state):
                    if not fresh(state, destination.value.id) or destination.attr not in (
                            '__doc__', '__name__', '__qualname__'):
                        raise ValueError()
                    evaluated = expression(value, state, values)
                    metadata_write(destination.value.id, destination.attr, value, state, values, statement)
                    metadata.append(span(statement))
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
                stores.append(span(statement))
                store_metadata(string(statement.value.args[1], values),
                               statement.value.args[2].id, state, statement)
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
    for invocation in invocations:
        for wrapper in invocation.get('metadata_wrappers', []):
            assumptions.extend(wrapper['assumptions'])
    hashes = dict(analyzer.hashes)
    for record in generated:
        assumptions.extend(record['metadata_formation']['assumptions'])
        hashes.update(record['metadata_formation']['source_hashes'])
    for query in namespace_queries:
        query['assumptions'] = sorted(set(query['assumptions'] + [
            'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation']))
        assumptions.extend(query['assumptions'])
        hashes.update(query['source_hashes'])
    if exception_branches:
        assumptions.extend(['standard_builtin_namespace_preserved',
                            'no_unmodeled_indirect_builtin_mutation'])
    return transformed, {'kind': 'source_deferred_class_functions',
        'scope': 'class_decoration_only', 'status': 'declaration_effects_bounded',
        'runtime_bodies_executed': False, 'future_method_effects': 'unmodeled',
        'declarations': declarations, 'factory_invocations': invocations,
        'protected_class_stores': stores, 'fresh_function_metadata_writes': metadata,
        'generated_class_members': [{key: value for key, value in record.items() if key != '_token'}
                                    for record in generated],
        'class_write_sites': write_sites,
        'expression_helper_calls': expression_calls,
        'class_namespace_queries': namespace_queries,
        'native_exception_branches': exception_branches,
        'source_hashes': dict(sorted(hashes.items())),
        'assumptions': sorted(set(assumptions))}
