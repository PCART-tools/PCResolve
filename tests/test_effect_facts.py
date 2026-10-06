## @package tests.test_effect_facts
#  Effect facts describe syntax and builtin protocols without analysis payloads.

import ast

import pytest

from pcresolve.effect_facts import (container_method_effect, contains_yield,
                                    function_effects)


def _function(source):
    return ast.parse(source).body[0]


def test_container_method_effects_preserve_shapes_arity_and_parameters():
    append = container_method_effect('append', {'list'}, 1)
    assert append.operation == 'append'
    assert append.parameters == ('object',)
    assert append.mutates_receiver

    get = container_method_effect('get', {'dict'}, 2)
    assert get.operation == 'get'
    assert get.parameters == ('key', 'default')
    assert not get.mutates_receiver

    assert container_method_effect('append', {'set'}, 1) is None
    assert container_method_effect('get', {'dict'}, 0) is None
    mapping_pop = container_method_effect('pop', {'dict'}, 1)
    assert mapping_pop.operation == 'mapping_pop'
    assert mapping_pop.parameters == ('key', 'default')
    assert mapping_pop.mutates_receiver
    assert container_method_effect('pop', {'dict'}, 0) is None


def test_function_effects_extract_complete_straight_line_summary():
    node = _function('''
def update(values, item, replacement):
    """Apply exact supported effects."""
    nonlocal current
    values.append(item)
    values.clear()
    current = replacement
''')
    effects = function_effects(node)
    assert [(effect.kind, effect.target, effect.source) for effect in effects] == [
        ('container_append', 'values', 'item'),
        ('container_clear', 'values', None),
        ('nonlocal_write', 'current', 'replacement'),
    ]
    assert [effect.statement.lineno for effect in effects] == [
        5, 6, 7]


def test_function_effects_reject_partial_or_deferred_summaries():
    conditional = _function('''
def update(values, item, flag):
    if flag:
        values.append(item)
''')
    generator = _function('''
def update(values, item):
    values.append(item)
    yield item
''')
    unsupported = _function('''
def update(values):
    values.extend(other)
''')
    assert function_effects(conditional) is None
    assert function_effects(generator) is None
    assert function_effects(unsupported) is None


def test_yield_detection_stops_at_nested_definition_boundaries():
    direct = _function('''
def values():
    yield 1
''')
    nested = _function('''
def values():
    def deferred():
        yield 1
    return deferred
''')
    assert contains_yield(direct)
    assert not contains_yield(nested)


def test_mapping_parameter_effects_are_symbolic_and_shape_constrained():
    node = _function('''
def clean(mapping):
    alias = mapping
    alias.pop("out", None)
    del mapping["other"]
    return alias
''')
    effects = function_effects(node)
    assert effects is not None
    assert [(value.kind, value.target, value.element_path, value.receiver_shape)
            for value in effects] == [
                ('mapping_pop', 'mapping', ('out',), 'dict'),
                ('mapping_delete', 'mapping', ('other',), 'dict')]
    assert effects[0].may_raise is None and effects[1].may_raise == 'KeyError'


@pytest.mark.parametrize('body', [
    'mapping.pop(key, None)',
    'mapping.pop("out", factory())',
    'mapping.pop("out", None)\n    external(mapping)',
    'mapping.pop("out", None)\n    mapping["out"] = None',
    'if flag:\n        mapping.pop("out", None)',
    'for key in ("out", "other"):\n        mapping.pop(key, None)',
])
def test_mapping_summary_does_not_return_partial_effects(body):
    assert function_effects(_function('def clean(mapping, key=None, flag=False):\n    ' + body)) is None


def test_returned_popped_value_retains_write_not_container_identity():
    effects = function_effects(_function('def popped(mapping):\n    return mapping.pop("out", None)'))
    assert effects is not None and len(effects) == 1
    assert effects[0].kind == 'mapping_pop'
