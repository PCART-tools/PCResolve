## @package tests.test_value_flow_generated_dispatch

from pcresolve import FlowAnalyzer, FunctionRef
import pytest


def source(tmp_path, extra='', names="{'fixed': None, 'accepts': None}", expression=None):
    expression = expression or "{'test_' + name: globals()[name] for name in NAMES.keys()}"
    path = tmp_path / 'cases.py'
    path.write_text("def fixed(allowed=0): return allowed\n"
                    "def accepts(**kwargs): return kwargs\n"
                    f"NAMES = {names}\nTABLE = {expression}\n"
                    "def dispatch(key, **kwargs): return TABLE[key](**kwargs)\n" + extra)
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'dispatch'))


def test_closed_generated_source_symbols_export_finite_targets(tmp_path):
    result = source(tmp_path)
    call = result.find_calls(callee_name='TABLE[key]')[0]
    assert call.target_status == 'bounded_alternatives'
    assert {item['qualname'] for item in call.target_candidates} == {'fixed', 'accepts'}


@pytest.mark.parametrize('extra', [
    'NAMES["other"] = None\n',
    'escaped = NAMES\n',
    'TABLE["test_fixed"] = external\n',
    'escaped = TABLE\n',
    'globals = external\n',
    'def alter():\n global fixed\n fixed = external\n',
    'def alter(): globals()["fixed"] = external\n',
    'fixed.__code__ = external\n',
])
def test_mutation_escapes_shadowing_and_rebinding_do_not_close_targets(tmp_path, extra):
    result = source(tmp_path, extra)
    call = result.find_calls(callee_name='TABLE[key]')[0]
    assert not call.target_candidates


@pytest.mark.parametrize('names,expression', [
    ("{'fixed': None, 'missing': None}", None),
    ('external', None),
    ("{'fixed': None}", "{name: globals()[name] for name in NAMES.keys() if external(name)}"),
    ("{'fixed': None}", "{name: globals()[name] for name in external(NAMES)}"),
])
def test_open_names_filters_and_iterators_keep_unknown(tmp_path, names, expression):
    assert not source(tmp_path, names=names, expression=expression).find_calls(
        callee_name='TABLE[key]')[0].target_candidates


def test_generated_table_budget_is_explicit(tmp_path):
    names = '{' + ','.join(repr('fixed' + str(i)) + ':None' for i in range(65)) + '}'
    result = source(tmp_path, names=names)
    assert not result.find_calls(callee_name='TABLE[key]')[0].target_candidates
    assert any(item['reason'] == 'generated_dispatch_budget' for item in result.boundaries)


def test_source_keys_must_exist_at_table_construction(tmp_path):
    result = source(tmp_path, expression="{name: globals()[name] for globals in NAMES.keys()}")
    assert not result.find_calls(callee_name='TABLE[key]')[0].target_candidates
