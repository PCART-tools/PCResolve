import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "Python-Workshop")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 5

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_sklearn(calls_by_top): assert "sklearn" in calls_by_top

def test_xrange_not_top(calls_by_top):
    assert "xrange" not in calls_by_top
