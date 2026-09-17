## @package pcresolve.return_resolution
#  Owner-neutral call bindings and bounded return-dependency substitution.

from dataclasses import dataclass


## Values supplied to one named parameter or lexical capture at a call site.
@dataclass(frozen=True)
class CallBinding:
    ## Binding category: parameter or capture.
    kind: str
    ## Formal parameter or capture name.
    name: object
    ## Opaque analysis values in the consumer's established order.
    values: tuple
    ## Element path within a variadic formal binding.
    target_path: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, 'values', tuple(self.values))
        object.__setattr__(self, 'target_path', tuple(self.target_path))


## Return-substitution view of one exact call occurrence.
@dataclass(frozen=True)
class ReturnCall:
    ## Snapshot-local call identifier.
    id: str
    ## Hashable function-summary key, or None for an external summary.
    target: object
    ## Normalized parameter and capture bindings.
    bindings: tuple
    ## Opt-in external/builtin return dependencies.
    return_dependencies: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, 'bindings', tuple(self.bindings))
        object.__setattr__(self, 'return_dependencies',
                           tuple(self.return_dependencies))


## Explicit fixed-point budgets for return substitution.
@dataclass(frozen=True)
class ResolutionLimits:
    ## Maximum whole-project summary iterations.
    max_iterations: int = 32
    ## Maximum distinct dependencies retained per function.
    max_dependencies: int = 2048


## Result of resolving one entry parameter through return dependencies.
@dataclass(frozen=True)
class ReturnResolution:
    ## Proven dependency records for the requested parameter.
    paths: tuple
    ## converged or bounded.
    status: str
    ## Number of fixed-point rounds performed.
    iterations: int
    ## Whether a per-function dependency budget truncated candidates.
    limited: bool = False


## Select bindings by category and exact formal name without merging paths.
#  @param bindings Iterable of CallBinding facts.
#  @param kind parameter or capture.
#  @param name Formal name.
#  @return Matching bindings in original order.
def select_call_bindings(bindings, kind, name):
    return tuple(binding for binding in bindings
                 if binding.kind == kind and binding.name == name)


## Read the first value under the existing ownership bounded-context policy.
#  @param bindings Iterable of CallBinding facts.
#  @param kind parameter or capture.
#  @param name Formal name.
#  @return First opaque value, or None when unavailable.
def first_bound_value(bindings, kind, name):
    for binding in select_call_bindings(bindings, kind, name):
        if binding.values:
            return binding.values[0]
    return None


## Combine dependency relations using the flow contract's precedence.
#  @param relations Iterable containing direct, contained, or derived.
#  @return Strongest composed relation.
def dependency_relation(relations):
    return ('derived' if 'derived' in relations else
            'contained' if 'contained' in relations else 'direct')


## Project return dependencies through one output path.
#  @param values Dependency dictionaries.
#  @param projection Requested element path.
#  @return Projected dependency dictionaries.
def select_dependencies(values, projection):
    if not projection:
        return values
    result = []
    for value in values:
        excluded = value.get('excluded_paths', [])
        if (projection and '*' not in projection
                and any(len(path) <= len(projection)
                        and path == projection[:len(path)] for path in excluded)):
            continue
        path = value.get('output_path', [])
        if path:
            if not all(a == b or a == '*' or b == '*'
                       for a, b in zip(path, projection)):
                continue
            selected = dict(value, output_path=path[len(projection):])
            remaining = [item[len(projection):] for item in excluded
                         if len(item) > len(projection)
                         and item[:len(projection)] == projection]
            if remaining:
                selected['excluded_paths'] = remaining
            else:
                selected.pop('excluded_paths', None)
            if len(projection) > len(path):
                selected['projection'] = (
                    value.get('projection', []) + projection[len(path):])
            result.append(selected)
        else:
            result.append(dict(
                value, relation='derived',
                projection=value.get('projection', []) + projection))
    return result


## Resolve one parameter through local summaries and opt-in call contracts.
#  Dependencies remain dictionaries because their evidence and condition
#  payloads belong to the value-flow adapter. This function routes dependency
#  kinds, sources, relations, and element paths, and concatenates the opaque
#  evidence, condition, and call-context sequences without interpreting them.
#  @param entry_key Hashable key of the entry summary.
#  @param parameter Entry parameter to retain in the final result.
#  @param summaries Mapping of function key to return dependency iterable.
#  @param calls Mapping of call ID to ReturnCall.
#  @param limits Explicit fixed-point budgets.
#  @return ReturnResolution with composed paths and convergence state.
def resolve_return_dependencies(entry_key, parameter, summaries, calls,
                                limits=ResolutionLimits()):
    resolved = {key: [] for key in summaries}
    limited = False

    def dependency_key(value):
        return repr({key: item for key, item in value.items()
                     if key not in ('evidence', 'conditions', 'call_context')})

    def compact(values):
        nonlocal limited
        unique = {}
        for value in values:
            key = dependency_key(value)
            if key not in unique:
                if len(unique) >= limits.max_dependencies:
                    limited = True
                    break
                unique[key] = value
        return list(unique.values())

    def sources(values, stack):
        found = []
        for value in values:
            if value['kind'] in ('parameter', 'capture'):
                found.append(dict(value, call_context=[]))
                continue
            call = calls.get(value['source'])
            if call is None or call.id in stack:
                continue
            inner_values = (resolved.get(call.target, [])
                            if call.target is not None
                            else call.return_dependencies)
            for inner in select_dependencies(
                    inner_values, value.get('projection', [])):
                kind = 'capture' if inner['kind'] == 'capture' else 'parameter'
                for binding in select_call_bindings(
                        call.bindings, kind, inner['source']):
                    target_path = list(binding.target_path)
                    outer_values = ([
                        dict(source,
                             output_path=target_path + source.get('output_path', []))
                        for source in binding.values]
                        if target_path else binding.values)
                    selected = select_dependencies(
                        outer_values, inner.get('projection', []))
                    for outer in sources(selected, stack + (call.id,)):
                        path = (value.get('output_path', [])
                                + inner.get('output_path', [])
                                + outer.get('output_path', []))
                        combined = dict(
                            outer,
                            relation=dependency_relation([
                                item['relation'] for item in
                                (value, inner, outer)]),
                            evidence=(outer['evidence'] + inner['evidence']
                                      + value['evidence']),
                            conditions=(outer.get('conditions', [])
                                        + inner.get('conditions', [])
                                        + value.get('conditions', [])),
                            call_context=(outer['call_context'] + [call.id]
                                          + inner.get('call_context', [])))
                        if path:
                            combined['output_path'] = path
                        else:
                            combined.pop('output_path', None)
                        found.append(combined)
        return compact(found)

    status = 'bounded'
    iterations = 0
    for iteration in range(limits.max_iterations):
        iterations = iteration + 1
        updated = {
            key: compact(resolved[key] + sources(summary, ()))
            for key, summary in summaries.items()}
        if all({dependency_key(value) for value in updated[key]} ==
               {dependency_key(value) for value in resolved[key]}
               for key in summaries):
            resolved = updated
            status = 'bounded' if limited else 'converged'
            break
        resolved = updated
    paths = tuple(value for value in resolved[entry_key]
                  if value['source'] == parameter
                  and value['kind'] == 'parameter')
    return ReturnResolution(paths, status, iterations, limited)
