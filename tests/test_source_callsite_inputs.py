## @package tests.test_source_callsite_inputs

import ast
import builtins

from pcresolve.program_facts import SourceSpan
from pcresolve._caller_inputs import literal_inputs
from pcresolve.source_snapshot import SourceStore


def query(tmp_path, source, *, which=-1, **options):
    path = tmp_path / 'client.py'
    path.write_text(source, encoding='utf-8')
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
    calls.sort(key=lambda n: (n.lineno, n.col_offset))
    return literal_inputs(SourceSpan.from_ast(str(path), calls[which]), **options)


def _put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_callsite_literals_retain_import_target_spans_and_source_hash(tmp_path, monkeypatch):
    original = builtins.__import__

    def no_client_import(name, *args, **kwargs):
        assert name not in ('client', 'unavailable')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', no_client_import)
    result = query(tmp_path, '''from unavailable import target
X = [[0, 1], [2, 3]]
metric = 'euclidean'
result = target(X, metric, p=None)
''')
    assert result['status'] == 'source_bound'
    assert result['target'] == 'unavailable.target'
    expected = ast.parse('target(X, metric, p=None)', mode='eval').body
    assert result['call_syntax'] == ast.dump(expected, include_attributes=False)
    assert result['runtime_values_observed'] is False
    assert len(result['source_hashes']) == 1
    values = result['arguments']
    assert values[0]['value']['kind'] == 'list'
    assert values[0]['value']['items'][0]['items'][1]['value'] == 1
    assert values[1]['value'] == {'kind': 'scalar', 'type': 'str', 'value': 'euclidean'}
    assert values[2]['argument'] == {'keyword': 'p'}
    assert values[2]['value'] == {'kind': 'scalar', 'type': 'NoneType', 'value': None}
    assert any(e['lineno'] == 2 for e in values[0]['evidence'])
    assert result['assumptions']
    assert result['target_binding_evidence'][0]['lineno'] == 1


def test_mutations_and_opaque_calls_cannot_reuse_a_previous_literal(tmp_path):
    for mutation in ('alias.append(7)', 'alias[0] = 7', 'opaque()', 'X += [7]'):
        result = query(tmp_path, 'from unavailable import target\nX = [1]\nalias = X\n'
                       + mutation + '\nresult = target(X)\n')
        assert result['status'] == 'unconfirmed' or not any(
            a.get('status') == 'source_literal' for a in result.get('arguments', []))


def test_unknown_sibling_argument_does_not_invent_a_value(tmp_path):
    result = query(tmp_path, 'from unavailable import target\nX = [1]\n'
                   'result = target(X, unknown)\n')
    assert result['arguments'][0]['status'] == 'source_literal'
    assert result['arguments'][1]['status'] == 'unproven'


def test_target_rebinding_nested_calls_and_nonmodule_scope_retain_boundaries(tmp_path):
    examples = [
        'from unavailable import target\nX = [1]\ntarget = opaque\nresult = target(X)\n',
        'from unavailable import target\nX = [1]\nresult = target(opaque(), X)\n',
        'from unavailable import target\ndef entry(X):\n    return target(X)\n',
        'from unavailable import target\nX = [1]\ny = 1 if flag else 2\nresult = target(X)\n',
        'from unavailable import target\nX = [1]\ny: effect() = 1\nresult = target(X)\n',
        'from unavailable import target\nX = [1]\nresult = target(-unknown, X)\n',
    ]
    for source in examples:
        result = query(tmp_path, source, which=0 if 'target(opaque()' in source else -1)
        assert result['status'] == 'unconfirmed'
        assert result['boundaries']


def test_budget_and_content_edits_never_reuse_old_arguments(tmp_path):
    source = 'from unavailable import target\nX = [1]\nresult = target(X)\n'
    store = SourceStore()
    result = query(tmp_path, source, store=store)
    assert result['status'] == 'source_bound'
    assert query(tmp_path, source, max_nodes=1)['status'] == 'unconfirmed'
    changed = query(tmp_path, source.replace('[1]', '[2]'), store=store)
    assert changed['source_hashes'] != result['source_hashes']
    assert changed['arguments'][0]['value']['items'][0]['value'] == 2
    repeated = ('from unavailable import target\nX = [0]\n'
                + 'X = [X, X]\n' * 30 + 'result = target(X)\n')
    assert query(tmp_path, repeated)['status'] == 'unconfirmed'


def test_module_aliases_and_primitive_values_remain_json_safe(tmp_path):
    import json

    result = query(tmp_path, '''import unavailable as library
alias = library
X = (b'value', -2, False, None)
result = alias.target(X)
''')
    assert result['status'] == 'source_bound'
    assert result['target'] == 'unavailable.target'
    assert result['arguments'][0]['value']['items'][0]['value_hex'] == b'value'.hex()
    json.dumps(result)


def test_invalid_spans_and_source_failures_are_explicit(tmp_path):
    assert literal_inputs(SourceSpan('', 1, 0, 1, 3))['status'] == 'unconfirmed'
    missing = literal_inputs(SourceSpan(str(tmp_path / 'missing.py'), 1, 0, 1, 3))
    assert missing['boundaries'] == [{'reason': 'caller_source_unavailable'}]


def test_imported_stub_return_protocol_proves_local_call_result_iterable(tmp_path):
    _put(tmp_path, 'numpy/__init__.pyi', 'from .factory import arange as arange\n')
    _put(tmp_path, 'numpy/factory.pyi', '''
class Array:
    def __iter__(self): ...
def arange(start, stop, step) -> Array: ...
''')
    result = query(tmp_path, '''import numpy as np
ticks = np.arange(0, 1, 0.2)
np.consume(ticks)
''', import_roots=[tmp_path])
    argument = result['arguments'][0]
    assert result['status'] == 'source_bound'
    assert argument['status'] == 'source_protocol'
    assert argument['protocol']['kind'] == 'iterable'
    assert argument['protocol']['basis'] == 'bounded_stub_return_protocol'
    assert argument['protocol']['call_target'] == 'numpy.arange'
    assert result['supporting_source_sha256']
    assert all(path.startswith(str(tmp_path)) for path in result['supporting_source_sha256'])


def test_unannotated_or_noniterable_stub_return_stays_unproven(tmp_path):
    _put(tmp_path, 'numpy/__init__.pyi', 'from .factory import make as make\n')
    _put(tmp_path, 'numpy/factory.pyi', '''
class Token: ...
def make() -> Token: ...
''')
    result = query(tmp_path, '''import numpy as np
value = np.make()
np.consume(value)
''', import_roots=[tmp_path])
    assert result['arguments'][0]['status'] == 'unproven'
    assert result['arguments'][0].get('protocol') is None


def test_iterability_fact_is_available_for_exact_method_callsite(tmp_path):
    _put(tmp_path, 'numpy/__init__.pyi', 'from .factory import arange as arange\n')
    _put(tmp_path, 'numpy/factory.pyi', '''
class Array:
    def __iter__(self): ...
def arange(start, stop, step) -> Array: ...
''')
    result = query(tmp_path, '''import numpy as np
ticks = np.arange(0, 1, 0.2)
array = np.wrap(ticks)
array.api(ticks, legacy=None)
''', import_roots=[tmp_path])
    assert result['status'] == 'source_bound'
    assert result['target'] is None
    assert result['target_status'] == 'receiver_expression_only'
    assert result['target_expression'] == "Attribute(value=Name(id='array', ctx=Load()), attr='api', ctx=Load())"
    assert result['arguments'][0]['status'] == 'source_protocol'


def test_context_manager_binding_is_reported_for_module_callsite(tmp_path):
    result = query(tmp_path, '''import library
file_path = './data.json'
with open(file_path, 'r', encoding='utf-8') as stream:
    library.consume(stream, strict=None)
''')

    assert result['status'] == 'source_bound'
    assert result['target'] == 'library.consume'
    assert result['arguments'][0]['status'] == 'unproven'
    assert result['arguments'][1]['value'] == {
        'kind': 'scalar', 'type': 'NoneType', 'value': None}
    context = result['context_managers'][0]
    assert context['manager']['source_text'] == "open(file_path, 'r', encoding='utf-8')"
    assert context['manager']['arguments'][0]['value'] == {
        'kind': 'scalar', 'type': 'str', 'value': './data.json'}
    assert context['binding']['name'] == 'stream'
    assert result['context_argument_bindings'] == [{
        'argument': {'position': 0}, 'name': 'stream', 'manager_index': 0,
        'binding_evidence': context['binding']['evidence'],
        'argument_evidence': result['arguments'][0]['evidence'][0],
    }]
    assert result['runtime_values_observed'] is False


def test_context_manager_binding_is_generic_and_async_aware(tmp_path):
    result = query(tmp_path, '''import library
path = 'payload'
async with library.open_resource(path) as resource:
    library.consume(resource)
''')

    assert result['status'] == 'source_bound'
    context = result['context_managers'][0]
    assert context['kind'] == 'async_context_manager'
    assert context['manager']['target'] == 'library.open_resource'
    assert context['binding']['name'] == 'resource'
    assert result['context_argument_bindings'][0]['name'] == 'resource'


def test_conditional_or_extra_context_body_keeps_with_call_unconfirmed(tmp_path):
    sources = (
        '''import library
with open('payload', 'r', encoding='utf-8') as stream:
    if enabled:
        library.consume(stream)
''',
        '''import library
with open('payload', 'r', encoding='utf-8') as stream:
    prepare()
    library.consume(stream)
''',
    )
    for source in sources:
        result = query(tmp_path, source)
        assert result['status'] == 'unconfirmed'
        assert result['boundaries']


def test_imported_prefix_call_is_reported_as_unmodeled_effect(tmp_path):
    result = query(tmp_path, '''import factory
from library import target
value = factory.bind()
target(value)
''')
    boundary = next(item for item in result['boundaries']
                    if item['reason'] == 'caller_prefix_call_effect_unconfirmed')
    assert boundary['target'] == 'factory.bind'
    assert boundary['evidence']['lineno'] == 3
