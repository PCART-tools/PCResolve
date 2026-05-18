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
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["hf", "sim", "hd"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"

def test_no_structured_tuples(calls_by_top):
    structured = [k for k in calls_by_top if isinstance(k, tuple) or str(k).startswith("(")]
    assert not structured, f"Structured tuples leaked: {structured}"

def test_uncond_var_is_local_not_python(calls_by_top):
    """self.uncond_var(...) is a locally-defined static method — should be local, not python."""
    calls = calls_by_top.get("python", [])
    uncond_var_calls = [c for c in calls if "uncond_var" in c.expression]
    assert not uncond_var_calls, (
        f"self.uncond_var is local, got python: {[c.expression for c in uncond_var_calls]}"
    )

def test_self_attr_pandas_methods_are_pandas(calls_by_top):
    """self.price/cum_feature were assigned from pd.DataFrame, so their pandas
    methods should resolve to pandas, not local."""
    local_calls = calls_by_top.get("local", [])
    leaked = [c for c in local_calls
              if "self.price" in c.expression and "between_time" in c.expression
              or "self.cum_feature" in c.expression and "between_time" in c.expression]
    assert not leaked, (
        f"self.price/cum_feature.between_time should be pandas, got local: "
        f"{[c.expression for c in leaked]}"
    )
