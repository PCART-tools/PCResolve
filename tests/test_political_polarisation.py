import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "political-polarisation")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_files_analyzed(result): assert len(result.files) == 1

def test_networkx_calls(calls_by_top):
    assert "networkx" in calls_by_top

def test_pandas_calls(calls_by_top):
    assert "pandas" in calls_by_top

def test_matplotlib_calls(calls_by_top):
    assert "matplotlib" in calls_by_top

def test_IPython_calls(calls_by_top):
    assert "IPython" in calls_by_top

@pytest.mark.xfail(reason="KNOWN: WordCloud() not resolved to wordcloud library (2 calls)")
def test_wordcloud_calls(calls_by_top):
    assert "wordcloud" in calls_by_top

@pytest.mark.xfail(reason="KNOWN: df_name local var leaks as top_library (10 calls)")
def test_df_name_not_top(calls_by_top):
    assert "df_name" not in calls_by_top

def test_item_not_top(calls_by_top):
    assert "item()" not in calls_by_top
