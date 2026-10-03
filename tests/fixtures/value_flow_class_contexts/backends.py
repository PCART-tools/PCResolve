## @package value_flow_class_contexts.backends


class BaseBackend:
    ## Initialize a source-visible instance.
    def __init__(self):
        pass

    ## @return The supplied mapping.
    def initialize(self, **kwargs):
        return kwargs


class DerivedBackend:
    ## Initialize a source-visible instance.
    def __init__(self):
        pass

    ## @return The supplied mapping.
    def initialize(self, **kwargs):
        return kwargs


class OtherBackend:
    ## Initialize a source-visible instance.
    def __init__(self):
        pass

    ## @return The supplied mapping.
    def initialize(self, **kwargs):
        return kwargs
