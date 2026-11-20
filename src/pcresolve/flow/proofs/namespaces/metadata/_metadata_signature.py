## @package pcresolve.flow.proofs.namespaces.metadata._metadata_signature
#  Prove source signature formation.
#
#
#  Native inspect metadata formation from bounded, callback-free source data.
#  根据有界且无回调的源码数据构造原生 inspect 元数据事实。



import ast
import copy
import inspect
import importlib.util
from dataclasses import asdict
from pathlib import Path

from pcresolve.flow.proofs.callables._function_factory import _canonical, _signature_namespace
from pcresolve.flow.proofs.namespaces.metadata._metadata_namespace import builtin_namespace
from pcresolve.flow.proofs.namespaces.metadata._kind_alias_scan import (
    imported_kind_aliases_are_closed, inspect_module_kind_aliases,
)
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.classes._class_definition import namespace_issues
from pcresolve.facts.scope_facts import statement_scope_facts


## Capture source coordinates for metadata evidence.
## 记录元数据证据对应的源码位置。
#
#  @param ref Source definition reference.
#  @param node AST node providing the location.
#  @return File path and source-coordinate mapping.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
            'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}


## Resolve one stable source marker used as a parameter default.
## 解析一个稳定的源码标记参数默认值。
#
#  @param analyzer Source analyzer with bindings and snapshot facts.
#  @param caller Caller source reference and function node.
#  @param expression Default expression to resolve.
#  @return Marker metadata fact, or None when the binding is not stable.
def _marker_default(analyzer, caller, expression):
    ref, function = caller
    if not isinstance(expression, ast.Name):
        return None
    name = expression.id
    scope = analyzer._scope_facts(function)
    if name in scope.bound | scope.nonlocals or '.' in ref.qualname.rpartition('.')[0]:
        return None
    tables = analyzer.import_binding_facts.get(ref.module, [])
    bindings = tables[0].get(name, []) if len(tables) == 1 else []
    if len(bindings) != 1 or not isinstance(bindings[0], ast.Assign):
        return None
    assignment = bindings[0]
    bodies = analyzer.module_bodies.get(ref.module, [])
    if (len(bodies) != 1 or assignment not in bodies[0][1]
            or len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name)
            or assignment.targets[0].id != name or not unmodified(analyzer, ref.module + '.' + name)):
        return None
    call = assignment.value
    if not isinstance(call, ast.Call) or call.args or call.keywords or not isinstance(call.func, ast.Name):
        return None
    selected = analyzer._definition_index.find(ref.module, call.func.id, kind='class')
    if len(selected) != 1:
        return None
    owner, cls = selected[0]
    if (cls.bases or cls.keywords or cls.decorator_list or cls not in bodies[0][1]
            or cls.lineno >= assignment.lineno or analyzer.definition_conditions.get(owner)
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
            or {'__new__', '__init__', '__del__'} & statement_scope_facts(cls.body).bound):
        return None
    if namespace_issues(analyzer, selected, assumptions=set()):
        return None
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    if truncated or any(written == owner for written, _, _, _, _ in writes):
        return None
    return {'kind': 'source_marker_metadata_default', 'binding_name': name,
        'source_class': asdict(owner), 'binding_evidence': _span(ref, assignment),
        'allocation': {'protocol': 'builtin_object_new_and_init_no_arguments',
                       'evidence': _span(ref, call)},
        'signature_use': 'opaque_reference_storage', 'runtime_creation_confirmed': False,
        'source_hashes': dict(sorted(analyzer.hashes.items()))}


## Resolve one unchanged module literal used as a parameter default.
## 解析用作形参默认值且未改变的模块级字面量。
#
#  @param analyzer Source analyzer with import bindings and module bodies.
#  @param caller Caller source reference and function node.
#  @param expression Default expression to resolve.
#  @return Literal binding fact, or None when the value is open or mutable.
def _module_literal_default(analyzer, caller, expression):
    ref, function = caller
    if not isinstance(expression, ast.Name):
        return None
    name = expression.id
    scope = analyzer._scope_facts(function)
    if name in scope.bound | scope.nonlocals:
        return None
    tables = analyzer.import_binding_facts.get(ref.module, [])
    bindings = tables[0].get(name, []) if len(tables) == 1 else []
    if len(bindings) != 1 or not isinstance(bindings[0], ast.Assign):
        return None
    assignment = bindings[0]
    bodies = analyzer.module_bodies.get(ref.module, [])
    if (len(bodies) != 1 or assignment not in bodies[0][1]
            or len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name)
            or assignment.targets[0].id != name or not unmodified(analyzer, ref.module + '.' + name)
            or not isinstance(assignment.value, ast.Constant)):
        return None
    value = assignment.value.value
    if (type(value) not in (str, int, float, bool, type(None))
            or type(value) is str and len(value) > 2000
            or type(value) is int and value.bit_length() > 64):
        return None
    owner_name = ref.qualname.rpartition('.')[0]
    if owner_name:
        owners = analyzer._definition_index.find(ref.module, owner_name, kind='class')
        if len(owners) != 1 or assignment.lineno >= owners[0][1].lineno:
            return None
    elif assignment.lineno >= function.lineno:
        return None
    return {'kind': 'source_module_literal_default', 'binding_name': name,
        'value': value, 'binding_evidence': _span(ref, assignment),
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
                        'unchanged_module_literal_binding']}


## Prove inspect kind aliases cannot escape or acquire callback-capable uses.
## 证明 inspect kind 别名不会逃逸或获得可调用回调的用法。
#
#  @param analyzer Source analyzer with module and definition facts.
#  @param caller_ref Source reference containing the signature construction.
#  @param decorator_evidence Mutable destination for decorator proof facts.
#  @param receiver_class Optional source receiver class constraint.
#  @param fresh_decoration Optional provider of fresh-decoration facts for decorator proofs.
#  @return True when every protected alias use is closed and stable.
def _kind_aliases_closed(analyzer, caller_ref, decorator_evidence=None, receiver_class=None,
                         fresh_decoration = None):
    # Native kind enums are instances of a mutable Python enum class. Retaining
    # an alias and reflecting its class can change constructor comparisons.
    inspected = 0
    pending_decorator_evidence = []

    ## Resolve an inspect/functools name through imports and lexical bindings.
    ## 通过导入与词法绑定解析 inspect/functools 名称。
    #
    #  @param ref Source reference containing the expression.
    #  @param scope Lexical scope used to detect local shadowing.
    #  @param node Name or attribute expression.
    #  @return Canonical dotted name, or an empty string when unresolved.
    def canonical(ref, scope, node):
        value = _canonical(analyzer, ref, scope, node)
        if value:
            return value
        if not isinstance(node, (ast.Name, ast.Attribute)):
            return ''
        name = ast.unparse(node)
        head, dot, rest = name.partition('.')
        bindings = (analyzer._scope_facts(scope).bound
                    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                    else statement_scope_facts(scope.body).bound if isinstance(scope, ast.ClassDef)
                    else set())
        imported = analyzer.imports.get(ref.module, {}).get(head, '')
        if head in bindings or not imported:
            return ''
        if imported in ('inspect', 'functools') or imported.startswith(('inspect.', 'functools.')):
            return imported + (dot + rest if dot else '')
        return ''

    ## Check whether a node is used only in an identity comparison.
    ## 检查节点是否仅用于身份比较。
    #
    #  @param node Candidate comparison operand.
    #  @param parent Parent AST node.
    #  @return True when the operand participates in an is/is not comparison.
    def identity_operand(node, parent):
        return (isinstance(parent, ast.Compare)
                and all(isinstance(operator, (ast.Is, ast.IsNot)) for operator in parent.ops)
                and (parent.left is node or any(value is node for value in parent.comparators)))

    signature_source_cache = {}
    parameter_cache = {}

    relevant_setters = None
    if receiver_class is not None:
        hierarchy = analyzer._class_mro(receiver_class.module, receiver_class.qualname)
        if not hierarchy:
            return False
        relevant_setters = {(owner.module, owner.file_path, member.lineno, member.name)
            for owner, cls in hierarchy for member in cls.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name.startswith('set_')}

    ## Prove inspect.signature receives a fresh source function in this helper.
    ## 证明此辅助函数中的 inspect.signature 接收新建源码函数。
    #
    #  @param scope Candidate source function scope.
    #  @param scope_ref Source reference identifying the scope.
    #  @return True when one validated signature wrapper is constructed.
    def source_signature_decorator(scope, scope_ref):
        if scope in signature_source_cache:
            return signature_source_cache[scope]
        signature_source_cache[scope] = False
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        parameters = scope.args.posonlyargs + scope.args.args
        if not any(parameter.arg == 'func' for parameter in parameters):
            return False
        signatures = []
        for statement in scope.body:
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and isinstance(statement.value, ast.Call)
                    and canonical(scope_ref, scope, statement.value.func)
                        == 'inspect.signature'
                    and len(statement.value.args) == 1
                    and isinstance(statement.value.args[0], ast.Name)
                    and statement.value.args[0].id == 'func'
                    and not statement.value.keywords):
                signatures.append(statement.targets[0].id)
        if len(signatures) != 1:
            return False
        signature_name = signatures[0]
        helper_name = scope_ref.module + '.' + scope_ref.qualname

        ## Check whether a callable expression resolves to the helper function.
        ## 检查可调用表达式是否解析为该辅助函数。
        #
        #  @param module_ref Source reference containing the expression.
        #  @param lexical_scope Lexical scope of the expression.
        #  @param expression Callable expression to resolve.
        #  @return True when the expression identifies the exact helper.
        def refers_to_helper(module_ref, lexical_scope, expression):
            resolved = canonical_name(module_ref, lexical_scope, expression)
            if resolved == helper_name:
                return True
            if not resolved:
                return False
            selected = analyzer._definition_index.resolve_qualified(
                [resolved], analyzer.imports, qualified_guard=analyzer._stable_import_name)
            if selected is not None:
                return selected[0] == scope_ref
            return source_star_reexport(resolved, scope_ref)

        ## Resolve a stable public name re-exported by a source package.
        ## 解析源码包重新导出的稳定公开名称。
        #
        #  @param resolved Qualified public name to inspect.
        #  @param target_ref Target source function reference.
        #  @return True when one stable star re-export resolves to the target.
        def source_star_reexport(resolved, target_ref):
            package, separator, public_name = resolved.rpartition('.')
            if not separator or not public_name or public_name.startswith('_'):
                return False
            exported = analyzer._definition_index.find_qualified(
                [scope_ref.module + '.' + scope_ref.qualname], kind='function')
            if len(exported) != 1 or exported[0][0] != target_ref:
                return False
            bodies = analyzer.module_bodies.get(package, ())
            if len(bodies) != 1 or Path(bodies[0][0]).name != '__init__.py':
                return False
            module_path, body = bodies[0]
            if not analyzer._stable_import_name(target_ref.module + '.' +
                                                target_ref.qualname):
                return False
            if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == '__getattr__' for node in body):
                return False
            bindings = analyzer.import_binding_facts.get(package, ())
            if len(bindings) != 1 or '__all__' in bindings[0]:
                return False
            star_imports = []
            for statement in body:
                if not isinstance(statement, ast.ImportFrom):
                    continue
                if not any(alias.name == '*' for alias in statement.names):
                    continue
                try:
                    module = importlib.util.resolve_name(
                        '.' * statement.level + (statement.module or ''), package)
                except (ImportError, ValueError):
                    return False
                if module == target_ref.module:
                    star_imports.append(statement)
            if len(star_imports) != 1:
                return False
            imported = False
            for statement in body:
                if statement is star_imports[0]:
                    imported = True
                    continue
                if imported and public_name in statement_scope_facts([statement]).bound:
                    return False
            if any(isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in ('exec', 'eval', 'globals')
                    for node in ast.walk(ast.Module(body=body, type_ignores=[]))):
                return False
            return True

        ## Normalize canonical-name lookup for this lexical helper analysis.
        ## 规范化当前词法辅助函数分析中的名称查询。
        #
        #  @param module_ref Source reference containing the expression.
        #  @param lexical_scope Lexical scope of the expression.
        #  @param expression Name or attribute expression.
        #  @return Canonical dotted name or an empty string.
        def canonical_name(module_ref, lexical_scope, expression):
            return canonical(module_ref, lexical_scope, expression)

        partial_bindings = set()
        for statement in scope.body:
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and isinstance(statement.value, ast.Call)
                    and canonical(scope_ref, scope, statement.value.func)
                        == 'functools.partial'
                    and statement.value.args
                    and refers_to_helper(scope_ref, scope, statement.value.args[0])):
                expansions = [keyword for keyword in statement.value.keywords
                              if keyword.arg is None]
                kwargs_name = scope.args.kwarg.arg if scope.args.kwarg is not None else None
                if (len(expansions) > 1
                        or any(not isinstance(keyword.value, ast.Name)
                               or keyword.value.id != kwargs_name for keyword in expansions)):
                    continue
                partial_bindings.add(statement.targets[0].id)
        if len(partial_bindings) != 1:
            return False
        partial_name = next(iter(partial_bindings))
        curried = False
        for index, statement in enumerate(scope.body):
            if not isinstance(statement, ast.If) or not isinstance(statement.test, ast.Compare):
                continue
            test = statement.test
            if (len(test.ops) == 1 and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                    and isinstance(test.left, ast.Name) and test.left.id == 'func'
                    and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
                    and test.comparators[0].value is None
                    and isinstance(test.ops[0], ast.Is)):
                prior = scope.body[:index]
                if prior and (isinstance(prior[0], ast.Expr)
                              and isinstance(prior[0].value, ast.Constant)
                              and isinstance(prior[0].value.value, str)):
                    prior = prior[1:]
                factory = [item for item in prior if isinstance(item, ast.Assign)
                    and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name)
                    and item.targets[0].id == partial_name]
                kwargs_name = scope.args.kwarg.arg if scope.args.kwarg is not None else None
                local_extractions = [item for item in prior if item not in factory]
                safe_extractions = (not local_extractions or bool(kwargs_name) and all(
                    isinstance(item, ast.Assign) and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name)
                    and isinstance(item.value, ast.Call)
                    and isinstance(item.value.func, ast.Attribute)
                    and item.value.func.attr == 'pop'
                    and isinstance(item.value.func.value, ast.Name)
                    and item.value.func.value.id == kwargs_name
                    and len(item.value.args) == 2 and not item.value.keywords
                    and isinstance(item.value.args[0], ast.Constant)
                    and type(item.value.args[0].value) is str
                    and isinstance(item.value.args[1], ast.Constant)
                    and item.value.args[1].value is None
                    for item in local_extractions))
                kwargs_stores = [node for node in ast.walk(scope)
                    if isinstance(node, ast.Name) and node.id == kwargs_name
                    and isinstance(node.ctx, (ast.Store, ast.Del))]
                curried = (len(factory) == 1 and safe_extractions
                    and (not kwargs_stores or all(node is item.value.func.value
                        for item in local_extractions for node in kwargs_stores))
                    and isinstance(factory[0].value, ast.Call)
                    and canonical(scope_ref, scope, factory[0].value.func) == 'functools.partial'
                    and factory[0] in prior
                    and statement.orelse == [] and len(statement.body) == 1
                    and isinstance(statement.body[0], ast.Return)
                    and isinstance(statement.body[0].value, ast.Name)
                    and statement.body[0].value.id == partial_name)
        if not curried:
            return False
        # Source invocations must be bottom-most decorators or be stacked over
        # this same verified decorator. That chain preserves a native
        # Signature created by this function.
        calls = []
        for candidate_module, candidate_bodies in analyzer.module_bodies.items():
            if not candidate_bodies:
                continue
            module_ref = type(scope_ref)(candidate_module, '', candidate_bodies[0][0])
            for module_path, body in candidate_bodies:
                for current in ast.walk(ast.Module(body=body, type_ignores=[])):
                    if not isinstance(current, ast.Call):
                        continue
                    if not refers_to_helper(module_ref, None, current.func):
                        continue
                    decorated = next((definition for definition in body_nodes(body)
                        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and current in definition.decorator_list), None)
                    if relevant_setters is not None:
                        if (decorated is None or (candidate_module, module_path,
                                decorated.lineno, decorated.name) not in relevant_setters):
                            continue
                    if decorated is None:
                        return False
                    if any(item.arg == 'func' for item in current.keywords):
                        return False
                    if (any(not isinstance(value, ast.Constant) for value in current.args)
                            or any(not isinstance(item.value, ast.Constant)
                                   for item in current.keywords)):
                        return False
                    calls.append((current, decorated, module_ref))
        if not calls:
            if relevant_setters is None:
                return False
            signature_source_cache[scope] = signature_name
            return signature_name
        for _, decorated, _ in calls:
            # Defaults and annotations execute before decorator application.
            # Keep their signature metadata inputs to inert source expressions.
            arguments = decorated.args.posonlyargs + decorated.args.args + decorated.args.kwonlyargs
            arguments += [arg for arg in (decorated.args.vararg, decorated.args.kwarg) if arg]
            values = decorated.args.defaults + [item for item in decorated.args.kw_defaults if item]
            values += [arg.annotation for arg in arguments if arg.annotation is not None]
            values += [decorated.returns] if decorated.returns is not None else []

            ## Check that a declaration value contains only inert syntax forms.
            ## 检查声明值是否只包含无执行副作用的语法形式。
            #
            #  @param value AST value expression.
            #  @param depth Recursive tuple nesting depth.
            #  @return True when the value cannot execute arbitrary code.
            def inert_declaration_value(value, depth=0):
                if depth > 8:
                    return False
                if isinstance(value, (ast.Constant, ast.Name, ast.Attribute)):
                    return True
                return (isinstance(value, ast.Tuple)
                        and all(inert_declaration_value(item, depth + 1) for item in value.elts))

            if any(not inert_declaration_value(value) for value in values):
                return False
            # A lower decorator may run before this signature-inspecting
            # helper. Admit it only when PCResolve independently proves that
            # it returns the same fresh function and changes no execution or
            # signature metadata. This covers documentation-only source
            # decorators without treating arbitrary wrappers as transparent.
            for current, current_decorated, module_ref in calls:
                if current_decorated is not decorated:
                    continue
                position = decorated.decorator_list.index(current)
                for inner in decorated.decorator_list[position + 1:]:
                    if (isinstance(inner, ast.Call)
                            and refers_to_helper(module_ref, None, inner.func)):
                        continue
                    try:
                        from pcresolve.flow.proofs.callables.decorators._decorator_effects import _DecoratorEffects
                        decoration = _DecoratorEffects(analyzer, (module_ref, decorated),
                            _span, 2000).fact(inner)
                    except _ClassEffectLimit:
                        return False
                    if (decoration.get('identity_status') != 'preserved'
                            or any(boundary.get('reason') != 'decorator_data_protocol_unproven'
                                   for boundary in decoration.get('boundaries', ()))
                            or any(effect.get('target') == 'input_function'
                                   and effect.get('impact') not in ('documentation', 'module_metadata')
                                   for effect in decoration.get('effects', ()))):
                        # Some documentation formatters are callable objects
                        # whose ordinary effect summary cannot bind inherited
                        # helper calls. For the bottom-most decorator only,
                        # independently prove formatting on the fresh function
                        # before its name is bound. This proof does not cover
                        # arbitrary wrappers or any execution-field mutation.
                        if decorated.decorator_list.index(inner) != len(decorated.decorator_list) - 1:
                            return False
                        decorated_ref = next((candidate for candidate, definition
                            in analyzer.definitions if definition is decorated), None)
                        if decorated_ref is None:
                            return False
                        fresh_node = copy.copy(decorated)
                        fresh_node.decorator_list = [inner]
                        try:
                            fresh_fact = (fresh_decoration or
                                          getattr(analyzer, '_fresh_decoration_fact', None))
                            if fresh_fact is None:
                                return False
                            fresh = fresh_fact(decorated_ref, fresh_node, 2000)
                        except _ClassEffectLimit:
                            return False
                        if (fresh is None or fresh.get('identity_status') != 'preserved'
                                or fresh.get('body_binding_status') != 'preserved'
                                or fresh.get('boundaries')):
                            return False
                        if any(effect.get('target') == 'input_function'
                                and effect.get('impact') not in ('documentation', 'module_metadata')
                                for effect in fresh.get('effects', ())):
                            return False
                        key = (decorated_ref, inner.lineno, inner.col_offset,
                               inner.end_lineno, inner.end_col_offset)
                        if all(item.get('_dedup_key') != key for item in pending_decorator_evidence):
                            fresh['_dedup_key'] = key
                            pending_decorator_evidence.append(fresh)
        signature_source_cache[scope] = signature_name
        return signature_name

    ## Yield every descendant node from a bounded set of function bodies.
    ## 遍历给定函数体中的所有后代 AST 节点。
    #
    #  @param body Ordered source statements to traverse.
    #  @return Descendant AST nodes in traversal order.
    def body_nodes(body):
        pending = list(body)
        while pending:
            current = pending.pop()
            yield current
            pending.extend(ast.iter_child_nodes(current))

    ## Prove a value is a native Parameter kind from a fresh signature.
    ## 证明一个值来自新建签名中的原生 Parameter kind。
    #
    #  @param scope Function scope that constructs or inspects the signature.
    #  @param scope_ref Source reference for the lexical scope.
    #  @param value_name Candidate value expression.
    #  @return True when the value is a supported native parameter kind.
    def signature_parameters(scope, scope_ref, value_name):
        cache_key = (scope, ast.dump(value_name, include_attributes=False))
        if cache_key in parameter_cache:
            return parameter_cache[cache_key]
        signature_name = source_signature_decorator(scope, scope_ref)
        if not signature_name:
            parameter_cache[cache_key] = False
            return False
        if isinstance(value_name, ast.Attribute) and value_name.attr == 'kind':
            receiver = value_name.value
            if (isinstance(receiver, ast.Subscript) and isinstance(receiver.value, ast.Attribute)
                    and receiver.value.attr == 'parameters'
                    and isinstance(receiver.value.value, ast.Name)
                    and receiver.value.value.id == signature_name):
                parameter_cache[cache_key] = True
                return True
            if isinstance(receiver, ast.Name):
                # Comprehension variables from signature.parameters.values()
                # retain the exact native Parameter entries.
                for node in ast.walk(scope):
                    if not isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                        continue
                    for generator in node.generators:
                        iterable = generator.iter
                        if (isinstance(generator.target, ast.Name)
                                and generator.target.id == receiver.id
                                and isinstance(iterable, ast.Call)
                                and isinstance(iterable.func, ast.Attribute)
                                and iterable.func.attr == 'values'
                                and isinstance(iterable.func.value, ast.Attribute)
                                and iterable.func.value.attr == 'parameters'
                                and isinstance(iterable.func.value.value, ast.Name)
                                and iterable.func.value.value.id == signature_name):
                            parameter_cache[cache_key] = True
                            return True
        elif isinstance(value_name, ast.Name):
            for node in ast.walk(scope):
                if not isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                    continue
                for generator in node.generators:
                    iterable = generator.iter
                    if (isinstance(generator.target, ast.Name)
                            and generator.target.id == value_name.id
                            and isinstance(iterable, ast.Call)
                            and isinstance(iterable.func, ast.Attribute)
                            and iterable.func.attr == 'values'
                            and isinstance(iterable.func.value, ast.Attribute)
                            and iterable.func.value.attr == 'parameters'
                            and isinstance(iterable.func.value.value, ast.Name)
                            and iterable.func.value.value.id == signature_name):
                        parameter_cache[cache_key] = True
                        return True
        parameter_cache[cache_key] = False
        return False

    scope_refs = {node: ref for ref, node in analyzer.definitions}
    ## Recognize comparisons against a proven native Parameter kind.
    ## 识别与已证明的原生 Parameter kind 进行的比较。
    #
    #  @param node Candidate enum value reference.
    #  @param parent Parent expression using the reference.
    #  @param scope Lexical scope of the expression.
    #  @return True when the comparison is an allowed identity/value check.
    def native_kind_comparison(node, parent, scope):
        if (not isinstance(parent, ast.Compare) or len(parent.ops) != 1
                or not isinstance(parent.ops[0], (ast.Eq, ast.NotEq))):
            return False
        other = (parent.comparators[0] if parent.left is node and len(parent.comparators) == 1
                 else parent.left if parent.comparators == [node] else None)
        scope_ref = scope_refs.get(scope)
        if other is None or scope_ref is None:
            return False
        if signature_parameters(scope, scope_ref, other):
            return True
        # Parameter.kind may appear on the left while the enum constant is
        # reached through a module-level alias on the right.
        return signature_parameters(scope, scope_ref, parent.left)

    ## Recognize replacement of a native Parameter kind in supported metadata.
    ## 识别受支持元数据中原生 Parameter kind 的替换用法。
    #
    #  @param node Candidate enum value reference.
    #  @param parent Parent expression using the reference.
    #  @param scope Lexical scope of the expression.
    #  @return True when the value is used in a supported replacement path.
    def native_kind_replacement(node, parent, scope):
        if not isinstance(parent, ast.keyword) or parent.arg != 'kind':
            return False
        call = parents.get(parent)
        if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute)
                or call.func.attr != 'replace' or not isinstance(call.func.value, ast.Name)):
            return False
        scope_ref = scope_refs.get(scope)
        return (scope_ref is not None
                and signature_parameters(scope, scope_ref, call.func.value))

    module_aliases = set()

    ## Preserve the diagnostic for an alias whose use is outside the closed grammar.
    ## 保留别名用法超出封闭语法时的诊断信息。
    #
    #  @param module Source module containing the alias use.
    #  @param node Alias load node outside the supported grammar.
    #  @param parent Parent AST node that consumes the alias.
    #  @param scope Lexical scope of the alias use.
    #  @return None; prints a diagnostic when kind-alias tracing is enabled.
    def debug_alias_use(module, node, parent, scope):
        if not getattr(analyzer, '_debug_kind_aliases', False):
            return
        scope_ref = scope_refs.get(scope)
        parameter_key = (scope, ast.dump(
            parents.get(parent).func.value if isinstance(parent, ast.keyword)
            and isinstance(parents.get(parent), ast.Call)
            and isinstance(parents[parent].func, ast.Attribute)
            else node, include_attributes=False))
        print('KIND_ALIAS_DETAIL', module, ast.unparse(node),
            ast.unparse(parent) if parent is not None else None,
            getattr(scope_ref, 'qualname', None),
            signature_source_cache.get(scope), parameter_cache.get(parameter_key),
            flush=True)

    for module, bodies in analyzer.module_bodies.items():
        nodes, parents, scopes = [], {}, {}
        for _, body in bodies:
            pending = [(node, None) for node in body]
            while pending:
                node, scope = pending.pop()
                inspected += 1
                if inspected > 1000000:
                    return False
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                nodes.append(node)
                scopes[node] = scope
                for child in ast.iter_child_nodes(node):
                    parents[child] = node
                    pending.append((child, node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                     ast.ClassDef, ast.Lambda)) else scope))
        reference = type(caller_ref)(module, '', bodies[0][0])
        aliases = inspect_module_kind_aliases(
            module, nodes, parents, scopes, reference,
            canonical=canonical,
            identity_operand=identity_operand,
            kind_comparison=native_kind_comparison,
            kind_replacement=native_kind_replacement,
            stable_module_alias=lambda source_module, local_name: unmodified(
                analyzer, source_module + '.' + local_name),
            debug_alias_use=debug_alias_use)
        if aliases is None:
            return False
        module_aliases.update(aliases)

    # A locally safe enum alias cannot cross an import boundary and acquire
    # a new callback-capable use in another source module.
    if not imported_kind_aliases_are_closed(
            module_aliases, analyzer.module_bodies, analyzer.imports, identity_operand):
        return False
    if decorator_evidence is not None:
        for fact in pending_decorator_evidence:
            if all(item.get('_dedup_key') != fact['_dedup_key'] for item in decorator_evidence):
                decorator_evidence.append(fact)
    return True



## Bind native Signature and Parameter constructors using literal source metadata.
## 使用源码字面量元数据绑定原生 Signature 和 Parameter 构造。
#
#  @param analyzer Fixed source/import snapshot and cooperative effect budget.
#  @param caller Exact source definition containing the construction.
#  @param call Actual outer Signature invocation, never a target runtime value.
#  @param native_lists Source-bound private query results keyed by internal names.
#  @param receiver_class Optional source class associated with the call context.
#  @param fresh_decoration Optional provider of fresh-decoration facts for kind-alias checks.
#  @return Source-bound normal-return formation evidence or None for open inputs.
def signature_creation(analyzer, caller, call, native_lists=None, receiver_class=None,
                       fresh_decoration = None):
    ref, function = caller
    if (not isinstance(call, ast.Call)
            or _canonical(analyzer, ref, function, call.func) != 'inspect.Signature'):
        return None
    nodes = list(ast.walk(call))
    analyzer._class_effect_fact_steps -= len(nodes)
    if analyzer._analysis_budget is not None:
        analyzer._analysis_budget.checkpoint()
    if len(nodes) > 2000 or analyzer._class_effect_fact_steps < 0:
        raise _ClassEffectLimit()
    if (len(call.args) != 1 or not isinstance(call.args[0], (ast.List, ast.Tuple))
            or any(item.arg != 'return_annotation' for item in call.keywords)
            or len(call.keywords) > 1 or not _signature_namespace(analyzer)
            or not _kind_aliases_closed(analyzer, ref, decorator_evidence := [],
                                        receiver_class=receiver_class,
                                        fresh_decoration=fresh_decoration)
            or not builtin_namespace(analyzer, ref)[0]):
        return None

    ## Convert one supported syntax expression to a bounded native literal.
    ## 将一个受支持的语法表达式转换为有界原生字面量。
    #
    #  @param node Candidate literal expression.
    #  @return Native literal value, or raises ValueError for open signature data.
    def literal(node):
        if isinstance(node, ast.Constant):
            value = node.value
            if (type(value) in (bool, float, type(None))
                    or type(value) is str and len(value) <= 2000
                    or type(value) is int and value.bit_length() <= 64):
                return value
        if (isinstance(node, ast.Attribute) and node.attr == 'empty'
                and _canonical(analyzer, ref, function, node.value) in ('inspect.Parameter', 'inspect.Signature')):
            return inspect.Signature.empty
        raise ValueError('Open signature data')

    ## Resolve an excluded name sequence only under a proven class-creation prefix.
    ## 仅在类创建前缀已证明时解析名称排除序列。
    #
    #  @param node Candidate sequence or class attribute expression.
    #  @param input_query Source-bound query result providing prefix evidence.
    #  @return Name sequence and binding evidence, or None when unproven.
    def exclusion_sequence(node, input_query):
        if not isinstance(node, (ast.List, ast.Tuple)):
            binding = (input_query or {}).get('input_binding', {})
            prefix = binding.get('module_prefix') or binding.get('class_creation_prefix')
            receiver = (binding.get('receiver_class')
                        or (input_query or {}).get('receiver_class'))
            if (not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name)
                    or not isinstance(prefix, dict) or not isinstance(receiver, dict)):
                return None
            if prefix.get('kind') == 'source_module_fresh_class_prefix':
                if (prefix.get('status') != 'source_bound'
                        or prefix.get('call_effects') != 'unproved'
                        or prefix.get('phase') != 'before_module_call'
                        or prefix.get('receiver_class') != receiver
                        or len((input_query or {}).get('input_binding', {}).get(
                            'matching_members', ())) < 0):
                    return None
                owner = analyzer._definition_index.find(
                    receiver.get('module'), receiver.get('qualname'), kind='class')
                if (len(owner) != 1 or owner[0][0].file_path != receiver.get('file_path')
                        or owner[0][0].lineno != receiver.get('lineno')
                        or owner[0][1].name != node.value.id
                        or owner[0][1].decorator_list or owner[0][1].bases
                        or owner[0][1].keywords):
                    return None
                phase = 'module_call_entry'
            elif prefix.get('kind') == 'source_class_creation_prefix':
                if (prefix.get('status') != 'source_bound'
                        or prefix.get('phase') != 'after_class_body_before_class_decorators'
                        or prefix.get('receiver_class') != receiver
                        or any(name == '*' or name == node.attr
                               for name in prefix.get('possible_class_writes', ()))):
                    return None
                candidates = []
                for item in prefix.get('class_hierarchy', ()):
                    if (item.get('module') == ref.module and item.get('qualname') == node.value.id):
                        candidates.extend(analyzer._definition_index.find(
                            item['module'], item['qualname'], kind='class'))
                if len(candidates) != 1 or candidates[0][1].decorator_list or candidates[0][1].keywords:
                    return None
                owner = candidates
                phase = 'class_creation_entry'
            else:
                return None
            matches = []
            for statement in owner[0][1].body:
                if (isinstance(statement, ast.Assign)
                        and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name)
                        and statement.targets[0].id == node.attr):
                    matches.append((statement, statement.value))
                elif (isinstance(statement, ast.AnnAssign)
                        and isinstance(statement.target, ast.Name)
                        and statement.target.id == node.attr):
                    matches.append((statement, statement.value))
            if len(matches) != 1 or matches[0][1] is None:
                return None
            statement, node = matches[0]
            if (not isinstance(node, (ast.List, ast.Tuple))
                    or statement not in owner[0][1].body):
                return None
            table_binding = {'kind': 'source_class_literal_string_sequence',
                'attribute': matches[0][0].targets[0].id if isinstance(
                    matches[0][0], ast.Assign) else matches[0][0].target.id,
                'source_class': asdict(owner[0][0]), 'receiver_class': receiver, 'phase': phase,
                'required_preservation': 'complete_current_call',
                'binding_evidence': _span(owner[0][0], statement),
                'source_hashes': dict(prefix.get('source_hashes', {})),
                'assumptions': list(prefix.get('assumptions', ())) + [
                    'source_class_literal_sequence_binding']}
        else:
            table_binding = None
        values = node.elts
        if (len(values) > 2000 or any(not isinstance(value, ast.Constant)
                or type(value.value) is not str or len(value.value) > 2000 for value in values)):
            return None
        if table_binding is not None:
            table_binding['values'] = [value.value for value in values]
            table_binding['value_evidence'] = _span(
                owner[0][0], matches[0][0])
        return [value.value for value in values], table_binding

    parameters, evidence, defaults, dynamic = [], [], [], []
    try:
        for expression in call.args[0].elts:
            generator = None
            input_query = None
            filters = []
            if isinstance(expression, ast.Starred) and isinstance(expression.value, ast.ListComp):
                comprehension = expression.value
                if len(comprehension.generators) != 1:
                    return None
                generator = comprehension.generators[0]
                if (generator.is_async or not isinstance(generator.target, ast.Name)
                        or not isinstance(generator.iter, ast.Name)):
                    return None
                if len(generator.ifs) > 64:
                    return None
                input_query = (native_lists or {}).get(generator.iter.id)
                for condition in generator.ifs:
                    if (not isinstance(condition, ast.Compare) or len(condition.ops) != 1
                            or not isinstance(condition.ops[0], ast.NotIn)
                            or not isinstance(condition.left, ast.Name)
                            or condition.left.id != generator.target.id
                            or len(condition.comparators) != 1
                            ):
                        return None
                    sequence = exclusion_sequence(condition.comparators[0], input_query)
                    if sequence is None:
                        return None
                    exclusions, table_binding = sequence
                    filters.append({'operation': 'native_string_not_in_literal_sequence',
                        'excluded_names': exclusions,
                        **({'table_binding': table_binding} if table_binding is not None else {}),
                        'evidence': _span(ref, condition)})
                if (not isinstance(input_query, dict) or input_query.get('status') != 'source_bound'
                        or input_query.get('result_shape') != 'native_string_list'):
                    return None
                expression = comprehension.elt
                if not isinstance(expression, ast.Call):
                    return None
                if any(isinstance(node, ast.Name) and node.id == generator.target.id
                       for value in [expression.func] + [item.value for item in expression.keywords]
                       for node in ast.walk(value)):
                    return None
            elif dynamic:
                # Only a trailing native keyword-only segment is modeled.
                return None
            if (not isinstance(expression, ast.Call) or len(expression.args) != 2
                    or _canonical(analyzer, ref, function, expression.func) != 'inspect.Parameter'
                    or any(item.arg not in ('default', 'annotation') for item in expression.keywords)
                    or len({item.arg for item in expression.keywords}) != len(expression.keywords)):
                return None
            name, kind = expression.args
            if (not isinstance(kind, ast.Attribute)
                    or _canonical(analyzer, ref, function, kind.value) != 'inspect.Parameter'
                    or kind.attr not in ('POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD', 'VAR_POSITIONAL',
                                         'KEYWORD_ONLY', 'VAR_KEYWORD')):
                return None
            if generator is not None:
                if (kind.attr != 'KEYWORD_ONLY' or not isinstance(name, ast.Name)
                        or name.id != generator.target.id
                        or any(isinstance(node, ast.Name) and node.id == generator.target.id
                               for node in ast.walk(kind))):
                    return None
                name_value = 'source_dynamic_parameter_' + str(len(dynamic))
                while any(parameter.name == name_value for parameter in parameters):
                    name_value += '_'
                dynamic.append({'kind': 'native_keyword_only_parameter_segment',
                    'input_query': copy.deepcopy(input_query), 'names': 'unresolved_native_strings',
                    'parameter_kind': 'KEYWORD_ONLY', 'evidence': _span(ref, comprehension),
                    'filters': filters,
                    'completion': 'normal_return_only',
                    'validation': 'name_validity_and_duplicates_may_raise'})
            elif isinstance(name, ast.Constant) and type(name.value) is str and len(name.value) <= 2000:
                name_value = name.value
            else:
                return None
            metadata = {}
            for item in expression.keywords:
                try:
                    metadata[item.arg] = literal(item.value)
                except ValueError:
                    marker = _marker_default(analyzer, caller, item.value) if item.arg == 'default' else None
                    literal_default = (_module_literal_default(analyzer, caller, item.value)
                                       if marker is None and item.arg == 'default' else None)
                    if marker is None and literal_default is None:
                        return None
                    default_fact = marker or literal_default
                    defaults.append(default_fact)
                    if literal_default is not None:
                        metadata[item.arg] = literal_default['value']
                    else:
                        # Host placeholders validate structural signature rules;
                        # they never represent or execute the target marker value.
                        metadata[item.arg] = object()
            parameters.append(inspect.Parameter(name_value, getattr(inspect.Parameter, kind.attr), **metadata))
            evidence.append(_span(ref, expression))
        # These host stdlib objects contain source literals only. No target
        # function, annotation, default expression or target package is loaded.
        inspect.Signature(parameters, **{item.arg: literal(item.value) for item in call.keywords})
    except (ValueError, TypeError):
        return None
    assumptions = ['source_snapshot_bindings_hold', 'standard_library_inspect_signature_creation',
        'standard_library_inspect_parameter_creation', 'standard_builtin_namespace_preserved',
        'no_unmodeled_indirect_builtin_mutation', 'no_unmodeled_indirect_module_mutation',
        'no_external_monkeypatch_or_import_hook']
    hashes = dict(analyzer.hashes)
    for decorator in decorator_evidence:
        assumptions.extend(decorator.get('assumptions', ()))
        hashes.update(decorator.get('source_hashes', {}))
    for default in defaults:
        assumptions.extend(default.get('assumptions', ()))
        hashes.update(default.get('source_hashes', {}))
    for segment in dynamic:
        assumptions.extend(segment['input_query']['assumptions'])
        hashes.update(segment['input_query']['source_hashes'])
        for filter_fact in segment['filters']:
            binding = filter_fact.get('table_binding')
            if binding is not None:
                assumptions.extend(binding['assumptions'])
                hashes.update(binding['source_hashes'])
    return {'kind': 'source_native_signature_creation', 'status': 'source_bound',
        'caller': asdict(ref), 'result_kind': 'native_inspect_signature',
        'completion': 'normal_return_only', 'runtime_creation_confirmed': False,
        'call_evidence': _span(ref, call), 'parameter_evidence': evidence,
        'input_binding': ('source_dynamic_native_metadata' if dynamic else
                          'source_marker_native_metadata' if defaults else 'literal_native_metadata'),
        'dynamic_parameters': dynamic,
        'decorator_evidence': [{key: value for key, value in fact.items() if key != '_dedup_key'}
                               for fact in decorator_evidence],
        'default_bindings': defaults, 'value_operations': 'storage_only' if defaults else 'native_literal_data',
        'source_hashes': dict(sorted(hashes.items())), 'assumptions': sorted(set(assumptions))}
