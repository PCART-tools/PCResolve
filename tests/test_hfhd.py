import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "hfhd")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 6

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_seaborn(calls_by_top): assert "seaborn" in calls_by_top
def test_numba(calls_by_top): assert "numba" in calls_by_top
def test_datetime(calls_by_top): assert "datetime" in calls_by_top
@pytest.mark.xfail(reason="KNOWN: local vars (hf:2, sim:1, hd:1) + structured tuples (2)")
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["hf", "sim", "hd"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
