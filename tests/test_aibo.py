## @package tests.test_aibo
#  Test pcresolve against the AIBO project oracle.
#
#  AIBO is a black-box optimization framework with 10 Python files.
#  It uses: numpy, scipy, matplotlib, gym, pygame, Box2D, cma,
#  pybobyqa, pymoo, nevergrad, AIBO, LassoBench.
#
#  Oracle built by manual code review of all 10 source files.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "tested_projects", "AIBO")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


@pytest.fixture(scope="module")
def calls_by_top(result):
    """Return dict of top_library -> list of ApiCall."""
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


@pytest.fixture(scope="module")
def calls_by_file(result):
    """Return dict of filename -> list of ApiCall."""
    d = {}
    for f in result.files:
        key = os.path.basename(f.file_path)
        d[key] = f.api_calls
    return d


# ── Structural checks ──────────────────────────────────────────────────

def test_all_files_analyzed(result):
    """All 10 Python files should be analyzed."""
    names = {os.path.basename(f.file_path) for f in result.files}
    expected = {
        "run.py", "__init__.py", "synthetic.py", "lasso.py", "test.py",
        "mujoco.py", "push_utils.py", "robot_push.py", "rover.py", "rover_utils.py",
    }
    missing = expected - names
    assert not missing, f"Files not analyzed: {missing}"


def test_no_files_errored(result):
    """All files should have a module_name (sanity check that parsing succeeded)."""
    for f in result.files:
        assert f.module_name is not None, f"{os.path.basename(f.file_path)} has no module_name"


# ── Correct third-party classification ─────────────────────────────────

def test_numpy_calls(calls_by_top):
    """numpy calls should be classified correctly."""
    assert "numpy" in calls_by_top, "No numpy calls found"
    # numpy is the most common third-party import
    assert len(calls_by_top["numpy"]) > 100


def test_scipy_calls(calls_by_top):
    """scipy calls should be classified as scipy."""
    assert "scipy" in calls_by_top
    scipy_exprs = [c.expression for c in calls_by_top["scipy"]]
    assert any("dual_annealing" in e or "minimize" in e for e in scipy_exprs)


def test_matplotlib_calls(calls_by_top):
    """matplotlib calls should be classified correctly."""
    assert "matplotlib" in calls_by_top


def test_pygame_calls(calls_by_top):
    """pygame calls should be classified as pygame."""
    assert "pygame" in calls_by_top


def test_gym_calls(calls_by_top):
    """gym.make() calls should be classified as gym."""
    assert "gym" in calls_by_top


# ── Local function / method classification ─────────────────────────────

def test_local_module_classes_are_local(calls_by_top):
    """Locally defined classes (Levy, Ackley, Rover, etc.) should be local."""
    local_exprs = [c.expression for c in calls_by_top.get("local", [])]
    # Various local class instantiations
    local_indicators = [
        "PushReward(", "Rover(", "HalfCheetah(", "Levy(", "Ackley(",
        "Rastrigin(", "Rosenbrock(", "Griewank(", "Schwefel(",
        "tracker(", "LassoBenchFunction(",
        "guiWorld(", "b2WorldInterface(", "end_effector(",
        "create_body(", "make_base(", "run_simulation(",
    ]
    found = sum(1 for e in local_exprs for ind in local_indicators if ind in e)
    assert found > 0, "Expected local class instantiations classified as local"


# ── Known issues — documented limitations ──────────────────────────────

def test_np_alias_resolves_to_numpy(calls_by_top):
    """np.* calls should resolve to numpy, not np."""
    assert "np" not in calls_by_top, "np alias should be merged to numpy"


def test_ng_alias_resolves_to_nevergrad(calls_by_top):
    """ng.* calls should resolve to nevergrad, not ng."""
    assert "nevergrad" in calls_by_top, "No nevergrad calls found"
    ng_exprs = [c.expression for c in calls_by_top["nevergrad"]]
    assert any("ng." in e for e in ng_exprs), "Expected ng.* calls under nevergrad"
    # Verify all ng.*-pattern calls are under nevergrad, not ng
    ng_alias_calls_in_ng = [
        c.expression for c in calls_by_top.get("ng", [])
        if c.expression.startswith("ng.")
    ]
    assert not ng_alias_calls_in_ng, (
        f"ng.* alias calls still under 'ng': {ng_alias_calls_in_ng}"
    )


def test_box2d_wildcard_imports_resolve_to_box2d(calls_by_top):
    """b2Vec2/b2World/b2PolygonShape/b2CircleShape should resolve to Box2D."""
    assert "Box2D" in calls_by_top, "Box2D should appear as top_library"
    wildcard_names = ["b2Vec2", "b2World", "b2PolygonShape", "b2CircleShape"]
    leaked = [n for n in wildcard_names if n in calls_by_top]
    assert not leaked, f"Box2D wildcard names leaked: {leaked}"


def test_baselines_is_third_party(calls_by_top):
    """baselines (OpenAI Baselines) is a third-party library."""
    assert "baselines" in calls_by_top


def test_local_variables_are_not_top_library(calls_by_top):
    local_vars = ["UCB"]
    leaked = [v for v in local_vars if v in calls_by_top]
    assert not leaked, f"Local variables leaked: {leaked}"


# ── No unresolved structured tuples ────────────────────────────────────

def test_stdlib_modules_classified_by_own_name(calls_by_top):
    """stdlib modules (os, time, etc.) should keep their own module name."""
    stdlib_mods = ["argparse", "time", "os", "json", "datetime", "re"]
    for m in stdlib_mods:
        assert m in calls_by_top, (
            f"{m} should appear as top_library (stdlib, needs import)"
        )

def test_no_unresolved_structured_tuples(calls_by_top):
    """Structured tuples like ('container_item', ...) should not appear."""
    structured = [k for k in calls_by_top if isinstance(k, tuple) or str(k).startswith("(")]
    assert not structured, f"Unresolved structured tuples: {structured}"
