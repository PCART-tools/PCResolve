import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "giantpopflucts")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 9

def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_seaborn(calls_by_top): assert "seaborn" in calls_by_top
def test_pystan(calls_by_top): assert "pystan" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_random_is_third_party(calls_by_top): assert "random" in calls_by_top

def test_local_vars_not_top(calls_by_top):
    for v in ["df_freq()", "p"]:
        assert v not in calls_by_top, f"'{v}' leaked as top_library"
