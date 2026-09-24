DEFAULTS = {"out": None}
DEFAULTS["mode"] = "raise"


class Validator:
    def __init__(self, defaults, *, method):
        self.defaults = defaults
        self.method = method

    def __call__(self, args, kwargs):
        return self.defaults, self.method, args, kwargs


validator = Validator(DEFAULTS, method="kwargs")
reassigned = Validator(DEFAULTS, method="kwargs")
reassigned = unknown_factory()
unknown = unknown_factory()
modified = Validator(DEFAULTS, method="kwargs")
modified.__class__.__call__ = replacement
if condition:
    conditional = Validator(DEFAULTS, method="kwargs")


class ReboundValidator:
    def __init__(self, defaults, *, method):
        self.defaults = defaults

    def __call__(self, args, kwargs):
        return args, kwargs


ReboundValidator = unknown_factory()
class_rebound = ReboundValidator(DEFAULTS, method="kwargs")
