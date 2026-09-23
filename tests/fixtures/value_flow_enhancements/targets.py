class Root:
    def inherited(self, value):
        return value

    def __new__(cls, value=None, **options):
        return object.__new__(cls)


class MixIn:
    pass


class Child(MixIn, Root):
    @classmethod
    def build(cls, value, **options):
        return super(Child, cls).__new__(cls, value, **options)

    def forward(self, value):
        return super().inherited(value)


class Product:
    def __init__(self, value, **options):
        self.value = value

    def consume(self, value):
        return value


def construct(value, **options):
    return Product(value, **options)


def construct_new(value):
    return Root(value)


def local_receiver(value):
    product = Product(value)
    return product.consume(value)


class Alpha:
    def consume(self, value):
        return value


class Beta:
    def consume(self, value):
        return value


def bounded_receiver(flag, value):
    if flag:
        product = Alpha()
    else:
        product = Beta()
    return product.consume(value)


from unavailable import External


class Uncertain(External, Root):
    def forward(self, value):
        return super().inherited(value)


def nested_constructor(value):
    class Nested:
        def __init__(self, item):
            self.item = item

    return Nested(value)


class Common:
    def inherited(self, value):
        return value


class Left(Common):
    pass


class Right(Common):
    def inherited(self, value):
        return value


class Diamond(Left, Right):
    def forward(self, value):
        return super().inherited(value)
