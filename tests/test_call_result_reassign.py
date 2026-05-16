import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test_call_result_reassign")


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
    assert len(result.files) == 1


def test_all_pandas(result):
    for f in result.files:
        for c in f.api_calls:
            assert c.top_library == "pandas", f"{c.expression} -> {c.top_library}"


def test_no_df_in_top(calls_by_top):
    assert "df" not in calls_by_top


def test_no_df_call_result_in_top(calls_by_top):
    assert "df()" not in calls_by_top


def test_no_local(calls_by_top):
    assert "local" not in calls_by_top
