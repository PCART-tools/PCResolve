import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "simulation")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 8

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_porepy(calls_by_top): assert "porepy" in calls_by_top
def test_os(calls_by_top): assert "os" in calls_by_top
def test_sys(calls_by_top): assert "sys" in calls_by_top
def test_itertools(calls_by_top): assert "itertools" in calls_by_top
def test_seaborn(calls_by_top): assert "seaborn" in calls_by_top
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["data", "create_grid", "analytical", "discretization", "solve", "export_results"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
