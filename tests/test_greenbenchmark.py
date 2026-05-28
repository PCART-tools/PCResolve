import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "greenbenchmark")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE, scope_model="v1")

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_all_files_analyzed(result): assert len(result.files) == 11

def test_matplotlib(calls_by_top): assert "matplotlib" in calls_by_top
def test_pandas(calls_by_top): assert "pandas" in calls_by_top
def test_numpy(calls_by_top): assert "numpy" in calls_by_top
def test_scipy(calls_by_top): assert "scipy" in calls_by_top
def test_tqdm(calls_by_top): assert "tqdm" in calls_by_top
def test_statsmodels(calls_by_top): assert "statsmodels" in calls_by_top

# com.android.monkeyrunner / com.dtmilano.android.viewclient are legitimate 3rd-party libraries
def test_com_is_third_party(calls_by_top): assert "com" in calls_by_top

def test_no_local_vars_leaked(calls_by_top):
    leaked = [v for v in ["touch", "back", "swipeUp", "save_interaction", "v",
                          "device", "type_text", "hold", "sleep", "test_helper"]
              if v in calls_by_top]
    assert not leaked, f"Local vars/modules leaked: {leaked}"

def test_accuracy_100_percent(calls_by_top):
    good = {"local", "python", "matplotlib", "pandas", "numpy", "scipy",
            "tqdm", "statsmodels", "os", "time", "sys", "json", "argparse", "com"}
    total = sum(len(v) for v in calls_by_top.values())
    correct = sum(len(v) for k, v in calls_by_top.items() if k in good)
    assert correct == total, f"Accuracy: {correct}/{total}"
