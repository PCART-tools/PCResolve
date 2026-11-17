## @package pcresolve.flow.transfer.call_binding_state
#  Share call-argument binding facts between transfer stages.
#
#
#  Tracks argument values, binding records and issues for one call.
#  Distinguishes a proved invalid binding from an unavailable signature.
#  在单次调用中保存实参值、绑定记录及问题，并区分已证明的绑定错误和不可用的签名。



from collections import namedtuple
import ast
from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call


CallArgumentsBinding = namedtuple(
    'CallArgumentsBinding', ('params', 'positional', 'records', 'instance_parameter', 'invalid'))


class CallArgumentValues:
    def __init__(self, actual_values=None, protocol_values=None):
        # The mapping and effects phases own these mutable per-call values.
        self.actual_values = dict() if actual_values is None else actual_values
        self.protocol_values = dict() if protocol_values is None else protocol_values


def record_protocol_values(arguments, record,
                           values):
    # Preserve the original values before callability refinement.
    slot = record['argument']
    if isinstance(slot, dict) and 'position' in slot:
        position = slot['position']
        if not isinstance(position, int):
            raise TypeError('call argument position must be an integer')
        arguments.protocol_values[position] = values


def record_actual_values(arguments, record,
                         values):
    # Multiple records can map to one parameter (including unknown None).
    parameter = record['parameter']
    unique = []
    for value in arguments.actual_values.get(parameter, []) + values:
        if value not in unique:
            unique.append(value)
    arguments.actual_values[parameter] = unique


CallEffectsResult = namedtuple(
    'CallEffectsResult', ('invalid_binding', 'container_result', 'effects_complete',
                          'selected_target', 'capture_values', 'arguments', 'effective_name'))


class CallBindingMixin:
    # One analysis result owns the evidence emitted by this transfer.

    def bind_call_arguments(self, node, params,
                            positional, call
                            ):
        return bind_call_syntax(self.result, call, node, params, positional)


def unavailable_call_binding(node, call):
    # Preserve syntactic argument evidence when no signature is available.
    records = [
        {'argument': {'position': index},
         'node': arg.value if isinstance(arg, ast.Starred) else arg,
         'parameter': None, 'target_path': [], 'status': 'unresolved',
         'binding_kind': 'dynamic_starred' if isinstance(arg, ast.Starred) else 'explicit',
         'destination_kind': 'unresolved'}
        for index, arg in enumerate(node.args)]
    records.extend(
        {'argument': {'keyword': kw.arg}, 'node': kw.value, 'parameter': None,
         'target_path': [], 'status': 'unresolved', 'binding_kind': 'explicit',
         'destination_kind': 'unresolved'}
        for kw in node.keywords)
    call.binding_status = 'unavailable'
    return records


def record_argument_binding(call, record):
    # Publish one syntax binding in the call's public result schema.
    output = {
        'argument': record['argument'], 'parameter': record['parameter'],
        'status': record['status'],
        'destination_kind': record.get('destination_kind', 'unresolved'),
    }
    if record['target_path']:
        output['target_path'] = record['target_path']
    if record['binding_kind'] != 'explicit':
        output['binding_kind'] = record['binding_kind']
    call.parameter_bindings.append(output)


def unbound_default_arguments(node, binding,
                              published):
    # A dynamic expansion may supply a parameter, so its default is not proven.
    params = binding.params
    if params is None:
        return []
    supplied = {item['parameter'] for item in published if item['status'] == 'exact'}
    defaults = list(zip(binding.positional[len(binding.positional) - len(params.defaults):],
                        params.defaults))
    defaults.extend((arg, default) for arg, default in zip(params.kwonlyargs, params.kw_defaults)
                    if default is not None)
    unknown_keywords = any(keyword.arg is None and not isinstance(keyword.value, ast.Dict)
                           for keyword in node.keywords)
    unknown_positions = any(isinstance(argument, ast.Starred)
                            and not isinstance(argument.value, (ast.Tuple, ast.List))
                            for argument in node.args)
    return [(arg, default) for arg, default in defaults
            if arg.arg not in supplied and not (unknown_keywords or (
                unknown_positions and arg in binding.positional))]


def bind_call_syntax(result, call, node,
                     params, positional
                     ):
    # Bind real syntax, record its evidence and return the resulting facts.
    records, reasons = bind_ast_call(node, FunctionSignature.from_ast(params, positional))
    record_syntax_binding(result, call, records, reasons)
    return records


def record_syntax_binding(result, call,
                          records,
                          reasons):
    # Attach syntax-binding diagnostics and status to the current call.
    result.boundaries.extend({'call_id': call.id, 'reason': reason} for reason in reasons)
    for record in records:
        if record['status'] == 'missing':
            call.binding_issues.append({
                'kind': 'missing_required', 'parameter': record['parameter']})
        elif record['status'] == 'duplicate':
            call.binding_issues.append({
                'kind': 'duplicate_binding', 'parameter': record['parameter'],
                'argument': record['argument'],
                'conflicts_with': record.get('conflicts_with')})
        elif (record['status'] == 'unresolved'
              and record['binding_kind'] not in ('dynamic_starred', 'dynamic_keyword')):
            call.binding_issues.append({
                'kind': 'unresolved_argument', 'argument': record['argument']})
    if 'dynamic_argument_expansion' in reasons:
        call.binding_issues.append({'kind': 'dynamic_expansion'})
    unique = []
    for issue in call.binding_issues:
        if issue not in unique:
            unique.append(issue)
    call.binding_issues = unique
    call.binding_status = ('invalid' if any(
        issue['kind'] in ('missing_required', 'duplicate_binding', 'unresolved_argument')
        for issue in call.binding_issues) else
        'uncertain' if call.binding_issues else 'complete')


def has_invalid_binding(has_signature,
                        records):
    # Distinguish a proved binding error from an unavailable signature.
    #
    # A dynamic expansion is not itself a proved invalid binding. Missing or
    # duplicate arguments remain invalid even if no signature was available.
    if has_signature and any(
            item['status'] == 'unresolved'
            and item['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
            for item in records):
        return True
    return any(item['status'] in ('missing', 'duplicate') for item in records)
