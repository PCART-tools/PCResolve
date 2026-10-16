class NameMarker(str):
    def __radd__(self, prefix):
        return 'fixed'


def rename(owner):
    owner.__name__ = NameMarker('renamed')


class NameSetter:
    def __set_name__(self, owner, name):
        rename(owner)


def install_hook():
    import inspect
    namespace = inspect.currentframe().f_back.f_locals
    namespace['__init_subclass__'] = classmethod(lambda cls: rename(cls))
