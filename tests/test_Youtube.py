import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "Youtube")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 2

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_gensim(calls_by_top): assert "gensim" in calls_by_top
def test_pyprind(calls_by_top): assert "pyprind" in calls_by_top
def test_logging(calls_by_top): assert "logging" in calls_by_top
def test_collections(calls_by_top): assert "collections" in calls_by_top
def test_operator(calls_by_top): assert "operator" in calls_by_top
def test_pickle(calls_by_top): assert "pickle" in calls_by_top
def test_time(calls_by_top): assert "time" in calls_by_top
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in [] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
