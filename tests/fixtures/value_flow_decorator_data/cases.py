def clean_text(text):
    return text


def choose_text(text, suffix=''):
    return text + suffix


class Cache(dict):
    def __missing__(self, key):
        return self.setdefault(key, clean_text('cached'))


class ChildCache(Cache):
    pass


class OverrideCache(Cache):
    def setdefault(self, key, default=None):
        unknown_effect(default)
        return default


class LookupCache(Cache):
    def __getattribute__(self, name):
        return unknown_value


class ItemCache(Cache):
    def __getitem__(self, key):
        unknown_effect(key)
        return 'cached'


class WrittenCache(Cache):
    pass


WrittenCache.setdefault = unknown_callable


class DynamicWrittenCache(Cache):
    pass


setattr(DynamicWrittenCache, 'setdefault', unknown_callable)


class UnknownBaseCache(unknown_base):
    pass


class CustomNewCache(Cache):
    def __new__(cls):
        return unknown_value


class EscapingCache(dict):
    def __missing__(self, key):
        unknown_helper(self)
        return self.setdefault(key, 'cached')


class StatefulCache(dict):
    def __init__(self):
        self.setdefault('value', 'cached')


class OpaqueDefaultCache(dict):
    def __missing__(self, key):
        return self.setdefault(key, unknown_default(key))


class AnnotatedCache(dict):
    def __missing__(self, key: unknown_annotation()):
        return self.setdefault(key, 'cached')


class Document:
    def __init__(self):
        self.params = Cache()

    def __call__(self, func):
        func.__doc__ = clean_text(func.__doc__) % self.params
        return func


class InheritedDocument(Document):
    def __init__(self):
        self.params = ChildCache()


class OverriddenDocument(Document):
    def __init__(self):
        self.params = OverrideCache()


class LookupDocument(Document):
    def __init__(self):
        self.params = LookupCache()


class ItemDocument(Document):
    def __init__(self):
        self.params = ItemCache()


class WrittenDocument(Document):
    def __init__(self):
        self.params = WrittenCache()


class DynamicWrittenDocument(Document):
    def __init__(self):
        self.params = DynamicWrittenCache()


class UnknownBaseDocument(Document):
    def __init__(self):
        self.params = UnknownBaseCache()


class CustomNewDocument(Document):
    def __init__(self):
        self.params = CustomNewCache()


class EscapingDocument(Document):
    def __init__(self):
        self.params = EscapingCache()


class StatefulDocument(Document):
    def __init__(self):
        self.params = StatefulCache()


class OpaqueDefaultDocument(Document):
    def __init__(self):
        self.params = OpaqueDefaultCache()


class AnnotatedDocument(Document):
    def __init__(self):
        self.params = AnnotatedCache()


def calculated(func):
    func.__doc__ = choose_text(suffix=' extra', text=func.__doc__)
    return func


def opaque_text(text):
    return unknown_helper(text)


def opaque_document(func):
    func.__doc__ = opaque_text(func.__doc__)
    return func


def change_code(func):
    func.__code__ = replacement.__code__
    return 'text'


def code_document(func):
    func.__doc__ = change_code(func)
    return func


def defaults_document(func):
    func.__defaults__ = (1,)
    return func


def change_kwdefaults(func):
    func.__kwdefaults__ = {'value': 1}
    return 'text'


def kwdefaults_document(func):
    func.__doc__ = change_kwdefaults(func)
    return func


def recursive_text(text):
    return recursive_text(text)


def recursive_document(func):
    func.__doc__ = recursive_text(func.__doc__)
    return func


def signature_document(func):
    func.__signature__ = unknown_signature
    return func


def unknown_format(func):
    func.__doc__ = func.__doc__ % unknown_mapping
    return func


def escaped_document(func):
    unknown_helper(func)
    return func


def joined_document(func):
    func.__doc__ = func if func.__doc__ else 'text'
    return func


@Document()
def documented():
    """%(value)s"""


@InheritedDocument()
def inherited():
    """%(value)s"""


@OverriddenDocument()
def overridden():
    """%(value)s"""


@LookupDocument()
def custom_lookup():
    """%(value)s"""


@ItemDocument()
def custom_item():
    """%(value)s"""


@WrittenDocument()
def written():
    """%(value)s"""


@DynamicWrittenDocument()
def dynamic_written():
    """%(value)s"""


@UnknownBaseDocument()
def unknown_base():
    """%(value)s"""


@CustomNewDocument()
def custom_new():
    """%(value)s"""


@EscapingDocument()
def escaping_cache():
    """%(value)s"""


@StatefulDocument()
def stateful_cache():
    """%(value)s"""


@OpaqueDefaultDocument()
def opaque_default():
    """%(value)s"""


@AnnotatedDocument()
def annotated_cache():
    """%(value)s"""


@calculated
def calculated_entry():
    """text"""


@opaque_document
def opaque_entry():
    """text"""


@code_document
def code_entry():
    """text"""


@defaults_document
def defaults_entry(value=0):
    """text"""


@signature_document
def signature_entry():
    """text"""


@kwdefaults_document
def kwdefaults_entry(*, value=0):
    """text"""


@recursive_document
def recursive_entry():
    """text"""


@unknown_format
def unknown_format_entry():
    """%(value)s"""


@escaped_document
def escaped_entry():
    """text"""


@joined_document
def joined_entry():
    """text"""


def ordinary_unknown(mapping, key):
    return mapping.setdefault(key, 'cached')
