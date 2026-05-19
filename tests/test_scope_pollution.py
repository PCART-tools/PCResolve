import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test_scope_pollution")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


def test_files_analyzed(result):
    assert len(result.files) == 1


def test_local_class_instantiation(calls_by_top):
    assert "local" in calls_by_top
    exprs = [c.expression for c in calls_by_top["local"]]
    assert any("Container()" in e for e in exprs)


def test_item_not_top(calls_by_top):
    assert "item" not in calls_by_top
