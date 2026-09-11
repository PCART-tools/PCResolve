## @package value_flow_matrix.containers.cases
# Independent explicit-value-dependency examples. Control dependence is excluded.

from helpers import clear_values, push_value


## Select a nested tuple element without the unrelated sibling.
def nested_index(x, y):
    return [(x, y)][0][1]


## Normalize a negative index using the sequence length.
def negative_index(x, y, z):
    return [x, y, z][-2]


## Preserve the elements selected by a reverse stride.
def reverse_stride(x, y, z):
    return [x, y, z][::-2]


## Reindex the result of a slice before a second selection.
def slice_then_index(x, y, z):
    return [x, y, z][1:][0]


## A statically invalid selection cannot return its container element.
def caught_out_of_range(x, fallback):
    try:
        return [x][3]
    except IndexError:
        return fallback


## Both keys and values belong to the returned mapping.
def returned_dictionary(key, value):
    return {key: value}


## A later literal key overwrites even a potentially equal dynamic key.
def overwritten_dynamic_key(key, x, y):
    values = {key: x, 'chosen': y}
    return values['chosen']


## A missing literal key selects only the explicit default.
def missing_dictionary_default(x, fallback):
    return {'present': x}.get('missing', fallback)


## A literal entry supersedes the same key imported by unpacking.
def unpacked_dictionary_overwrite(x, y):
    return {**{'key': x}, 'key': y}['key']


## A write through an alias replaces the original stored value.
def dictionary_alias_write(x, y):
    values = {'key': x}
    alias = values
    alias['key'] = y
    return values['key']


## Clearing through a nested alias removes the former content.
def nested_alias_clear(x):
    inner = [x]
    outer = [inner]
    alias = outer[0]
    alias.clear()
    return outer


## Rebinding the local does not replace a previously captured container.
def detached_rebinding(x, y):
    inner = [x]
    outer = [inner]
    inner = [y]
    return outer


## A cycle does not alter the independent second element.
def cyclic_selected_element(x):
    values = []
    values.append(values)
    values.append(x)
    return values[1]


## Append's return is None, independent of the inserted value.
def append_result(x):
    values = []
    return values.append(x)


## A possible append creates a value dependency, not a flag dependency.
def conditional_append(x, flag):
    values = []
    if flag:
        values.append(x)
    return values


## A branch that skips clearing preserves one possible content path.
def conditional_clear(x, flag):
    values = [x]
    if flag:
        values.clear()
    return values


## Clearing on both branches removes all paths from the old content.
def unconditional_branch_clear(x, flag):
    values = [x]
    if flag:
        values.clear()
    else:
        values.clear()
    return values


## A resolved callee mutates the caller's returned container.
def cross_call_append(x):
    values = []
    push_value(values, x)
    return values


## A resolved callee removes the caller's former content.
def cross_call_clear(x):
    values = [x]
    clear_values(values)
    return values


## Comprehension keys and values both contribute explicit result content.
def dictionary_comprehension(key, value):
    return {key: value for unused in [0]}


## The predicate chooses membership without contributing an element value.
def filtered_comprehension(values, predicate):
    return [item for item in values if predicate]


## A statically empty iterable never evaluates the element expression.
def empty_comprehension(x):
    return [x for unused in ()]


## A comprehension target cannot overwrite the enclosing local binding.
def comprehension_scope(values, outside):
    item = outside
    ignored = [item for item in values]
    return item


## Literal-string join consumes the elements of its iterable argument.
def joined_values(x, y):
    return ','.join([x, y])


## Pop returns the removed element, not every element in the list.
def popped_element(x, y):
    values = [x, y]
    return values.pop(0)
