class Cache(dict):
    def __missing__(self, key):
        alias = self
        alias.setdefault = unknown_callable
        return self.setdefault(key, 'cached')
