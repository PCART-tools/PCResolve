import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test_wildcard_re_export", "pkg")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


def test_files_analyzed(result):
    assert len(result.files) == 2


def test_stats_is_third_party(calls_by_top):
    """stats from `from explore import *` should not be local."""
    assert "local" not in calls_by_top


def test_no_stats_string_in_top(calls_by_top):
    """stats should resolve to scipy, not stay as raw 'stats'."""
    assert "stats" not in calls_by_top


def test_scipy_is_third_party(calls_by_top):
    assert "scipy" in calls_by_top
