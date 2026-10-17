"""Closed per-key access footprints must not hide whole-mapping escapes."""
import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def analyze(tmp_path, body):
    path = tmp_path / 'example.py'
    path.write_text('def entry(value=None, **params):\n' + body, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('example', 'entry'))
    return {'functions': result.functions}


def test_key_local_reads_are_control_flow_independent_source_facts(tmp_path):
    result = analyze(tmp_path, "    if value:\n        x = params['mean']\n"
                     "    for x in value:\n        y = params.get('tol', 0.1)\n"
                     "    return 'enabled' in params\n")
    fact = result['functions'][0]['mapping_key_accesses'][0]
    assert fact['status'] == 'key_local'
    assert fact['parameter'] == 'params'
    assert fact['keys'] == ['enabled', 'mean', 'tol']
    assert len(fact['accesses']) == 3
    assert fact['control_flow_proven'] is False
    assert fact['source_hash']


@pytest.mark.parametrize('body', [
    '    return params\n',
    '    alias = params\n',
    '    return target(**params)\n',
    '    return len(params)\n',
    '    return params.get(value)\n',
    "    params['mean'] = 1\n",
    "    del params['mean']\n",
    "    def nested():\n        return params.get('mean')\n    return nested()\n",
    "    return eval('params')\n",
    "    read = locals\n    read()\n    return params.get('mean')\n",
    "    read = inspect.currentframe\n    read()\n    return params.get('mean')\n",
    "    read = getattr(scope, method)\n    read()\n    return params.get('mean')\n",
    "    from inspect import currentframe as read\n    read()\n    return params.get('mean')\n",
    "    inspect.currentframe()\n    return params.get('mean')\n",
    "    return params.get('mean', **value)\n",
    "    return params.get('mean', *value)\n",
])
def test_unsupported_access_never_produces_a_closed_footprint(tmp_path, body):
    result = analyze(tmp_path, body)
    assert not result['functions'][0]['mapping_key_accesses']


def test_unused_capture_and_ordinary_parameter_have_no_key_read_fact(tmp_path):
    assert not analyze(tmp_path, '    return value\n')['functions'][0]['mapping_key_accesses']


def test_fixed_key_pop_is_local_when_the_remaining_mapping_never_escapes(tmp_path):
    result = analyze(tmp_path, "    mode = params.pop('mode', 'normal')\n"
                     "    return params.get('index', mode)\n")
    fact = result['functions'][0]['mapping_key_accesses'][0]
    assert fact['keys'] == ['index', 'mode']
    assert {item['operation'] for item in fact['accesses']} == {'get', 'pop'}


@pytest.mark.parametrize('body', [
    "    params.pop('mode', None)\n    return params\n",
    "    params.pop('mode', None)\n    return bool(params)\n",
    "    return params.pop(value, None)\n",
    "    return params.pop('mode', *value)\n",
    "    return params.pop('mode', **value)\n",
    "    method = params.pop\n    return method('mode')\n",
])
def test_pop_cannot_hide_dynamic_keys_aliases_or_remaining_container_use(tmp_path, body):
    assert not analyze(tmp_path, body)['functions'][0]['mapping_key_accesses']
