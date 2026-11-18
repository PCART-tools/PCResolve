import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def query(tmp_path, body, prefix=''):
    (tmp_path / 'cases.py').write_text(prefix + 'def entry(args, options, key):\n' + body)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'entry'))
    return result.functions[0]['container_predicates']


@pytest.mark.parametrize('expression,operation,parameter', [
    ('not args', 'truth', 'args'),
    ('options', 'truth', 'options'),
    ("'legacy' in options", 'contains', 'options'),
    ('key not in options', 'contains', 'options'),
    ('len(args) < 2', 'length', 'args'),
    ("'legacy' in options and external()", 'contains', 'options'),
    ('not (not args)', 'truth', 'args'),
])
def test_predicate_fact_requires_observed_container_and_execution(tmp_path, expression,
                                                                 operation, parameter):
    fact = query(tmp_path, '    if ' + expression + ':\n        return 1\n    return 0\n')[0]
    assert fact['operation'] == operation
    assert fact['parameter'] == parameter
    assert fact['status'] == 'requires_observation'
    assert fact['predicate_completed'] is False
    assert fact['container_type_proven'] is False
    assert fact['source_hash']


@pytest.mark.parametrize('expression', [
    'external() and options',
    'obj.options',
    'len(external()) < 2',
    "'legacy' in external()",
    'args[0]',
    'key in options and args',
])
def test_unsupported_or_not_definitely_evaluated_parts_are_not_promoted(tmp_path, expression):
    facts = query(tmp_path, '    if ' + expression + ':\n        return 1\n    return 0\n')
    if expression == 'key in options and args':
        assert len(facts) == 1 and facts[0]['parameter'] == 'options'
    else:
        assert not facts


def test_shadowed_len_has_no_builtin_length_obligation(tmp_path):
    assert not query(tmp_path, '    if len(args) < 2:\n        return 1\n',
                     prefix='from external import len\n')


def test_nested_named_scope_is_not_attributed_to_the_outer_function(tmp_path):
    assert not query(tmp_path, "    def nested(options):\n        if options:\n            return 1\n    return nested\n")
