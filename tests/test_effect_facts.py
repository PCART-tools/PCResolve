## @package tests.test_effect_facts
#  Effect facts describe syntax and builtin protocols without analysis payloads.

import ast

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
    assert container_method_effect('pop', {'dict'}, 1) is None


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
