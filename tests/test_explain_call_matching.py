## @package tests.test_explain_call_matching
#  Regression coverage for callable-name matching in explain-call queries.

import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import analyze_project
from pcresolve.views import build_explain_call_view


FIXTURE = Path(__file__).parent / 'fixtures' / 'explain_call_matching'


@pytest.fixture(scope='module')
def result():
    return analyze_project(FIXTURE)


@pytest.mark.parametrize('query, expected', [
    ('Series', ['Series', 'pd.Series', 'SeriesAlias']),
    ('pd.Series', ['pd.Series']),
    ('pandas.Series', ['pd.Series']),
    ('pandas.core.series.Series', ['Series', 'SeriesAlias']),
    ('core.series.Series', ['Series', 'SeriesAlias']),
    ('SeriesAlias', ['SeriesAlias']),
    ('ABCSeries', ['ABCSeries']),
    ('Series.to_numpy', ['Series.to_numpy']),
    ('np.array', ['np.array']),
    ('numpy.array', ['np.array']),
    ('array', ['np.array']),
    ('Ser', []),
    ('series', []),
    ('pandas', []),
    ('Series(', []),
    ('', []),
])
def test_query_matches_callable_name_or_dotted_suffix(result, query, expected):
    view = build_explain_call_view(result, query, top=0)
    assert view['query'] == query
    assert view['count'] == len(expected)
    assert [call['func_name'] for call in view['matches']] == expected


@pytest.mark.parametrize('top, expected', [
    (1, ['Series']),
    (2, ['Series', 'pd.Series']),
    (0, ['Series', 'pd.Series', 'SeriesAlias']),
])
def test_count_is_not_limited_by_top(result, top, expected):
    view = build_explain_call_view(result, 'Series', top=top)
    assert view['count'] == 3
    assert [call['func_name'] for call in view['matches']] == expected


@pytest.mark.parametrize('query, count, top', [
    ('Series', 3, 0),
    ('Series', 3, 1),
    ('pandas.core.series.Series', 2, 0),
    ('Ser', 0, 0),
])
def test_cli_uses_callable_name_matching(query, count, top):
    run = subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'pcresolve',
         str(FIXTURE / 'main.py'), '--explain-call', query, '--top', str(top)],
        capture_output=True, text=True, encoding='utf-8',
    )
    assert run.returncode == 0, run.stderr
    assert 'Matches: %d' % count in run.stdout
    assert 'expression: TypeError(' not in run.stdout
    assert 'expression: isinstance(' not in run.stdout
    if query == 'Series':
        assert 'expression: ABCSeries(' not in run.stdout
        assert 'expression: SeriesExtra(' not in run.stdout
        assert 'expression: Series.to_numpy(' not in run.stdout
        assert run.stdout.count('    expression: ') == (min(top, count) if top > 0 else count)
