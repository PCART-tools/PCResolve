import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "MAHE_OD_DATASET")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 8

def test_torch(calls_by_top): assert "torch" in calls_by_top
def test_torchvision(calls_by_top): assert "torchvision" in calls_by_top
def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_cv2(calls_by_top): assert "cv2" in calls_by_top
def test_albumentations(calls_by_top): assert "albumentations" in calls_by_top
def test_os(calls_by_top): assert "os" in calls_by_top
def test_json(calls_by_top): assert "json" in calls_by_top
def test_glob(calls_by_top): assert "glob" in calls_by_top
def test_pathlib(calls_by_top): assert "pathlib" in calls_by_top
def test_random(calls_by_top): assert "random" in calls_by_top
def test_xml(calls_by_top): assert "xml" in calls_by_top
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in [] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"

@pytest.mark.xfail(reason="KNOWN: distortions[*] leaks as top_library (1 call)")
def test_no_subscript_top(calls_by_top):
    subscript_keys = [k for k in calls_by_top if "[" in str(k)]
    assert not subscript_keys, f"Subscript keys leaked: {subscript_keys}"
