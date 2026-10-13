def fixed(allowed=0):
    return allowed


class Noop:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Suppress(Noop):
    def __exit__(self, *exc):
        return True


class Throw(Noop):
    def __exit__(self, *exc):
        raise RuntimeError()


class FailEnter(Noop):
    def __enter__(self):
        raise ValueError()


class Unknown(Noop):
    def __exit__(self, *exc):
        unknown_effect(self)


def normal(**kwargs):
    with Noop():
        pass
    return fixed(**kwargs)


def suppress_raise(**kwargs):
    with Suppress():
        raise ValueError()
    return fixed(**kwargs)


def propagate_raise(**kwargs):
    with Noop():
        raise ValueError()
    return fixed(**kwargs)


def unknown_truth(flag, **kwargs):
    class UnknownTruth(Noop):
        def __exit__(self, *exc):
            return flag

    with UnknownTruth():
        raise ValueError()
    return fixed(**kwargs)


def pending_return(**kwargs):
    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()
            return False

    with Clear():
        return kwargs


def pending_copy(**kwargs):
    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    with Clear():
        return kwargs.copy()


def pending_rebind(**kwargs):
    mapping = kwargs

    class Rebind(Noop):
        def __exit__(self, *exc):
            nonlocal mapping
            mapping = {}

    with Rebind():
        return mapping


def reverse_order(value, **kwargs):
    class Restore(Noop):
        def __exit__(self, *exc):
            kwargs.update({'restored': value})

    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    with Restore(), Clear():
        return kwargs


def nested_order(value, **kwargs):
    class Restore(Noop):
        def __exit__(self, *exc):
            kwargs.update({'restored': value})

    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    with Restore():
        with Clear():
            return kwargs


def later_enter_failure(**kwargs):
    with Suppress(), FailEnter():
        unreachable(**kwargs)
    return fixed(**kwargs)


def later_expression_failure(**kwargs):
    with Suppress(), unknown_factory():
        pass
    return fixed(**kwargs)


def exit_replaces_return(**kwargs):
    try:
        with Throw():
            return kwargs
    except RuntimeError:
        return {}


def outer_suppresses_exit_raise(**kwargs):
    with Suppress(), Throw():
        return kwargs
    return fixed(**kwargs)


def true_does_not_cancel_return(**kwargs):
    with Suppress():
        return kwargs
    unreachable(**kwargs)


def break_exit(**kwargs):
    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    for item in (0,):
        with Clear():
            break
    return fixed(**kwargs)


def continue_exit(**kwargs):
    class Clear(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    for item in (0,):
        with Clear():
            continue
        unreachable(**kwargs)
    return fixed(**kwargs)


def saved_manager(**kwargs):
    manager = Noop()
    with manager as alias:
        manager = Throw()
        alias = Suppress()
    return fixed(**kwargs)


def unknown_exit(**kwargs):
    with Unknown():
        return kwargs


def exception_sensitive(**kwargs):
    class Conditional(Noop):
        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                kwargs.clear()
                return True
            return True

    with Conditional():
        raise ValueError()
    return kwargs


def normal_sensitive(**kwargs):
    class Conditional(Noop):
        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                kwargs.clear()
            return False

    with Conditional():
        return kwargs


def finite_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            kwargs.pop('out', None)

    with Pop():
        return kwargs


def exit_pop_raises(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            kwargs.pop('out')

    try:
        with Pop():
            return kwargs
    except KeyError:
        return {}


def caught_pop_failure(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            try:
                kwargs.pop('out')
            except KeyError:
                return False

    with Pop():
        return kwargs


def caught_delete_failure(**kwargs):
    class Delete(Noop):
        def __exit__(self, *exc):
            try:
                del kwargs['out']
            except KeyError:
                return False

    with Delete():
        return kwargs


def popped_exit_result(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            return kwargs.pop('out')

    try:
        with Pop():
            return kwargs
    except KeyError:
        return kwargs


def unknown_truth_mutation(flag, **kwargs):
    class UnknownTruth(Noop):
        def __exit__(self, *exc):
            return flag

    kwargs.pop('out', None)
    with UnknownTruth():
        raise ValueError()
    return kwargs


def normal_unknown_truth(flag, **kwargs):
    class UnknownTruth(Noop):
        def __exit__(self, *exc):
            return flag

    with UnknownTruth():
        return kwargs


def dynamic_key(key, **kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            kwargs.pop(key, None)

    with Pop():
        return kwargs


def unknown_attribute(obj, **kwargs):
    class Read(Noop):
        def __exit__(self, *exc):
            value = obj.attribute
            return False

    kwargs.pop('out', None)
    with Read():
        return kwargs


def partial_unknown(**kwargs):
    class Partial(Noop):
        def __exit__(self, *exc):
            kwargs.pop('out', None)
            unknown_effect(kwargs)

    with Partial():
        return kwargs


def recursive_exit(**kwargs):
    class Recursive(Noop):
        def __exit__(self, *exc):
            with Recursive():
                pass
            return False

    with Recursive():
        return kwargs


def many_exits(**kwargs):
    with Unknown(), Unknown(), Unknown(), Unknown(), Unknown(), Unknown(), Unknown():
        return kwargs


def return_once(**kwargs):
    with Noop():
        return kwargs.pop('out', None)


def literal_truth_alias(**kwargs):
    class Aliased(Noop):
        def __exit__(self, *exc):
            flag = True
            return flag

    with Aliased():
        raise ValueError()
    return fixed(**kwargs)


def unknown_hash(key, **kwargs):
    class Hash(Noop):
        def __exit__(self, *exc):
            cache = {key: 0}
            return False

    with Hash():
        return kwargs


def unknown_iteration(obj, **kwargs):
    class Unpack(Noop):
        def __exit__(self, *exc):
            a, b = obj
            return False

    with Unpack():
        return kwargs


def unmodeled_instance_field(**kwargs):
    class Field(Noop):
        def __init__(self, mapping):
            self.mapping = mapping

        def __exit__(self, *exc):
            self.mapping.clear()

    with Field(kwargs):
        return kwargs


def captured_default_rebinding(**kwargs):
    class Capture(Noop):
        def __exit__(self, *exc):
            kwargs.clear()

    original = kwargs
    with Capture():
        kwargs = {}
        return original


def final_exit(**kwargs):
    class Final(Noop):
        def __exit__(self, *exc):
            try:
                return False
            finally:
                kwargs.clear()

    with Final():
        return kwargs


def failing_enter_changes_state(**kwargs):
    class Failing(Noop):
        def __enter__(self):
            unknown_effect(kwargs)
            raise ValueError()

    kwargs.pop('out', None)
    with Suppress(), Failing():
        unreachable(**kwargs)
    return kwargs


def alias_pop(**kwargs):
    class Alias(Noop):
        def __exit__(self, *exc):
            mapping = kwargs
            mapping.pop('out', None)

    with Alias():
        return kwargs


def nested_argument_failure(**kwargs):
    class Nested(Noop):
        def __exit__(self, *exc):
            kwargs.update({'result': kwargs.pop('out')})

    with Nested():
        return kwargs


def unknown_body(**kwargs):
    with Noop():
        assert unknown_condition
    return fixed(**kwargs)


def assigned_missing_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = mapping.pop('missing')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def annotated_missing_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected: object = mapping.pop('missing')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def assigned_present_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {'present': 1}
            selected = mapping.pop('present')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def annotated_present_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {'present': 1}
            selected: object = mapping.pop('present')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def assigned_default_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = mapping.pop('missing', None)
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def annotated_default_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected: object = mapping.pop('missing', None)
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def assigned_unknown_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            selected = kwargs.pop('out')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def annotated_unknown_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            selected: object = kwargs.pop('out')
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def caught_assigned_missing_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = True
            try:
                selected = mapping.pop('missing')
            except KeyError:
                return selected
            return False

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def caught_annotated_missing_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            mapping = {}
            selected = True
            try:
                selected: object = mapping.pop('missing')
            except KeyError:
                return selected
            return False

    with Pop():
        raise ValueError()
    return fixed(**kwargs)


def assigned_caught_open_pop(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            selected = True
            try:
                selected = kwargs.pop('out')
            except KeyError:
                return True
            return True

    with Pop():
        return kwargs


def assigned_nested_failure(**kwargs):
    class Pop(Noop):
        def __exit__(self, *exc):
            selected = kwargs.pop('out', unknown_effect(kwargs))
            return True

    with Pop():
        raise ValueError()
    return fixed(**kwargs)
