def fixed(allowed=0):
    return allowed


class Appender:
    def __init__(self, text):
        self.text = text

    def __call__(self, function):
        function.__doc__ = (function.__doc__ or "") + self.text
        return function


@Appender("Appended")
def factory_entry(**kwargs):
    return fixed(**kwargs)


@Appender("Appended")
def empty_doc_entry(**kwargs):
    """"""
    return fixed(**kwargs)


@Appender("Appended")
def documented_entry(**kwargs):
    """Original documentation."""
    return fixed(**kwargs)


def explicit_doc(text):
    def decorate(function):
        function.__doc__ = text
        function.__doc__ = (function.__doc__ or "") + "suffix"
        return function
    return decorate


@explicit_doc(None)
def none_entry():
    pass


@explicit_doc("")
def empty_entry():
    pass


@explicit_doc("original")
def nonempty_entry():
    pass


def choose(text):
    def decorate(function):
        function.__doc__ = (text or "fallback") + "suffix"
        return function
    return decorate


@choose(None)
def none_argument():
    pass


@choose("")
def empty_argument():
    pass


@choose("original")
def nonempty_argument():
    pass


def and_string(function):
    text = function.__doc__ or ""
    function.__doc__ = (text and "suffix") + "tail"
    return function


@and_string
def and_string_entry():
    pass


def and_nullable(function):
    function.__doc__ = (function.__doc__ and "suffix") + "tail"
    return function


@and_nullable
def and_nullable_entry():
    pass


def skipped_or(function):
    "kept" or unknown(function)
    return function


def skipped_and(function):
    "" and unknown(function)
    return function


def skipped_none(function):
    None and unknown(function)
    return function


def skipped_chain(function):
    function.__doc__ or "fallback" or unknown(function)
    return function


def skipped_nested(function):
    (function.__doc__ or "fallback") or unknown(function)
    return function


def empty_result():
    return ""


def skipped_helper_result(function):
    empty_result() and unknown(function)
    return function


def reachable_or(function):
    "" or unknown(function)
    return function


def reachable_and(function):
    "kept" and unknown(function)
    return function


def conditional_or(function):
    function.__doc__ or unknown(function)
    return function


def conditional_and(function):
    function.__doc__ and unknown(function)
    return function


def conditional_chain(function):
    function.__doc__ or "" or unknown(function)
    return function


def unknown_truth(function):
    value = unknown_value()
    value or "fallback"
    return function


def function_operand(function):
    function or "fallback"
    return function


def unknown_result(function):
    function.__doc__ = (unknown_value() or "") + "suffix"
    return function


class CustomTruth:
    def __bool__(self):
        unknown_effect()
        return True


def custom_truth(function):
    value = CustomTruth()
    function.__doc__ = (value or "") + "suffix"
    return function


def fill_empty(function):
    function.__doc__ = ""
    return "filled"


def fill_none(function):
    function.__doc__ = None
    return "filled"


def conditional_fill(function):
    function.__doc__ or fill_empty(function)
    function.__doc__ = function.__doc__ + "suffix"
    return function


def conditional_none(function):
    function.__doc__ or fill_none(function)
    function.__doc__ = function.__doc__ + "suffix"
    return function


def change_code(function):
    function.__code__ = replacement.__code__
    return "changed"


def conditional_code(function):
    function.__doc__ or change_code(function)
    return function


def replacement():
    pass


@skipped_or
def skipped_or_entry():
    pass


@skipped_and
def skipped_and_entry():
    pass


@skipped_none
def skipped_none_entry():
    pass


@skipped_chain
def skipped_chain_entry():
    pass


@skipped_nested
def skipped_nested_entry():
    pass


@skipped_helper_result
def skipped_helper_result_entry():
    pass


@reachable_or
def reachable_or_entry():
    pass


@reachable_and
def reachable_and_entry():
    pass


@conditional_or
def conditional_or_entry():
    pass


@conditional_and
def conditional_and_entry():
    pass


@conditional_chain
def conditional_chain_entry():
    pass


@unknown_truth
def unknown_truth_entry():
    pass


@function_operand
def function_operand_entry():
    pass


@unknown_result
def unknown_result_entry():
    pass


@custom_truth
def custom_truth_entry():
    pass


@conditional_fill
def conditional_fill_entry():
    pass


@conditional_none
def conditional_none_entry():
    pass


@conditional_code
def conditional_code_entry():
    pass
