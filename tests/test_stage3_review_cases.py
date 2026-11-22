import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow" / "review_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
CALLER = FunctionRef(module="probe", qualname="entry")


def normalized_controls(call):
    rows = []
    for flow in call.control_flows:
        path = tuple((step["test"]["lineno"], bool(step["branch"])) for step in flow["path"])
        rows.append((path, flow["return"]["lineno"]))
    return Counter(rows)


def expected_controls(case, callee):
    return Counter((tuple((int(line), bool(branch)) for line, branch in path), int(ret))
                   for path, ret in case["expected"][callee])


def observed_identity(call, by_id):
    rows = []
    for flow in call.control_flows:
        path = []
        for step in flow["path"]:
            test = step["test"]
            path.append((Path(test["file_path"]).name, test["lineno"],
                         test["col_offset"], test["end_lineno"], test["end_col_offset"],
                         bool(step["branch"]),
                         tuple(by_id[item].callee_name if item in by_id else item
                               for item in step["call_ids"])))
        returned = flow["return"]
        rows.append((tuple(path), (Path(returned["file_path"]).name,
                                   returned["lineno"], returned["col_offset"],
                                   returned["end_lineno"], returned["end_col_offset"])))
    return Counter(rows)


def expected_identity(case, callee):
    rows = []
    for path, ret in case["expected_identity"][callee]:
        rows.append((
            tuple((name, int(line), int(col), int(end_line), int(end_col),
                   bool(branch), tuple(names))
                  for name, line, col, end_line, end_col, branch, names in path),
            (ret[0], int(ret[1]), int(ret[2]), int(ret[3]), int(ret[4])),
        ))
    return Counter(rows)


def assert_identity(observed, expected, label):
    assert observed == expected, "%s guard identity: missing=%r extra=%r" % (
        label, sorted((expected - observed).items()), sorted((observed - expected).items()))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_stage3_review_case_controls(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        CALLER, max_depth=2)
    calls = {call.callee_name: call for call in analysis.find_calls(caller=CALLER)}
    by_id = {call.id: call for call in calls.values()}
    for callee in case["calls"]:
        assert callee in calls, "missing call %s" % callee
        observed = normalized_controls(calls[callee])
        expected = expected_controls(case, callee)
        assert observed == expected, "%s control rows: missing=%r extra=%r" % (
            callee, sorted((expected - observed).items()), sorted((observed - expected).items()))
        assert_identity(observed_identity(calls[callee], by_id),
                        expected_identity(case, callee), callee)
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def _identity_rows(calls, callee):
    by_id = {call.id: call for call in calls.values()}
    rows = []
    for flow in calls[callee].control_flows:
        path = []
        for step in flow["path"]:
            test = step["test"]
            path.append((Path(test["file_path"]).name, test["lineno"],
                         test["col_offset"], test["end_lineno"], test["end_col_offset"],
                         bool(step["branch"]),
                         tuple(by_id[item].callee_name if item in by_id else item
                               for item in step["call_ids"])))
        returned = flow["return"]
        rows.append((tuple(path), (Path(returned["file_path"]).name,
                                   returned["lineno"], returned["col_offset"],
                                   returned["end_lineno"], returned["end_col_offset"])))
    return rows


def test_stage3_review_comparator_rejects_guard_identity_swap(tmp_path):
    by_id = {case["id"]: case for case in CASES}
    case = by_id["guard-15"]
    _, _, calls = _analyze_case(tmp_path, case)
    expected = expected_identity(case, "p")
    p_name = "p"
    rows = _identity_rows(calls, "p")
    true_row = next(index for index, (path, ret) in enumerate(rows)
                    if path[0][1] == 5 and path[0][5] is True and path[0][6] == (p_name,)
                    and path[1][1] == 7 and path[1][5] is False and path[1][6] == (p_name,))
    false_row = next(index for index, (path, ret) in enumerate(rows)
                     if path[0][1] == 5 and path[0][5] is False and path[0][6] == (p_name,)
                     and path[1][1] == 7 and path[1][5] is True and path[1][6] == ())

    removed = list(rows)
    path, ret = removed[true_row]
    removed[true_row] = (path[:1] + (path[1][:6] + ((),),), ret)
    with pytest.raises(AssertionError):
        assert_identity(Counter(removed), expected, "guard-15")

    added = list(rows)
    path, ret = added[false_row]
    added[false_row] = (path[:1] + (path[1][:6] + ((p_name,),),), ret)
    with pytest.raises(AssertionError):
        assert_identity(Counter(added), expected, "guard-15")


def test_stage3_review_fixture_shape():
    assert len(CASES) == 73
    assert len({case["id"] for case in CASES}) == 73
    for case in CASES:
        digest = hashlib.sha256(case["source"].encode("utf-8")).hexdigest()
        assert digest == case["source_sha256"], "fixture source hash"
    counts = Counter(case["class"] for case in CASES)
    assert counts == Counter({"pass": 46, "A": 10, "B": 8, "D": 4, "C": 4, "E": 1})


def _analyze_case(tmp_path, case):
    root = tmp_path / case["id"]
    root.mkdir()
    source = root / "probe.py"
    source.write_text(case["source"], encoding="utf-8")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[root]).analyze(
        CALLER, max_depth=2)
    calls = {call.callee_name: call for call in analysis.find_calls(caller=CALLER)}
    return source, analysis, calls


def _guard_ids(flow):
    return [(step["test"]["lineno"], tuple(step["call_ids"])) for step in flow["path"]]


def test_stage3_review_control_call_identity(tmp_path):
    by_id = {case["id"]: case for case in CASES}
    _, _, calls = _analyze_case(tmp_path, by_id["guard-13"])
    p_id, q_id = calls["p"].id, calls["q"].id
    expected = [(5, (p_id,)), (7, (q_id,))]
    for name in ("p", "q"):
        for flow in calls[name].control_flows:
            assert flow["call_id"] == calls[name].id
            assert _guard_ids(flow) == expected

    _, _, calls = _analyze_case(tmp_path, by_id["guard-15"])
    p_id = calls["p"].id
    expected_ids = {
        ((5, False), (7, True)): ((5, (p_id,)), (7, ())),
        ((5, True), (7, False)): ((5, (p_id,)), (7, (p_id,))),
        ((5, False), (7, False)): ((5, (p_id,)), (7, ())),
    }
    for flow in calls["p"].control_flows:
        path = tuple((step["test"]["lineno"], bool(step["branch"]))
                     for step in flow["path"])
        assert tuple(_guard_ids(flow)) == expected_ids[path]

    _, _, calls = _analyze_case(tmp_path, by_id["guard-06"])
    p_id = calls["p"].id
    for flow in calls["p"].control_flows:
        assert _guard_ids(flow) == [(5, (p_id,)), (7, ())]

    _, _, calls = _analyze_case(tmp_path, by_id["guard-40"])
    p_id = calls["p"].id
    patterns = {tuple(_guard_ids(flow)) for flow in calls["p"].control_flows}
    assert patterns == {
        ((4, (p_id,)), (5, ())),
        ((4, (p_id,)),),
    }

    _, _, calls = _analyze_case(tmp_path, by_id["two-10"])
    p_id, q_id = calls["p"].id, calls["q"].id
    assert calls["p"].control_flows == []
    for flow in calls["q"].control_flows:
        assert _guard_ids(flow) == [(5, (p_id,)), (9, (q_id,))]
