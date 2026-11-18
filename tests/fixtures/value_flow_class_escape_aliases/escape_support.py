class NameMarker(str):
    def __radd__(self, prefix):
        return 'fixed'


def rename(owner):
    owner.__name__ = NameMarker('renamed')


def rename_first(values):
    rename(values[0])


def rename_value(values):
    rename(values['owner'])


def rename_returned(callback):
    rename(callback())
