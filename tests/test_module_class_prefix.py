## @package tests.test_module_class_prefix

import ast

import pytest

from pcresolve import FlowAnalyzer
from pcresolve.flow.proofs._module_class_prefix import module_class_prefix

SOURCE = '''class Root:
    values = ['hidden']
    @classmethod
    def initialize(cls): cls.marker = True
    def method(self): pass
class Observer:
    def __init__(self, value): self.value = value
def unused():
    opaque(Root)
Root.initialize()
'''


def prepare(root, source=SOURCE):
    (root / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Root', kind='class')[0]
    body = analyzer.module_bodies['example'][0][1]
    statement = body[-1]
    call = statement.value if isinstance(statement, ast.Expr) else None
    return module_class_prefix(analyzer, target, call)


def test_unused_deferred_class_uses_do_not_change_the_pre_call_prefix(tmp_path):
    fact = prepare(tmp_path)
    assert fact['status'] == 'source_bound'
    assert fact['phase'] == 'before_module_call'
    assert fact['call_effects'] == 'unproved'
    assert fact['runtime_initialization_confirmed'] is False
    assert fact['deferred_bodies_executed'] is False


@pytest.mark.parametrize('prefix', [
    'opaque()', 'opaque(Root)', 'Root.method = opaque', 'saved = Root',
    'import external', 'if condition: opaque()',
    'class Child(Root): pass',
    '@opaque\nclass Observer2: pass',
    'def callback(value=opaque()): pass',
])
def test_unproved_intermediate_execution_does_not_supply_a_fresh_prefix(tmp_path, prefix):
    assert prepare(tmp_path, SOURCE.replace('Root.initialize()', prefix + '\nRoot.initialize()')) is None


def test_a_later_module_call_cannot_reuse_the_first_call_prefix(tmp_path):
    assert prepare(tmp_path, SOURCE + 'Root.initialize()\n') is None


def test_a_source_function_alias_does_not_invoke_its_deferred_body(tmp_path):
    source = SOURCE.replace('Root.initialize()', 'alias = unused\nRoot.initialize()')
    fact = prepare(tmp_path, source)
    assert fact is not None
    assert fact['function_aliases'][0]['binding_name'] == 'alias'
    assert fact['function_aliases'][0]['target']['qualname'] == 'unused'
    assert fact['function_aliases'][0]['body_execution'] == 'deferred'


@pytest.mark.parametrize('binding', ['alias = opaque', 'alias = Root', 'alias = unused()'])
def test_open_alias_values_do_not_acquire_a_function_declaration_proof(tmp_path, binding):
    assert prepare(tmp_path, SOURCE.replace('Root.initialize()', binding + '\nRoot.initialize()')) is None
