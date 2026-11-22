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
    / "predicate_chain_cases.json"
)
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CALLER = FunctionRef(module="probe", qualname="entry")


def rows(call):
    return Counter(
        (tuple((step["test"]["lineno"], bool(step["branch"])) for step in flow["path"]),
         flow["return"]["lineno"])
        for flow in call.control_flows)


def expected_rows(entries):
    return Counter(
        (tuple((int(line), bool(branch)) for line, branch in path), int(ret))
        for path, ret in entries)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_predicate_chain_keeps_reachable_returns(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = {(call.callee_name, call.lineno): call
             for call in analysis.find_calls(caller=CALLER)}
    for label, entries in case["expected"].items():
        callee, lineno = label.split("@")
        call = calls.get((callee, int(lineno)))
        assert call is not None, "missing call %s" % label
        observed = rows(call)
        expected = expected_rows(entries)
        assert observed == expected, "%s: missing=%r extra=%r" % (
            label, sorted((expected - observed).items()), sorted((observed - expected).items()))
    assert analysis.to_dict().get("boundaries") == []
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_predicate_chain_fixture_shape():
    assert len(CASES) == 5
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"]
