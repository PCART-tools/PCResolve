import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "SDOML")

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
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_skimage(calls_by_top): assert "skimage" in calls_by_top
def test_sunpy(calls_by_top): assert "sunpy" in calls_by_top
def test_multiprocessing(calls_by_top): assert "multiprocessing" in calls_by_top
def test_argparse(calls_by_top): assert "argparse" in calls_by_top
def test_os(calls_by_top): assert "os" in calls_by_top
def test_random(calls_by_top): assert "random" in calls_by_top
def test_warnings(calls_by_top): assert "warnings" in calls_by_top
@pytest.mark.xfail(reason="KNOWN: function expression leaks (enumerate/Xr/p/open: 9 calls)")
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["enumerate()", "Xr()", "p()", "open()"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
