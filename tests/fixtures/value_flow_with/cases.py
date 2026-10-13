def fixed(allowed=0):
    return allowed


def with_receiver(**kwargs):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, value=0):
            return value

    with Session() as session:
        return session.request(**kwargs)


def protocol_narrowing(**kwargs):
    with SimpleSession() as session:
        return session.request(**kwargs)


class SimpleSession:
    def __enter__(self):
        alias = self
        return alias

    def __exit__(self, *args):
        return False

    def request(self, value=0):
        return value


class Other:
    def request(self, allowed=0):
        return allowed


class OtherManager(SimpleSession):
    def __enter__(self):
        return Other()


class UnknownManager(SimpleSession):
    def __enter__(self):
        return unknown_factory()


class FailingManager(SimpleSession):
    def __enter__(self):
        raise ValueError()


class UnknownExit(SimpleSession):
    def __exit__(self, *args):
        unknown_effect(self)


class UnknownEnter(SimpleSession):
    def __enter__(self):
        unknown_effect(self)
        return self


class NoneManager(SimpleSession):
    def __enter__(self):
        pass


class MixedManager(SimpleSession):
    def __enter__(self):
        if choose:
            return self
        return unknown_factory()


class DecoratedManager(SimpleSession):
    @unknown_decorator
    def __enter__(self):
        return self


class AsyncEnter(SimpleSession):
    async def __enter__(self):
        return self


class GeneratorEnter(SimpleSession):
    def __enter__(self):
        yield self


class CustomLookup(SimpleSession):
    def __getattribute__(self, name):
        return unknown_factory(name)


class WrittenManager(SimpleSession):
    pass


WrittenManager.__enter__ = unknown_enter


class DescriptorManager(SimpleSession):
    __enter__ = custom_descriptor


class RecursiveManager(SimpleSession):
    def __enter__(self):
        with self as entered:
            return entered


class ClassEnter(SimpleSession):
    @classmethod
    def __enter__(cls):
        return cls


def other_receiver(**kwargs):
    with OtherManager() as session:
        return session.request(**kwargs)


def unknown_return(**kwargs):
    with UnknownManager() as session:
        return session.request(**kwargs)


def unknown_receiver(manager, **kwargs):
    with manager as session:
        return session.request(**kwargs)


def enter_raises(**kwargs):
    with FailingManager() as session:
        return session.request(**kwargs)


def unknown_exit(**kwargs):
    with UnknownExit() as session:
        return session.request(**kwargs)


def unknown_enter(**kwargs):
    with UnknownEnter() as session:
        return session.request(**kwargs)


def none_return(**kwargs):
    with NoneManager() as session:
        return session.request(**kwargs)


def mixed_return(**kwargs):
    with MixedManager() as session:
        return session.request(**kwargs)


def decorated_enter(**kwargs):
    with DecoratedManager() as session:
        return session.request(**kwargs)


def async_enter(**kwargs):
    with AsyncEnter() as session:
        return session.request(**kwargs)


def generator_enter(**kwargs):
    with GeneratorEnter() as session:
        return session.request(**kwargs)


def customized_lookup(**kwargs):
    with CustomLookup() as session:
        return session.request(**kwargs)


def written_enter(**kwargs):
    with WrittenManager() as session:
        return session.request(**kwargs)


def descriptor_enter(**kwargs):
    with DescriptorManager() as session:
        return session.request(**kwargs)


def class_enter(**kwargs):
    with ClassEnter() as session:
        return session.request(**kwargs)


def recursive_enter(**kwargs):
    with RecursiveManager() as session:
        return session.request(**kwargs)


def no_as(**kwargs):
    with SimpleSession():
        return fixed(**kwargs)


def normal_body(**kwargs):
    with SimpleSession() as session:
        kwargs.pop('out', None)
        session.request(**kwargs)
    return fixed(**kwargs)


def unknown_exit_contents(**kwargs):
    with UnknownExit():
        kwargs.pop('out', None)
    return fixed(**kwargs)


def multiple(**kwargs):
    with SimpleSession() as first, OtherManager() as second:
        first.request(**kwargs)
        return second.request(**kwargs)


def nested(**kwargs):
    with SimpleSession() as first:
        with OtherManager() as second:
            return second.request(**kwargs)


def second_context_uses_first(**kwargs):
    with SimpleSession() as first, first as second:
        return second.request(**kwargs)


def early_return(**kwargs):
    with SimpleSession():
        return fixed(**kwargs)
    unreachable(**kwargs)


def raise_in_body(**kwargs):
    with SimpleSession():
        raise ValueError()
    unreachable(**kwargs)


def body_break(**kwargs):
    for value in values:
        with SimpleSession():
            fixed(**kwargs)
            break
        unreachable(**kwargs)


def body_continue(**kwargs):
    for value in values:
        with SimpleSession():
            fixed(**kwargs)
            continue
        unreachable(**kwargs)


async def async_with(**kwargs):
    async with unknown_factory() as session:
        return session.request(**kwargs)


class RequiredEnter(SimpleSession):
    def __enter__(self, required):
        return self


class NoReceiverEnter(SimpleSession):
    def __enter__():
        return Other()


class RequiredExit(SimpleSession):
    def __exit__(self, first, second, third, required):
        pass


class SuppressingExit(SimpleSession):
    def __exit__(self, *args):
        return True


class EnterOnly:
    def __enter__(self):
        return self

    def request(self, allowed=0):
        return allowed


def required_enter(**kwargs):
    with RequiredEnter() as session:
        return session.request(**kwargs)


def no_receiver_enter(**kwargs):
    with NoReceiverEnter() as session:
        return session.request(**kwargs)


def required_exit(**kwargs):
    with RequiredExit() as session:
        return session.request(**kwargs)


def suppressing_exit(**kwargs):
    with SuppressingExit():
        raise ValueError()
    unknown_after(**kwargs)


def missing_exit(**kwargs):
    with EnterOnly() as session:
        return session.request(**kwargs)


def unknown_exit_receiver(**kwargs):
    with UnknownExit() as session:
        session.request(**kwargs)
    return session.request(**kwargs)


def enter_effects_after_pop(**kwargs):
    kwargs.pop('out', None)
    with UnknownEnter():
        return fixed(**kwargs)


def distinct_allocations(**kwargs):
    with OtherManager() as first, OtherManager() as second:
        first.request(**kwargs)
        return second.request(**kwargs)


def second_enter_fails(**kwargs):
    with UnknownExit() as first, FailingManager() as second:
        return second.request(**kwargs)


class ReclassifiedManager(SimpleSession):
    def __init__(self):
        self.__class__ = Other


def reclassified_manager(**kwargs):
    with ReclassifiedManager() as session:
        return session.request(**kwargs)


class IdleMethodManager(SimpleSession):
    def restore(self, state):
        for key, value in state.items():
            setattr(self, key, value)


class DynamicConstructorManager(SimpleSession):
    def __init__(self):
        setattr(self, unknown_key, Other)


class BoundMutatorManager(SimpleSession):
    def __init__(self):
        self.__setattr__(unknown_key, None)


class AliasClassWriteManager(SimpleSession):
    def __init__(self):
        alias = self
        alias.__class__ = Other


class HelperClassWriteManager(SimpleSession):
    def __init__(self):
        self.replace_type()

    def replace_type(self):
        self.__class__ = Other


def idle_method_manager(**kwargs):
    with IdleMethodManager() as session:
        return session.request(**kwargs)


def dynamic_constructor_manager(**kwargs):
    with DynamicConstructorManager() as session:
        return session.request(**kwargs)


def bound_mutator_manager(**kwargs):
    with BoundMutatorManager() as session:
        return session.request(**kwargs)


def alias_class_write_manager(**kwargs):
    with AliasClassWriteManager() as session:
        return session.request(**kwargs)


def helper_class_write_manager(**kwargs):
    with HelperClassWriteManager() as session:
        return session.request(**kwargs)
