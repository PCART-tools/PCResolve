import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''def entry(items, **options):
    for item in items:
        work(item)
    layout = dict(width=900, annotations=[])
    result = dict(data=items, layout=layout)
    result['layout'].update(options)
    result['layout']['annotations'].append({'title': 'hello'})
    result['layout']['width'] = 1000
    return result
'''


def query(tmp_path, source=SOURCE):
    (tmp_path / 'cases.py').write_text(source)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'entry'))
    return result.functions[0]['mapping_return_transfers']


def test_fresh_nested_mapping_retains_keys_on_normal_return(tmp_path):
    fact = query(tmp_path)[0]
    assert fact['kind'] == 'normal_return_mapping_transfer'
    assert fact['parameter'] == 'options'
    assert fact['return_root'] == 'result'
    assert fact['return_path'] == ['layout']
    assert fact['excluded_keys'] == ['annotations', 'width']
    assert fact['normal_completion_proven'] is False
    assert fact['update_evidence']['lineno'] == 6
    assert fact['return_evidence']['lineno'] == 9


@pytest.mark.parametrize('source', [
    SOURCE.replace('return result', "return result['layout']"),
    SOURCE.replace("result['layout']['width'] = 1000", "result['layout'].clear()"),
    SOURCE.replace("result['layout']['width'] = 1000", "alias = result['layout']"),
    SOURCE.replace("result['layout']['width'] = 1000", 'publish(result)'),
    SOURCE.replace("result['layout']['width'] = 1000", 'result = {}'),
    SOURCE.replace("result['layout']['width'] = 1000", "result['layout'] = {}"),
    SOURCE.replace("result['layout']['width'] = 1000", "result[key] = {}"),
    SOURCE.replace("result['layout']['width'] = 1000", 'publish(layout)'),
    SOURCE.replace('result = dict(data=items, layout=layout)', 'result = build(layout)'),
    SOURCE.replace('layout = dict(width=900, annotations=[])', 'layout = external()'),
    SOURCE.replace('result = dict(data=items, layout=layout)', 'result = dict(data=layout, layout=layout)'),
    SOURCE.replace('result = dict(data=items, layout=layout)', 'publish(layout)\n    result = dict(data=items, layout=layout)'),
    SOURCE.replace('    result[\'layout\'].update(options)', "    if items:\n        result['layout'].update(options)"),
    SOURCE.replace('    for item in items:', '    if items:\n        return {}\n    for item in items:'),
    SOURCE.replace('    for item in items:', '    dict = external\n    for item in items:'),
    SOURCE.replace('    for item in items:', '    peek = locals\n    for item in items:'),
    SOURCE.replace('    for item in items:', '    external(options)\n    for item in items:'),
    SOURCE.replace('    return result', '    def nested():\n        return result\n    return result'),
])
def test_escape_rebinding_overwrite_or_unsupported_construction_has_no_fact(tmp_path, source):
    assert not query(tmp_path, source)
