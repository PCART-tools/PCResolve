from cases import Cache as BaseCache, Document as BaseDocument


class Cache(BaseCache):
    pass


class Document(BaseDocument):
    def __init__(self):
        self.params = Cache()


@Document()
def entry():
    """%(value)s"""
