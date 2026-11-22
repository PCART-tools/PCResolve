import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow"
    / "predicate_polarity_cases.json"
)
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CALLER = FunctionRef(module="probe", qualname="entry")


def control_rows(calls):
    rows = set()
    for call in calls:
        for flow in call.control_flows:
            path = tuple((step["test"]["lineno"], bool(step["branch"]))
                         for step in flow["path"])
            rows.add((path, flow["return"]["lineno"]))
    return rows


def expected_rows(entries):
    return {(tuple((int(line), bool(branch)) for line, branch in path), int(ret))
            for path, ret in entries}


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_predicate_polarity_keeps_singleton_truth_and_truthiness_apart(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = analysis.find_calls(caller=CALLER)
    observed = control_rows(calls)
    expected = expected_rows(case["expected"])
    assert observed == expected, "missing=%r extra=%r" % (
        sorted(expected - observed), sorted(observed - expected))
    assert analysis.to_dict().get("boundaries") == []
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_predicate_polarity_representatives_per_call(tmp_path):
    by_label = {case["label"]: case for case in CASES}
    expectations = {
        "not not x; a": {
            "q@4": [("[[5, false]]", 9), ("[[5, true], [6, true]]", 7),
                    ("[[5, true], [6, false]]", 8)],
            "p@6": [("[[5, true], [6, true]]", 7), ("[[5, true], [6, false]]", 8)],
        },
        "x is not True; y is True; not q(a); x": {
            "q@5": [("[[5, false]]", 9), ("[[5, true], [6, true]]", 7)],
            "p@4": [],
        },
    }
    for label, expected_by_call in expectations.items():
        case = by_label[label]
        root = tmp_path / label.replace(" ", "_").replace(";", "_")
        root.mkdir()
        source = root / "probe.py"
        source.write_text(case["source"], encoding="utf-8")
        analysis = FlowAnalyzer(source_files=[source], import_roots=[root]).analyze(
            CALLER, max_depth=2)
        calls = {(call.callee_name, call.lineno): call
                 for call in analysis.find_calls(caller=CALLER)}
        for label_call, expected in expected_by_call.items():
            callee, lineno = label_call.split("@")
            call = calls[(callee, int(lineno))]
            rows = {(tuple((step["test"]["lineno"], bool(step["branch"]))
                           for step in flow["path"]), flow["return"]["lineno"])
                    for flow in call.control_flows}
            assert rows == {
                (tuple((int(line), bool(branch))
                       for line, branch in json.loads(path)), ret)
                for path, ret in expected}
            for flow in call.control_flows:
                assert flow["call_id"] == call.id
        # The two representative APIs and CLIs agree on the full record.
        command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
                   "--import-root", str(root), "--value-flow", "--entry", "probe:entry",
                   "--depth", "2", "--json"]
        assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_predicate_polarity_fixture_shape():
    assert len(CASES) == 80
    assert sum(case["family"] == "identity_chain" for case in CASES) == 64
    assert sum(case["family"] == "truth_conversion" for case in CASES) == 16
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"]
