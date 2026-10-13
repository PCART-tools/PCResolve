def fixed(allowed=0):
    return allowed


class Noop:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def tuple_missing_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = (mapping.pop('missing'),)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def list_missing_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = [mapping.pop('missing')]
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def dict_missing_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = {'value': mapping.pop('missing')}
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def annotated_tuple_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected: object = (mapping.pop('missing'),)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def annotated_list_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected: object = [mapping.pop('missing')]
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def annotated_dict_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected: object = {'value': mapping.pop('missing')}
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def return_nested_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            return (mapping.pop('missing'),)

    with Exit():
        pass
    return fixed(**kwargs)


def expression_nested_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            {'value': mapping.pop('missing')}
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def deep_nested_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = ({'value': [mapping.pop('missing')]},)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def dict_key_nested_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = {mapping.pop('missing'): 0}
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def nested_default_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = (mapping.pop('missing', None),)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def sequential_mutations(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            kwargs.pop('out', None)
            selected = (kwargs.clear(), mapping.pop('missing'))
            return True

    with Exit():
        return kwargs


def pure_literal_rhs(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            selected = ({'value': [1, None]},)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def pure_data_rhs(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            selected = ({'value': kwargs},)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def unreachable_nested_pop(**kwargs):
    class Exit(Noop):
        def __exit__(self, *exc):
            mapping = {}
            if False:
                selected = (mapping.pop('missing'),)
            return True

    with Exit():
        raise ValueError()
    return fixed(**kwargs)


def ordinary_nested_pop(**kwargs):
    return (kwargs.pop('out', None), kwargs)
