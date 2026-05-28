import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "polire")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 35

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_sklearn(calls_by_top): assert "sklearn" in calls_by_top
def test_seaborn(calls_by_top): assert "seaborn" in calls_by_top
def test_shapely(calls_by_top): assert "shapely" in calls_by_top
def test_pykrige(calls_by_top): assert "pykrige" in calls_by_top
def test_xgboost(calls_by_top): assert "xgboost" in calls_by_top
def test_GPy(calls_by_top): assert "GPy" in calls_by_top
def test_multiprocessing(calls_by_top): assert "multiprocessing" in calls_by_top

def test_math(calls_by_top): assert "math" in calls_by_top
def test_time(calls_by_top): assert "time" in calls_by_top
def test_pytest(calls_by_top): assert "pytest" in calls_by_top
def test_setuptools(calls_by_top): assert "setuptools" in calls_by_top
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["NSGP", "GP", "[local,GP]"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
