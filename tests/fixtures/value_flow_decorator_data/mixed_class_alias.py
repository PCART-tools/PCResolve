class Cache(dict):
    def __missing__(self, key):
        return self.setdefault(key, 'cached')


class Other:
    pass


Alias = Cache if unknown_condition else Other
unknown_register(Alias)
