## @package tests.test_metadata_observer_namespace

import ast
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs._class_definition import namespace_issues


SOURCE = '''import inspect
import functools
import re
class Observer:
    pattern = re.compile(r'Alias (.*)')
    @staticmethod
    @functools.lru_cache(maxsize=None)
    def count(fn):
        return len(inspect.signature(fn).parameters)
    @staticmethod
    @functools.lru_cache(maxsize=None)
    def alias(fn):
        text = inspect.getdoc(fn)
        if text is None:
            return False
        return text.startswith('Alias ')
    def __init__(self, value):
        self.value = value
'''


def prepare(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Observer', kind='class')[0]
    return analyzer, target, path


def test_native_cache_and_regex_creation_can_preserve_a_class_namespace(tmp_path):
    analyzer, target, path = prepare(tmp_path)
    assumptions, dependencies = set(), set()
    assert namespace_issues(analyzer, [target], dependencies=dependencies,
                            assumptions=assumptions) == []
    assert 'standard_library_native_regex_pattern_creation' in assumptions
    assert 'standard_library_staticmethod_cache_creation' in assumptions
    assert str(path) in dependencies
    result = analyzer.analyze(FunctionRef('example', 'Observer'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    # Namespace formation makes no claim about executing a wrapped method.
    opaque = SOURCE.replace('return len(inspect.signature(fn).parameters)', 'return opaque(fn)')
    analyzer, target, _ = prepare(tmp_path, opaque)
    assert namespace_issues(analyzer, [target], assumptions=set()) == []


def test_native_creation_has_an_independent_runtime_control(tmp_path):
    _, _, path = prepare(tmp_path)
    values = runpy.run_path(str(path))
    cls = values['Observer']
    def described(one, two=0):
        """Alias documented."""
    assert cls.count(described) == 2
    assert cls.alias(described) is True
    assert cls(3).value == 3
    assert cls.pattern.search('Alias documented').group(1) == 'documented'


@pytest.mark.parametrize('prefix,decorator', [
    ('', 'functools.lru_cache'),
    ('from functools import lru_cache\n', 'lru_cache'),
])
def test_direct_decorator_use_does_not_expose_the_stdlib_entry_point(tmp_path, prefix, decorator):
    source = prefix + SOURCE + '\n@' + decorator + '\ndef other(value):\n    return value\n'
    analyzer, target, _ = prepare(tmp_path, source)
    assert namespace_issues(analyzer, [target], assumptions=set()) == []


@pytest.mark.parametrize('old,new', [
    ('re.compile(r\'Alias (.*)\')', 're.compile(opaque)'),
    ('re.compile(r\'Alias (.*)\')', "re.compile('(')"),
    ('re.compile(r\'Alias (.*)\')', "re.compile('x', flags=opaque)"),
    ('functools.lru_cache(maxsize=None)', 'functools.lru_cache(maxsize=opaque)'),
    ('@staticmethod', '@opaque'),
    ('@functools.lru_cache(maxsize=None)', '@opaque'),
    ('class Observer:', 'class Observer:\n    staticmethod = opaque'),
    ('class Observer:', 'class Observer:\n    functools = None'),
])
def test_unknown_creation_protocols_and_arguments_keep_namespace_issues(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE.replace(old, new))
    assert namespace_issues(analyzer, [target], assumptions=set())


@pytest.mark.parametrize('tail', [
    're.compile = opaque',
    'functools.lru_cache = opaque',
    'saved = re\nopaque(saved)',
    'saved = re.compile\nopaque(saved)',
    'saved = functools\nopaque(saved)',
    "__import__('re').compile = opaque",
    're._cache.clear()',
    're._cache = opaque',
    'functools._lru_cache_wrapper = opaque',
    "import sys\nsys.modules['re']._cache = opaque",
    'import builtins\nbuiltins.staticmethod = opaque',
    'import builtins\nsaved = builtins\nopaque(saved)',
    'from re import _compiler as compiler\ncompiler.compile = opaque',
    'from functools import _lru_cache_wrapper\nopaque(_lru_cache_wrapper)',
    'import builtins\nbuiltins.callable = opaque',
])
def test_replaced_or_exposed_creation_namespaces_are_not_native(tmp_path, tail):
    analyzer, target, _ = prepare(tmp_path, SOURCE + '\n' + tail + '\n')
    assert namespace_issues(analyzer, [target], assumptions=set())


def test_member_source_ast_is_not_changed_by_namespace_specialization(tmp_path):
    analyzer, target, _ = prepare(tmp_path)
    before = ast.dump(target[1])
    namespace_issues(analyzer, [target], assumptions=set())
    assert ast.dump(target[1]) == before


def test_literal_regex_parser_recursion_is_an_open_namespace(tmp_path):
    pattern = '(' * 600 + 'x' + ')' * 600
    source = SOURCE.replace("r'Alias (.*)'", repr(pattern))
    analyzer, target, _ = prepare(tmp_path, source)
    assert namespace_issues(analyzer, [target], assumptions=set())


def test_regex_debug_output_is_not_executed_during_source_analysis(tmp_path, capsys):
    source = SOURCE.replace("re.compile(r'Alias (.*)')", "re.compile('x', 128)")
    analyzer, target, _ = prepare(tmp_path, source)
    assert namespace_issues(analyzer, [target], assumptions=set())
    assert capsys.readouterr().out == ''


def test_regex_creation_checks_the_builtin_dependencies_of_the_stdlib_protocol(tmp_path):
    source = "import re\nclass Observer:\n    pattern = re.compile('x')\n"
    analyzer, target, _ = prepare(tmp_path, source + 'import builtins\nbuiltins.isinstance = opaque\n')
    assert namespace_issues(analyzer, [target], assumptions=set())
