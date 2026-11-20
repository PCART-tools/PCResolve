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


## Hold the mutable actual and protocol value mappings for one call.
## 保存单次调用可变的实参值和协议值映射。
class CallArgumentValues:
    ## Store the per-call mappings without copying caller-provided ones.
    ## 保存单次调用的映射，不复制调用方传入的映射。
    #
    #  @param actual_values Values keyed by parameter, or None for a new mapping.
    #  @param protocol_values Values keyed by position, or None for a new mapping.
    #  @return None
    def __init__(self, actual_values=None, protocol_values=None):
        # The mapping and effects phases own these mutable per-call values.
        self.actual_values = dict() if actual_values is None else actual_values
        self.protocol_values = dict() if protocol_values is None else protocol_values


## Record pre-refinement protocol values for one positional argument slot.
## 记录单个位置实参槽位在修正前的协议值。
#
#  @param arguments Per-call holder receiving the protocol value mapping.
#  @param record Binding record whose argument slot identifies the position.
#  @param values Values evaluated from that argument before any refinement.
#  @return None
def record_protocol_values(arguments, record,
                           values):
    # Preserve the original values before callability refinement.
    slot = record['argument']
    if isinstance(slot, dict) and 'position' in slot:
        position = slot['position']
        if not isinstance(position, int):
            raise TypeError('call argument position must be an integer')
        arguments.protocol_values[position] = values


## Merge values under one parameter name without duplicating entries.
## 在单个形参名下合并且不重复地记录值。
#
#  @param arguments Per-call holder receiving the actual value mapping.
#  @param record Binding record naming the destination parameter.
#  @param values Actual values appended in first-seen order.
#  @return None
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


## Expose call-argument binding to transfer classes through the shared result.
## 通过共享结果向各 transfer 类提供调用实参绑定入口。
class CallBindingMixin:
    # One analysis result owns the evidence emitted by this transfer.

    ## Bind the call's real argument syntax against the target parameters.
    ## 按目标形参绑定调用的真实实参语法。
    #
    #  @param node Call expression whose arguments provide the binding syntax.
    #  @param params Target formal parameters after receiver removal.
    #  @param positional Positional parameter nodes after receiver removal.
    #  @param call Call record receiving the published binding evidence.
    #  @return Binding records produced for the call arguments.
    def bind_call_arguments(self, node, params,
                            positional, call
                            ):
        return bind_call_syntax(self.result, call, node, params, positional)


## Build unresolved binding records when no target signature is available.
## 在缺少目标签名时构造未解析的绑定记录。
#
#  @param node Call expression whose positional and keyword syntax is recorded.
#  @param call Call record marked with an unavailable binding status.
#  @return One unresolved record per positional and keyword argument.
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


## Publish one internal syntax binding in the call's public result schema.
## 将一条内部语法绑定发布到调用的公共结果结构。
#
#  @param call Call record whose parameter_bindings list receives the entry.
#  @param record Internal binding record to publish.
#  @return None
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


## List parameters whose default is not proven to be replaced by the call.
## 列出未被调用证明会替换默认值的形参。
#
#  @param node Call expression inspected for dynamic argument expansions.
#  @param binding Binding phase result exposing params and positional syntax.
#  @param published Published parameter bindings used to find exact supplies.
#  @return Parameter and default AST pairs that remain unproven.
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


## Bind real argument syntax, record its evidence and return the records.
## 绑定真实实参语法，记录绑定证据并返回绑定记录。
#
#  @param result Analysis result receiving binding boundary records.
#  @param call Call record updated with binding issues and status.
#  @param node Call expression providing the argument syntax.
#  @param params Target formal parameters converted into a signature.
#  @param positional Positional parameter nodes remaining after receiver binding.
#  @return Binding records produced for the call arguments.
def bind_call_syntax(result, call, node,
                     params, positional
                     ):
    # Bind real syntax, record its evidence and return the resulting facts.
    records, reasons = bind_ast_call(node, FunctionSignature.from_ast(params, positional))
    record_syntax_binding(result, call, records, reasons)
    return records


## Attach syntax-binding boundaries, issues and status to the current call.
## 将语法绑定边界、问题及状态附加到当前调用。
#
#  @param result Analysis result receiving binding boundary records.
#  @param call Call record updated with binding issues and status.
#  @param records Binding records whose statuses become call issues.
#  @param reasons Binding reasons that may add a boundary record.
#  @return None
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


## Decide whether the binding records prove an invalid call binding.
## 判断绑定记录是否已证明调用绑定无效。
#
#  @param has_signature Whether a callable signature was available.
#  @param records Binding records produced for the call arguments.
#  @return True when the records prove an invalid binding.
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
