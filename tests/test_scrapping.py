import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "scrapping")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 2

def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_requests(calls_by_top): assert "requests" in calls_by_top
def test_bs4(calls_by_top): assert "bs4" in calls_by_top
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["self", "self()"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"


def test_unresolved_local_return_chain_is_not_claimed_local(result):
    calls = [
        call for file_analysis in result.files
        for call in file_analysis.api_calls
        if call.expression == "link.find(':')"
    ]
    assert len(calls) == 8
    assert all(call.top_library == "unknown" for call in calls)
