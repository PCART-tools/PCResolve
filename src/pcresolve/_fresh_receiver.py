## @package pcresolve._fresh_receiver
#  Partial method lookup on the unexposed prefix of a fresh source receiver.

import ast
import copy
from dataclasses import asdict

from .class_attribute_effects import _ClassEffectLimit
from .effect_facts import contains_yield
from .scope_facts import statement_scope_facts
from ._property_namespace import _stable_builtin_namespace
from ._class_creation import creation_effects, written_attributes
from ._function_observation import nonobserving_source
from ._class_decoration import member_preservation
from ._function_factory import factory_wrapper
from ._constructor_retention import retained_stores

_CUSTOM = {'__getattribute__', '__getattr__', '__setattr__', '__delattr__',
           '__slots__', '__dict__', '__class__', '__new__'}
_ASSUMPTIONS = ['source_snapshot_bindings_hold', 'builtin_type_call_and_new_binding',
    'builtin_object_allocation_empty_dictionary', 'builtin_instance_method_descriptor',
    'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation',
    'no_unmodeled_indirect_instance_mutation', 'no_external_frame_or_gc_observation',
    'python_method_lookup_precedes_argument_evaluation']


def _hooks_absent(analyzer, hierarchy, target, binding):
    modules = {owner.module for owner, _ in hierarchy}
    modules.add(target[0].module)

    def include_modules(value):
        if isinstance(value, dict):
            module = value.get('module')
            if isinstance(module, str) and module:
                modules.add(module)
            for key, child in value.items():
                if key not in ('source_hashes', 'evidence', 'hook_evidence',
                               'class_evidence', 'assumptions', 'boundaries'):
                    include_modules(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                include_modules(child)

    include_modules(binding.get('class_decorations', ()))
    include_modules(binding.get('class_creation_hooks', ()))
    selected = tuple(sorted(modules))
    cache_key = (selected, tuple(sorted(analyzer.hashes.items())))
    cache = getattr(analyzer, '_fresh_receiver_hook_premises', {})
    analyzer._fresh_receiver_metadata_guard = None
    if cache_key in cache:
        return cache[cache_key]
    guard = nonobserving_source(analyzer, modules=selected)
    if guard is None:
        cache[cache_key] = False
        analyzer._fresh_receiver_hook_premises = cache
        return False
    if guard['frame_metadata']:
        analyzer._fresh_receiver_metadata_guard = guard
    cache[cache_key] = True
    analyzer._fresh_receiver_hook_premises = cache
    return True


def _closed_layout(analyzer, hierarchy, attribute=None):
    for owner, cls in hierarchy:
        if (_CUSTOM & statement_scope_facts(cls.body).bound
                or cls.keywords or analyzer.definition_conditions.get(owner)):
            return False
    # Keep import-time class escapes and every direct class write in scope.
    # Function-body escapes elsewhere in a package are not evidence that this
    # newly allocated receiver's class was mutated before the queried call;
    # calls on the active constructor path are checked by its flow summary.
    # Counting every such escape here conflates e.g. ``type(self).method`` or
    # unrelated plotting helpers with a class binding mutation.
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    identities = {owner for owner, _ in hierarchy}
    affected = _CUSTOM | {'__bases__', '*', '__code__', '__defaults__', '__kwdefaults__'}
    if attribute is not None:
        affected.add(attribute)
    if member_preservation(analyzer, hierarchy, affected) is None:
        return False
    hooks = creation_effects(analyzer, hierarchy[0])
    return (hooks is not None and not affected & written_attributes(hooks) and not truncated
            and not any(owner in identities and name in affected
                        and not (reason == 'visible_class_escape' and source.qualname)
                        for owner, name, reason, source, _ in writes))


## Describe an empty receiver at the entry of an ordinary source class call.
#  @param analyzer Fixed source snapshot and bounded class binding machinery.
#  @param hierarchy Already checked source MRO.
#  @param target Selected initializer source definition.
#  @param binding Source class invocation fact; direct method queries are excluded.
#  @return Conditional allocation origin, or None for open layouts/namespaces.
def allocation_origin(analyzer, hierarchy, target, binding):
    if (binding.get('status') != 'source_bound' or binding.get('phase') != '__init__'
            or binding.get('query_kind') != 'source_class_call'
            or not hierarchy or not _closed_layout(analyzer, hierarchy)):
        return None
    try:
        if not _hooks_absent(analyzer, hierarchy, target, binding):
            return None
        stable, _ = _stable_builtin_namespace(analyzer, target[0],
                                               ('object', 'type', '__build_class__'))
    except _ClassEffectLimit:
        return None
    if not stable:
        return None
    parameters = target[1].args.posonlyargs + target[1].args.args
    hooks = binding.get('class_creation_hooks', [])
    allocation = {'kind': 'builtin_object_new', 'basis': 'source_snapshot',
                'entry': asdict(target[0]), 'receiver_class': copy.deepcopy(binding['receiver_class']),
                'runtime_allocation_confirmed': False,
                'source_hashes': dict(sorted(analyzer.hashes.items())),
                'assumptions': list(_ASSUMPTIONS)}
    observer = analyzer._fresh_receiver_metadata_guard
    allocation['frame_observation'] = ('native_metadata_only' if observer is not None
                                       else 'no_visible_frame_or_gc_hooks')
    if observer is not None:
        allocation['observation_guard'] = copy.deepcopy(observer)
        allocation['assumptions'] = sorted(set(allocation['assumptions'] + observer['assumptions']))
    if hooks:
        allocation['class_creation_hooks'] = copy.deepcopy(hooks)
        allocation['assumptions'].extend(binding['assumptions'])
    if binding.get('class_decorations'):
        allocation['class_decorations'] = copy.deepcopy(binding['class_decorations'])
        allocation['assumptions'] = sorted(set(allocation['assumptions'] + binding['assumptions']))
    return {'allocation': allocation,
            'current_function': asdict(target[0]), 'parameter': parameters[0].arg,
            'own_attributes': [], 'path': []}


def _pure_argument(node):
    return isinstance(node, (ast.Name, ast.Constant))


def _input_attributes_before(summary, node, receiver):
    found, statements = _truncate_before(summary.node.body, node)
    if not found:
        return set()
    parameters = {arg.arg for arg in summary.node.args.posonlyargs + summary.node.args.args
        + summary.node.args.kwonlyargs + [arg for arg in (summary.node.args.vararg,
                                                           summary.node.args.kwarg) if arg]}
    attributes = set()
    for statement in statements:
        for child in ast.walk(statement):
            if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                continue
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            value = child.value
            for target in targets:
                if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id == receiver):
                    if isinstance(value, ast.Name) and value.id in parameters:
                        attributes.add(target.attr)
                    else:
                        attributes.discard(target.attr)
    return attributes


def _input_access(node, receiver, input_attributes):
    return (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == receiver and node.attr in input_attributes)


def _receiver_argument_escapes(node, receiver, input_attributes):
    if isinstance(node, ast.Name):
        return node.id == receiver
    if isinstance(node, ast.Attribute) and _input_access(node, receiver, input_attributes):
        return False
    return any(_receiver_argument_escapes(child, receiver, input_attributes)
               for child in ast.iter_child_nodes(node))


def _lookup_argument_safe(summary, node, receiver, input_attributes, depth=0):
    """Allow finite argument expressions without opaque calls or receiver escapes."""
    if depth > 24:
        return False
    if _pure_argument(node):
        return True
    if _input_access(node, receiver, input_attributes):
        return True
    if isinstance(node, ast.Attribute) and _input_access(node.value, receiver, input_attributes):
        return True
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        module = summary.analyzer.imports.get(summary.ref.module, {}).get(node.value.id)
        return bool(module) and summary.analyzer._stable_import_name(
            summary.ref.module + '.' + node.value.id)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_lookup_argument_safe(summary, item, receiver, input_attributes, depth + 1)
                   for item in node.elts)
    if isinstance(node, ast.Dict):
        capture = summary.node.args.kwarg
        for key, value in zip(node.keys, node.values):
            if key is None:
                if (capture is None or not isinstance(value, ast.Name)
                        or value.id != capture.arg):
                    return False
            elif not _lookup_argument_safe(summary, key, receiver, input_attributes, depth + 1):
                return False
            if not _lookup_argument_safe(summary, value, receiver, input_attributes, depth + 1):
                return False
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Not)):
        return _lookup_argument_safe(summary, node.operand, receiver, input_attributes, depth + 1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult,
            ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
        return (_lookup_argument_safe(summary, node.left, receiver, input_attributes, depth + 1)
                and _lookup_argument_safe(summary, node.right, receiver, input_attributes, depth + 1))
    if isinstance(node, ast.Call):
        if node.keywords and any(keyword.arg is None for keyword in node.keywords):
            return False
        if isinstance(node.func, ast.Name):
            if summary.analyzer._builtin_name_status(summary.ref, summary.node, node.func.id) \
                    != 'confirmed_builtin':
                return False
        elif isinstance(node.func, ast.Attribute):
            if _input_access(node.func.value, receiver, input_attributes):
                pass
            elif (isinstance(node.func.value, ast.Name)
                    and summary.analyzer.imports.get(summary.ref.module, {}).get(
                        node.func.value.id)
                    and summary.analyzer._stable_import_name(
                        summary.ref.module + '.' + node.func.value.id)):
                pass
            else:
                return False
        else:
            return False
        return (all(_lookup_argument_safe(summary, arg, receiver, input_attributes, depth + 1)
                    for arg in node.args)
                and all(_lookup_argument_safe(summary, keyword.value, receiver,
                    input_attributes, depth + 1) for keyword in node.keywords))
    return False


def _source_enum_auto_member(analyzer, owner, expression):
    """Prove an imported enum member declared with stdlib ``auto()``."""
    if not isinstance(expression, ast.Attribute) or not isinstance(expression.value, ast.Name):
        return False
    alias = expression.value.id
    imported = analyzer.imports.get(owner.module, {}).get(alias)
    if (not imported or not analyzer._stable_import_name(owner.module + '.' + alias)
            or analyzer.imports.get(owner.module, {}).get('auto') != 'enum.auto'
            or not analyzer._stable_import_name(owner.module + '.auto')):
        return False
    target = analyzer._resolve_class(owner, alias)
    if target is None or target[0].module + '.' + target[0].qualname != imported:
        return False
    ref, cls = target
    hierarchy = analyzer._class_mro(ref.module, ref.qualname)
    if (not hierarchy or len(hierarchy) > 64 or cls.decorator_list or cls.keywords
            or analyzer.definition_conditions.get(ref)):
        return False
    enum_base = False
    for base_ref, base_class in hierarchy:
        if (base_class.decorator_list or base_class.keywords
                or analyzer.definition_conditions.get(base_ref)
                or {'__getattribute__', '__getattr__', '__bases__', '__class__'}
                    & statement_scope_facts(base_class.body).bound):
            return False
        for base in base_class.bases:
            if (isinstance(base, ast.Name) and base.id == 'Enum'
                    and analyzer.imports.get(base_ref.module, {}).get('Enum') == 'enum.Enum'
                    and analyzer._stable_import_name(base_ref.module + '.Enum')):
                enum_base = True
    members = [statement for statement in cls.body
               if expression.attr in statement_scope_facts([statement]).bound]
    if (not enum_base or len(members) != 1 or not isinstance(members[0], ast.Assign)
            or len(members[0].targets) != 1
            or not isinstance(members[0].targets[0], ast.Name)
            or members[0].targets[0].id != expression.attr
            or not isinstance(members[0].value, ast.Call)
            or not isinstance(members[0].value.func, ast.Name)
            or members[0].value.func.id != 'auto'
            or members[0].value.args or members[0].value.keywords):
        return False
    writes, truncated = analyzer._class_binding_writes()
    return not truncated and not any(
        written == ref and (attribute in (expression.attr, '*', '__class__', '__bases__'))
        for written, attribute, _, _, _ in writes)


def _bounded_capture_setdefault(summary, node):
    """Accept an exact builtin dict.setdefault on the current **kwargs map."""
    capture = summary.node.args.kwarg
    if (capture is None or not isinstance(node.func, ast.Attribute)
            or node.func.attr != 'setdefault' or not isinstance(node.func.value, ast.Name)
            or node.func.value.id != capture.arg or node.keywords
            or len(node.args) not in (1, 2)
            or any(isinstance(value, ast.Starred) for value in node.args)
            or not isinstance(node.args[0], ast.Constant)
            or type(node.args[0].value) is not str):
        return False
    for value in node.args[1:]:
        if _pure_argument(value):
            continue
        if (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name)
                and summary.analyzer.imports.get(summary.ref.module, {}).get(value.value.id)
                and summary.analyzer._stable_import_name(
                    summary.analyzer.imports[summary.ref.module][value.value.id] + '.' + value.attr)
                or _source_enum_auto_member(summary.analyzer, summary.ref, value)):
            continue
        return False
    location = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
    calls = [call for call in summary.calls
             if (call.lineno, call.col_offset, call.end_lineno, call.end_col_offset) == location]
    if len(calls) != 1:
        return False
    call = calls[0]
    effects = call.effects
    expected_source = '$parameter:{}:{}:{}'.format(
        summary.ref.file_path, summary.ref.qualname, capture.arg)
    if (call.callee_name != capture.arg + '.setdefault'
            or call.target is not None or call.target_candidates
            or call.target_status != 'local_container_protocol'
            or call.analysis_status != 'analyzed' or call.binding_status != 'complete'
            or call.binding_issues or len(effects) != 1 or call.result_sources == []
            or any(boundary.get('call_id') == call.id
                   and boundary.get('reason') not in {'depth_limit'}
                   for boundary in summary.result.boundaries)):
        return False
    effect = effects[0]
    mapping = effect.get('mapping')
    evidence = effect.get('evidence')
    exact_evidence = (isinstance(evidence, dict)
        and evidence.get('file_path') == summary.ref.file_path
        and (evidence.get('lineno'), evidence.get('col_offset'),
             evidence.get('end_lineno'), evidence.get('end_col_offset')) == location
        and evidence.get('source_text') == ast.unparse(node))
    receiver = [value for value in call.receiver_sources
                if value.get('kind') == 'parameter' and value.get('source') == capture.arg]
    return (effect.get('kind') == 'mapping_element'
        and effect.get('operation') == 'setdefault'
        and effect.get('object_source') == expected_source
        and effect.get('element_path') == [node.args[0].value]
        and effect.get('status') == 'bounded'
        and effect.get('completion') == 'normal_return'
        and isinstance(mapping, (list, tuple))
        and any(isinstance(value, dict) and value.get('kind') == 'parameter'
                and value.get('name') == capture.arg for value in mapping)
        and bool(receiver)
        and all(value.get('relation') in {'direct', 'contained'}
                and not any(value.get(flag) for flag in (
                    'value_incomplete', 'import_incomplete', 'import_modified'))
                for value in receiver)
        and all(value in receiver or value.get('relation') == 'contained'
                for value in call.receiver_sources)
        and exact_evidence)


def _truncate_before(statements, node):
    prefix = []
    for statement in statements:
        value = (statement.value if isinstance(statement, (ast.Expr, ast.Return, ast.Assign,
                                                            ast.AnnAssign)) else None)
        if value is node:
            return True, prefix
        if any(child is node for child in ast.walk(statement)):
            if not isinstance(statement, ast.If) or any(child is node for child in ast.iter_child_nodes(statement.test)):
                return False, []
            found, branch = _truncate_before(statement.body, node)
            updated = copy.copy(statement)
            if found:
                updated.body, updated.orelse = branch, []
            else:
                found, branch = _truncate_before(statement.orelse, node)
                if not found:
                    return False, []
                updated.body, updated.orelse = list(statement.body), branch
            prefix.append(updated)
            return True, prefix
        prefix.append(statement)
    return False, []


def _prune_known_if(statements, summary):
    parameters = summary.node.args.posonlyargs + summary.node.args.args
    environment = {}
    if summary.node.args.defaults:
        for parameter, default in zip(parameters[-len(summary.node.args.defaults):],
                                      summary.node.args.defaults):
            try:
                environment[parameter.arg] = ast.literal_eval(default)
            except (ValueError, TypeError, SyntaxError):
                pass
    facts = getattr(summary, 'incoming', {})
    for name, values in facts.items():
        if len(values) == 1 and 'literal' in values[0]:
            literal = values[0]['literal']
            if isinstance(literal, dict) and literal.get('type') == 'none':
                environment[name] = None
            elif isinstance(literal, dict) and literal.get('type') in (
                    'bool', 'int', 'float', 'str', 'bytes'):
                environment[name] = literal.get('value')
    result = []
    for statement in statements:
        if isinstance(statement, ast.If):
            test = statement.test
            known = False
            truth = False
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                    and len(test.comparators) == 1 and isinstance(test.left, ast.Name)
                    and isinstance(test.comparators[0], ast.Constant)
                    and test.comparators[0].value is None
                    and test.left.id in environment):
                known = True
                is_none = environment[test.left.id] is None
                truth = is_none if isinstance(test.ops[0], ast.Is) else not is_none
            if known:
                branch = statement.body if truth else statement.orelse
                result.extend(_prune_known_if(branch, summary))
                continue
            cloned = copy.copy(statement)
            cloned.body = _prune_known_if(statement.body, summary)
            cloned.orelse = _prune_known_if(statement.orelse, summary)
            result.append(cloned)
            continue
        result.append(statement)
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name):
                try:
                    environment[target.id] = ast.literal_eval(statement.value)
                except (ValueError, TypeError, SyntaxError):
                    environment.pop(target.id, None)
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            try:
                environment[statement.target.id] = ast.literal_eval(statement.value)
            except (ValueError, TypeError, SyntaxError):
                environment.pop(statement.target.id, None)
    return result


def _effect_prefix(summary, node, origin):
    found, statements = _truncate_before(summary.node.body, node)
    if not found:
        return None
    statements = _prune_known_if(statements, summary)
    receiver = origin['parameter']
    input_attributes = _input_attributes_before(summary, node, receiver)
    capture = summary.node.args.kwarg
    parameters = {arg.arg for arg in summary.node.args.posonlyargs + summary.node.args.args
        + summary.node.args.kwonlyargs + [arg for arg in (summary.node.args.vararg,
                                                           summary.node.args.kwarg) if arg]}
    assigned = set()
    tests = {call for statement in ast.walk(ast.Module(body=statements, type_ignores=[]))
        if isinstance(statement, ast.If)
        for call in ast.walk(statement.test) if isinstance(call, ast.Call)}
    for statement in ast.walk(ast.Module(body=statements, type_ignores=[])):
        if isinstance(statement, ast.If):
            test = statement.test
            is_none_test = (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot)) and len(test.comparators) == 1
                and isinstance(test.left, ast.Name)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None)
            length_test = (isinstance(test, ast.Call) and test in tests
                and isinstance(test.func, ast.Name) and test.func.id == 'len'
                and capture is not None and len(test.args) == 1 and not test.keywords
                and isinstance(test.args[0], ast.Name) and test.args[0].id == capture.arg
                and summary.analyzer._builtin_name_status(summary.ref, summary.node, 'len')
                    == 'confirmed_builtin')
            if not (is_none_test or length_test):
                return None
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            if isinstance(statement, ast.AnnAssign) and not (
                    isinstance(statement.annotation, ast.Constant)
                    and type(statement.annotation.value) is str):
                return None
            destinations = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if (len(destinations) == 1
                    and isinstance(destinations[0], (ast.Tuple, ast.List))
                    and isinstance(statement.value, (ast.Tuple, ast.List))
                    and len(destinations[0].elts) == len(statement.value.elts)
                    and destinations[0].elts
                    and all(isinstance(destination, ast.Attribute)
                        and isinstance(destination.value, ast.Name)
                        and destination.value.id == receiver
                        and not destination.attr.startswith('__')
                        and _pure_argument(value)
                        and not (isinstance(value, ast.Name) and value.id == receiver)
                        for destination, value in zip(
                            destinations[0].elts, statement.value.elts))):
                continue
            if len(destinations) != 1:
                return None
            destination = destinations[0]
            if isinstance(destination, ast.Name):
                if destination.id in (receiver, capture.arg if capture else None):
                    return None
                if isinstance(statement.value, ast.Name) and statement.value.id == receiver:
                    return None
                if destination.id not in parameters:
                    if destination.id in assigned:
                        return None
                    assigned.add(destination.id)
            elif isinstance(destination, ast.Attribute):
                if not isinstance(destination.value, ast.Name) or destination.value.id != receiver:
                    return None
            else:
                return None
    for call in (child for child in ast.walk(ast.Module(body=statements, type_ignores=[]))
                 if isinstance(child, ast.Call)):
        if call in tests:
            continue
        is_receiver_call = (isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == receiver
            and not call.func.attr.startswith('__')
            and all(_lookup_argument_safe(summary, value, receiver, input_attributes)
                    for value in call.args)
            and all(keyword.arg is not None and _lookup_argument_safe(
                summary, keyword.value, receiver, input_attributes)
                for keyword in call.keywords))
        is_super_call = (isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Call)
            and isinstance(call.func.value.func, ast.Name)
            and call.func.value.func.id == 'super'
            and summary.analyzer._builtin_name_status(summary.ref, summary.node, 'super')
                == 'confirmed_builtin')
        safe_external_call = False
        if isinstance(call.func, ast.Name):
            imported = summary.analyzer.imports.get(summary.ref.module, {}).get(call.func.id)
            safe_external_call = (summary.analyzer._builtin_name_status(
                summary.ref, summary.node, call.func.id) == 'confirmed_builtin'
                or bool(imported) and summary.analyzer._stable_import_name(
                    summary.ref.module + '.' + call.func.id))
        elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            imported = summary.analyzer.imports.get(summary.ref.module, {}).get(
                call.func.value.id)
            safe_external_call = bool(imported) and summary.analyzer._stable_import_name(
                summary.ref.module + '.' + call.func.value.id)
        elif (isinstance(call.func, ast.Attribute)
                and _input_access(call.func.value, receiver, input_attributes)):
            safe_external_call = True
        receiver_escapes = any(_receiver_argument_escapes(
            argument, receiver, input_attributes)
            for argument in call.args + [keyword.value for keyword in call.keywords])
        capture_setdefault = _bounded_capture_setdefault(summary, call)
        opaque_reflection = any(isinstance(value, ast.Name) and value.id in (
            'exec', 'eval', 'globals', 'locals', 'vars', 'compile', '__import__')
            for value in ast.walk(call))
        if not (is_receiver_call or is_super_call or capture_setdefault
                or safe_external_call and not receiver_escapes and not opaque_reflection):
            return None
    identity = origin['allocation']['receiver_class']
    for attribute in (child for child in ast.walk(ast.Module(body=statements, type_ignores=[]))
                      if isinstance(child, ast.Attribute)
                      and isinstance(child.value, ast.Call)
                      and isinstance(child.value.func, ast.Name)
                      and child.value.func.id == 'type'
                      and len(child.value.args) == 1
                      and isinstance(child.value.args[0], ast.Name)
                      and child.value.args[0].id == receiver):
        if summary.analyzer._builtin_name_status(summary.ref, summary.node, 'type') != 'confirmed_builtin':
            return None
        selected = summary.analyzer._instance_method_candidate(
            identity['module'], identity['qualname'], attribute.attr)
        if selected is None or selected[1].decorator_list:
            return None
    truncated = copy.copy(summary.node)
    truncated.body = statements
    allocation = origin['allocation']
    binding = {'status': 'source_bound', 'phase': '__init__',
        'receiver_class': allocation['receiver_class'],
        'source_hashes': allocation['source_hashes'],
        'class_creation_hooks': allocation.get('class_creation_hooks', []),
        'class_decorations': allocation.get('class_decorations', []),
        'assumptions': allocation.get('assumptions', [])}
    effects = retained_stores(summary.analyzer,
        summary.analyzer._class_mro(allocation['receiver_class']['module'],
                                    allocation['receiver_class']['qualname']),
        (summary.ref, truncated), binding, lookup_name=node.func.attr, return_effects=True)
    if effects is None:
        return None
    own = sorted(set(origin['own_attributes']) | set(effects['writes']))
    evidence = [summary.evidence(statement) for statement in statements]
    enum_member_used = any(_source_enum_auto_member(summary.analyzer, summary.ref, child)
        for statement in statements for call in ast.walk(statement) if isinstance(call, ast.Call)
        for child in call.args[1:])
    assumptions = ['standard_library_enum_member_protocol'] if enum_member_used else []
    return own, evidence, assumptions


def _simple_prefix(summary, node, origin):
    receiver = origin['parameter']
    own = set(origin['own_attributes'])
    hierarchy = summary.analyzer._class_mro(
        origin['allocation']['receiver_class']['module'],
        origin['allocation']['receiver_class']['qualname'])
    if not hierarchy:
        return None
    namespace = set().union(*(statement_scope_facts(cls.body).bound for _, cls in hierarchy))
    namespace.update(written_attributes(origin['allocation'].get('class_creation_hooks', [])))
    namespace.update(written_attributes(origin['allocation'].get('class_decorations', [])))
    witnesses = []
    parameters = summary.node.args.posonlyargs + summary.node.args.args + summary.node.args.kwonlyargs
    parameters += [arg for arg in (summary.node.args.vararg, summary.node.args.kwarg) if arg]
    locals_seen = {arg.arg for arg in parameters}
    for statement in summary.node.body:
        value = (statement.value if isinstance(statement, (ast.Expr, ast.Return, ast.Assign,
                                                           ast.AnnAssign)) else None)
        if value is node:
            return sorted(own), witnesses
        if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str):
            continue
        if (not isinstance(statement, (ast.Assign, ast.AnnAssign))
                or not _pure_argument(statement.value)):
            return None
        if isinstance(statement, ast.AnnAssign) and not (
                isinstance(statement.annotation, ast.Constant) and type(statement.annotation.value) is str):
            return None
        destinations = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if len(destinations) != 1:
            return None
        destination = destinations[0]
        if isinstance(destination, ast.Name):
            if destination.id in locals_seen or (isinstance(statement.value, ast.Name)
                                               and statement.value.id == receiver):
                return None
            locals_seen.add(destination.id)
        elif (isinstance(destination, ast.Attribute) and isinstance(destination.value, ast.Name)
                and destination.value.id == receiver and not destination.attr.startswith('__')
                and destination.attr not in namespace
                and not (isinstance(statement.value, ast.Name) and statement.value.id == receiver)):
            own.add(destination.attr)
        else:
            return None
        witnesses.append(summary.evidence(statement))
    return None


def _prefix(summary, node, origin):
    simple = _simple_prefix(summary, node, origin)
    return simple if simple is not None else _effect_prefix(summary, node, origin)


## Bound one plain source instance method before the receiver can escape.
#  @param summary Current source summary, with an explicit allocation origin.
#  @param node Attribute call reached in that summary.
#  @param target Selected source candidate; nominal types alone cannot authorize it.
#  @param receiver Direct receiver provenance at this call.
#  @return Lookup-prefix binding fact or None; callee/returned state is not proved.
#  Attribute lookup occurs before argument evaluation, so argument expressions
#  cannot change the already-bound source method; this does not prove their effects.
def method_binding(summary, node, target, receiver):
    if (target is None or not isinstance(node.func, ast.Attribute)
            or not isinstance(node.func.value, ast.Name) or node.func.attr.startswith('__')
            or not isinstance(target[1], ast.FunctionDef) or target[1].decorator_list
            or contains_yield(target[1]) or not receiver):
        return None
    input_attributes = _input_attributes_before(summary, node, node.func.value.id)
    kwarg = summary.node.args.kwarg
    if (not all(_lookup_argument_safe(summary, value, node.func.value.id, input_attributes)
                for value in node.args)
            or not all((keyword.arg is None and isinstance(keyword.value, ast.Name)
                        and kwarg is not None and keyword.value.id == kwarg.arg)
                       or (keyword.arg is not None and _lookup_argument_safe(
                           summary, keyword.value, node.func.value.id, input_attributes))
                       for keyword in node.keywords)):
        return None
    origins = [value.get('fresh_receiver_origin') for value in receiver]
    if (not origins[0] or any(value != origins[0] for value in origins)
            or any(value.get('relation') != 'direct' or any(value.get(flag)
                   for flag in ('projection', 'output_path',
                                'attribute_provenance', 'import_modified', 'import_incomplete'))
                   for value in receiver)):
        return None
    origin = origins[0]
    analyzer = summary.analyzer
    if (origin['current_function'] != asdict(summary.ref)
            or origin['parameter'] != node.func.value.id
            or origin['allocation']['source_hashes'] != analyzer.hashes):
        return None
    identity = origin['allocation']['receiver_class']
    if any(value.get('instance_type') != identity for value in receiver):
        return None
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    if not hierarchy or not _closed_layout(analyzer, hierarchy, node.func.attr):
        return None
    for owner, cls in hierarchy:
        members = [statement for statement in cls.body
                   if node.func.attr in statement_scope_facts([statement]).bound]
        if members:
            if members != [target[1]]:
                return None
            break
    else:
        return None
    prefix = _prefix(summary, node, origin)
    if prefix is None or node.func.attr in prefix[0]:
        return None
    return {'kind': 'fresh_source_instance_method', 'status': 'source_bound',
        'basis': 'source_snapshot', 'runtime_target_confirmed': False,
        'target': asdict(target[0]), 'receiver_class': copy.deepcopy(identity),
        'origin': copy.deepcopy(origin), 'own_attributes': prefix[0],
        'instance_state': 'lookup_prefix_only', 'descriptor': 'plain_source_function',
        'call_id': '%s:%s:%s:%s:%s' % (summary.ref.file_path, node.lineno, node.col_offset,
                                      node.end_lineno, node.end_col_offset),
        'call_evidence': summary.evidence(node), 'prefix_evidence': prefix[1],
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': sorted(set(_ASSUMPTIONS + origin['allocation']['assumptions'])), 'issues': []}


## Carry fresh receiver identity through an exact zero-argument super method call.
#  @param summary Current source summary with a fresh allocation origin.
#  @param node Exact super method call.
#  @param target PCResolve's selected next-MRO implementation.
#  @param receiver Direct receiver provenance at the call.
#  @return Invocation binding fact, or None when lookup/forwarding is open.
def super_method_binding(summary, node, target, receiver):
    if (target is None or not isinstance(node.func, ast.Attribute)
            or not isinstance(node.func.value, ast.Call)
            or not isinstance(node.func.value.func, ast.Name)
            or node.func.value.func.id != 'super' or node.func.value.args
            or node.func.value.keywords or node.func.attr != target[1].name
            or target[1].name != '__init__' or not isinstance(target[1], ast.FunctionDef)
            or contains_yield(target[1]) or not receiver):
        return None
    if (summary.analyzer._builtin_name_status(summary.ref, summary.node, 'super')
            != 'confirmed_builtin'):
        return None
    parameters = summary.node.args.posonlyargs + summary.node.args.args
    if not parameters or not isinstance(node.func.value, ast.Call):
        return None
    parameter = parameters[0].arg
    origins = [value.get('fresh_receiver_origin') for value in receiver]
    if (not origins[0] or any(value != origins[0] for value in origins)
            or any(value.get('relation') != 'direct' or value.get('source') != parameter
                   or any(value.get(flag) for flag in (
                       'projection', 'output_path', 'attribute_provenance',
                       'import_modified', 'import_incomplete', 'value_incomplete'))
                   for value in receiver)):
        return None
    origin = origins[0]
    analyzer = summary.analyzer
    if (origin.get('current_function') != asdict(summary.ref)
            or origin.get('parameter') != parameter
            or origin.get('allocation', {}).get('source_hashes') != analyzer.hashes):
        return None
    identity = origin['allocation']['receiver_class']
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    lexical = summary.ref.qualname.rpartition('.')[0]
    owner_index = next((index for index, (ref, _) in enumerate(hierarchy or ())
                        if ref.module == summary.ref.module and ref.qualname == lexical), None)
    if hierarchy is None or owner_index is None:
        return None
    expected = None
    for owner, cls in hierarchy[owner_index + 1:]:
        if target[1].name in statement_scope_facts(cls.body).bound:
            matches = analyzer._definition_index.find(owner.module,
                owner.qualname + '.' + target[1].name)
            if len(matches) != 1 or matches[0][1] is not target[1]:
                return None
            expected = matches[0]
            break
    if expected is None or expected[0] != target[0]:
        return None
    prefix = _prefix(summary, node, origin)
    if prefix is None:
        return None
    wrapper = None
    if target[1].decorator_list:
        wrapper = factory_wrapper(analyzer, target)
        forwarding = wrapper.get('forwarding') if wrapper else None
        if (forwarding is None or forwarding.get('forwarded_function') != asdict(target[0])
                or forwarding.get('argument_scope') != 'same_args_and_kwargs'
                or forwarding.get('normal_return_paths') !=
                'all_explicit_returns_forward_original_args_kwargs'):
            return None
    call_id = '%s:%s:%s:%s:%s' % (summary.ref.file_path, node.lineno,
        node.col_offset, node.end_lineno, node.end_col_offset)
    assumptions = list(_ASSUMPTIONS + origin['allocation']['assumptions'])
    if wrapper is not None:
        assumptions.extend(wrapper.get('assumptions', ()))
    return {'kind': 'fresh_source_super_method', 'status': 'source_bound',
        'basis': 'source_snapshot', 'runtime_target_confirmed': False,
        'target': asdict(target[0]), 'receiver_class': copy.deepcopy(identity),
        'origin': copy.deepcopy(origin), 'own_attributes': prefix[0],
        'instance_state': 'lookup_prefix_only',
        'descriptor': 'source_function_wrapper' if wrapper else 'plain_source_function',
        'wrapper_forwarding': copy.deepcopy(wrapper.get('forwarding')) if wrapper else None,
        'call_id': call_id, 'call_evidence': summary.evidence(node),
        'prefix_evidence': prefix[1], 'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': sorted(set(assumptions)), 'issues': []}


def incoming_origin(binding, parameter):
    origin = copy.deepcopy(binding['origin'])
    origin['current_function'] = copy.deepcopy(binding['target'])
    origin['parameter'] = parameter
    origin['own_attributes'] = list(binding['own_attributes'])
    origin['path'].append(binding['call_id'])
    return origin


def recover_lookup_receiver(summary, node, values):
    if not values or not any(value.get('value_incomplete') for value in values):
        return values
    origin = values[0].get('fresh_receiver_origin')
    if not origin or not isinstance(node.func, ast.Attribute):
        return values
    identity = origin['allocation']['receiver_class']
    target = summary.analyzer._instance_method_candidate(identity['module'], identity['qualname'],
                                                           node.func.attr)
    if method_binding(summary, node, target, values) is None:
        return values
    # Recover only this lookup's receiver, after replaying its complete fresh
    # prefix. The ambient environment and all other instance state stay unknown.
    return [{key: item for key, item in value.items()
             if key not in ('value_incomplete', 'instance_candidates')} for value in values]
