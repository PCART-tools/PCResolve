def make():
    return Worker()


class Worker:
    def convert(self, value):
        return value


def nested(value):
    return make().convert(value)


class Base:
    def echo(self, value):
        return value


class Child(Base):
    def via_super(self, value):
        return super().echo(value)
