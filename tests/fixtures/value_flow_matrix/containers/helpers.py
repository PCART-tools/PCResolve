## @package value_flow_matrix.containers.helpers


## Append through a parameter alias without returning the inserted value.
# @param values Mutable list supplied by the caller.
# @param value Element to append.
def push_value(values, value):
    values.append(value)


## Remove all list content through the supplied parameter.
# @param values Mutable list supplied by the caller.
def clear_values(values):
    values.clear()
