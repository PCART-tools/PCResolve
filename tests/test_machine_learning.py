import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "machine-learning")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_files_analyzed(result): assert len(result.files) == 1

def test_numpy_calls(calls_by_top):
    assert "numpy" in calls_by_top

def test_scipy_calls(calls_by_top):
    assert "scipy" in calls_by_top

def test_uarr_not_top_1(calls_by_top):
    assert "uarr" not in calls_by_top
