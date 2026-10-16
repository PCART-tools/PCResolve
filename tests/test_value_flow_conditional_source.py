## @package tests.test_value_flow_conditional_source

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_conditional_source'


def test_conditional_source_path_retains_uncertainty_as_a_required_predicate():
    analyzer = FlowAnalyzer(project_root=ROOT)
    strict = analyzer.analyze(FunctionRef('cases', 'Client'), max_depth=4)
    assert strict.find_calls(callee_name='super(Client, cls).__new__')[0].target is None
    result = analyzer.analyze(FunctionRef('cases', 'Client'), max_depth=4,
                              conditional_source_state=True)
    call = result.find_calls(callee_name='super(Client, cls).__new__')[0]
    assert call.target.qualname == 'Factory.__new__'
    assert result.inputs['conditional_source_state'] is True
    assert any(condition.get('kind') == 'source_state_preserved' for condition in call.conditions)
    assert any(boundary['reason'] == 'conditional_source_state' for boundary in result.boundaries)
    initialized = result.find_calls(callee_name='instance.initialize')[0]
    assert {target['qualname'] for target in initialized.target_candidates} == {'Backend.initialize'}
    assert initialized.candidate_paths and initialized.candidate_paths[0]['conditions']
    assert analyzer.analyze(FunctionRef('cases', 'Client'), max_depth=4).to_dict() == strict.to_dict()


def test_known_structural_writes_cannot_be_conditioned_away():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Changed'),
        max_depth=4, conditional_source_state=True)
    assert result.find_calls(callee_name='super(Client, cls).__new__')[0].target is None


def test_generic_parameter_is_not_a_source_class_entry():
    with pytest.raises(ValueError, match='source class'):
        FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'generic'),
                                              conditional_source_state=True)


@pytest.mark.parametrize('entry', ['ChangedByName', 'Rebound', 'Unreachable'])
def test_known_replacement_rebinding_and_inactive_paths_do_not_recover_initialization(entry):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', entry),
        max_depth=4, conditional_source_state=True)
    assert not any(call.target or call.target_candidates
                   for call in result.find_calls(callee_name='instance.initialize'))


def test_expansion_restores_the_selected_mode_after_another_query():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', 'Client'), conditional_source_state=True)
    call = result.find_calls(callee_name='super(Client, cls).__new__')[0]
    before = result.to_dict()
    analyzer.analyze(FunctionRef('cases', 'Client'))
    expanded = analyzer.expand(result, call.id)
    assert expanded.inputs['conditional_source_state'] is True
    assert expanded.find_calls(callee_name='instance.initialize')
    assert result.to_dict() == before


def test_conditional_lookup_respects_context_budgets_and_argument_validation():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', 'Client'), max_call_contexts=1,
                              conditional_source_state=True)
    assert any('budget' in boundary['reason'] for boundary in result.boundaries)
    assert not result.find_calls(callee_name='instance.initialize')
    with pytest.raises(ValueError, match='must be bool'):
        analyzer.analyze(FunctionRef('cases', 'Client'), conditional_source_state=1)
