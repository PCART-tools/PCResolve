# 1.0.5: builtin container methods belong to Python in every scope.
# Scope-aware tracking prevents unrelated same-name local objects from
# inheriting the container kind.

# Module-level containers: methods should be python
module_list = []
module_dict = {}

# Module-level container via comprehension: methods should be python
module_listcomp = [x for x in range(3)]


class ClassContainers:
    """Container attributes retain their literal Python shape."""

    LOOKUP = {"one": 1}

    @classmethod
    def values(cls):
        return cls.LOOKUP.values()

    @staticmethod
    def unrelated_receiver(cls):
        return cls.LOOKUP.values()


def helper_dynamic_dict_items():
    """Uniform subscript writes establish the selected item shape."""
    buckets = {}
    buckets["first"] = []
    buckets["second"] = list()
    buckets["first"].append(1)
    return buckets


class LocalBag:
    def append(self, value):
        return value


def helper_conflicting_dict_items(flag):
    """Conflicting writes must not claim a Python list receiver."""
    buckets = {}
    buckets["first"] = []
    buckets["second"] = LocalBag()
    key = "first" if flag else "second"
    buckets[key].append(1)
    return buckets


def helper_rebound_dict_items():
    """A new dict binding starts a fresh item-shape flow."""
    buckets = {}
    buckets["first"] = LocalBag()
    buckets = {}
    buckets["second"] = []
    buckets["second"].append(1)
    return buckets


def helper_build_list():
    """Function-local builtin list: .append() belongs to Python."""
    local_list = []
    local_list.append(1)
    return local_list


def helper_build_listcomp():
    """Function-local list comprehension: .append() belongs to Python."""
    local_listcomp = [x for x in range(3)]
    local_listcomp.append(4)
    return local_listcomp


def main():
    module_list.append(1)
    module_dict.get("key", "default")
    module_listcomp.append(4)

    result1 = helper_build_list()
    result2 = helper_build_listcomp()

    return result1, result2
