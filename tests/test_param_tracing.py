import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test_param_tracing")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE, scope_model="v2")


@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


def test_files_analyzed(result):
    assert len(result.files) == 1


def test_param_df_traces_to_pandas(result):
    for f in result.files:
        for c in f.api_calls:
            if c.expression in ("df.info()", "df.dropna()"):
                assert c.top_library == "pandas", f"{c.expression} -> {c.top_library}"


def test_return_value_head_traces_to_pandas(result):
    for f in result.files:
        for c in f.api_calls:
            if "result.head" in c.expression:
                assert c.top_library == "pandas", f"{c.expression} -> {c.top_library}"


def test_unbound_name_not_traced_to_same_named_parameter():
    """An unbound module-level name must not be traced to a parameter
    of a function that happens to use the same name."""
    import tempfile, os
    code = ("import pandas as pd\n"
            "def identity(df):\n"
            "    return df\n"
            "all_df = pd.read_csv('x')\n"
            "identity(all_df)\n"
            "df.head()\n")
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write(code)
        r = analyze_project(td, scope_model="v2")
        head_calls = [c for c in r.all_api_calls if "df.head" in c.expression]
        assert len(head_calls) >= 1
        assert head_calls[0].top_library != "pandas", (
            "Unbound df.head() must NOT be traced to identity's df param")
