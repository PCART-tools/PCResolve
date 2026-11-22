def write_payload(receiver, value):
    receiver.payload = value


def write_other_field(receiver, value):
    receiver.other = value


def write_class(receiver, value):
    receiver.__class__ = value


def write_second(unused, receiver, value):
    receiver.payload = value


def stop_before_next_argument():
    raise ValueError()


def stop_runtime_before_next_argument():
    raise RuntimeError("stop")


def stop_bare_before_next_argument():
    raise ValueError


def maybe_stop(flag):
    if flag:
        raise ValueError()
    return None


def consume_pair(first, second):
    return None


def consume_triple(first, second, third):
    return None


def write_when(receiver, value, enabled):
    if enabled:
        receiver.payload = value


class IgnoredWrite:
    @property
    def payload(self):
        return "old"

    @payload.setter
    def payload(self, value):
        pass


class Plain:
    pass


class CustomStore:
    def __setattr__(self, name, value):
        pass


class Receiver:
    def set_payload(self, value):
        self.payload = value

    def set_other(self, value):
        self.other = value

    def conditional_write(self, value, enabled):
        if enabled:
            self.set_payload(value)
        return self.payload

    def overwrite(self, first, second):
        self.set_payload(first)
        self.set_payload(second)
        return self.payload

    def read_before_write(self, value):
        previous = self.payload
        self.set_payload(value)
        return previous

    def read_after_write(self, value):
        self.set_payload(value)
        return self.payload

    def direct_write_read(self, value):
        self.payload = value
        return self.payload

    def write_other_read_payload(self, value):
        self.set_other(value)
        return self.payload

    def write_payload_read_other(self, other, value):
        self.set_payload(value)
        return other.payload

    def exact_overwrite(self, first, second):
        write_payload(self, first)
        write_payload(self, second)
        return self.payload

    def unknown_receiver_write(self, other, value):
        write_payload(other, value)
        return other.payload

    def fresh_plain_overwrite(self, first, second):
        obj = Plain()
        write_payload(obj, first)
        write_payload(obj, second)
        return obj.payload

    def fresh_descriptor_write(self, value):
        obj = IgnoredWrite()
        write_payload(obj, value)
        return obj.payload

    def fresh_custom_store_write(self, value):
        obj = CustomStore()
        write_payload(obj, value)
        return obj.payload

    def fresh_escaped_write(self, value):
        obj = Plain()
        unknown_effect(obj)
        write_payload(obj, value)
        return obj.payload

    def fresh_special_field_write(self, value):
        obj = Plain()
        write_class(obj, value)
        return obj

    def fresh_mismatched_receiver(self, other, value):
        obj = Plain()
        write_second(obj, other, value)
        return other.payload

    def internal_conditional_write(self, value, enabled):
        write_when(self, value, enabled)
        return self.payload

    def alias_write(self, value):
        alias = self
        write_payload(alias, value)
        return self.payload

    def other_object_read(self, other, value):
        write_payload(self, value)
        return other.payload

    def exact_other_field_write(self, value):
        write_other_field(self, value)
        return self.payload

    def raise_before_write(self, value, fail):
        if fail:
            raise ValueError()
        self.payload = value

    def write_before_raise(self, value):
        self.payload = value
        raise ValueError()
        self.other = value

    def write_then_raise(self, value):
        self.payload = value
        raise ValueError()

    def raise_then_write(self, value):
        raise ValueError()
        self.payload = value

    def read_after_caught_write(self, value):
        try:
            self.write_then_raise(value)
        except ValueError:
            return self.payload

    def read_after_caught_early_raise(self, value):
        try:
            self.raise_then_write(value)
        except ValueError:
            return self.payload

    def read_after_two_caught_writes(self, first, second):
        try:
            write_payload(self, first)
            self.write_then_raise(second)
        except ValueError:
            return self.payload

    def read_other_after_caught_write(self, other, value):
        try:
            self.write_then_raise(value)
        except ValueError:
            return other.payload

    def read_after_tuple_assignment_exception(self, value):
        try:
            first, second = self.write_then_raise(value), 0
        except ValueError:
            return self.payload

    def read_after_guard_exception(self, value):
        try:
            if self.write_then_raise(value):
                pass
        except ValueError:
            return self.payload

    def read_after_earlier_argument_raises(self, value):
        try:
            consume_pair(stop_before_next_argument(), write_payload(self, value))
        except ValueError:
            return self.payload

    def assign_after_earlier_argument_raises(self, value):
        try:
            result = consume_pair(stop_before_next_argument(), write_payload(self, value))
        except ValueError:
            return self.payload

    def guard_after_earlier_argument_raises(self, value):
        try:
            if consume_pair(stop_before_next_argument(), write_payload(self, value)):
                pass
        except ValueError:
            return self.payload

    def read_after_maybe_raising_argument(self, flag, value):
        try:
            consume_pair(maybe_stop(flag), write_payload(self, value))
        except ValueError:
            pass
        return self.payload

    def read_after_second_argument_raises(self, value):
        try:
            consume_triple(0, stop_before_next_argument(), write_payload(self, value))
        except ValueError:
            return self.payload

    def read_after_runtime_argument_raises(self, value):
        try:
            consume_pair(stop_runtime_before_next_argument(), write_payload(self, value))
        except RuntimeError:
            return self.payload

    def read_after_bare_argument_raises(self, value):
        try:
            consume_pair(stop_bare_before_next_argument(), write_payload(self, value))
        except ValueError:
            return self.payload

    def read_after_for_iterator_exception(self, value):
        try:
            for item in self.write_then_raise(value):
                pass
        except ValueError:
            return self.payload

    def read_after_while_guard_exception(self, value):
        try:
            while self.write_then_raise(value):
                pass
        except ValueError:
            return self.payload
