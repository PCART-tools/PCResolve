import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "polars-book-cn")

@pytest.fixture(scope="module")
def result(): return analyze_project(FIXTURE)

@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls: d.setdefault(c.top_library, []).append(c)
    return d

def test_files_analyzed(result): assert len(result.files) == 1

def test_polars_calls(calls_by_top):
    assert "polars" in calls_by_top

def test_datetime_calls(calls_by_top):
    assert "datetime" in calls_by_top
