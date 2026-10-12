class dict:
    pass


class Cache(dict):
    def __missing__(self, key):
        return self.setdefault(key, 'cached')
