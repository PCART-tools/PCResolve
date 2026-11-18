## @package tests.test_module_getattr_missing

import runpy

import pytest

from pcresolve import FlowAnalyzer
from pcresolve.flow.proofs._module_getattr import missing


FACTORY = '''import functools as memo
def expose(subject):
    entries = {label: descriptor for label, descriptor in vars(subject).items()
               if isinstance(descriptor, property)}
    instance = subject()
    @memo.lru_cache(None)
    def resolve(label):
        if label in entries:
            return entries[label].__get__(instance)
        raise AttributeError(f'{subject.__module__}: {label}')
    return resolve
'''
PACKAGE = '''from factory import expose
@expose
class __getattr__:
    visible = property(lambda self: 'text')
    ignored = 7
'''


def setup(root, factory=FACTORY, package=PACKAGE):
    (root / 'factory.py').write_text(factory, encoding='utf-8')
    (root / 'bundle.py').write_text(package, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer


def test_finite_property_dispatch_exposes_a_missing_name_without_running_a_getter(tmp_path, monkeypatch):
    analyzer = setup(tmp_path)
    fact = missing(analyzer, 'bundle', 'data')
    assert fact['status'] == 'missing_on_dispatch'
    assert fact['property_names'] == ['visible']
    assert fact['runtime_lookup_confirmed'] is False
    assert fact['factory']['qualname'] == 'expose'
    assert set(fact['source_hashes']) == {str(tmp_path / name) for name in ('factory.py', 'bundle.py')}
    assert missing(analyzer, 'bundle', 'visible') is None
    monkeypatch.syspath_prepend(str(tmp_path))
    values = runpy.run_path(str(tmp_path / 'bundle.py'))
    assert values['__getattr__']('visible') == 'text'
    with pytest.raises(AttributeError):
        values['__getattr__']('data')


@pytest.mark.parametrize('old,new', [
    ('return entries[label].__get__(instance)', 'return entries.pop(label).__get__(instance)'),
    ('instance = subject()', 'instance = opaque(subject)'),
    ('return resolve', 'return unknown'),
    ('if label in entries:', 'if opaque(label):'),
    ('raise AttributeError', 'raise unknown'),
    ('@memo.lru_cache(None)', '@unknown(None)'),
    ('entries = {label:', 'entries = {opaque(label):'),
    ('if isinstance(descriptor, property)', 'if opaque(descriptor)'),
    ('instance = subject()', "entries['data'] = unknown\n    instance = subject()"),
])
def test_unproven_factory_or_mutating_dispatch_does_not_prove_absence(tmp_path, old, new):
    analyzer = setup(tmp_path, factory=FACTORY.replace(old, new))
    assert missing(analyzer, 'bundle', 'data') is None


@pytest.mark.parametrize('package', [
    PACKAGE.replace('class __getattr__:', 'class __getattr__(unknown):'),
    PACKAGE.replace("visible = property(lambda self: 'text')", "visible = opaque()"),
    PACKAGE + '\n__getattr__ = unknown\n',
    PACKAGE.replace('ignored = 7', 'def __init__(self): opaque(self)'),
    PACKAGE.replace('ignored = 7', '__module__ = opaque()'),
    '__name__ = unknown\n' + PACKAGE,
])
def test_customized_source_namespace_does_not_prove_missing_lookup(tmp_path, package):
    assert missing(setup(tmp_path, package=package), 'bundle', 'data') is None


@pytest.mark.parametrize('prefix', ['property = unknown\n', 'vars = unknown\n',
                                  'import builtins\nbuiltins.property = unknown\n',
                                  'import functools\ndef alter(): functools.lru_cache = unknown\n',
                                  'from functools import lru_cache as captured\nopaque(captured)\n',
                                  'import functools\ndef alter(): vars(functools)["lru_cache"] = unknown\n'])
def test_lookup_requires_unshadowed_and_preserved_builtin_protocols(tmp_path, prefix):
    assert missing(setup(tmp_path, factory=prefix + FACTORY), 'bundle', 'data') is None
