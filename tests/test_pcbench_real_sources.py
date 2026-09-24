## @package tests.test_pcbench_real_sources
#  Optional regressions against the hash-checked PCBench source inventory.

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


INVENTORY = Path('C:/GitHub/VPPDetector/tmp/pcbench_sources/sources.json')
FIXTURES = Path(__file__).parent / 'fixtures' / 'pcbench_regressions'


def source(source_id):
    if not INVENTORY.is_file():
        pytest.skip('PCBench source inventory is not available')
    items = json.loads(INVENTORY.read_text(encoding='utf-8'))['sources']
    record = next((item for item in items if item['source_id'] == source_id), None)
    if record is None or record['status'] != 'ready':
        pytest.skip('PCBench source is not ready: ' + source_id)
    root = Path(record['package_root_absolute'])
    if not root.is_dir():
        pytest.skip('PCBench source directory is not available: ' + source_id)
    return root


def analyze(source_id, files, module, qualname, extra_files=()):
    package = source(source_id)
    selected = [package / name for name in files]
    selected.extend(extra_files)
    if not all(path.is_file() for path in selected):
        pytest.skip('PCBench source files are not available')
    analyzer = FlowAnalyzer(
        source_files=selected,
        import_roots=[package.parent, FIXTURES])
    return analyzer.analyze(FunctionRef(module=module, qualname=qualname))


def test_tornado_constructor_and_explicit_super():
    latest = analyze('tornado-6.0', ['httpclient.py'],
                     'tornado.httpclient', 'AsyncHTTPClient.fetch')
    request = latest.find_calls(callee_name='HTTPRequest')[0]
    assert request.target.qualname == 'HTTPRequest.__init__'
    assert request.target.module == 'tornado.httpclient'
    assert request.target_status == 'constructor'

    previous = analyze('tornado-3.0', ['httpclient.py', 'util.py'],
                       'tornado.httpclient', 'AsyncHTTPClient.__new__')
    super_call = previous.find_calls(
        callee_name='super(AsyncHTTPClient, cls).__new__')[0]
    assert super_call.target.qualname == 'Configurable.__new__'
    assert super_call.target.module == 'tornado.util'


def test_pandas_inherited_entry_and_mapping_as_ordinary_argument():
    result = analyze('pandas-2.0.0',
                     ['core/frame.py', 'core/generic.py', 'core/arraylike.py',
                      'compat/numpy/function.py'],
                     'pandas.core.frame', 'DataFrame.take')
    assert result.entry.module == 'pandas.core.generic'
    assert result.entry.qualname == 'NDFrame.take'
    call = result.find_calls(callee_name='nv.validate_take')[0]
    mapping = next(item for item in call.argument_sources
                   if item['argument'] == {'position': 1})
    assert any(value['kind'] == 'parameter' and value['source'] == 'kwargs'
               and value.get('output_path') == ['*']
               for value in mapping['sources'])
    assert call.target.module == 'pandas.compat.numpy.function'
    assert call.target.qualname == 'CompatValidator.__call__'
    assert call.target_status == 'callable_instance_candidate'
    assert call.callable_instance_evidence['constructor_arguments'][0][
        'source']['qualified_name'] == 'pandas.compat.numpy.function.TAKE_DEFAULTS'
    assert any(item['source'] == {'kind': 'literal', 'value': 'kwargs'}
               for item in call.callable_instance_evidence['constructor_arguments'])


def test_pandas_series_take_passes_kwargs_as_ordinary_mapping():
    result = analyze('pandas-2.0.0',
                     ['core/series.py', 'compat/numpy/function.py'],
                     'pandas.core.series', 'Series.take')
    call = result.find_calls(callee_name='nv.validate_take')[0]
    mapping = next(item for item in call.argument_sources
                   if item['argument'] == {'position': 1})
    assert any(value['kind'] == 'parameter' and value['source'] == 'kwargs'
               and value.get('output_path') == ['*']
               for value in mapping['sources'])
    assert call.target.module == 'pandas.compat.numpy.function'
    assert call.target.qualname == 'CompatValidator.__call__'
    assert call.callable_instance_evidence['qualified_name'] == (
        'pandas.compat.numpy.function.validate_take')


def test_aiohttp_assignment_boundaries_do_not_name_kwargs():
    result = analyze('aiohttp-0.8.2', ['connector.py'],
                     'aiohttp.connector', 'BaseConnector.__init__')
    assignments = [item for item in result.boundaries
                   if item['reason'] == 'unsupported_assignment']
    assert assignments
    assert all('kwargs' not in {root['name']
                               for root in item['affected_values']}
               for item in assignments)
    assert all(item['affected_scope'] == 'known' for item in assignments)
    full = FlowAnalyzer(project_root=source('aiohttp-0.8.2').parent).analyze(
        FunctionRef(module='aiohttp.connector', qualname='BaseConnector.__init__'))
    unavailable = [item for item in full.boundaries
                   if item['reason'] == 'source_unavailable']
    assert unavailable
    assert any(item['affected_scope'] == 'none'
               and item['entry_relation'] == 'unrelated'
               for item in unavailable)
    assert all(item['affected_scope'] == 'none' or
               {'kind': 'parameter', 'name': 'kwargs',
                'element_path': []} in item['unaffected_values']
               for item in unavailable)


def test_keras_and_dask_mapping_element_facts():
    keras = analyze('keras-2.1.6', ['callbacks.py'],
                    'keras.callbacks', 'ReduceLROnPlateau.__init__')
    assert any(item['operation'] == 'pop'
               and item['element_path'] == ['epsilon']
               for item in keras.functions[0]['mapping_effects'])
    assert any(item['reason'] == 'unsupported_assignment'
               and {'kind': 'parameter', 'name': 'kwargs',
                    'element_path': ['epsilon']} in item['affected_values']
               for item in keras.boundaries)

    dask = analyze('dask-2022.4.2', ['dataframe/io/parquet/core.py'],
                   'dask.dataframe.io.parquet.core', 'read_parquet')
    assert any(item['operation'] == 'pop'
               and item['element_path'] == ['gather_statistics']
               and item['state_after'] == 'conditional'
               for item in dask.functions[0]['mapping_effects'])


def test_pydantic_real_signature_reports_required_missing():
    result = analyze('pydantic-1.5', ['main.py'],
                     'real_pydantic_callsite', 'entry',
                     extra_files=[FIXTURES / 'real_pydantic_callsite.py'])
    call = result.find_calls(callee_name='create_model')[0]
    assert call.target.qualname == 'create_model'
    assert {'kind': 'missing_required', 'parameter': '__model_name'} in call.binding_issues
    keyword = next(item for item in call.parameter_bindings
                   if item['argument'] == {'keyword': 'model_name'})
    assert keyword['parameter'] == 'field_definitions'
    assert keyword['destination_kind'] == 'var_keyword'


@pytest.mark.parametrize('source_id,owner', [
    ('matplotlib-3.6.0', 'FancyArrowPatch'),
    ('matplotlib-3.7.0', 'FancyBboxPatch')])
def test_matplotlib_decorated_super_has_source_candidate_and_boundary(source_id, owner):
    result = analyze(source_id, ['patches.py'],
                     'matplotlib.patches', owner + '.__init__')
    call = result.find_calls(callee_name='super().__init__')[0]
    assert call.target.qualname == 'Patch.__init__'
    assert any(item['call_id'] == call.id
               and item['reason'] == 'decorated_target_candidate'
               for item in result.boundaries)


def test_matplotlib_shadow_receiver_candidate_retains_decorated_class_boundary():
    result = analyze('matplotlib-3.5.0', ['patches.py', 'artist.py'],
                     'matplotlib.patches', 'Shadow.__init__')
    call = result.find_calls(callee_name='self.update')[0]
    assert call.target.qualname == 'Artist.update'
    assert any(item.get('call_id') == call.id
               and item['reason'] == 'decorated_class_candidate'
               for item in result.boundaries)


def test_matplotlib_colorbar_external_receiver_remains_unresolved():
    result = analyze('matplotlib-3.7.0', ['colorbar.py'],
                     'matplotlib.colorbar', 'Colorbar.set_ticks')
    call = result.find_calls(callee_name='self._long_axis().set_ticks')[0]
    assert call.target is None and call.target_status == 'receiver_unresolved'
    assert any(item.get('call_id') == call.id
               and item['reason'] == 'receiver_unresolved'
               for item in result.boundaries)
