import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "tensorflow1")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_files_analyzed(result): assert len(result.files) == 1

def test_tensorflow(calls_by_top): assert "tensorflow" in calls_by_top

@pytest.mark.xfail(reason="KNOWN: 1 calls")
def test_issues_not_top(calls_by_top):
    for v in ["super()"]:
        assert v not in calls_by_top, f"{v} leaked"
