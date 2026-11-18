from escape_support import NameMarker, rename, rename_first, rename_returned, rename_value


class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    @classmethod
    def touch(cls):
        name = '_cache_' + cls.__name__
        setattr(cls, name, {})
        return getattr(cls, name)

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class ListEscape(Base):
    pass


items = [ListEscape]
rename_first(items)


class DictEscape(Base):
    pass


mapping = {'owner': DictEscape}
rename_value(mapping)


class TupleAliasEscape(Base):
    pass


packed = (TupleAliasEscape,)
alias = packed
rename_first(alias)


class BranchContainerEscape(Base):
    pass


flag = True
branch = [BranchContainerEscape] if flag else []
rename_first(branch)


class LambdaEscape(Base):
    pass


callback = lambda: LambdaEscape
rename_returned(callback)


class ReturnEscape(Base):
    pass


def supplier():
    return ReturnEscape


rename_returned(supplier)


class StoredEscape(Base):
    pass


slots = [None]
slots[0] = StoredEscape
rename_first(slots)


class ConstructorEscape(Base):
    def __new__(cls, **kwargs):
        return cls


rename(ConstructorEscape())


class DormantContainer(Base):
    pass


unused = [DormantContainer]


class ShadowedContainer(Base):
    pass


shadowed = [ShadowedContainer]


def unrelated(shadowed):
    rename_first(shadowed)


class UnrelatedContainer(Base):
    pass


rename_first([type('Other', (), {})])


class ProjectedWrite(Base):
    pass


projected_items = [ProjectedWrite]
projected = projected_items[0]
projected.__name__ = NameMarker('renamed')


class DestructuredEscape(Base):
    pass


destructured, ignored = (DestructuredEscape, 0)
rename(destructured)


class InvokedCapture(Base):
    pass


captured = lambda: rename(InvokedCapture)
captured()


class DefaultCapture(Base):
    pass


default_capture = lambda owner=DefaultCapture: owner
rename_returned(default_capture)


class ExtendedContainer(Base):
    pass


extended = []
extended += [ExtendedContainer]
rename_first(extended)


class ShadowedLambda(Base):
    pass


lambda_capture = [ShadowedLambda]
shadowed_callback = lambda lambda_capture: lambda_capture
shadowed_callback(None)
