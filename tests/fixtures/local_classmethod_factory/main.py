class LocalValue:
    @classmethod
    def make(cls):
        return LocalValue()

    def local_method(self):
        return None


value = LocalValue.make()
value.local_method()


class FirstValue:
    def value(self):
        return None


class SecondValue:
    def value(self):
        return None


class AmbiguousFactory:
    @classmethod
    def make(cls, flag):
        if flag:
            return FirstValue()
        return SecondValue()


ambiguous = AmbiguousFactory.make(True)
ambiguous.value()
