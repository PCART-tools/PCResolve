from provider import first_array, no_value, python_value, second_array


class ArraySelector:
    def __init__(self, use_first):
        if use_first:
            self.transform = first_array
        else:
            self.transform = second_array

    def apply(self, value):
        result = self.transform(value)
        result.reshape(1, -1)


class MixedSelector:
    def __init__(self, use_array):
        if use_array:
            self.transform = first_array
        else:
            self.transform = python_value

    def apply(self, value):
        result = self.transform(value)
        result.copy()


class IncompleteSelector:
    def __init__(self, use_array):
        if use_array:
            self.transform = first_array
        else:
            self.transform = no_value

    def apply(self, value):
        result = self.transform(value)
        result.reshape(-1)


ArraySelector(True).apply([1, 2])
MixedSelector(True).apply("[1, 2]")
IncompleteSelector(True).apply([1, 2])
