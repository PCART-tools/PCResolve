class Cache(dict):
    def __missing__(self, key):
        return self.setdefault(key, 'cached')


method = Cache.__missing__
method.__code__ = unknown_code
