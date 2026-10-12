class Cache(dict):
    def __missing__(self, key):
        self.__dict__['setdefault'] = unknown_callable
        return self.setdefault(key, 'cached')
