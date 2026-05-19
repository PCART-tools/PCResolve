class Container(list):
    """A container that holds items."""

    @classmethod
    def build(cls, data):
        obj = Container()
        obj.append(data)
        return obj

    def process(self):
        """Iterates over self, method calls on loop var should be local."""
        for item in self:
            item.validate()


class Item(object):
    def validate(self):
        pass
