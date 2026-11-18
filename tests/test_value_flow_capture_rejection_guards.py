import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def query(tmp_path, text):
    (tmp_path / 'example.py').write_text(text)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('example', 'checked'))
    return result.functions[0]['capture_rejection_guards']


@pytest.mark.parametrize('condition', ['kw', 'labels is None and kw'])
def test_dictionary_truth_rejection_requires_independent_execution_evidence(tmp_path, condition):
    facts = query(tmp_path, 'def checked(labels=None, **kw):\n    if ' + condition +
                  ':\n        raise ValueError("invalid labels")\n')
    assert len(facts) == 1
    fact = facts[0]
    assert fact['status'] == 'requires_observation' and fact['parameter'] == 'kw'
    assert fact['exception'] == 'ValueError'
    assert fact['guard_completed'] is False and fact['runtime_rejection_confirmed'] is False
    assert fact['source_hash'] and fact['presence_evidence']


@pytest.mark.parametrize('text', [
    'def checked(**kw):\n    if not kw:\n        raise ValueError("empty")\n',
    'def checked(labels=None, **kw):\n    if labels or kw:\n        raise ValueError("labels")\n',
    'def checked(**kw):\n    if kw:\n        clean(kw)\n        raise ValueError("invalid")\n',
    'def checked(**kw):\n    if kw:\n        raise external("invalid")\n',
    'from external import ValueError\ndef checked(**kw):\n    if kw:\n        raise ValueError("invalid")\n',
    'def checked(**kw):\n    def nested(kw):\n        if kw:\n            raise ValueError("invalid")\n',
])
def test_other_polarity_control_effects_and_exception_protocols_are_excluded(tmp_path, text):
    assert not query(tmp_path, text)
