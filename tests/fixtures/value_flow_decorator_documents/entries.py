from documents import Base, CustomBase, CustomChild, decorated, plain, undocumented
from decorators import ConditionalDocument, Document, opaque_document
from decorators import (ConditionalNormalize, EscapingNormalize, Normalize,
                        UnknownNormalize, missing_helper, shared, unsafe_join)


@Document(Base.method.__doc__)
def source_method(**kwargs):
    return kwargs


@Document(undocumented.__doc__)
def source_function(**kwargs):
    return kwargs


@Document(plain.__doc__)
def changed_document(**kwargs):
    return kwargs


@Document(Base.method.__doc__, indents=1)
def reachable_helper(**kwargs):
    return kwargs


@Document(opaque_document())
def opaque_argument(**kwargs):
    return kwargs


@ConditionalDocument()
def unchanged_defaults(**kwargs):
    return kwargs


@ConditionalDocument(1)
def changed_defaults(**kwargs):
    return kwargs


@ConditionalDocument(unknown_mode)
def uncertain_defaults(**kwargs):
    return kwargs


@Document(CustomBase.method.__doc__)
def custom_class_lookup(**kwargs):
    return kwargs


@Document(CustomChild.method.__doc__)
def inherited_custom_lookup(**kwargs):
    return kwargs


@Document(decorated.__doc__)
def decorated_source(**kwargs):
    return kwargs


@Normalize(Base.method.__doc__)
def normalized_method(**kwargs):
    return kwargs


@Normalize()
def normalized_empty(**kwargs):
    return kwargs


@shared
def shared_normalization(**kwargs):
    return kwargs


@UnknownNormalize()
def unknown_normalization(**kwargs):
    return kwargs


@EscapingNormalize()
def escaping_normalization(**kwargs):
    return kwargs


@unsafe_join
def unknown_join(**kwargs):
    return kwargs


@missing_helper
def unavailable_cleaner(**kwargs):
    return kwargs


@ConditionalNormalize()
def conditional_mutation(**kwargs):
    return kwargs
