import builtins as builtin_module
from builtins import getattr as read_attribute


class Frame:
    def module_axis(self, name):
        return builtin_module.getattr(self, name)

    def imported_axis(self, name):
        return read_attribute(self, name)

    def check(self, name):
        self.module_axis(name).equals(self)
        self.imported_axis(name).equals(self)
        builtin_module.getattr(self, name)()
        read_attribute(self, name)()

    def mixed_axis(self, name, flag):
        if flag:
            return getattr(self, name)
        return []

    def check_mixed(self, name, flag):
        self.mixed_axis(name, flag).copy()
