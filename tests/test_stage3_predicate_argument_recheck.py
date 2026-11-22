import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow"
    / "predicate_argument_recheck.json"
)
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CALLER = FunctionRef(module="probe", qualname="entry")


def path_key(path):
    return tuple((step["test"]["lineno"], bool(step["branch"])) for step in path)


def identity_key(path, calls):
    return tuple((step["test"]["lineno"], bool(step["branch"]),
                  tuple(calls[item].callee_name if item in calls else item
                        for item in step["call_ids"])) for step in path)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_predicate_argument_branch_fact_reaches_argument_source(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = {call.callee_name: call for call in analysis.find_calls(caller=CALLER)}
    by_id = {call.id: call for call in calls.values()}
    for callee in ("p", "q"):
        expected_rows = Counter(
            (tuple((int(line), bool(branch)) for line, branch in path), int(ret))
            for path, ret in case["expected"][callee])
        observed_rows = Counter(
            (path_key(flow["path"]), flow["return"]["lineno"])
            for flow in calls[callee].control_flows)
        assert observed_rows == expected_rows, "%s path rows" % callee
        expected_identity = Counter(
            (tuple((int(line), bool(branch), tuple(names))
                   for line, branch, names in path), int(ret))
            for path, ret in case["expected_identity"][callee])
        observed_identity = Counter(
            (identity_key(flow["path"], by_id), flow["return"]["lineno"])
            for flow in calls[callee].control_flows)
        assert observed_identity == expected_identity, "%s guard identity" % callee
    assert analysis.to_dict().get("boundaries") == []
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_predicate_argument_recheck_fixture_shape():
    assert len(CASES) == 32
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"]
