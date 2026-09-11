## @package cases
# Independent control-flow and interprocedural value-flow gold examples.
# Expected relationships describe data values, excluding control-only dependence.


## @param value Input value.
## @return The same value.
def identity(value):
    return value


## @param value An intentionally discarded input.
## @return A constant.
def discard(value):
    return 0


## @param x Initial value.
## @param y Replacement value.
## @return The replacement only.
def reassignment(x, y):
    value = x
    value = y
    return value


## @param x Returned value.
## @param flag Branch condition only.
## @return The same value on either branch.
def control_only(x, flag):
    if flag:
        value = x
    else:
        value = x
    return value


## @param x First possible value.
## @param y Second possible value.
## @param flag Selects the branch.
## @return One of the two values.
def conditional(x, y, flag):
    return x if flag else y


## @param x Possible right operand.
## @param flag Possible returned left operand.
## @return A Python and operand, rather than only its truth value.
def short_circuit(x, flag):
    return flag and x


## @param x Initial value, retained if the loop is skipped.
## @param y Replacement when the loop runs.
## @param flag Loop condition only.
## @return The zero-iteration or one-iteration value.
def loop_zero_or_one(x, y, flag):
    value = x
    while flag:
        value = y
        break
    return value


## @param x Initial accumulator.
## @param y Assigned only before an unconditional continue.
## @return The unchanged accumulator.
def continue_skips_assignment(x, y):
    value = x
    for item in (y,):
        continue
        value = item
    return value


## @param x Value chosen by break.
## @param y Value chosen by loop else.
## @param flag Branch condition only.
## @return The selected value.
def break_or_else(x, y, flag):
    for item in (flag,):
        if item:
            value = x
            break
    else:
        value = y
    return value


## @param x Value in the matching handler.
## @param y Value in the nonmatching handler.
## @return The ValueError handler value.
def matching_exception(x, y):
    try:
        raise ValueError()
    except TypeError:
        return y
    except ValueError:
        return x


## @param x Value in a replaced return.
## @param y Value in the finally return.
## @return The finally value.
def finally_overrides_return(x, y):
    try:
        return identity(x)
    finally:
        return y


## @param x Value evaluated before finally.
## @param y Later local rebinding.
## @return The previously selected scalar value.
def finally_rebinds_local(x, y):
    value = x
    try:
        return value
    finally:
        value = y


## @param x Value assigned after an unconditional raise.
## @return No normal result exists.
def raised_exit(x):
    raise ValueError()
    return x


## @param x Initial captured binding.
## @param y Call-time captured binding.
## @return The late-bound closure value.
def closure_late_binding(x, y):
    value = x

    ## @return The call-time binding of value.
    def inner():
        return value

    value = y
    return inner()


## @param x Definition-time default value.
## @param y Later binding of the same local variable.
## @return The captured default value.
def default_snapshot(x, y):
    ## @param value Definition-time default.
    ## @return The argument or its default.
    def inner(value=x):
        return value

    x = y
    return inner()


## @param x Initial nonlocal binding.
## @param y Value written through a nonlocal declaration.
## @return The value after the inner call.
def nonlocal_write(x, y):
    value = x

    ## @return None, after updating the outer binding.
    def replace():
        nonlocal value
        value = y

    replace()
    return value


## @param x Lambda argument.
## @return The lambda's identity result.
def lambda_call(x):
    apply = lambda value: value
    return apply(x)


## @param x Passed to a callee that discards it.
## @return The callee constant.
def discarded_by_callee(x):
    return discard(x)


## @param x Passed to a callee whose result is discarded.
## @param y The actual returned value.
## @return y only.
def discarded_call_result(x, y):
    identity(x)
    return y


## @param x Routed through two calls.
## @return The composed identity value.
def chained_calls(x):
    return identity(identity(x))


## @param a One possible terminal value.
## @param b The other possible terminal value.
## @param remaining Nonnegative integer controlling recursion only.
## @return a or b according to recursion depth parity.
def mutual_left(a, b, remaining):
    if remaining <= 0:
        return a
    return mutual_right(b, a, remaining - 1)


## @param a One possible terminal value.
## @param b The other possible terminal value.
## @param remaining Nonnegative integer controlling recursion only.
## @return a or b according to recursion depth parity.
def mutual_right(a, b, remaining):
    if remaining <= 0:
        return a
    return mutual_left(b, a, remaining - 1)


## @param x Recursively forwarded input without a base return.
## @return No normal result exists.
def recursion_without_result(x):
    return recursion_without_result(x)


## @param x The first element.
## @param y The second element.
## @return Both elements in order.
def make_pair(x, y):
    return x, y


## @param x Discarded first element.
## @param y Returned second element.
## @return The second element of a callee result.
def return_projection(x, y):
    left, right = make_pair(x, y)
    return right


## @param x Returned by an async function.
## @return x after awaiting the coroutine.
async def async_identity(x):
    return x


## @param x Passed to and returned by the awaited callee.
## @return x.
async def awaited_call(x):
    return await async_identity(x)


## @param target Container to mutate when awaited.
## @param value Item to append.
## @return None.
async def async_append(target, value):
    target.append(value)


## @param x Captured by a coroutine that is never executed.
## @return An empty list.
def unawaited_effect(x):
    result = []
    async_append(result, x)
    return result


## @param x The yielded value.
## @return An iterator yielding x once.
def generate_one(x):
    yield x


## @param x The value obtained by consuming the generator.
## @return The first yielded value.
def consumed_generator(x):
    return next(generate_one(x))


## @param target Container to mutate only when the generator is advanced.
## @param value Item to append.
## @return An iterator yielding None after the append.
def generator_append(target, value):
    target.append(value)
    yield None


## @param x Captured by an iterator that is never advanced.
## @return An empty list.
def unconsumed_generator_effect(x):
    result = []
    generator_append(result, x)
    return result
