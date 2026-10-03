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


def analyze(source_id, files, module, qualname, extra_files=(), max_depth=1):
    package = source(source_id)
    selected = [package / name for name in files]
    selected.extend(extra_files)
    if not all(path.is_file() for path in selected):
        pytest.skip('PCBench source files are not available')
    analyzer = FlowAnalyzer(
        source_files=selected,
        import_roots=[package.parent, FIXTURES])
    return analyzer.analyze(
        FunctionRef(module=module, qualname=qualname), max_depth=max_depth)


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


@pytest.mark.parametrize('qualname,module,class_name', [
    ('AsyncHTTPClient.configurable_base', 'tornado.httpclient', 'AsyncHTTPClient'),
    ('AsyncHTTPClient.configurable_default',
     'tornado.simple_httpclient', 'SimpleAsyncHTTPClient')])
def test_tornado_helpers_return_source_classes(qualname, module, class_name):
    result = analyze('tornado-3.0',
                     ['httpclient.py', 'util.py', 'simple_httpclient.py'],
                     'tornado.httpclient', qualname)
    returned = result.functions[0]['returns']
    assert returned
    assert {(value['module'], value['source']) for value in returned} == {
        (module, class_name)}
    assert all(value['kind'] == 'class'
               and value['class_type']['module'] == module
               and value['class_type']['qualname'] == class_name
               for value in returned)
    assert any(evidence['source_text'] == 'return ' + class_name
               for value in returned for evidence in value['evidence'])
    if class_name == 'SimpleAsyncHTTPClient':
        assert any('from tornado.simple_httpclient import SimpleAsyncHTTPClient'
                   == evidence['source_text']
                   for value in returned for evidence in value['evidence'])


@pytest.mark.parametrize('depth', [2, 4])
def test_tornado_inherited_new_preserves_class_context_and_unknown_configuration(depth):
    result = analyze('tornado-3.0',
                     ['httpclient.py', 'util.py', 'simple_httpclient.py'],
                     'tornado.httpclient', 'AsyncHTTPClient.__new__',
                     max_depth=depth)
    inherited = result.find_calls(
        callee_name='super(AsyncHTTPClient, cls).__new__')[0]
    assert inherited.target.module == 'tornado.util'
    assert inherited.target.qualname == 'Configurable.__new__'
    first_argument = next(argument for argument in inherited.argument_sources
                          if argument['parameter'] == 'cls')
    assert all(value['class_type']['qualname'] == 'AsyncHTTPClient'
               for value in first_argument['sources'])

    base_calls = result.find_calls(callee_name='cls.configurable_base')
    assert base_calls
    assert all(call.target.module == 'tornado.httpclient'
               and call.target.qualname == 'AsyncHTTPClient.configurable_base'
               for call in base_calls)
    assert all(value['class_type']['module'] == 'tornado.httpclient'
               and value['class_type']['qualname'] == 'AsyncHTTPClient'
               for call in base_calls for value in call.receiver_sources)
    if depth == 4:
        default_calls = result.find_calls(callee_name='cls.configurable_default')
        assert default_calls
        assert all(call.target.module == 'tornado.httpclient'
                   and call.target.qualname == 'AsyncHTTPClient.configurable_default'
                   for call in default_calls)
        assert all(value['class_type']['qualname'] == 'AsyncHTTPClient'
                   for call in default_calls for value in call.receiver_sources)
        configuration = next(summary for summary in result.functions
                             if summary['function']['qualname'] ==
                             'Configurable.configured_class')
        assert not any(value.get('class_type') for value in configuration['returns'])
        assert any(boundary['reason'] == 'unsupported_assignment'
                   and boundary.get('function', {}).get('qualname') ==
                   'Configurable.configured_class'
                   for boundary in result.boundaries)

    for name in ('super(Configurable, cls).__new__', 'instance.initialize'):
        call = result.find_calls(callee_name=name)[0]
        assert call.target is None
        assert call.target_candidates == []
        assert call.target_status == 'receiver_unresolved'
        assert any(boundary.get('call_id') == call.id
                   and boundary['reason'] == 'receiver_unresolved'
                   for boundary in result.boundaries)

    update = next(call for call in result.find_calls(callee_name='args.update')
                  if any(value['kind'] == 'parameter' and value['source'] == 'kwargs'
                         for argument in call.argument_sources
                         for value in argument['sources']))
    initialize = result.find_calls(callee_name='instance.initialize')[0]
    for call in (update, initialize):
        assert any(value['kind'] == 'parameter' and value['source'] == 'kwargs'
                   and value.get('output_path') == ['*']
                   for argument in call.argument_sources
                   for value in argument['sources'])


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


def test_sympy_local_import_reexport_and_identity_decorator_keep_variadic_facts():
    result = analyze('sympy-1.5', [
        'core/expr.py', 'polys/__init__.py', 'polys/rationaltools.py',
        'utilities/__init__.py', 'utilities/decorator.py'],
        'sympy.core.expr', 'Expr.together')
    call = result.find_calls(callee_name='together')[0]
    assert (call.target.module, call.target.qualname, call.target.lineno) == (
        'sympy.polys.rationaltools', 'together', 11)
    assert call.target_status == 'resolved'
    assert call.target_candidates == [result.to_dict()['calls'][0]['target']]
    assert call.binding_status == 'uncertain'
    assert call.decorator_identity_evidence[0]['decorator']['qualname'] == 'public'
    assert call.decorator_identity_evidence[0]['decorator']['module'] == (
        'sympy.utilities.decorator')
    for parameter, expansion in [('args', 'dynamic_starred'),
                                 ('kwargs', 'dynamic_keyword')]:
        binding = next(item for item in call.parameter_bindings
                       if item.get('binding_kind') == expansion)
        assert binding['status'] == 'unresolved'
        argument = next(item for item in call.argument_sources
                        if item['argument'] == binding['argument'])
        assert any(item['kind'] == 'parameter'
                   and item['source'] == parameter
                   and item.get('output_path') == ['*']
                   for item in argument['sources'])
        assert any(item['source_parameter'] == parameter
                   and item.get('output_path') == ['*']
                   for item in call.parameter_flows)
    reasons = {item['reason'] for item in result.boundaries
               if item.get('call_id') == call.id}
    assert 'identity_decorator_effects_unmodeled' in reasons
    assert 'dynamic_argument_expansion' in reasons
    assert 'definition_unavailable' not in reasons


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
