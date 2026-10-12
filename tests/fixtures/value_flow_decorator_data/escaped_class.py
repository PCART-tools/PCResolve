class Cache(dict):
    def __missing__(self, key):
        return self.setdefault(key, 'cached')


Alias = Cache
unknown_register(Alias)
