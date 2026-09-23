## @package tests.test_value_flow_enhancements
#  PCBench-driven additive flow-0.2 regression coverage.

from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_enhancements'
PCB = Path(__file__).parent / 'fixtures' / 'pcbench_regressions'


def analyze(root, module, qualname, depth=1):
    return FlowAnalyzer(project_root=root).analyze(
        FunctionRef(module=module, qualname=qualname), max_depth=depth)


def test_constructor_super_inheritance_and_local_receiver_targets():
    constructed = analyze(ROOT, 'targets', 'construct')
    assert constructed.find_calls(callee_name='Product')[0].target.qualname == 'Product.__init__'
    new_only = analyze(ROOT, 'targets', 'construct_new')
    assert new_only.find_calls(callee_name='Root')[0].target.qualname == 'Root.__new__'

    explicit = analyze(ROOT, 'targets', 'Child.build')
    assert explicit.find_calls(callee_name='super(Child, cls).__new__')[0].target.qualname == 'Root.__new__'

    inherited = analyze(ROOT, 'targets', 'Child.forward')
    assert inherited.find_calls(callee_name='super().inherited')[0].target.qualname == 'Root.inherited'

    local = analyze(ROOT, 'targets', 'local_receiver')
    assert local.find_calls(callee_name='product.consume')[0].target.qualname == 'Product.consume'

    bounded = analyze(ROOT, 'targets', 'bounded_receiver')
    call = bounded.find_calls(callee_name='product.consume')[0]
    assert call.target is None and call.target_status == 'bounded_alternatives'
    assert {candidate['qualname'] for candidate in call.target_candidates} == {
        'Alpha.consume', 'Beta.consume'}

    uncertain = analyze(ROOT, 'targets', 'Uncertain.forward')
    assert uncertain.find_calls(callee_name='super().inherited')[0].target is None

    nested = analyze(ROOT, 'targets', 'nested_constructor')
    assert nested.find_calls(callee_name='Nested')[0].target.qualname == (
        'nested_constructor.Nested.__init__')

    diamond = analyze(ROOT, 'targets', 'Diamond.forward')
    assert diamond.find_calls(callee_name='super().inherited')[0].target.qualname == (
        'Right.inherited')


def test_pcbench_tornado_and_pandas_target_regressions():
    tornado = analyze(PCB, 'tornado_httpclient', 'AsyncHTTPClient.fetch')
    assert tornado.find_calls(callee_name='HTTPRequest')[0].target.qualname == 'HTTPRequest.__init__'
    tornado_new = analyze(PCB, 'tornado_httpclient', 'AsyncHTTPClient.__new__')
    assert tornado_new.find_calls(
        callee_name='super(AsyncHTTPClient, cls).__new__')[0].target.qualname == 'Configurable.__new__'

    pandas = analyze(PCB, 'pandas_take', 'DataFrame.take')
    assert pandas.entry.qualname == 'NDFrame.take'
    assert pandas.functions[0]['function']['qualname'] == 'NDFrame.take'

    for owner in ('FancyArrowPatch', 'FancyBboxPatch'):
        matplotlib = analyze(PCB, 'matplotlib_receivers', owner + '.__init__')
        call = matplotlib.find_calls(callee_name='super().__init__')[0]
        assert call.target.qualname == 'Patch.__init__'
        assert any(boundary['reason'] == 'decorated_caller_semantics'
                   for boundary in matplotlib.boundaries)
    shadow = analyze(PCB, 'matplotlib_receivers', 'Shadow.__init__')
    assert shadow.find_calls(callee_name='self.update')[0].target.qualname == 'Artist.update'


def test_boundaries_report_affected_roots_and_unrelated_source_files():
    result = analyze(ROOT, 'boundaries', 'Connector.__init__')
    assignments = [item for item in result.boundaries
                   if item['reason'] == 'unsupported_assignment']
    assert assignments
    assert all(item['affected_scope'] == 'known' for item in assignments)
    assert all('kwargs' not in {root['name'] for root in item['affected_values']}
               for item in assignments)
    unavailable = next(item for item in result.boundaries
                       if item['reason'] == 'source_unavailable')
    assert unavailable['affected_scope'] == 'none'
    assert unavailable['entry_relation'] == 'unrelated'

    related = analyze(ROOT, 'related_boundary', 'entry')
    unavailable = next(item for item in related.boundaries
                       if item['reason'] == 'source_unavailable')
    assert unavailable['affected_scope'] == 'unknown'
    assert unavailable['entry_relation'] == 'possible'

    unused = analyze(ROOT, 'related_boundary', 'unused')
    unavailable = next(item for item in unused.boundaries
                       if item['reason'] == 'source_unavailable')
    assert {'kind': 'parameter', 'name': 'kwargs', 'element_path': []} in (
        unavailable['unaffected_values'])

    reflected = analyze(ROOT, 'related_boundary', 'reflected')
    unavailable = next(item for item in reflected.boundaries
                       if item['reason'] == 'source_unavailable')
    assert unavailable['unaffected_values'] == []

    write = analyze(ROOT, 'boundaries', 'unknown_mapping_write')
    boundary = next(item for item in write.boundaries
                    if item['reason'] == 'unsupported_assignment')
    assert {'kind': 'parameter', 'name': 'mapping',
            'element_path': ['feature']} in boundary['affected_values']


def test_mapping_element_facts_cover_pop_membership_delete_update_merge_and_argument():
    result = analyze(ROOT, 'mappings', 'mapping_operations')
    summary = result.functions[0]
    operations = {item['operation'] for item in summary['mapping_effects']}
    assert {'pop', 'membership', 'delete', 'update', 'merge'} <= operations
    pop = next(item for item in summary['mapping_effects'] if item['operation'] == 'pop')
    assert pop['element_path'] == ['epsilon'] and pop['state_after'] == 'absent'
    removed = next(item for item in summary['mapping_effects'] if item['operation'] == 'delete')
    assert removed['element_path'] == ['gather_statistics']
    assert removed['state_after'] == 'conditional'

    call = result.find_calls(callee_name='validate_take')[0]
    mapping = next(item for item in call.argument_sources
                   if item['argument'] == {'position': 1})
    assert any(source['kind'] == 'parameter' and source['source'] == 'kwargs'
               and source.get('output_path') == ['*'] for source in mapping['sources'])


def test_pcbench_mapping_regressions_expose_element_specific_facts():
    keras = analyze(PCB, 'mapping_cases', 'keras_reduce_lr')
    assert any(item['operation'] == 'pop' and item['element_path'] == ['epsilon']
               for item in keras.functions[0]['mapping_effects'])
    dask = analyze(PCB, 'mapping_cases', 'dask_gather')
    effect = next(item for item in dask.functions[0]['mapping_effects']
                  if item['operation'] == 'pop')
    assert effect['element_path'] == ['gather_statistics']
    assert effect['state_after'] == 'conditional'
    pandas = analyze(PCB, 'mapping_cases', 'pandas_series_take')
    call = pandas.find_calls(callee_name='validate_take')[0]
    assert any(source['source'] == 'kwargs' and source.get('output_path') == ['*']
               for source in call.argument_sources[1]['sources'])


def test_complete_binding_facts_report_missing_duplicate_keyword_destination_and_star_slots():
    captured = analyze(ROOT, 'bindings', 'pydantic_style')
    call = captured.find_calls(callee_name='create_model')[0]
    assert call.binding_status == 'invalid'
    assert {'kind': 'missing_required', 'parameter': '__model_name'} in call.binding_issues
    old_name = next(item for item in call.parameter_bindings
                    if item['argument'] == {'keyword': 'model_name'})
    assert old_name['parameter'] == 'field_definitions'
    assert old_name['destination_kind'] == 'var_keyword'
    assert old_name['target_path'] == ['model_name']

    duplicate = analyze(ROOT, 'bindings', 'duplicate')
    call = duplicate.find_calls(callee_name='positional')[0]
    assert any(item['kind'] == 'duplicate_binding' and item['parameter'] == 'value'
               for item in call.binding_issues)

    starred = analyze(ROOT, 'bindings', 'literal_star')
    call = starred.find_calls(callee_name='positional')[0]
    assert next(item for item in call.parameter_bindings
                if item['parameter'] == 'items')['target_path'] == [0]


def test_pcbench_pydantic_required_parameter_regression():
    result = analyze(PCB, 'pydantic_create_model', 'captured_old_name')
    call = result.find_calls(callee_name='create_model')[0]
    assert {'kind': 'missing_required', 'parameter': '__model_name'} in call.binding_issues
    captured = next(item for item in call.parameter_bindings
                    if item['argument'] == {'keyword': 'model_name'})
    assert captured['destination_kind'] == 'var_keyword'
