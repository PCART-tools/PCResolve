import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow"
    / "saved_value_identity_cases.json"
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
def test_saved_value_identity_contradictions_are_pruned(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = {(call.callee_name, call.lineno): call
             for call in analysis.find_calls(caller=CALLER)}
    union = set().union(*(observed(call) for call in calls.values()))
    assert union == rows(case["expected_union"])
    assert not (union & rows(case["forbidden"])), "contradictory path retained"
    for label, entries in case["expected_calls"].items():
        callee, lineno = label.split("@")
        call = calls.get((callee, int(lineno)))
        assert call is not None, "missing call %s" % label
        assert observed(call) == rows(entries), "%s per-call rows" % label
    assert analysis.to_dict().get("boundaries") == []
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_saved_value_identity_fixture_shape():
    assert len(CASES) == 8
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"]
