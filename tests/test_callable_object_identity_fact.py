from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs._class_definition import _source_callable_object_identity
import pytest


SOURCE = '''import inspect as tools
class Documenter:
    params = {}
    def __call__(self, item):
        if item.__doc__:
            item.__doc__ = tools.cleandoc(item.__doc__) % self.params
        return item
decorate = Documenter()
'''


def _fact(tmp_path, helper=SOURCE, owner_suffix=''):
    package = tmp_path / 'example'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    if helper is not None:
        (package / 'helper.py').write_text(helper, encoding='utf-8')
    owner = package / 'api.py'
    owner.write_text('''from . import helper as docs
class Service:
    @docs.decorate
    def run(self, **kwargs):
        return kwargs
''' + owner_suffix, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef('example.api', 'Service.run', str(owner)))
    return result.functions[0]['decorator_effects'][0]


def test_callable_object_proof_is_attached_to_exact_function(tmp_path):
    fact = _fact(tmp_path)
    proof = fact['callable_object_identity_proof']
    assert proof['status'] == 'source_bound'
    assert proof['function'] == fact['function']
    assert proof['expression'] == fact['expression']
    assert proof['returned_object'] == 'original_function'
    assert proof['mutated_function_attributes'] == ['__doc__']
    assert any(path.endswith('helper.py') for path in proof['source_hashes'])
    assert proof['decorator_source_files']
    assert set(proof['decorator_source_files']).issubset(proof['source_hashes'])
    assert proof['completion'] == 'normal_return'


def test_callable_object_proof_rejects_replacement(tmp_path):
    fact = _fact(tmp_path, SOURCE.replace('return item', 'return lambda: item'))
    assert 'callable_object_identity_proof' not in fact


def test_callable_object_proof_rejects_extra_function_mutation(tmp_path):
    fact = _fact(tmp_path, SOURCE.replace('return item', 'item.extra = 1\n        return item'))
    assert 'callable_object_identity_proof' not in fact


def test_callable_object_proof_rejects_missing_dependency(tmp_path):
    fact = _fact(tmp_path, None)
    assert 'callable_object_identity_proof' not in fact


def test_callable_object_proof_supports_module_function(tmp_path):
    package = tmp_path / 'example'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'helper.py').write_text(SOURCE, encoding='utf-8')
    owner = package / 'api.py'
    owner.write_text('''from . import helper as docs
@docs.decorate
def run(**kwargs): return kwargs
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef('example.api', 'run', str(owner)))
    fact = result.functions[0]['decorator_effects'][0]
    assert fact['callable_object_identity_proof']['function'] == fact['function']


def test_callable_object_proof_rejects_rebound_helper_class(tmp_path):
    fact = _fact(tmp_path, SOURCE.replace('decorate = Documenter()',
                                         'Documenter = lambda: object()\ndecorate = Documenter()'))
    assert 'callable_object_identity_proof' not in fact


def test_callable_object_proof_rejects_rebound_call_method(tmp_path):
    fact = _fact(tmp_path, SOURCE.replace('decorate = Documenter()',
                                         '    __call__ = unknown\ndecorate = Documenter()'))
    assert 'callable_object_identity_proof' not in fact


@pytest.mark.parametrize('helper', [
    SOURCE.replace('decorate = Documenter()',
                   'Documenter = lambda: object()\ndecorate = Documenter()'),
    SOURCE.replace('decorate = Documenter()',
                   '    __call__ = unknown\ndecorate = Documenter()'),
    SOURCE + '\nDocumenter.__call__ = unknown\n',
    SOURCE + "\nsetattr(Documenter, '__call__', unknown)\n",
    SOURCE + '\ndecorate.params = unknown\n',
    SOURCE.replace('decorate = Documenter()',
                   '    __init__ = unknown\ndecorate = Documenter()'),
    SOURCE.replace('decorate = Documenter()',
                   '    def __new__(cls): return object()\ndecorate = Documenter()'),
])
def test_existing_internal_proof_rejects_unstable_decorator_bindings(tmp_path, helper):
    package = tmp_path / 'example'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'helper.py').write_text(helper, encoding='utf-8')
    (package / 'api.py').write_text('''from . import helper as docs
class Service:
    @docs.decorate
    def run(self, **kwargs): return kwargs
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    owner, cls = analyzer._definition_index.find('example.api', 'Service', kind='class')[0]
    method = next(item for item in cls.body if getattr(item, 'name', None) == 'run')
    assert _source_callable_object_identity(analyzer, owner, method, set(), set()) is None
