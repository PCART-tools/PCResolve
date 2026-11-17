## @package pcresolve.flow.query.return_paths
#  Compose return dependencies from a flow result.
#
#
#  Traverses recorded dependencies to answer parameter-to-return queries.
#  沿已记录的依赖关系查询参数到返回值的传播路径。



import copy
from dataclasses import asdict
from pcresolve.facts.return_resolution import CallBinding, ReturnCall, resolve_return_dependencies


## Trace one entry parameter without modifying the result.
#  @param result Existing value-flow result.
#  @param parameter Entry parameter name.
#  @param function_type Function identity type, inferred from the entry by default.
#  @return Return paths and explicit boundaries.
def trace_parameter(result, parameter, function_type=None):
    if function_type is None:
        function_type = type(result.entry)
    ## Derive a definition key that distinguishes file, name and line.
    ## 构建区分文件、名称和行号的定义键。
    #
    #  @param ref FunctionRef or serialized function identity.
    #  @return Definition key tuple.
    def function_key(ref):
        value = asdict(ref) if isinstance(ref, function_type) else ref
        return (value['file_path'], value['qualname'], value['lineno'])

    functions = {function_key(f['function']): f for f in result.functions}
    entry_key = function_key(result.entry)
    if parameter not in functions[entry_key]['parameters']:
        raise ValueError('Unknown entry parameter: ' + parameter)
    calls = {}
    for call in result.calls:
        bindings = [
            CallBinding('capture', item.get('capture'),
                        tuple(value for value in item.get('sources', ())
                              if not value.get('object_only')),
                        tuple(item.get('target_path', ())))
            for item in call.capture_bindings]
        bindings.extend(
            CallBinding('parameter', item.get('parameter'),
                        tuple(value for value in item.get('sources', ())
                              if not value.get('object_only')),
                        tuple(item.get('target_path', ())))
            for item in call.argument_sources)
        calls[call.id] = ReturnCall(
            call.id, function_key(call.target) if call.target is not None else None,
            tuple(bindings), tuple(call.return_dependencies))
    # Compose supported return dependencies while preserving explicit boundaries.
    # 组合受支持的返回依赖，同时保留显式分析边界。
    resolution = resolve_return_dependencies(
        entry_key, parameter,
        {key: [value for value in summary['returns']
               if not value.get('object_only')]
         for key, summary in functions.items()},
        calls)
    boundaries = copy.deepcopy(result.boundaries)
    if resolution.status != 'converged':
        boundaries.append({'reason': 'return_summary_limit',
                           'iterations': resolution.iterations})
    return {'parameter': parameter, 'return_paths': list(resolution.paths),
            'status': 'flow_found' if resolution.paths else 'unknown',
            'summary_status': resolution.status,
            'summary_iterations': resolution.iterations,
            'boundaries': boundaries}
