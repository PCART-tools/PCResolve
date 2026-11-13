## @package pcresolve._class_creation_calls
#  Finite source classmethod effects during one ordinary class creation phase.
#  分析普通类创建阶段中有限的源码类方法影响。

import ast
import copy
from importlib import import_module
from dataclasses import asdict

from .class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from .effect_facts import contains_yield, execution_nodes
from .scope_facts import statement_scope_facts
from ._source_protocols import SourceProtocolResolver
from ._class_identity import identity_decorations
from ._runtime_namespace import unmodified
from ._source_dependencies import register as register_source_dependencies
from ._metadata_calls import bind_metadata_call
from ._metadata_signature import signature_creation
from ._class_observer_input import bind_observer_call, bind_documentation_observer_call
from ._function_factory import _canonical
from ._function_metadata_formation import metadata_formation
from ._source_callable_metadata import wrapper_metadata

_CLASS_CREATION_NODE_LIMIT = 2000


## Capture a source location for a class-creation proof.
## 记录类创建证明使用的源码位置。
#
#  @param ref Definition reference containing the source path.
#  @param node AST node carrying source coordinates.
#  @return Mapping of path and start/end coordinates.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
            'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}


## Check whether a node is a call-free literal expression.
## 判断节点是否为不含调用的字面量表达式。
#
#  @param node Candidate expression, or None.
#  @return True when literal evaluation succeeds.
def _literal(node):
    if node is None or any(isinstance(value, ast.Call) for value in ast.walk(node)):
        return False
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


## Prove a side-effect-free source helper returns one literal string.
## 证明无副作用的源码辅助函数返回一个字符串字面量。
#
#  @param analyzer Analyzer holding source and stable binding facts.
#  @param caller Caller reference and function definition.
#  @param call Candidate helper call.
#  @param argument Required forwarded argument name.
#  @return Source proof and evidence, or None when conditions are not met.
def _source_literal_helper_result(analyzer, caller, call, argument):
    """Prove a side-effect-free source helper returns one literal string."""
    if (not isinstance(call, ast.Call) or len(call.args) != 1 or call.keywords
            or not isinstance(call.args[0], ast.Name) or call.args[0].id != argument):
        return None
    canonical = _canonical(analyzer, caller[0], caller[1], call.func)
    if (not canonical or not analyzer._stable_import_name(canonical)
            or not unmodified(analyzer, canonical)):
        return None
    helper = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if helper is None:
        return None
    ref, function = helper
    body = function.body[1:] if (isinstance(function, ast.FunctionDef) and function.body
        and isinstance(function.body[0], ast.Expr)
        and isinstance(function.body[0].value, ast.Constant)
        and type(function.body[0].value.value) is str) else function.body
    parameters = function.args.posonlyargs + function.args.args
    if (not isinstance(function, ast.FunctionDef) or function.decorator_list
            or '.' in ref.qualname or len(parameters) != 1
            or parameters[0].annotation is not None
            or function.args.defaults or function.args.kwonlyargs or function.args.vararg
            or function.args.kwarg or function.returns is not None
            or analyzer.definition_conditions.get(ref) or len(body) != 1
            or not isinstance(body[0], ast.Return)
            or not isinstance(body[0].value, ast.Constant)
            or type(body[0].value.value) is not str or len(body[0].value.value) > 2000):
        return None
    return {'kind': 'source_literal_helper_result', 'status': 'source_bound',
        'target': asdict(ref), 'result': body[0].value.value,
        'call_evidence': _span(caller[0], call),
        'return_evidence': _span(ref, body[0]),
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
                        'source_helper_normal_return_literal']}


## Prove a literal or source-observed value for a member metadata write.
## 证明成员元数据写入的值是字面量或具有源码观察证据。
#
#  @param analyzer Analyzer holding source and binding facts.
#  @param owner Receiver class reference and definition.
#  @param selected Selected updater reference and definition.
#  @param statement Metadata assignment to inspect.
#  @param module_prefix Optional proof of the module-call prefix.
#  @return Metadata fact and evidence, or None for unsupported values.
def _source_member_metadata_value(analyzer, owner, selected, statement, module_prefix):
    """Prove a literal or source-observed value for one member metadata write."""
    attribute = statement.targets[0].attr
    value = statement.value
    if _literal(value):
        return {'kind': 'source_literal_member_metadata', 'attribute': attribute,
                'value_type': type(ast.literal_eval(value)).__name__,
                'write_evidence': _span(selected[0], statement)}
    if attribute == '__doc__':
        for node in ast.walk(value):
            if not isinstance(node, ast.Call):
                continue
            fact = bind_documentation_observer_call(
                analyzer, owner, selected, 'cls', node, module_prefix)
            if fact is not None:
                return {'kind': 'source_documentation_member_metadata',
                        'attribute': attribute, 'fact': fact,
                        'write_evidence': _span(selected[0], statement)}
            fact = _source_literal_helper_result(
                analyzer, selected, node, 'cls')
            if fact is not None:
                return {'kind': 'source_documentation_member_metadata',
                        'attribute': attribute, 'fact': fact,
                        'write_evidence': _span(selected[0], statement)}
        return None
    if attribute != '__signature__':
        return None

    # Replace independently proved observer results only in the copied syntax.
    # 仅在复制的语法中替换已独立证明的观察结果。
    signature_value = copy.deepcopy(value)
    native_lists = {}
    replacement_index = 0
    for original in ast.walk(value):
        if not isinstance(original, ast.ListComp):
            continue
        for generator in original.generators:
            if not isinstance(generator.iter, ast.Call):
                continue
            observer = bind_observer_call(
                analyzer, owner, selected, 'cls', generator.iter,
                ancestor_hooks=(), module_prefix=module_prefix)
            if (observer is None or observer.get('result_shape') != 'native_string_list'):
                continue
            name = '$source_metadata_list_' + str(replacement_index)
            replacement_index += 1
            native_lists[name] = observer
            for candidate in ast.walk(signature_value):
                if not isinstance(candidate, ast.ListComp):
                    continue
                for copied_generator in candidate.generators:
                    if (isinstance(copied_generator.iter, ast.Call)
                            and _span(selected[0], copied_generator.iter)
                            == _span(selected[0], generator.iter)):
                        copied_generator.iter = ast.copy_location(
                            ast.Name(id=name, ctx=ast.Load()), copied_generator.iter)

    signature = signature_creation(
        analyzer, selected, signature_value, native_lists=native_lists,
        receiver_class=owner[0])
    if signature is None:
        return None
    return {'kind': 'source_signature_member_metadata', 'attribute': attribute,
            'fact': signature, 'write_evidence': _span(selected[0], statement)}


## Prove a source classmethod installs member metadata at module load.
## 证明源码类方法在模块加载时写入成员元数据。
#
#  @param analyzer Analyzer holding module and definition facts.
#  @param selected Member reference and definition.
#  @param attribute Metadata attribute whose write must be unique.
#  @return Conditional initialization fact, or None if not proven.
def _source_module_initialized_member_metadata(analyzer, selected, attribute):
    """Prove a source classmethod installs member metadata at module load."""
    ref, member = selected
    if (not isinstance(member, ast.FunctionDef) or not isinstance(attribute, str)
            or not attribute.isidentifier() or member.decorator_list
            or '.' not in ref.qualname
            or len(analyzer.module_bodies.get(ref.module, ())) != 1):
        return None
    owner_name, member_name = ref.qualname.rsplit('.', 1)
    if not owner_name.isidentifier() or not member_name.isidentifier():
        return None
    owners = analyzer._definition_index.find(ref.module, owner_name, kind='class')
    if (len(owners) != 1 or owners[0][1].decorator_list
            or not analyzer._stable_import_name(ref.module + '.' + owner_name)):
        return None
    owner_ref, owner = owners[0]

    invocations = []
    for path, statements in analyzer.module_bodies.get(ref.module, ()):
        for statement in statements:
            call = statement.value if isinstance(statement, ast.Expr) else None
            if (isinstance(call, ast.Call) and not call.args and not call.keywords
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == owner_name):
                candidates = analyzer._definition_index.find(
                    ref.module, owner_name + '.' + call.func.attr)
                if (len(candidates) == 1 and isinstance(candidates[0][1], ast.FunctionDef)
                        and len(candidates[0][1].decorator_list) == 1
                        and analyzer._descriptor_kind(candidates[0]) == 'classmethod'):
                    invocations.append((path, statements, statement, candidates[0]))
    # Accept only a unique bounded updater with a closed initialization tail.
    # 仅接受唯一的有界更新方法及封闭的后续初始化语句。
    matching = []
    for path, statements, call_statement, updater_selected in invocations:
        updater_ref, updater = updater_selected
        parameters = updater.args.posonlyargs + updater.args.args
        body = [statement for statement in updater.body if not (
            isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
            and type(statement.value.value) is str)]
        if (len(parameters) != 1 or parameters[0].arg != 'cls' or updater.args.defaults
                or updater.args.kwonlyargs or updater.args.vararg or updater.args.kwarg
                or updater.returns is not None or not body
                or any(not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                    or not isinstance(statement.targets[0], ast.Attribute)
                    or not isinstance(statement.targets[0].value, ast.Attribute)
                    or not isinstance(statement.targets[0].value.value, ast.Name)
                    or statement.targets[0].value.value.id != 'cls'
                    or statement.targets[0].value.attr != member_name
                    or not statement.targets[0].attr.isidentifier()
                    for statement in body)):
            continue
        writes = [statement for statement in body
                  if statement.targets[0].attr == attribute]
        if len(writes) != 1:
            continue
        call_index = next(index for index, statement in enumerate(statements)
                          if statement is call_statement)
        trailing = statements[call_index + 1:]
        if any(not (isinstance(statement, ast.Pass) or isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str) for statement in trailing):
            continue
        module_prefix = None
        dynamic_writes = [statement for statement in body if not _literal(statement.value)]
        if dynamic_writes:
            from ._module_class_prefix import module_class_prefix
            module_prefix = module_class_prefix(
                analyzer, (owner_ref, owner), call_statement.value)
        write_facts = [_source_member_metadata_value(
            analyzer, (owner_ref, owner), updater_selected, statement, module_prefix)
            for statement in body]
        if any(fact is None for fact in write_facts):
            continue
        signature = next((fact['fact'] for fact in write_facts
                          if fact['attribute'] == '__signature__'
                          and fact['kind'] == 'source_signature_member_metadata'), None)
        matching.append((updater_ref, writes[0], call_statement, owner_ref,
                         signature, write_facts))
    if len(matching) != 1:
        return None
    updater_ref, write, module_call, evidence_ref, signature, write_facts = matching[0]
    fact = {'kind': 'source_module_initialization_member_metadata',
        'status': 'source_bound', 'target': asdict(ref), 'updater': asdict(updater_ref),
        'attribute': attribute, 'write_evidence': _span(updater_ref, write),
        'member_metadata_writes': write_facts,
        'module_call_evidence': _span(evidence_ref, module_call),
        'completion': 'normal_module_initialization_only',
        'runtime_metadata_confirmed': False,
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold',
            'source_module_initialization_completed_before_query',
            'exact_source_classmethod_dispatch', 'module_initialization_tail_is_closed',
            'no_external_monkeypatch_or_import_hook']}
    if signature is not None:
        fact['signature_creation'] = signature
        fact['assumptions'] = sorted(set(fact['assumptions'] + signature['assumptions']))
    return fact


## Bound native writes across a finite graph of exact source classmethod calls.
## 沿有限的精确源码类方法调用图对原生写入做有界分析。
#
#  @param analyzer Fixed source bindings and shared query-local effect budget.
#  @param target New class before its own decorators, with ordinary type creation.
#  @param hook Selected source __init_subclass__ definition.
#  @param prior_attributes Possible class writes from ancestor creation phases.
#  @param ancestor_hooks Independently completed ancestor creation records, if available.
#  @param module_prefix Optional independently proved first module-call prefix.
#  @return Attributes, evidence, method calls and query premises; None for open effects.
def creation_calls(analyzer, target, hook, prior_attributes=(), ancestor_hooks=None, module_prefix=None):
    ancestor_hooks = tuple(ancestor_hooks or ())
    hierarchy = analyzer._class_mro(target[0].module, target[0].qualname)
    owners = {owner for owner, _ in hierarchy}
    calls, attributes, evidence, methods, active, completed = [], [], [], set(), set(), set()
    queries, protocols = [], {}
    metadata_queries, metadata_results = [], {}
    signatures = []
    opaque_metadata = set()
    class_queries = []
    module_metadata_effects = {}
    native_lists = {}
    inspected = [0]

    ## Recognize bounded expressions built from native metadata values.
    ## 识别由原生元数据值构成的有界表达式。
    #
    #  @param node Candidate expression.
    #  @param depth Current recursive expression depth.
    #  @return True when all expression parts have supported native values.
    def native_data(node, depth=0):
        if depth > 32:
            return False
        if isinstance(node, ast.Name):
            return node.id in metadata_results and node.id not in opaque_metadata
        if isinstance(node, ast.Constant):
            return type(node.value) in (str, int, bool, float, type(None))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return native_data(node.operand, depth + 1)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return native_data(node.left, depth + 1) and native_data(node.right, depth + 1)
        if isinstance(node, ast.Compare) and all(isinstance(op, (
                ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot)) for op in node.ops):
            return all(native_data(value, depth + 1) for value in [node.left] + node.comparators)
        if isinstance(node, ast.BoolOp):
            return all(native_data(value, depth + 1) for value in node.values)
        return False

    ## Bind a supported class member metadata write to its source member.
    ## 将受支持的类成员元数据写入绑定到源码成员。
    #
    #  @param node Candidate metadata assignment.
    #  @param parameter Name of the implicit class receiver.
    #  @param ref Reference of the method containing the assignment.
    #  @return Conditional write fact, or None when the binding is unproven.
    def method_documentation_write(node, parameter, ref):
        if (module_prefix is None or not isinstance(node, ast.Assign) or len(node.targets) != 1
                or not isinstance(node.targets[0], ast.Attribute)
                or not isinstance(node.targets[0].value, ast.Attribute)
                or not isinstance(node.targets[0].value.value, ast.Name)
                or node.targets[0].value.value.id != parameter):
            return None
        owner, cls = target
        member_name = node.targets[0].value.attr
        attribute = node.targets[0].attr
        if not attribute.isidentifier():
            return None
        if attribute == '__signature__':
            if (not isinstance(node.value, ast.Name)
                    or metadata_results.get(node.value.id) != {'native_inspect_signature'}):
                return None
            value_shape = 'native_inspect_signature'
        elif attribute == '__name__':
            if not isinstance(node.value, ast.Constant) or type(node.value.value) is not str:
                return None
            value_shape = 'str'
        elif attribute == '__qualname__':
            value = node.value
            if (not isinstance(value, ast.JoinedStr) or len(value.values) != 2
                    or not isinstance(value.values[0], ast.FormattedValue)
                    or not isinstance(value.values[0].value, ast.Attribute)
                    or value.values[0].value.attr != '__qualname__'
                    or not isinstance(value.values[0].value.value, ast.Name)
                    or value.values[0].value.value.id != parameter
                    or not isinstance(value.values[1], ast.Constant)
                    or value.values[1].value != '.' + member_name):
                return None
            value_shape = 'source_class_qualname_suffix'
        else:
            if not native_data(node.value):
                return None
            value_shape = (type(node.value.value).__name__
                           if isinstance(node.value, ast.Constant) else 'source_native_value')
        hierarchy = analyzer._class_mro(owner.module, owner.qualname)
        members = [member for member in cls.body
                   if member_name in statement_scope_facts([member]).bound]
        if (hierarchy and len(hierarchy) == 1 and not cls.decorator_list and not cls.keywords
                and len(members) == 1 and isinstance(members[0], ast.FunctionDef)
                and members[0].name == member_name and not members[0].decorator_list):
            selected = analyzer._definition_index.find(
                owner.module, owner.qualname + '.' + member_name)
            if len(selected) != 1 or selected[0][1] is not members[0]:
                return None
            formation = metadata_formation(analyzer, selected[0])
            if formation is None or formation['metadata_shapes']['module'] != ['str']:
                return None
            return {'kind': 'source_bound_method_metadata_write', 'status': 'source_bound',
                'caller': asdict(ref), 'receiver_class': asdict(owner),
                'target': asdict(selected[0][0]), 'attribute': attribute,
                'value_shape': value_shape, 'completion': 'normal_return_only',
                'call_evidence': _span(ref, node), 'definition_evidence': _span(*selected[0]),
                'runtime_execution_confirmed': False, 'source_hashes': dict(analyzer.hashes),
                'function_metadata_formation': formation,
                'assumptions': ['source_snapshot_bindings_hold', 'source_module_fresh_class_prefix',
                    'native_source_function_metadata_write', 'no_external_monkeypatch_or_import_hook']}

        # A source __init_subclass__ may first install a fresh lambda and then
        # call a source classmethod that assigns its native function metadata.
        # Bind only a straight-line, exact lambda assignment and exact updater
        # call in the same class-creation prefix.
        if (module_prefix is None or module_prefix.get('kind') != 'source_class_creation_prefix'
                or module_prefix.get('status') != 'source_bound'
                or module_prefix.get('receiver_class') != asdict(owner)
                or module_prefix.get('phase') != 'after_class_body_before_class_decorators'
                or module_prefix.get('class_hierarchy') != [asdict(item[0])
                    for item in (hierarchy or ())]
                or not hierarchy or len(hierarchy) > 64):
            return None
        hook_identity = module_prefix.get('hook', {})
        hook_matches = analyzer._definition_index.find(
            hook_identity.get('module'), hook_identity.get('qualname'))
        if (len(hook_matches) != 1 or hook_matches[0][0].file_path != hook_identity.get('file_path')
                or hook_matches[0][0].lineno != hook_identity.get('lineno')):
            return None
        hook_ref, hook = hook_matches[0]
        hook_parameters = hook.args.posonlyargs + hook.args.args
        if (not isinstance(hook, ast.FunctionDef) or not hook_parameters
                or hook.decorator_list and analyzer._descriptor_kind(hook_matches[0]) != 'classmethod'):
            return None
        receiver = hook_parameters[0].arg
        hook_body = hook.body[1:] if (hook.body and isinstance(hook.body[0], ast.Expr)
            and isinstance(hook.body[0].value, ast.Constant)
            and type(hook.body[0].value.value) is str) else hook.body

        ## Recognize an assignment installing the requested lambda member.
        ## 识别安装目标 lambda 成员的赋值语句。
        #
        #  @param statement Candidate hook statement.
        #  @return True when it assigns a lambda to the receiver's member.
        def installs_member(statement):
            return (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Attribute)
                and isinstance(statement.targets[0].value, ast.Name)
                and statement.targets[0].value.id == receiver
                and statement.targets[0].attr == member_name
                and isinstance(statement.value, ast.Lambda))

        installs = [index for index, statement in enumerate(hook_body) if installs_member(statement)]
        updater_name = ref.qualname.rsplit('.', 1)[-1]
        updater_calls = [index for index, statement in enumerate(hook_body)
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Attribute)
            and isinstance(statement.value.func.value, ast.Name)
            and statement.value.func.value.id == receiver
            and statement.value.func.attr == updater_name
            and not statement.value.args and not statement.value.keywords]
        direct_hook_metadata = ref == hook_ref and attribute in ('__name__', '__qualname__')
        if direct_hook_metadata:
            current = [index for index, statement in enumerate(hook_body)
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Attribute)
                and isinstance(statement.targets[0].value, ast.Attribute)
                and statement.targets[0].attr == attribute
                and statement.targets[0].value.attr == member_name
                and statement.lineno == node.lineno and statement.col_offset == node.col_offset]
            stops = current
        else:
            stops = updater_calls
        if len(installs) != 1 or len(stops) != 1 or installs[0] >= stops[0]:
            return None
        assignment = hook_body[installs[0]]
        generated = assignment.value
        parameters = generated.args
        if (parameters.posonlyargs or len(parameters.args) != 1
                or parameters.args[0].annotation is not None or parameters.vararg is not None
                or parameters.kwarg is None or parameters.kwonlyargs or parameters.defaults
                or parameters.kw_defaults or parameters.kwarg.annotation is not None
                or any(isinstance(item, ast.Name) and item.id in (
                        parameters.args[0].arg, parameters.kwarg.arg)
                    and isinstance(item.ctx, ast.Store)
                    for statement in hook_body[installs[0] + 1:stops[0]]
                    for item in ast.walk(statement))):
            return None
        if (not isinstance(generated.body, ast.Call) or len(generated.body.args) != 1
                or not isinstance(generated.body.args[0], ast.Name)
                or generated.body.args[0].id != parameters.args[0].arg
                or len(generated.body.keywords) != 1
                or generated.body.keywords[0].arg is not None
                or not isinstance(generated.body.keywords[0].value, ast.Name)
                or generated.body.keywords[0].value.id != parameters.kwarg.arg):
            return None
        from ._function_factory import _canonical
        generated_target = _canonical(analyzer, hook_ref, hook, generated.body.func)
        if generated_target is None or not analyzer._stable_import_name(generated_target):
            return None
        expected_name, expected_qualname = [], []
        for statement in hook_body[installs[0] + 1:stops[0] + int(direct_hook_metadata)]:
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Attribute)
                    and isinstance(statement.targets[0].value, ast.Attribute)
                    and isinstance(statement.targets[0].value.value, ast.Name)
                    and statement.targets[0].value.value.id == receiver
                    and statement.targets[0].value.attr == member_name):
                attr = statement.targets[0].attr
                if attr == '__name__':
                    expected_name.append(statement)
                elif attr == '__qualname__':
                    expected_qualname.append(statement)
                else:
                    return None
        if (not expected_name or not isinstance(expected_name[0].value, ast.Constant)
                or expected_name[0].value.value != member_name
                or (not direct_hook_metadata and len(expected_name) != 1)
                or (attribute == '__qualname__' and not expected_qualname)
                or (not direct_hook_metadata and len(expected_qualname) != 1)
                or (expected_qualname and not isinstance(expected_qualname[0].value, ast.JoinedStr))
                or (expected_qualname and len(expected_qualname[0].value.values) != 2)
                or (expected_qualname and not isinstance(expected_qualname[0].value.values[0], ast.FormattedValue))
                or (expected_qualname and not isinstance(expected_qualname[0].value.values[0].value, ast.Attribute))
                or (expected_qualname and expected_qualname[0].value.values[0].value.attr != '__qualname__')
                or (expected_qualname and not isinstance(expected_qualname[0].value.values[0].value.value, ast.Name))
                or (expected_qualname and expected_qualname[0].value.values[0].value.value.id != receiver)
                or (expected_qualname and not isinstance(expected_qualname[0].value.values[1], ast.Constant))
                or (expected_qualname and expected_qualname[0].value.values[1].value != '.' + member_name)):
            return None
        generation = {'kind': 'source_class_creation_lambda_member',
            'status': 'source_bound', 'receiver_class': asdict(owner),
            'attribute': member_name, 'forward_target': generated_target,
            'binding_evidence': _span(hook_ref, assignment),
            **({'name_evidence': _span(hook_ref, expected_name[0])}
                if expected_name else {}),
            **({'qualname_evidence': _span(hook_ref, expected_qualname[0])}
                if expected_qualname else {}),
            **({'updater_call_evidence': _span(hook_ref, hook_body[updater_calls[0]].value)}
               if updater_calls else {}),
            'completion': 'normal_class_creation_path',
            'source_hashes': dict(sorted(analyzer.hashes.items())),
            'assumptions': ['source_snapshot_bindings_hold', 'source_class_creation_phase_prefix',
                'native_lambda_creation_and_binding', 'source_classmethod_call_binding']}
        return {'kind': 'source_bound_method_metadata_write', 'status': 'source_bound',
            'caller': asdict(ref), 'receiver_class': asdict(owner),
            'target': {'module': hook_ref.module, 'qualname': owner.qualname + '.' + member_name,
                'file_path': owner.file_path, 'lineno': assignment.lineno},
            'attribute': attribute, 'value_shape': value_shape,
            'completion': 'normal_return_only', 'call_evidence': _span(ref, node),
            'definition_evidence': _span(hook_ref, assignment),
            'runtime_execution_confirmed': False, 'source_hashes': dict(analyzer.hashes),
            'generated_member_binding': generation,
            'assumptions': sorted(set(generation['assumptions'] + [
                'native_source_function_metadata_write', 'no_external_monkeypatch_or_import_hook']))}

    ## Bind metadata written after a generated lambda member is installed.
    ## 绑定生成的 lambda 成员安装后的元数据写入。
    #
    #  @param node Candidate metadata assignment.
    #  @param parameter Name of the implicit class receiver.
    #  @param ref Reference of the containing source method.
    #  @param function Containing function definition.
    #  @return Conditional write fact, or None when the pattern is unsupported.
    def generated_member_metadata_write(node, parameter, ref, function):
        if (not isinstance(node, ast.Assign) or len(node.targets) != 1
                or not isinstance(node.targets[0], ast.Attribute)
                or not isinstance(node.targets[0].value, ast.Attribute)
                or not isinstance(node.targets[0].value.value, ast.Name)
                or node.targets[0].value.value.id != parameter
                or not node.targets[0].attr.isidentifier()):
            return None
        name = node.targets[0].attr
        member_name = node.targets[0].value.attr
        assignments = [statement for statement in function.body
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Attribute)
            and isinstance(statement.targets[0].value, ast.Name)
            and statement.targets[0].value.id == parameter
            and statement.targets[0].attr == member_name
            and isinstance(statement.value, ast.Lambda)]
        if len(assignments) != 1 or assignments[0].lineno >= node.lineno:
            return None
        generated = assignments[0].value
        parameters = generated.args
        if (parameters.posonlyargs or len(parameters.args) != 1
                or parameters.vararg is not None or parameters.kwarg is None
                or parameters.kwonlyargs or parameters.defaults or parameters.kw_defaults
                or not isinstance(generated.body, ast.Call)
                or len(generated.body.args) != 1
                or not isinstance(generated.body.args[0], ast.Name)
                or generated.body.args[0].id != parameters.args[0].arg
                or len(generated.body.keywords) != 1
                or generated.body.keywords[0].arg is not None
                or not isinstance(generated.body.keywords[0].value, ast.Name)
                or generated.body.keywords[0].value.id != parameters.kwarg.arg):
            return None
        from ._function_factory import _canonical
        forwarded = _canonical(analyzer, ref, function, generated.body.func)
        if forwarded is None or not analyzer._stable_import_name(forwarded):
            return None
        if name == '__name__':
            valid = isinstance(node.value, ast.Constant) and node.value.value == member_name
            value_shape = 'str'
        elif name == '__qualname__':
            receiver = node.targets[0].value.value.id
            expected = ast.parse(f'f"{{{receiver}.__qualname__}}.{member_name}"',
                                 mode='eval').body
            valid = ast.dump(node.value, include_attributes=False) == ast.dump(
                expected, include_attributes=False)
            value_shape = 'source_class_qualname_suffix'
        else:
            valid = native_data(node.value)
            value_shape = (type(node.value.value).__name__
                           if isinstance(node.value, ast.Constant) else 'source_native_value')
        if not valid:
            return None
        binding = {'kind': 'source_class_creation_lambda_member',
            'status': 'source_bound', 'receiver_class': asdict(target[0]),
            'attribute': member_name, 'forward_target': forwarded,
            'binding_evidence': _span(ref, assignments[0]),
            'completion': 'normal_class_creation_path',
            'source_hashes': dict(sorted(analyzer.hashes.items())),
            'assumptions': ['source_snapshot_bindings_hold', 'source_class_creation_phase_prefix',
                'native_lambda_creation_and_binding', 'no_external_monkeypatch_or_import_hook']}
        return {'kind': 'source_bound_method_metadata_write',
            'status': 'source_bound', 'caller': asdict(ref),
            'receiver_class': asdict(target[0]),
            'target': {'module': ref.module,
                'qualname': target[0].qualname + '.' + member_name,
                'file_path': target[0].file_path, 'lineno': assignments[0].lineno},
            'attribute': name, 'value_shape': value_shape,
            'effect_scope': 'function_metadata_only', 'completion': 'normal_return_only',
            'call_evidence': _span(ref, node),
            'definition_evidence': binding['binding_evidence'],
            'runtime_execution_confirmed': False,
            'source_hashes': dict(sorted(analyzer.hashes.items())),
            'generated_member_binding': binding,
            'assumptions': ['source_snapshot_bindings_hold',
                'source_class_creation_phase_prefix',
                'function_metadata_write_does_not_rebind_class_member',
                'no_external_monkeypatch_or_import_hook']}

    ## Charge inspected nodes against local and shared effect budgets.
    ## 从本地和共享影响分析预算中扣除已检查节点。
    #
    #  @param count Number of inspected nodes to charge.
    #  @return None; raises _ClassEffectLimit when a budget is exhausted.
    def charge(count):
        analyzer._class_effect_fact_steps -= count
        inspected[0] += count
        if (inspected[0] > _CLASS_CREATION_NODE_LIMIT
                or analyzer._class_effect_fact_steps < 0):
            raise _ClassEffectLimit()

    ## Select a uniquely defined source classmethod in hierarchy order.
    ## 按类层次顺序选择唯一定义的源码类方法。
    #
    #  @param name Method name to resolve.
    #  @return Definition reference and node, or None when unconfirmed.
    def select(name):
        if name.startswith('__') or name == 'mro':
            return None
        for owner, cls in hierarchy:
            members = [node for node in cls.body if name in statement_scope_facts([node]).bound]
            if not members:
                continue
            if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
                    or members[0].name != name or owner != target[0] and cls.decorator_list):
                return None
            matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
            if (len(matches) != 1 or matches[0][1] is not members[0]
                    or analyzer._descriptor_kind(matches[0]) != 'classmethod'):
                return None
            return matches[0]
        return None

    ## Collect potential receiver writes through bounded classmethod calls.
    ## 沿有界类方法调用收集可能的接收者写入。
    #
    #  @param selected Method reference and definition.
    #  @param seen Methods already visited on this call path.
    #  @return Attribute names; '*' represents an open or unknown write.
    def possible_class_writes(selected, seen=()):
        ref, function = selected
        if ref in seen or len(seen) >= 16:
            return {'*'}
        parameters = function.args.posonlyargs + function.args.args
        if not parameters:
            return {'*'}
        receiver = parameters[0].arg
        writes = set()
        for node in execution_nodes(function):
            if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
                root, first = node, None
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    if isinstance(root, ast.Attribute):
                        first = root.attr if first is None else first
                    root = root.value
                if isinstance(root, ast.Name) and root.id == receiver:
                    writes.add(first or '*')
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ('setattr', 'delattr') and node.args
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == receiver):
                name = node.args[1].value if len(node.args) > 1 and isinstance(
                    node.args[1], ast.Constant) and type(node.args[1].value) is str else '*'
                writes.add(name)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == receiver):
                callee = select(node.func.attr)
                if callee is not None:
                    writes.update(possible_class_writes(callee, seen + (ref,)))
        return writes

    if module_prefix is not None and module_prefix.get('kind') == 'source_class_creation_prefix':
        module_prefix = copy.deepcopy(module_prefix)
        module_prefix['possible_class_writes'] = sorted(possible_class_writes(hook))

    ## Bind a supported native query over the implicit class receiver.
    ## 绑定针对隐式类接收者的受支持原生查询。
    #
    #  @param ref Reference of the function containing the call.
    #  @param function Function definition containing the call.
    #  @param parameter Name of the implicit class receiver.
    #  @param call Candidate query call.
    #  @return Query fact, or None when the required evidence is missing.
    def native_query(ref, function, parameter, call):
        if (not isinstance(call.func, (ast.Name, ast.Attribute)) or len(call.args) != 1
                or call.keywords or not isinstance(call.args[0], ast.Name)
                or call.args[0].id != parameter):
            return None
        name = ast.unparse(call.func)
        head, dot, rest = name.partition('.')
        lexical = analyzer._scope_facts(function)
        if head in lexical.bound | lexical.globals | lexical.nonlocals:
            return None
        if not analyzer._stable_import_name(ref.module + '.' + head):
            return None
        imported = analyzer.imports.get(ref.module, {}).get(head)
        canonical = imported + dot + rest if imported else ref.module + '.' + name
        if not unmodified(analyzer, canonical):
            return None
        # Before its own decorators, a new class from ordinary source bases
        # has native metaclass type. Ancestor decorators need an independent
        # identity proof; a source spelling alone cannot establish that input.
        if any(cls.keywords or owner != target[0] and cls.decorator_list
               and identity_decorations(analyzer, (owner, cls)) is None
               for owner, cls in hierarchy):
            return None
        if canonical not in protocols:
            module, _, attribute = canonical.rpartition('.')
            ambient = [(module, analyzer._source_snapshot.documents[path])
                       for module, bodies in analyzer.module_bodies.items() for path, _ in bodies]
            reader = SourceProtocolResolver(analyzer.roots, budget=analyzer._analysis_budget,
                                            analyzer_factory=type(analyzer),
                                            ambient_documents=ambient)
            proof = reader.iterability(module, attribute)
            if analyzer.support_source_protocols:
                # Failed semantic matches also have lookup inputs. Watching
                # their versions prevents stale negative results on reuse.
                register_source_dependencies(analyzer, {
                    path: document.sha256 for path, document in reader.documents.items()
                    if document.sha256})
            # Dependency protocols require explicit opt-in and keep their own
            # versions. They never enlarge the primary flow/naming snapshot.
            if proof is not None and not register_source_dependencies(
                    analyzer, proof['source_hashes']):
                proof = None
            protocols[canonical] = proof
        proof = protocols[canonical]
        if proof is None:
            return None
        queries.append({'caller': asdict(ref), 'receiver_class': asdict(target[0]),
            'parameter': parameter, 'argument_binding': 'implicit_classmethod_receiver',
            'callee': canonical, 'result': proof['result'],
            'phase': 'before_class_decorators', 'call_evidence': _span(ref, call),
            'source_protocol': copy.deepcopy(proof)})
        return ast.copy_location(ast.Constant(value=proof['result']), call)

    ## Resolve a supported hasattr query against source method metadata.
    ## 解析针对源码方法元数据的受支持 hasattr 查询。
    #
    #  @param ref Reference of the function containing the call.
    #  @param function Function definition containing the call.
    #  @param parameter Name of the implicit class receiver.
    #  @param call Candidate hasattr call.
    #  @return Boolean constant AST with evidence, or None when unproven.
    def callable_hasattr(ref, function, parameter, call):
        if (not isinstance(call.func, ast.Name) or call.func.id != 'hasattr'
                or analyzer._builtin_name_status(ref, function, 'hasattr') != 'confirmed_builtin'
                or len(call.args) != 2 or call.keywords
                or not isinstance(call.args[0], ast.Attribute)
                or not isinstance(call.args[0].value, ast.Name)
                or call.args[0].value.id != parameter
                or not isinstance(call.args[1], ast.Constant)
                or type(call.args[1].value) is not str):
            return None
        member_name, metadata_name = call.args[0].attr, call.args[1].value
        for owner, cls in hierarchy:
            members = [node for node in cls.body
                       if member_name in statement_scope_facts([node]).bound]
            if not members:
                continue
            if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
                    or members[0].name != member_name):
                return None
            selected = analyzer._definition_index.find(owner.module,
                owner.qualname + '.' + member_name)
            if len(selected) != 1 or selected[0][1] is not members[0]:
                return None
            wrapper = wrapper_metadata(analyzer, selected[0], metadata_name)
            if wrapper is not None:
                assumptions = sorted(set(wrapper.get('assumptions', ()) + [
                    'source_class_method_lookup', 'builtin_hasattr_protocol']))
                proof = {'kind': 'source_wrapper_callable_metadata_presence',
                    'status': 'source_bound', 'target': asdict(selected[0][0]),
                    'attribute': metadata_name, 'metadata_write': wrapper,
                    'completion': 'normal_return_only', 'runtime_metadata_confirmed': False,
                    'source_hashes': dict(sorted(wrapper.get(
                        'source_hashes', analyzer.hashes).items())),
                    'assumptions': assumptions}
                query = {'kind': 'source_bound_callable_metadata_presence',
                    'status': 'source_bound', 'caller': asdict(ref),
                    'receiver_class': asdict(target[0]),
                    'operation': 'builtin_hasattr', 'method_name': member_name,
                    'metadata_attribute': metadata_name, 'result': True,
                    'target': asdict(selected[0][0]),
                    'completion': 'normal_return_only',
                    'runtime_execution_confirmed': False, 'metadata_fact': proof,
                    'call_evidence': _span(ref, call),
                    'source_hashes': proof['source_hashes'],
                    'assumptions': assumptions}
                class_queries.append(query)
                return ast.copy_location(ast.Constant(value=True), call)
            generated_writes = [item for item in class_queries
                if item.get('kind') == 'source_bound_method_metadata_write'
                and item.get('receiver_class') == asdict(target[0])
                and item.get('target', {}).get('qualname', '').rsplit('.', 1)[-1] == member_name
                and item.get('attribute') == metadata_name]
            if generated_writes:
                if len(generated_writes) != 1:
                    return None
                write = generated_writes[0]
                proof = {'kind': 'source_class_creation_method_metadata_presence',
                    'status': 'source_bound', 'target': copy.deepcopy(write['target']),
                    'attribute': metadata_name, 'metadata_write': copy.deepcopy(write),
                    'completion': 'normal_return_only', 'runtime_metadata_confirmed': False,
                    'source_hashes': dict(sorted(write['source_hashes'].items())),
                    'assumptions': sorted(set(write['assumptions'] + [
                        'source_class_creation_method_metadata_presence',
                        'source_creation_phase_class_metadata_input',
                        'builtin_hasattr_protocol']))}
                query = {'kind': 'source_bound_callable_metadata_presence',
                    'status': 'source_bound', 'caller': asdict(ref),
                    'receiver_class': asdict(target[0]),
                    'operation': 'builtin_hasattr', 'method_name': member_name,
                    'metadata_attribute': metadata_name, 'result': True,
                    'target': copy.deepcopy(write['target']),
                    'completion': 'normal_return_only',
                    'runtime_execution_confirmed': False, 'metadata_fact': proof,
                    'call_evidence': _span(ref, call),
                    'source_hashes': proof['source_hashes'],
                    'assumptions': proof['assumptions']}
                class_queries.append(query)
                return ast.copy_location(ast.Constant(value=True), call)
            module_metadata = _source_module_initialized_member_metadata(
                analyzer, selected[0], metadata_name)
            if module_metadata is not None:
                query = {'kind': 'source_bound_callable_metadata_presence',
                    'status': 'source_bound', 'caller': asdict(ref),
                    'receiver_class': asdict(target[0]),
                    'operation': 'builtin_hasattr', 'method_name': member_name,
                    'metadata_attribute': metadata_name, 'result': True,
                    'target': asdict(selected[0][0]),
                    'completion': 'normal_return_only',
                    'runtime_execution_confirmed': False,
                    'metadata_fact': module_metadata,
                    'call_evidence': _span(ref, call),
                    'source_hashes': module_metadata['source_hashes'],
                    'assumptions': sorted(set(module_metadata['assumptions'] + [
                        'source_class_method_lookup', 'builtin_hasattr_protocol']))}
                class_queries.append(query)
                return ast.copy_location(ast.Constant(value=True), call)
            ancestor_writes = [query for fact in ancestor_hooks
                for query in fact.get('class_metadata_queries', ())
                if query.get('kind') == 'source_bound_method_metadata_write'
                and query.get('target', {}).get('qualname', '').rsplit('.', 1)[-1] == member_name
                and query.get('attribute') == metadata_name]
            if ancestor_writes:
                result = True
                proof = {'kind': 'source_ancestor_class_creation_method_metadata',
                    'status': 'source_bound', 'target': ancestor_writes[-1]['target'],
                    'attribute': metadata_name, 'creation_fact': copy.deepcopy(ancestor_writes[-1]),
                    'ancestor_creation_hooks': copy.deepcopy(ancestor_hooks),
                    'completion': 'normal_return_only', 'runtime_metadata_confirmed': False,
                    'source_hashes': dict(sorted({**analyzer.hashes,
                        **ancestor_writes[-1].get('source_hashes', {})}.items())),
                    'assumptions': sorted(set(ancestor_writes[-1].get('assumptions', ()) + [
                        'source_ancestor_creation_method_metadata', 'no_external_monkeypatch_or_import_hook']))}
                query = {'kind': 'source_bound_callable_metadata_presence', 'status': 'source_bound',
                    'caller': asdict(ref), 'receiver_class': asdict(target[0]),
                    'operation': 'builtin_hasattr', 'method_name': member_name,
                    'metadata_attribute': metadata_name, 'result': result,
                    'target': asdict(selected[0][0]), 'completion': 'normal_return_only',
                    'runtime_execution_confirmed': False, 'metadata_fact': proof,
                    'call_evidence': _span(ref, call), 'source_hashes': proof['source_hashes'],
                    'assumptions': sorted(set(proof['assumptions'] + [
                        'source_class_method_lookup', 'builtin_hasattr_protocol']))}
                class_queries.append(query)
                return ast.copy_location(ast.Constant(value=result), call)
            if any(member_name in fact.get('attributes', ()) for fact in ancestor_hooks):
                return None
            if owner not in module_metadata_effects:
                module_metadata_effects[owner] = []
                if '.' not in owner.qualname and len(analyzer.module_bodies.get(owner.module, ())) == 1:
                    classes = analyzer._definition_index.find(owner.module, owner.qualname, kind='class')
                    body = analyzer.module_bodies[owner.module][0][1]
                    calls = [statement.value for statement in body
                        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                        and isinstance(statement.value.func, ast.Attribute)
                        and isinstance(statement.value.func.value, ast.Name)
                        and statement.value.func.value.id == owner.qualname
                        and not statement.value.args and not statement.value.keywords]
                    if len(classes) == 1 and len(calls) == 1:
                        call_node = calls[0]
                        call_position = next((index for index, statement in enumerate(body)
                            if isinstance(statement, ast.Expr) and statement.value is call_node), None)
                        trailing = body[call_position + 1:] if call_position is not None else [ast.Pass()]
                        if (call_position is not None and all(isinstance(statement, ast.Pass)
                                or isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                                and type(statement.value.value) is str for statement in trailing)):
                            module_class_effects = import_module(
                                __package__ + '._module_class_effects').module_class_effects
                            module_metadata_effects[owner] = module_class_effects(
                                analyzer, classes[0], call_node)
            module_effect = module_metadata_effects[owner]
            if module_effect is None:
                return None
            module_writes = [fact for fact in module_effect.get('class_metadata_queries', ())
                if fact.get('kind') == 'source_bound_method_metadata_write'
                and fact.get('target') == asdict(selected[0][0])
                and fact.get('attribute') == metadata_name] if isinstance(module_effect, dict) else []
            if module_writes:
                result = True
                write = module_writes[-1]
                proof = {'kind': 'source_module_initialization_method_metadata',
                    'status': 'source_bound', 'target': asdict(selected[0][0]),
                    'attribute': metadata_name, 'module_effect': copy.deepcopy(module_effect),
                    'metadata_write': copy.deepcopy(write),
                    'completion': 'normal_return_only', 'runtime_metadata_confirmed': False,
                    'source_hashes': dict(sorted({**analyzer.hashes,
                        **module_effect.get('source_hashes', {})}.items())),
                    'assumptions': sorted(set(module_effect.get('assumptions', ()) + [
                        'source_import_initialization_order', 'no_external_monkeypatch_or_import_hook']))}
                query = {'kind': 'source_bound_callable_metadata_presence', 'status': 'source_bound',
                    'caller': asdict(ref), 'receiver_class': asdict(target[0]),
                    'operation': 'builtin_hasattr', 'method_name': member_name,
                    'metadata_attribute': metadata_name, 'result': result,
                    'target': asdict(selected[0][0]), 'completion': 'normal_return_only',
                    'runtime_execution_confirmed': False, 'metadata_fact': proof,
                    'call_evidence': _span(ref, call), 'source_hashes': proof['source_hashes'],
                    'assumptions': sorted(set(proof['assumptions'] + [
                        'source_class_method_lookup', 'builtin_hasattr_protocol']))}
                class_queries.append(query)
                return ast.copy_location(ast.Constant(value=result), call)
            writes, truncated = analyzer._class_binding_writes(include_escapes=True)
            class_creation_prefix = (module_prefix is not None
                and module_prefix.get('kind') == 'source_class_creation_prefix'
                and module_prefix.get('status') == 'source_bound'
                and module_prefix.get('receiver_class') == asdict(target[0]))
            if truncated or any(written == owner and name in (metadata_name, '*')
                    and not (class_creation_prefix and reason == 'visible_class_escape')
                    for written, name, reason, _, _ in writes):
                return None
            custom = wrapper_metadata(analyzer, selected[0], metadata_name)
            if custom is not None:
                result = True
                proof = custom
            else:
                method = selected[0][1]
                if method.decorator_list:
                    return None
                formation = metadata_formation(analyzer, selected[0])
                if formation is None:
                    return None
                result = False
                proof = {'kind': 'source_plain_function_custom_metadata_absence',
                    'status': 'source_bound', 'target': asdict(selected[0][0]),
                    'attribute': metadata_name, 'metadata_formation': formation,
                    'ancestor_creation_hooks': copy.deepcopy(ancestor_hooks),
                    'completion': 'normal_return_only', 'runtime_metadata_confirmed': False,
                    'source_hashes': dict(sorted({**formation['source_hashes'], **analyzer.hashes}.items())),
                    'assumptions': sorted(set(formation['assumptions'] + [
                        'source_method_namespace_unmodified', 'no_external_monkeypatch_or_import_hook']))}
            query = {'kind': 'source_bound_callable_metadata_presence', 'status': 'source_bound',
                'caller': asdict(ref), 'receiver_class': asdict(target[0]),
                'operation': 'builtin_hasattr', 'method_name': member_name,
                'metadata_attribute': metadata_name, 'result': result,
                'target': asdict(selected[0][0]), 'completion': 'normal_return_only',
                'runtime_execution_confirmed': False, 'metadata_fact': proof,
                'call_evidence': _span(ref, call), 'source_hashes': proof['source_hashes'],
                'assumptions': sorted(set(proof['assumptions'] + [
                    'source_class_method_lookup', 'builtin_hasattr_protocol']))}
            class_queries.append(query)
            return ast.copy_location(ast.Constant(value=result), call)
        return None

    ## Prove the effects of a source classmethod and its bounded callees.
    ## 证明源码类方法及其有界被调用方法的影响。
    #
    #  @param selected Method reference and definition.
    #  @return True when effects are bounded; False on an open boundary.
    def visit(selected):
        ref, function = selected
        if ref in active:
            return False
        if ref in completed:
            return True
        if len(methods) >= 16:
            return False
        active.add(ref)
        methods.add(ref)
        args = function.args
        parameters = args.posonlyargs + args.args
        if (len(parameters) != 1 or args.defaults or args.kwonlyargs or args.vararg
                or function.returns is not None or parameters[0].annotation is not None
                or args.kwarg is not None and args.kwarg.annotation is not None
                or contains_yield(function)):
            return False
        parameter = parameters[0].arg
        if (parameter in statement_scope_facts(function.body).bound
                or any(isinstance(node, ast.Name) and node.id in ('super', '__class__')
                       for node in ast.walk(function))):
            return False

        metadata_updates = []
        if (calls and calls[-1].get('target') == asdict(ref)
                and analyzer._descriptor_kind(selected) == 'classmethod'
                and '.' in ref.qualname):
            owner_name = ref.qualname.rsplit('.', 1)[0]
            assigned_members = set()
            method_body = [statement for statement in function.body if not (
                isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str)]
            for statement in method_body:
                if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                        or not isinstance(statement.targets[0], ast.Attribute)
                        or not isinstance(statement.targets[0].value, ast.Attribute)
                        or not isinstance(statement.targets[0].value.value, ast.Name)
                        or statement.targets[0].value.value.id != 'cls'):
                    assigned_members = set()
                    break
                assigned_members.add((statement.targets[0].value.attr,
                                      statement.targets[0].attr))
            if assigned_members:
                for member_name, metadata_name in sorted(assigned_members):
                    candidates = analyzer._definition_index.find(
                        ref.module, owner_name + '.' + member_name)
                    if len(candidates) != 1:
                        metadata_updates = []
                        break
                    fact = _source_module_initialized_member_metadata(
                        analyzer, candidates[0], metadata_name)
                    if fact is None or fact.get('updater') != asdict(ref):
                        metadata_updates = []
                        break
                    metadata_updates.append(fact)
        if metadata_updates:
            invocation = calls[-1] if calls else None
            if (not isinstance(invocation, dict)
                    or invocation.get('target') != asdict(ref)):
                return False
            class_queries.append({'kind': 'source_class_creation_metadata_only',
                'status': 'source_bound', 'caller': invocation['caller'],
                'receiver_class': asdict(target[0]), 'target': asdict(ref),
                'call_evidence': copy.deepcopy(invocation['call_evidence']),
                'effect_scope': 'class_member_metadata_only',
                'metadata_updates': metadata_updates, 'completion': 'normal_return_only',
                'runtime_execution_confirmed': False,
                'source_hashes': dict(sorted(analyzer.hashes.items())),
                'assumptions': sorted(set().union(*(set(fact['assumptions'])
                    for fact in metadata_updates), {'source_creation_phase_class_metadata_input'}))})
            active.remove(ref)
            completed.add(ref)
            return True

        # A lambda body runs later, but local cells can retain the class across
        # creation. Include assignments after the declaration: Python closures
        # capture cells, not the values at the lambda's source position. Global
        # method lookups retain their separate namespace/escape checks.
        local_names = statement_scope_facts(function.body).bound | {parameter}
        if args.kwarg is not None:
            local_names |= {args.kwarg.arg}
        for node in ast.walk(function):
            if isinstance(node, ast.Lambda) and any(
                    isinstance(item, ast.Name) and item.id in local_names
                    for item in ast.walk(node)):
                return False

        ## Replace proven native queries in a copy of the selected method.
        ## 在所选方法的副本中替换已证明的原生查询。
        class NativeQueries(ast.NodeTransformer):
            ## Initialize the guard that excludes nested function bodies.
            ## 初始化用于排除嵌套函数体的标志。
            #
            #  @return None.
            def __init__(self):
                self.entered = False

            ## Visit the selected function up to an unconditional return.
            ## 访问所选函数直到无条件返回。
            #
            #  @param node Function definition to transform.
            #  @return Transformed function node.
            def visit_FunctionDef(self, node):
                if self.entered:
                    return node
                self.entered = True
                body = []
                for statement in node.body:
                    value = self.visit(statement)
                    values = value if isinstance(value, list) else [value]
                    body.extend(values)
                    if any(isinstance(item, ast.Return) for item in values):
                        break
                node.body = body
                return node

            ## Leave deferred lambda bodies untouched.
            ## 保持延后执行的 lambda 主体不变。
            #
            #  @param node Lambda expression.
            #  @return Original lambda node.
            def visit_Lambda(self, node):
                return node

            ## Leave deferred asynchronous function bodies untouched.
            ## 保持延后执行的异步函数体不变。
            #
            #  @param node Asynchronous function definition.
            #  @return Original definition node.
            def visit_AsyncFunctionDef(self, node):
                return node

            ## Leave nested class definitions untouched.
            ## 保持嵌套类定义不变。
            #
            #  @param node Nested class definition.
            #  @return Original definition node.
            def visit_ClassDef(self, node):
                return node

            ## Replace a proven query with its bounded synthetic value.
            ## 将已证明的查询替换为有界的合成值。
            #
            #  @param node Call expression to transform.
            #  @return Replacement or recursively transformed call node.
            def visit_Call(self, node):
                metadata_presence = callable_hasattr(ref, function, parameter, node)
                if metadata_presence is not None:
                    return metadata_presence
                observer = bind_observer_call(analyzer, target, selected, parameter, node,
                    ancestor_hooks=ancestor_hooks, module_prefix=module_prefix)
                if observer is not None:
                    name = '$class_metadata_result_' + str(len(class_queries))
                    class_queries.append(observer)
                    metadata_results[name] = {observer['result_shape']}
                    if observer['result_shape'] == 'native_string_list':
                        native_lists[name] = observer
                    return ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)
                documentation = bind_documentation_observer_call(
                    analyzer, target, selected, parameter, node, module_prefix)
                if documentation is not None:
                    name = '$class_metadata_result_' + str(len(class_queries))
                    class_queries.append(documentation)
                    metadata_results[name] = {'str'}
                    return ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)
                node = self.generic_visit(node)
                native = native_query(ref, function, parameter, node)
                if native is not None:
                    return native
                signature = signature_creation(analyzer, selected, node, native_lists=native_lists,
                                              receiver_class=target[0])
                if signature is not None:
                    name = '$signature_creation_' + str(len(signatures))
                    signatures.append(signature)
                    metadata_results[name] = {'native_inspect_signature'}
                    if signature.get('value_operations') == 'storage_only':
                        opaque_metadata.add(name)
                    return ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)
                metadata = bind_metadata_call(analyzer, target, selected, parameter, node)
                if metadata is None:
                    return node
                # These private names carry scalar kinds, never guessed values.
                name = '$metadata_query_result_' + str(len(metadata_queries))
                metadata_queries.append(metadata)
                metadata_results[name] = set(metadata['result_shapes'])
                return ast.copy_location(ast.Name(id=name, ctx=ast.Load()), node)

            ## Record proven metadata writes and remove them from later analysis.
            ## 记录已证明的元数据写入，并从后续分析中移除。
            #
            #  @param node Assignment statement to transform.
            #  @return Pass node for a proven write, otherwise the assignment.
            def visit_Assign(self, node):
                node = self.generic_visit(node)
                metadata_write = generated_member_metadata_write(
                    node, parameter, ref, function)
                if metadata_write is not None:
                    class_queries.append(metadata_write)
                    return ast.copy_location(ast.Pass(), node)
                documentation = method_documentation_write(node, parameter, ref)
                if documentation is None:
                    return node
                class_queries.append(documentation)
                return ast.copy_location(ast.Pass(), node)

            ## Fold a boolean negation after transforming its operand.
            ## 转换操作数后折叠布尔取反。
            #
            #  @param node Unary expression to transform.
            #  @return Boolean constant when known, otherwise the expression.
            def visit_UnaryOp(self, node):
                node = self.generic_visit(node)
                if (isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Constant)
                        and type(node.operand.value) is bool):
                    return ast.copy_location(ast.Constant(value=not node.operand.value), node)
                return node

            ## Visit only a proven branch or retain an unresolved conditional.
            ## 仅访问已证明的分支，或保留未解析的条件语句。
            #
            #  @param node Conditional statement to transform.
            #  @return Reached statements or the transformed conditional.
            def visit_If(self, node):
                node.test = self.visit(node.test)
                if isinstance(node.test, ast.Constant) and type(node.test.value) is bool:
                    # Visit only the reached suite. An unreachable opaque call
                    # is not a source effect of this normal creation path.
                    result = []
                    for statement in node.body if node.test.value else node.orelse:
                        value = self.visit(statement)
                        values = value if isinstance(value, list) else [value]
                        result.extend(values)
                        if any(isinstance(item, ast.Return) for item in values):
                            break
                    return result
                return self.generic_visit(node)

        function = NativeQueries().visit(copy.deepcopy(function))
        replacements = {}
        for node in ast.walk(function):
            charge(1)
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and isinstance(node.value.func.value, ast.Name)
                    and node.value.func.value.id == parameter):
                continue
            call = node.value
            if call.args or call.keywords:
                return False
            callee = select(call.func.attr)
            if callee is None:
                return False
            calls.append({'caller': asdict(ref), 'target': asdict(callee[0]),
                'receiver_class': asdict(target[0]), 'attribute': call.func.attr,
                'binding': 'builtin_classmethod', 'completion': 'normal_return_only',
                'argument_binding': 'implicit_receiver_only',
                'call_evidence': _span(ref, call), 'target_evidence': _span(*callee)})
            if not visit(callee):
                return False
            replacements[node] = ast.copy_location(ast.Pass(), node)

        # Transform a copy of the statement containers while retaining original
        # source nodes as evidence; validated callees contribute their own writes.
        transformed = copy.deepcopy(function)
        by_span = {(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset): value
                   for node, value in replacements.items()}

        ## Replace validated callee statements using their source coordinates.
        ## 根据源码位置替换已验证的被调用语句。
        class ReplaceSpans(ast.NodeTransformer):
            ## Replace an expression statement if its span was validated.
            ## 已验证源码范围时替换表达式语句。
            #
            #  @param node Expression statement to inspect.
            #  @return Recorded replacement or the original statement.
            def visit_Expr(self, node):
                return by_span.get((node.lineno, node.col_offset,
                                    node.end_lineno, node.end_col_offset), node)

        transformed = ReplaceSpans().visit(transformed)

        if any(isinstance(node, ast.Call) and not (
                isinstance(node.func, ast.Name) and node.func.id in ('setattr', 'delattr')
                and node.args and isinstance(node.args[0], ast.Name)
                and node.args[0].id == parameter) for node in execution_nodes(transformed)):
            return False
        for node in execution_nodes(transformed):
            if (isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, ast.Load)
                    or isinstance(node, (ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare,
                                         ast.Set, ast.Dict)) and not (_literal(node) or native_data(node))
                    or isinstance(node, (ast.JoinedStr, ast.Starred, ast.ListComp,
                                         ast.SetComp, ast.DictComp, ast.GeneratorExp))
                    or isinstance(node, ast.While) and not _literal(node.test)
                    or isinstance(node, (ast.If, ast.IfExp))
                    and not (_literal(node.test) or native_data(node.test))):
                return False
        proof = class_attribute_writes(transformed, parameter,
            lambda name: analyzer._builtin_name_status(ref, function, name) == 'confirmed_builtin',
            lambda node: node.id == '__class__', owner=ref.qualname.rsplit('.', 2)[-2],
            max_nodes=min(_CLASS_CREATION_NODE_LIMIT,
                          max(0, analyzer._class_effect_fact_steps)), charge=charge)
        if proof is None:
            return False
        attributes.extend(name for name in proof.attributes if name not in attributes)
        evidence.extend(_span(ref, node) for node in proof.evidence)
        active.remove(ref)
        completed.add(ref)
        return True

    try:
        if not visit(hook):
            return None
    except _ClassEffectLimit:
        return None
    protected = {call['attribute'] for call in calls}
    protected.update(query['input_binding']['attribute'] for query in metadata_queries)
    for signature in signatures:
        for segment in signature.get('dynamic_parameters', ()):
            for filter_fact in segment.get('filters', ()):
                table = filter_fact.get('table_binding')
                if table is not None:
                    protected.add(table['attribute'])
    if protected & (set(attributes) | set(prior_attributes)):
        return None
    for query in class_queries:
        if query.get('kind') != 'source_bound_class_metadata_query':
            continue
        prefixes = tuple(query['input_binding']['member_prefixes'])
        changed = set(attributes) | set(prior_attributes)
        if (changed & {'*', '__class__', '__bases__', '__dict__', '__mro__'}
                or any(name.startswith(prefixes) for name in changed)):
            return None
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    if module_prefix is None and (truncated or any(owner in owners and name in protected
            for owner, name, _, _, _ in writes)):
        return None
    return attributes, evidence, calls, queries, metadata_queries, signatures, class_queries
