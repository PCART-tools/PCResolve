## @package pcresolve._caller_inputs
#  Bounded caller literals, independent of library policy and runtime execution.

import ast
import math
from dataclasses import asdict

from .import_facts import import_facts
from .program_facts import SourceSpan
from .source_snapshot import FLOW_SOURCE, SourceStore
from ._stub_iterability import iterable_return_fact


def _copy_literal(value, remaining, depth):
    remaining[0] -= 1
    if remaining[0] < 0 or depth > 16:
        return None
    if value['kind'] == 'scalar':
        return dict(value)
    items = [_copy_literal(item, remaining, depth + 1) for item in value['items']]
    return dict(value, items=items) if all(item is not None for item in items) else None


def _literal(node, environment, remaining, evidence, depth=0):
    remaining[0] -= 1
    if remaining[0] < 0 or depth > 16:
        return None
    if isinstance(node, ast.Name):
        known = environment.get(node.id)
        if known is not None:
            evidence.extend(known[1])
            return _copy_literal(known[0], remaining, depth)
        return None
    if isinstance(node, ast.Constant):
        value = node.value
        if type(value) in (str, int, bool, type(None)):
            return {'kind': 'scalar', 'type': type(value).__name__, 'value': value}
        if type(value) is float and math.isfinite(value):
            return {'kind': 'scalar', 'type': 'float', 'value': value}
        if type(value) is bytes:
            return {'kind': 'scalar', 'type': 'bytes', 'value_hex': value.hex()}
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_literal(child, environment, remaining, evidence, depth + 1)
                  for child in node.elts]
        if all(value is not None for value in values):
            return {'kind': 'list' if isinstance(node, ast.List) else 'tuple', 'items': values}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _literal(node.operand, environment, remaining, evidence, depth + 1)
        if value and value.get('kind') == 'scalar' and value.get('type') in ('int', 'float'):
            if isinstance(node.op, ast.USub):
                value['value'] = -value['value']
            return value
    return None


def _has_effectful_syntax(node):
    return any(isinstance(child, (ast.Call, ast.Attribute, ast.Subscript,
                                 ast.Await, ast.Yield, ast.YieldFrom,
                                 ast.NamedExpr, ast.BinOp, ast.Compare,
                                 ast.BoolOp, ast.IfExp, ast.Starred,
                                 ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
               for child in ast.walk(node))


def _target(node, origins, module_origins):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name) or node.id not in origins:
        return None
    if parts and node.id not in module_origins:
        return None
    head = origins[node.id]
    return '.'.join([head] + list(reversed(parts)))


def _module_call_assignment(node, origins, module_origins):
    """Skip a bounded imported-module call assigned to a name as an unknown value."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    head = node.func
    while isinstance(head, ast.Attribute):
        head = head.value
    if (not isinstance(head, ast.Name) or head.id not in module_origins
            or _target(node.func, origins, module_origins) is None
            or any(_has_effectful_syntax(value) for value in node.args)
            or any(keyword.arg is None or _has_effectful_syntax(keyword.value)
                   for keyword in node.keywords)):
        return False
    return True


## Read finite literals and bounded return protocols at an exact top-level call site.
#  @param callsite Full SourceSpan, never a line-only or terminal-name selection.
#  @param store Optional source cache that rereads content for each query.
#  @param max_nodes Finite source-walk bound.
#  @param max_items Finite literal construction bound across the query.
#  @return Source literal records or explicit boundaries; no execution/reachability assertion.
def literal_inputs(callsite, store=None, max_nodes=50000, max_items=2000, import_roots=()):
    if (type(max_nodes) is not int or type(max_items) is not int
            or max_nodes <= 0 or max_items <= 0):
        raise ValueError('Caller input budgets must be positive integers')
    result = {'kind': 'source_callsite_inputs', 'status': 'unconfirmed',
        'scope': 'argument_reads_on_normal_module_prefix', 'runtime_values_observed': False,
        'arguments': [], 'boundaries': [], 'source_hashes': {},
        'supporting_source_sha256': {},
        'assumptions': ['source_snapshot_bindings_hold', 'standard_module_global_lookup',
                        'no_external_module_global_mutation']}

    def fail(reason):
        result['boundaries'].append({'reason': reason})
        return result

    fields = ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')
    if (not isinstance(callsite, SourceSpan)
            or not isinstance(callsite.file_path, str) or not callsite.file_path
            or not all(type(getattr(callsite, key)) is int for key in fields)):
        return fail('caller_callsite_span_unconfirmed')
    path = callsite.file_path
    document = (store or SourceStore()).snapshot([path], FLOW_SOURCE).documents[path]
    if document.error is not None:
        return fail('caller_source_unavailable')
    result['source_hashes'][path] = document.sha256
    nodes = []
    for node in ast.walk(document.tree):
        nodes.append(node)
        if len(nodes) > max_nodes:
            return fail('caller_input_budget')
    matches = [n for n in nodes if isinstance(n, ast.Call)
               and all(getattr(n, key) == getattr(callsite, key) for key in fields)]
    if len(matches) != 1:
        return fail('caller_callsite_unconfirmed')
    call = matches[0]
    owner = next((n for n in document.tree.body if getattr(n, 'value', None) is call), None)
    if not isinstance(owner, (ast.Assign, ast.AnnAssign, ast.Expr)):
        return fail('caller_callsite_not_module_expression')
    if any(_has_effectful_syntax(argument) for argument in call.args):
        return fail('caller_argument_evaluation_unconfirmed')
    if any(_has_effectful_syntax(keyword.value) for keyword in call.keywords):
        return fail('caller_argument_evaluation_unconfirmed')
    environment, origins, origin_evidence = {}, {}, {}
    module_origins, remaining = set(), [max_items]
    protocols, protocol_evidence = {}, {}

    def span(node):
        return asdict(SourceSpan.from_ast(path, node))

    for statement in document.tree.body:
        if statement is owner:
            break
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            # Imports bind only their declared local names. Keep independent
            # earlier bindings under the existing no-external-module-global-
            # mutation assumption, while a new import may replace its own name.
            for fact in import_facts(statement):
                if fact.wildcard or fact.level:
                    continue
                if fact.python_binding.startswith('__') and fact.python_binding.endswith('__'):
                    return fail('caller_namespace_customization_unconfirmed')
                origins[fact.python_binding] = (
                    fact.name if fact.kind == 'import' and fact.asname
                    else fact.python_binding if fact.kind == 'import'
                    else fact.module + '.' + fact.name)
                origin_evidence[fact.python_binding] = [span(statement)]
                if fact.kind == 'import':
                    module_origins.add(fact.python_binding)
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if (not all(isinstance(target, ast.Name) for target in targets)
                    or any(target.id.startswith('__') and target.id.endswith('__')
                           for target in targets)
                    or statement.value is None
                    or isinstance(statement, ast.AnnAssign)
                    and not isinstance(statement.annotation, (ast.Name, ast.Constant))):
                return fail('caller_prefix_effect_unconfirmed')
            if _has_effectful_syntax(statement.value):
                if not _module_call_assignment(statement.value, origins, module_origins):
                    return fail('caller_prefix_effect_unconfirmed')
                target = _target(statement.value.func, origins, module_origins)
                protocol = iterable_return_fact(target, import_roots) if target else None
                # Call results are never executed. A result receives a narrow
                # protocol fact only when every overload in a bounded installed
                # stub returns a declared iterable type.
                for target in targets:
                    environment.pop(target.id, None)
                    origins.pop(target.id, None)
                    origin_evidence.pop(target.id, None)
                    module_origins.discard(target.id)
                    protocols.pop(target.id, None)
                    protocol_evidence.pop(target.id, None)
                    if protocol is not None:
                        protocols[target.id] = protocol
                        protocol_evidence[target.id] = [span(statement)]
                        result['supporting_source_sha256'].update(protocol['source_hashes'])
                continue
            evidence = [span(statement)]
            value = _literal(statement.value, environment, remaining, evidence)
            origin = (_target(statement.value, origins, module_origins)
                      if isinstance(statement.value, ast.Name) else None)
            module_alias = (isinstance(statement.value, ast.Name)
                            and statement.value.id in module_origins)
            source_evidence = (list(origin_evidence.get(statement.value.id, []))
                               if isinstance(statement.value, ast.Name) else [])
            protocol = (protocols.get(statement.value.id)
                        if isinstance(statement.value, ast.Name) else None)
            protocol_sources = (list(protocol_evidence.get(statement.value.id, []))
                                if isinstance(statement.value, ast.Name) else [])
            if value is None and not isinstance(statement.value, (ast.Name, ast.Constant)):
                return fail('caller_prefix_value_unconfirmed')
            for target in targets:
                environment.pop(target.id, None)
                origins.pop(target.id, None)
                origin_evidence.pop(target.id, None)
                module_origins.discard(target.id)
                protocols.pop(target.id, None)
                protocol_evidence.pop(target.id, None)
                if value is not None:
                    environment[target.id] = value, list(evidence)
                if protocol is not None:
                    protocols[target.id] = protocol
                    protocol_evidence[target.id] = protocol_sources + [span(statement)]
                if origin is not None:
                    origins[target.id] = origin
                    origin_evidence[target.id] = source_evidence + [span(statement)]
                    if module_alias:
                        module_origins.add(target.id)
            continue
        if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)):
            continue
        return fail('caller_prefix_effect_unconfirmed')
    qualified = _target(call.func, origins, module_origins)
    target_status = 'source_bound'
    if qualified is None:
        # An exact method-expression receiver may be an object returned by an
        # opaque factory. Preserve argument facts without claiming its runtime
        # target; the consumer must match this exact function expression to an
        # independently supplied API identity.
        if not (isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)):
            return fail('caller_target_binding_unconfirmed')
        qualified = None
        target_status = 'receiver_expression_only'
    head = call.func
    while isinstance(head, ast.Attribute):
        head = head.value
    binding_evidence = ([span(call.func)] if target_status == 'receiver_expression_only'
                        else origin_evidence[head.id])
    result.update(target=qualified, target_status=target_status,
                  target_expression=(ast.dump(call.func, include_attributes=False)
                                     if target_status == 'receiver_expression_only' else None),
                  call_evidence=span(call),
                  call_syntax=ast.dump(call, include_attributes=False),
                  target_binding_evidence=binding_evidence)
    arguments = [({'position': index}, argument) for index, argument in enumerate(call.args)]
    arguments.extend(({'keyword': keyword.arg}, keyword.value) for keyword in call.keywords)
    if any(isinstance(argument, ast.Starred) for argument in call.args) or any(
            keyword.arg is None for keyword in call.keywords):
        return fail('caller_argument_expansion_unconfirmed')
    for slot, argument in arguments:
        evidence = [span(argument)]
        value = _literal(argument, environment, remaining, evidence)
        if value is None and any(not isinstance(child, (
                ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Load))
                for child in ast.walk(argument)):
            result['arguments'] = []
            return fail('caller_argument_evaluation_unconfirmed')
        record = {'argument': slot, 'evidence': evidence,
                  'status': 'source_literal' if value is not None else 'unproven'}
        if value is not None:
            record['value'] = value
        elif isinstance(argument, ast.Name) and argument.id in protocols:
            protocol = protocols[argument.id]
            record.update(status='source_protocol', protocol={
                'kind': 'iterable', 'basis': protocol['basis'],
                'call_target': protocol['target'],
                'supporting_source_sha256': protocol['source_hashes'],
            }, evidence=evidence + protocol_evidence[argument.id])
        result['arguments'].append(record)
    if remaining[0] < 0:
        result['arguments'] = []
        return fail('caller_input_budget')
    result['status'] = 'source_bound'
    return result
