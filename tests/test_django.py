## @package tests.test_django
#  Test pcresolve against the django (tornado proxy) project oracle.
#
#  Despite the name, this is a Tornado TCP proxy with Redis (1 file).
#  It uses: tornado, redis, itertools, signal, time, json.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "django"
)


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


# ── Structural ─────────────────────────────────────────────────────────

def test_one_file_analyzed(result):
    assert len(result.files) == 1
    assert result.files[0].module_name is not None


# ── Correct third-party classifications ─────────────────────────────────

def test_tornado_calls(calls_by_top):
    assert "tornado" in calls_by_top
    assert len(calls_by_top["tornado"]) >= 10

def test_redis_calls(calls_by_top):
    assert "redis" in calls_by_top

def test_stdlib_modules_are_third_party(calls_by_top):
    """itertools, signal, time, json are stdlib that need import."""
    for m in ["itertools", "signal", "time", "json"]:
        assert m in calls_by_top, f"{m} should be third-party (needs import)"


def test_line_not_top(calls_by_top):
    assert "line" not in calls_by_top
