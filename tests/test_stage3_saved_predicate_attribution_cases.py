import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow"
    / "saved_predicate_attribution_cases.json"
)
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CALLER = FunctionRef(module="probe", qualname="entry")


def rows(entries):
    return {(tuple((int(line), bool(branch)) for line, branch in path), int(ret))
            for path, ret in entries}


def observed(call):
    return {(tuple((step["test"]["lineno"], bool(step["branch"]))
                   for step in flow["path"]), flow["return"]["lineno"])
            for flow in call.control_flows}


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_saved_predicate_attribution(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = {(call.callee_name, call.lineno): call
             for call in analysis.find_calls(caller=CALLER)}
    union = set().union(*(observed(call) for call in calls.values()))
    assert union == rows(case["expected_union"])
    for label, entries in case["expected_calls"].items():
        callee, lineno = label.split("@")
        call = calls.get((callee, int(lineno)))
        assert call is not None, "missing call %s" % label
        assert observed(call) == rows(entries), "%s per-call rows" % label
    outer_line = next(
        index for index, line in enumerate(case["source"].splitlines(), 1)
        if "if p(y)" in line)
    outer = calls.get(("p", outer_line))
    assert outer is not None
    assert len(outer.control_flows) == case["expected_outer_records"]
    assert analysis.to_dict().get("boundaries") == []
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_saved_predicate_fixture_shape():
    assert len(CASES) == 22
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"]


@pytest.mark.parametrize("setup,left,right,expected", [
    ("v = p(x)", "not v", "not not not v", 0),
    ("v = observe(x)\n    w = observe(x)", "v", "w", 4),
])
def test_only_proved_boolean_equivalence_removes_control(tmp_path, setup, left, right, expected):
    code = (
        "def p(x): return x is True\n"
        "def observe(x): return not x\n"
        "def entry(x, y):\n"
        f"    {setup}\n"
        f"    if p(y):\n        a = {left}\n    else:\n        a = {right}\n"
        "    result = p(a)\n    if result:\n        return 1\n    return 0\n")
    source = tmp_path / "probe.py"
    source.write_text(code, encoding="utf-8")
    namespace = {}
    exec(compile(code, str(source), "exec"), namespace)

    class ChangingTruth:
        def __init__(self):
            self.calls = 0

        def __bool__(self):
            self.calls += 1
            return self.calls == 1

    returns = [namespace["entry"](ChangingTruth(), y) for y in (False, True)]
    assert (returns[0] != returns[1]) == bool(expected)
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    line = code.splitlines().index("    if p(y):") + 1
    outer, = [call for call in analysis.find_calls(caller=CALLER) if call.lineno == line]
    assert len(outer.control_flows) == expected


def test_direct_guard_preserves_distinct_equivalent_call_evidence(tmp_path):
    code = ("def p(x): return x is True\ndef entry(x, y):\n"
            "    v = p(x)\n    w = p(x)\n"
            "    if p(y):\n        a = w\n    else:\n        a = v\n"
            "    if a:\n        return 1\n    return 0\n")
    source = tmp_path / "probe.py"
    source.write_text(code, encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    first, second, outer = sorted(analysis.find_calls(caller=CALLER), key=lambda c: c.lineno)
    assert outer.control_flows == []
    for call, selected in ((first, False), (second, True)):
        assert len(call.control_flows) == 2
        for flow in call.control_flows:
            choice, test = flow["path"]
            assert choice["branch"] is selected and choice["call_ids"] == [outer.id]
            assert test["call_ids"] == [call.id] and flow["call_id"] == call.id
