class Base:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def request(self, allowed=0):
        return allowed


class Child(Base):
    pass
