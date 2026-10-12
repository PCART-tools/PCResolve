from cases import Cache as BaseCache

BaseCache = unknown_class


class Cache(BaseCache):
    def __missing__(self, key):
        return self.setdefault(key, 'cached')
