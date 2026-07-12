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
    tornado_exprs = {c.expression for c in calls_by_top["tornado"]}
    # Key Tornado API calls that must be classified as tornado
    for expr in ["tornado.gen.Return", "tornado.gen.Task",
                 "tornado.gen.Wait", "tornado.gen.Callback",
                 "tornado.tcpserver.TCPServer.__init__",
                 "tornado.ioloop.IOLoop.instance()",
                 "tornado.ioloop.IOLoop.instance().start()"]:
        assert any(expr in e for e in tornado_exprs), \
            f"Missing expected tornado call: {expr}"

def test_redis_calls(calls_by_top):
    assert "redis" in calls_by_top

def test_stdlib_modules_are_third_party(calls_by_top):
    """itertools, signal, time, json are stdlib that need import."""
    for m in ["itertools", "signal", "time", "json"]:
        assert m in calls_by_top, f"{m} should be third-party (needs import)"


def test_line_not_top(calls_by_top):
    assert "line" not in calls_by_top


# ── P0: Local method call identity protection ──────────────────────────

def test_set_expire_is_local(calls_by_top):
    """self.set_expire() (3 occurrences) — defined in local Scope class."""
    set_expire_calls = [c for c in calls_by_top.get("local", [])
                        if "set_expire" in c.expression]
    assert len(set_expire_calls) == 3, \
        f"Expected 3 self.set_expire() calls as local, found {len(set_expire_calls)}"
    # Verify they're not in redis
    redis_expire = [c for c in calls_by_top.get("redis", [])
                    if "set_expire" in c.expression]
    assert len(redis_expire) == 0, \
        "self.set_expire() should NOT be classified as redis"


def test_add_request_is_local(calls_by_top):
    """scope.add_request(...) — defined in local Scope class."""
    add_req_calls = [c for c in calls_by_top.get("local", [])
                     if "add_request" in c.expression]
    assert len(add_req_calls) >= 1, \
        f"Expected scope.add_request() as local, found {len(add_req_calls)}"
    # Verify it's not in redis
    redis_add_req = [c for c in calls_by_top.get("redis", [])
                     if "add_request" in c.expression]
    assert len(redis_add_req) == 0, \
        "scope.add_request() should NOT be classified as redis"


def test_self_r_calls_still_redis(calls_by_top):
    """self.r.set/zadd/expire(...) — receiver is external Redis client."""
    redis_calls = calls_by_top.get("redis", [])
    redis_exprs = {c.expression for c in redis_calls}
    # These are direct library method calls through self.r
    for pattern in ["self.r.set(", "self.r.zadd(", "self.r.expire("]:
        found = any(pattern in e for e in redis_exprs)
        assert found, f"Missing expected redis call: {pattern}"


# ── P0: Literal string methods + inherited external methods ──────────────


def test_literal_format_is_python(result):
    """'"{}".format(...)' on str literal → python."""
    format_calls = [c for c in result.all_api_calls
                    if "'{}'.format" in c.expression]
    assert len(format_calls) >= 1, \
        "literal '{}'.format() not found in output"
    for c in format_calls:
        assert c.top_library == "python", \
            f"'{c.expression}' should be python, got {c.top_library}"


def test_server_listen_is_tornado(calls_by_top):
    """server.listen(8889) — inherited from tornado.tcpserver.TCPServer."""
    tornado_calls = calls_by_top.get("tornado", [])
    listen_calls = [c for c in tornado_calls
                    if "server.listen" in c.expression]
    assert len(listen_calls) >= 1, \
        f"Expected server.listen() as tornado, found {len(listen_calls)}"
    # Verify it's not in local
    local_calls = calls_by_top.get("local", [])
    local_listen = [c for c in local_calls
                    if "server.listen" in c.expression]
    assert len(local_listen) == 0, \
        "server.listen() should NOT be classified as local"


def test_self_set_expire_still_local(calls_by_top):
    """self.set_expire() (3 occurrences) → local (not tornado)."""
    local_calls = calls_by_top.get("local", [])
    expire_local = [c for c in local_calls
                    if "set_expire" in c.expression]
    assert len(expire_local) == 3, \
        f"Expected 3 self.set_expire() as local, found {len(expire_local)}"
