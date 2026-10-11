from decorators import (
    identity, document, conditional_document, factory, Document,
    document_instance, super_instance, change_code, change_alias_code, indirect_code,
    change_defaults, change_kwdefaults, change_signature, opaque, capture, escape,
    dynamic, replacement, mixed, incomplete, recursive, final_change,
    UnsafeDocument, CustomDocument, RewrittenDocument, rebound,
    generator, asynchronous, definition_default, definition_annotation,
    ConditionalDocument, PropertyDocument, ShadowedGuard,
    annotated_factory, rename, conditional_code,
    ConditionalProperty,
    MixedDocument,
    ConditionalState, vararg_annotation, kwarg_annotation,
    UnknownDefaultState, unknown_default_factory,
)


@identity
def pure(**kwargs):
    return kwargs


@document
def documented(**kwargs):
    return kwargs


@conditional_document
def conditional(**kwargs):
    return kwargs


@factory('text')
def constructed_factory(**kwargs):
    return kwargs


@Document('text')
def constructed_instance(**kwargs):
    return kwargs


@document_instance
def inherited_instance(**kwargs):
    return kwargs


@super_instance
def super_documented(**kwargs):
    return kwargs


@change_code
def code_changed(**kwargs):
    return kwargs


@change_alias_code
def alias_code_changed(**kwargs):
    return kwargs


@indirect_code
def indirectly_changed(**kwargs):
    return kwargs


@change_defaults
def defaults_changed(**kwargs):
    return kwargs


@change_kwdefaults
def kwdefaults_changed(**kwargs):
    return kwargs


@change_signature
def signature_changed(**kwargs):
    return kwargs


@opaque
def unknown_helper(**kwargs):
    return kwargs


@capture
def captured(**kwargs):
    return kwargs


@escape
def escaped(**kwargs):
    return kwargs


@dynamic
def dynamic_write(**kwargs):
    return kwargs


@replacement
def replaced(**kwargs):
    return kwargs


@mixed
def mixed_return(**kwargs):
    return kwargs


@incomplete
def implicit_return(**kwargs):
    return kwargs


@recursive
def recursive_entry(**kwargs):
    return kwargs


@final_change
def finally_changed(**kwargs):
    return kwargs


@UnsafeDocument()
def unsafe_constructor(**kwargs):
    return kwargs


@CustomDocument()
def custom_lookup(**kwargs):
    return kwargs


@RewrittenDocument()
def method_written(**kwargs):
    return kwargs


@rebound
def rebound_entry(**kwargs):
    return kwargs


@identity
@document
def stacked(**kwargs):
    return kwargs


class Owner:
    @document
    def run(self, **kwargs):
        return self.method(**kwargs)

    def method(self, **kwargs):
        return kwargs


def consumer(**kwargs):
    return documented(**kwargs)


@generator
def generator_entry(**kwargs):
    return kwargs


@asynchronous
def async_entry(**kwargs):
    return kwargs


@definition_default
def nested_default(**kwargs):
    return kwargs


@definition_annotation
def nested_annotation(**kwargs):
    return kwargs


@ConditionalDocument()
def conditional_member(**kwargs):
    return kwargs


@PropertyDocument()
def property_member(**kwargs):
    return kwargs


@ShadowedGuard()
def shadowed_guard(**kwargs):
    return kwargs


@annotated_factory('text')
def factory_annotation(**kwargs):
    return kwargs


@rename
def renamed(**kwargs):
    return kwargs


@conditional_code
def guarded_code(**kwargs):
    return kwargs


@ConditionalProperty()
def conditional_property(**kwargs):
    return kwargs


@MixedDocument()
def mixed_mro(**kwargs):
    return kwargs


@ConditionalState(1)
def conditional_state(**kwargs):
    return kwargs


@vararg_annotation
def nested_vararg_annotation(**kwargs):
    return kwargs


@kwarg_annotation
def nested_kwarg_annotation(**kwargs):
    return kwargs


@UnknownDefaultState()
def unknown_default_state(**kwargs):
    return kwargs


@unknown_default_factory()
def unknown_factory_default(**kwargs):
    return kwargs
