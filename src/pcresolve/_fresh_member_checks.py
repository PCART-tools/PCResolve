## @package pcresolve._fresh_member_checks
#  Source obligations for first-item validation on a bounded fresh receiver.

import ast
import copy
from dataclasses import asdict

from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts
from .keyword_validation import checks
from ._fresh_receiver import _closed_layout
from ._property_namespace import _stable_builtin_namespace
from ._class_creation import written_attributes


def _plain_prefix(statements):
    """Reject executable work before the dynamic loop/lookup boundary."""
    for statement in statements:
        if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str):
            continue
        if (isinstance(statement, ast.Assign) and statement.targets
                and all(isinstance(target, ast.Name) for target in statement.targets)):
            try:
                ast.literal_eval(statement.value)
            except (ValueError, TypeError, SyntaxError):
                return False
            continue
        return False
    return True


def _pure_branch_test(node):
    if isinstance(node, (ast.Name, ast.Constant)):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_pure_branch_test(item) for item in node.elts)
    if isinstance(node, ast.UnaryOp):
        return isinstance(node.op, (ast.Not, ast.UAdd, ast.USub)) and _pure_branch_test(node.operand)
    if isinstance(node, ast.BoolOp):
        return all(_pure_branch_test(value) for value in node.values)
    if isinstance(node, ast.Compare):
        return (_pure_branch_test(node.left)
                and all(_pure_branch_test(value) for value in node.comparators))
    if isinstance(node, ast.BinOp):
        return (_pure_branch_test(node.left) and _pure_branch_test(node.right)
                and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Mod)))
    return False


def _lookup_prefix_safe(loop, lookup):
    def locate(statements):
        for index, statement in enumerate(statements):
            if statement is lookup:
                return _plain_prefix(statements[:index])
            if isinstance(statement, ast.If) and any(
                    child is lookup for child in ast.walk(statement)):
                if not _pure_branch_test(statement.test) or not _plain_prefix(statements[:index]):
                    return False
                in_body = any(child is lookup for item in statement.body
                              for child in ast.walk(item))
                in_else = any(child is lookup for item in statement.orelse
                              for child in ast.walk(item))
                if in_body == in_else:
                    return False
                branch = statement.body if in_body else statement.orelse
                return locate(branch)
            if any(child is lookup for child in ast.walk(statement)):
                return False
        return False
    return locate(loop.body)


def _loop_prefix_safe(summary, loop):
    """Validate every statement before a nested mapping loop, failing closed on unknown scopes."""
    def locate(statements):
        for index, statement in enumerate(statements):
            if statement is loop:
                return [] if _plain_prefix(statements[:index]) else None
            if isinstance(statement, ast.With) and any(
                    child is loop for child in ast.walk(statement)):
                if not _plain_prefix(statements[:index]):
                    return None
                effects = []
                for item in statement.items:
                    matches = [record for record in summary.context_managers
                               if all(record.get('context_expression', {}).get(field)
                                      == getattr(item.context_expr, field)
                                      for field in ('lineno', 'col_offset', 'end_lineno',
                                                    'end_col_offset'))]
                    if not matches:
                        return None
                    record = matches[0]
                    def record_shape(item):
                        return (
                            item.get('enter', {}).get('return_status'),
                            item.get('enter', {}).get('effects_status'),
                            item.get('exit', {}).get('effects_status'),
                            item.get('bounded_temporary_receiver_effects'),
                        )
                    if any(record_shape(item) != record_shape(record) for item in matches[1:]):
                        return None
                    bounded = record.get('bounded_temporary_receiver_effects')
                    if bounded is not None:
                        if (bounded.get('kind') != 'bounded_temporary_receiver_attributes'
                                or bounded.get('restored_on_all_exits') is not True
                                or bounded.get('runtime_protocol_confirmed') is not False
                                or bounded.get('source_hashes') != summary.analyzer.hashes
                                or record.get('enter', {}).get('effects_status') != 'source_modeled'
                                or record.get('exit', {}).get('effects_status') != 'source_modeled'):
                            return None
                        effects.append(bounded)
                    elif (record.get('enter', {}).get('return_status') != 'source_proven'
                          or record.get('enter', {}).get('effects_status') != 'source_modeled'
                          or record.get('exit', {}).get('effects_status') != 'source_noop'):
                        return None
                nested = locate(statement.body)
                return None if nested is None else effects + nested
            if any(child is loop for child in ast.walk(statement)):
                return None
        return None
    return locate(summary.node.body)


def _safe_error_expression(node, summary, receiver):
    """Accept only literal error text, the lookup key, and type(self).__name__."""
    if isinstance(node, (ast.Constant, ast.Name)):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(_safe_error_expression(value, summary, receiver) for value in node.values)
    if isinstance(node, ast.FormattedValue):
        return (node.conversion in (-1, 114, 115, 97)
                and _safe_error_expression(node.value, summary, receiver)
                and (node.format_spec is None
                     or _safe_error_expression(node.format_spec, summary, receiver)))
    if isinstance(node, ast.Call):
        return (isinstance(node.func, ast.Name) and node.func.id == 'type'
                and summary.analyzer._builtin_name_status(
                    summary.ref, summary.node, 'type') == 'confirmed_builtin'
                and len(node.args) == 1 and not node.keywords
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == receiver)
    if isinstance(node, ast.Attribute):
        return (node.attr == '__name__' and isinstance(node.value, ast.Call)
                and _safe_error_expression(node.value, summary, receiver))
    return False


def _plain_body(node):
    return [statement for statement in node.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]


def _namespace(hierarchy):
    names = set()
    for _, cls in hierarchy:
        owner = cls.name.lstrip('_')
        for name in statement_scope_facts(cls.body).bound:
            if owner and name.startswith('__') and not name.endswith('__'):
                name = '_' + owner + name
            names.add(name)
    return names


def _value_store(summary, target, namespace, own):
    ref, node = target
    args = node.args
    parameters = args.posonlyargs + args.args
    body = _plain_body(node)
    if body and isinstance(body[-1], ast.Return) and (body[-1].value is None
            or isinstance(body[-1].value, ast.Constant) and body[-1].value.value is None):
        body = body[:-1]
    if (not isinstance(node, ast.FunctionDef) or node.decorator_list or len(parameters) != 2
            or args.vararg or args.kwarg or args.kwonlyargs or args.defaults or len(body) != 1):
        return None
    statement = body[0]
    if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
            or not isinstance(statement.targets[0], ast.Attribute)
            or not isinstance(statement.targets[0].value, ast.Name)
            or statement.targets[0].value.id != parameters[0].arg
            or statement.targets[0].attr.startswith('__')
            or statement.targets[0].attr in namespace | own
            or not isinstance(statement.value, ast.Name) or statement.value.id != parameters[1].arg):
        return None
    return {'target': asdict(ref), 'parameter': parameters[1].arg,
            'attribute': statement.targets[0].attr, 'operation': 'fresh_dictionary_value_store',
            'evidence': summary.evidence_at(ref, statement), 'completion': 'normal_return'}


## Describe a finite first-iteration member validation under a fresh source origin.
#  @param summary Source checker summary with explicit incoming allocation evidence.
#  @return Neutral static lookup obligations; actual mapping/key remains a consumer input.
def fresh_checks(summary):
    node, analyzer = summary.node, summary.analyzer
    if not isinstance(node, ast.FunctionDef) or node.decorator_list:
        return []
    obligations = checks(analyzer, summary.ref, node)
    if len(obligations) != 1:
        return []
    obligation = obligations[0]
    if len({obligation[name] for name in ('mapping_parameter', 'receiver_parameter',
            'key_variable', 'value_variable', 'lookup_variable')}) != 5:
        return []
    def matches_span(item, span):
        return all(span.get(key) == getattr(item, key)
                   for key in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'))

    loop_matches = [item for item in ast.walk(node) if isinstance(item, ast.For)
                    and matches_span(item, obligation['iteration_evidence'])]
    lookup_matches = [item for item in ast.walk(node) if isinstance(item, ast.Assign)
                      and matches_span(item, obligation['lookup_evidence'])]
    guard_tests = [item.test for item in ast.walk(node) if isinstance(item, ast.If)
                   and matches_span(item.test, obligation['guard_evidence'])]
    guard_matches = [item for item in ast.walk(node) if isinstance(item, ast.If)
                     and any(item.test is test for test in guard_tests)]
    if len(loop_matches) != 1 or len(lookup_matches) != 1 or len(guard_matches) != 1:
        return []
    loop, lookup, guard = loop_matches[0], lookup_matches[0], guard_matches[0]
    loop_effects = _loop_prefix_safe(summary, loop)
    if (loop.orelse or loop_effects is None or not _lookup_prefix_safe(loop, lookup)):
        return []
    # The lookup, raising guard and selected-value invocation must form one
    # straight-line suite inside the mapping loop. Permit a wrapper such as
    # ``ret.append(func(value))`` while preserving the exact dynamic lookup.
    invocation = None
    key_conditions = []
    suites = []
    for parent in ast.walk(loop):
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                               ast.ClassDef)) and parent is not loop:
            continue
        for field in ('body', 'orelse', 'finalbody'):
            suite = getattr(parent, field, None)
            if isinstance(suite, list):
                lookup_at = next((i for i, item in enumerate(suite) if item is lookup), None)
                if lookup_at is None or lookup_at + 2 >= len(suite) or suite[lookup_at + 1] is not guard:
                    continue
                candidate = suite[lookup_at + 2]
                if not isinstance(candidate, ast.Expr) or not isinstance(candidate.value, ast.Call):
                    continue
                call = candidate.value
                selected_call = call
                if (isinstance(call.func, ast.Attribute) and call.func.attr == 'append'
                        and len(call.args) == 1 and not call.keywords
                        and isinstance(call.args[0], ast.Call)):
                    selected_call = call.args[0]
                if (not isinstance(selected_call.func, ast.Name)
                        or selected_call.func.id != obligation['lookup_variable']
                        or len(selected_call.args) != 1 or selected_call.keywords
                        or not isinstance(selected_call.args[0], ast.Name)
                        or selected_call.args[0].id != obligation['value_variable']):
                    continue
                invocation = candidate
                if isinstance(parent, ast.If) and parent is not guard:
                    test = parent.test
                    if (not isinstance(test, ast.Compare) or len(test.ops) != 1
                            or not isinstance(test.ops[0], (ast.Eq, ast.NotEq))
                            or len(test.comparators) != 1
                            or not isinstance(test.left, ast.Name)
                            or test.left.id != obligation['key_variable']
                            or not isinstance(test.comparators[0], ast.Constant)
                            or type(test.comparators[0].value) is not str):
                        continue
                    key_conditions.append({'operator': type(test.ops[0]).__name__,
                        'value': test.comparators[0].value,
                        'branch': field,
                        'evidence': summary.evidence_at(summary.ref, test)})
                suites.append((parent, field))
                break
    if invocation is None or not isinstance(guard, ast.If) or guard.orelse:
        return []
    if (len(guard.body) != 1 or not isinstance(guard.body[0], ast.Raise)
            or guard.body[0].cause is not None):
        return []
    raised = guard.body[0].exc
    if (not isinstance(raised, ast.Call) or not isinstance(raised.func, ast.Name)
            or raised.func.id != 'AttributeError'
            or summary.analyzer._builtin_name_status(
                summary.ref, summary.node, 'AttributeError') != 'confirmed_builtin'
            or any(not _safe_error_expression(
                argument, summary, receiver=obligation['receiver_parameter'])
                   for argument in raised.args)):
        return []
    if len(key_conditions) > 1:
        return []
    receiver = obligation['receiver_parameter']
    facts = summary.incoming.get(receiver, [])
    origins = [value.get('fresh_receiver_origin') for value in facts]
    if (not origins or not origins[0] or any(origin != origins[0] for origin in origins)
            or any(value.get('instance_type') != origins[0]['allocation']['receiver_class']
                   for value in facts)):
        return []
    origin = origins[0]
    identity = origin['allocation']['receiver_class']
    if origin['current_function'] != asdict(summary.ref) or origin['parameter'] != receiver:
        return []
    temporary_attributes = set()
    for effect in loop_effects:
        if (effect.get('receiver_parameter') != receiver
                or effect.get('receiver_class') != identity
                or effect.get('receiver_origin') != origin):
            return []
        temporary_attributes.update(effect.get('attributes', ()))
    lookup_own_attributes = sorted(
        set(origin.get('own_attributes', ())) | temporary_attributes)
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    if not hierarchy:
        return []
    namespace = _namespace(hierarchy)
    hook_attributes = written_attributes(origin['allocation'].get('class_creation_hooks', []))
    hook_attributes.update(written_attributes(origin['allocation'].get('class_decorations', [])))
    namespace.update(hook_attributes)
    if len(namespace) > 2000:
        return []
    # Import-time class writes can alter the whole lookup namespace. Function-body
    # visible-class escapes elsewhere are not executed merely because they share
    # this class; writes on the active allocation and lookup prefix are separately
    # excluded by the fresh origin and prefix proofs.
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    identities = {owner for owner, _ in hierarchy}
    if (truncated or not _closed_layout(analyzer, hierarchy)
            or any(owner in identities and not (reason == 'visible_class_escape'
                    and source.qualname) for owner, _, reason, source, _ in writes)):
        return []
    try:
        stable, _ = _stable_builtin_namespace(analyzer, summary.ref,
                                               ('getattr', 'callable', 'AttributeError'))
    except _ClassEffectLimit:
        return []
    if not stable:
        return []
    stores = {}
    for name in sorted(namespace):
        if name in hook_attributes:
            continue
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
        target = analyzer._instance_method_candidate(identity['module'], identity['qualname'], name)
        if target is not None:
            store = _value_store(summary, target, namespace, set(lookup_own_attributes))
            if store is not None:
                stores[name] = store
    return [{**obligation, 'kind': 'fresh_mapping_member_check',
        'status': ('requires_single_exact_mapping_item' if not key_conditions
                   else 'requires_bounded_mapping_member'),
        'invocation_evidence': summary.evidence_at(summary.ref, invocation),
        'key_conditions': key_conditions,
        'attribute_requires_nondunder': True,
        'runtime_lookup_confirmed': False, 'receiver_class': copy.deepcopy(identity),
        'origin': copy.deepcopy(origin), 'member_names': sorted(namespace),
        'own_attributes': lookup_own_attributes, 'value_stores': stores,
        'temporary_context_effects': loop_effects,
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': list(origin['allocation']['assumptions']) + [
            'standard_builtin_namespace_preserved', 'builtin_dictionary_items_order',
            'no_unmodeled_indirect_builtin_mutation'] + sorted(set().union(*(
                set(effect.get('assumptions', ())) for effect in loop_effects)))}]
