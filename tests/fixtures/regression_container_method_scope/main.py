# 1.0.5: builtin container methods belong to Python in every scope.
# Scope-aware tracking prevents unrelated same-name local objects from
# inheriting the container kind.

# Module-level containers: methods should be python
module_list = []
module_dict = {}

# Module-level container via comprehension: methods should be python
module_listcomp = [x for x in range(3)]


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
