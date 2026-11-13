## @package tests.test_dynamic_attribute_owner
#  Dynamic attribute results must not inherit the builtin callable owner.

from pathlib import Path

from pcresolve import analyze_project


ROOT = Path(__file__).parent / 'fixtures' / 'dynamic_attribute_owner'


def test_dynamic_attribute_result_does_not_inherit_getattr_owner():
    result = analyze_project(str(ROOT))
    calls = {call.expression: call for call in result.all_api_calls}
    dynamic = calls['self.dynamic_axis(name).equals(other)']
    assert dynamic.top_library == 'unknown'
    assert dynamic.reason == 'UNRESOLVED'
    assert dynamic.confidence != 1.0
    assert calls['getattr(self, name)'].top_library == 'python'
    assert calls['self.local_axis(name).equals(other)'].top_library == 'local'
    assert calls['self.forwarded_axis(name).equals(other)'].top_library == 'unknown'
    assert calls['json.loads(value)'].top_library == 'json'
    assert calls['[1].copy()'].top_library == 'python'
    assert next(call for call in result.all_api_calls
                if call.expression.startswith('all(')).top_library == 'python'
    provenance = next(item for item in result.all_symbol_provenance
                      if item.symbol == 'dynamic_axis.return')
    assert provenance.top_library == 'unknown'
    assert provenance.chain[-1] == 'unknown'
    assert calls['getattr(obj, name).equals(obj)'].top_library == 'local'
    assert calls['self.module_axis(name).equals(self)'].top_library == 'unknown'
    assert calls['self.imported_axis(name).equals(self)'].top_library == 'unknown'
    assert calls['self.mixed_axis(name, flag).copy()'].top_library == 'unknown'
    assert calls['getattr(obj, name)()'].top_library == 'unknown'
    assert calls['builtin_module.getattr(self, name)()'].top_library == 'unknown'
    assert calls['read_attribute(self, name)()'].top_library == 'unknown'
    assert calls['selected()'].top_library == 'unknown'
    assert calls['selected.equals(obj)'].top_library == 'unknown'
    selected = next(item for item in result.all_symbol_provenance
                    if item.symbol == 'selected')
    assert selected.top_library == 'unknown'
    assert selected.chain[-1] == 'unknown'
