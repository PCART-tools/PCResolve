## @package tests.test_flow_entry_global_binding

from pcresolve import FlowAnalyzer, FunctionRef


def test_source_definition_query_retains_body_and_marks_unconfirmed_public_lookup(tmp_path):
    (tmp_path / 'sample.py').write_text('''def fixed(allowed=0): return allowed
def api(**kwargs): return fixed(**kwargs)
class Changes:
    def update(self):
        global api
        api = lambda **kwargs: kwargs
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'api'))
    assert result.find_calls(callee_name='fixed')
    assert any(boundary['reason'] == 'module_callable_binding_unconfirmed'
               and boundary.get('lookup_scope') == 'module_entry'
               and boundary['function'] == result.to_dict()['entry']
               and boundary['declarations'] for boundary in result.boundaries)
    assert any(record['module'] == 'sample' and record['name'] == 'api'
               and record['status'] == 'may_write' and record['declarations']
               for record in result.inputs['module_global_rebindings'])
