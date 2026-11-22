import copy
import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from scripts.evaluate_stage3_boolean_paths import INJECTIONS, RUNTIME, replay_case, verify_injection
from scripts.evaluate_stage3_boolean_paths import cases_controls
from scripts.evaluate_stage3_boolean_paths import runtime_paths


COMPOSITION_REPORT = (
    Path(__file__).resolve().parent / "fixtures" / "stage3_value_flow"
    / "boolean_compositions.json"
)
COMPOSITION_CASES = json.loads(COMPOSITION_REPORT.read_text(encoding="utf-8"))


def check_composition_controls(detail, expected, p_id, q_id, code):
    observed = cases_controls(detail)
    assert set(observed) == expected, "control paths"
    assert all(count == 1 for count in observed.values()), "duplicate control path"
    syntax = ast.parse(code)
    guards = {node.lineno: node.test for node in ast.walk(syntax) if isinstance(node, ast.If)}
    returns = {node.lineno: node for node in ast.walk(syntax) if isinstance(node, ast.Return)
               and node.lineno > 3}
    for flow in detail["control_flows"]:
        assert flow["call_id"] == detail["id"], "control call identity"
        assert [guard["call_ids"] for guard in flow["path"]] == [[p_id], [q_id]], (
            "guard call identity")
        own_guard, = [guard for guard in flow["path"] if detail["id"] in guard["call_ids"]]
        assert flow["predicate"] == own_guard["test"] and flow["branch"] == own_guard["branch"], (
            "predicate evidence")
        for evidence, nodes in [(guard["test"], guards) for guard in flow["path"]] + [
                (flow["return"], returns)]:
            node = nodes[evidence["lineno"]]
            assert evidence["file_path"] == detail["caller"]["file_path"], "source file"
            assert all(evidence[field] == getattr(node, field)
                       for field in ("lineno", "col_offset", "end_lineno", "end_col_offset")), (
                "source span")
            assert evidence["source_text"] == ast.get_source_segment(code, node), "source text"


@pytest.mark.parametrize("case", COMPOSITION_CASES)
def test_boolean_compositions_match_runtime_paths(tmp_path, case):
    source = tmp_path / "probe.py"
    source.write_text(case["code"], encoding="utf-8")
    runs = runtime_paths(case["code"], source)
    assert json.loads(json.dumps(runs)) == case["runtime"]
    paths = {(tuple(tuple(guard) for guard in run["guards"]), run["return_line"])
             for run in runs}
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    calls = {call.callee_name: call for call in analysis.find_calls(caller=FunctionRef(
        module="probe", qualname="entry"))}
    for name, call in calls.items():
        detail = analysis.describe_call_flow(call.id)
        expected = paths if name == "p" else {path for path in paths if not path[0][0][1]}
        check_composition_controls(detail, expected, calls["p"].id, calls["q"].id, case["code"])
    q_detail = analysis.describe_call_flow(calls["q"].id)
    incoming_y, = [flow for flow in q_detail["argument_flows"]
                   if flow["kind"] == "parameter" and flow["source"] == "y"]
    assert {condition["branch"] for condition in incoming_y["conditions"]
            if condition["test"]["lineno"] == 4} == {False}
    changed = [flow for flow in q_detail["argument_flows"] if flow is not incoming_y]
    assert changed
    for flow in changed:
        assert {condition["branch"] for condition in flow["conditions"]
                if condition["test"]["lineno"] == 4} == {True}
        assert any("y =" in evidence["source_text"] for evidence in flow["evidence"])
        if flow["kind"] == "literal":
            true_run = next(run for run in runs if run["guards"][0][1])
            assert flow["source"] == repr(true_run["guards"][1][1])
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


@pytest.mark.parametrize("index", [
    4, 6, 12, 14, 20, 22, 28, 30, 36, 38, 44, 46, 52, 54, 60, 62,
])
def test_two_additional_negations_preserve_composition(tmp_path, index):
    case = copy.deepcopy(COMPOSITION_CASES[index])
    case["code"] = case["code"].replace("y = ", "y = not not ", 1)
    test_boolean_compositions_match_runtime_paths(tmp_path, case)


@pytest.mark.parametrize("mutation", [
    "missing", "impossible", "wrong_call", "guard_order", "return_span", "predicate_branch",
    "wrong_file",
])
def test_composition_comparator_detects_mutations(tmp_path, mutation):
    case = COMPOSITION_CASES[0]
    source = tmp_path / "probe.py"
    source.write_text(case["code"], encoding="utf-8")
    entry = FunctionRef(module="probe", qualname="entry")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        entry, max_depth=2)
    p, = analysis.find_calls(callee_name="p")
    q, = analysis.find_calls(callee_name="q")
    detail = analysis.describe_call_flow(p.id)
    runs = runtime_paths(case["code"], source)
    expected = {(tuple(run["guards"]), run["return_line"]) for run in runs}
    check_composition_controls(detail, expected, p.id, q.id, case["code"])
    changed = copy.deepcopy(detail)
    if mutation == "missing":
        changed["control_flows"].pop()
    elif mutation == "impossible":
        extra = copy.deepcopy(changed["control_flows"][0])
        extra["path"][0]["branch"] = True
        extra["path"][1]["branch"] = True
        extra["return"]["lineno"] = 7
        changed["control_flows"].append(extra)
    elif mutation == "wrong_call":
        changed["control_flows"][0]["path"][0]["call_ids"] = [q.id]
    elif mutation == "guard_order":
        changed["control_flows"][0]["path"].reverse()
    elif mutation == "return_span":
        changed["control_flows"][0]["return"]["col_offset"] += 1
    elif mutation == "wrong_file":
        changed["control_flows"][0]["return"]["file_path"] = "other.py"
    else:
        changed["control_flows"][0]["branch"] = not changed["control_flows"][0]["branch"]
    with pytest.raises(AssertionError):
        check_composition_controls(changed, expected, p.id, q.id, case["code"])


@pytest.mark.parametrize("expression", ["False", "not True", "not x"])
def test_equivalent_boolean_overwrites_preserve_return_paths(tmp_path, expression):
    source = tmp_path / "probe.py"
    source.write_text(
        "def p(x): return x is True\n"
        "def q(y): return y is True\n"
        "def entry(x, y):\n"
        "    if p(x):\n"
        f"        y = {expression}\n"
        "    if q(y):\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    p, = analysis.find_calls(callee_name="p")
    q, = analysis.find_calls(callee_name="q")
    p_paths = cases_controls(analysis.describe_call_flow(p.id))
    q_paths = cases_controls(analysis.describe_call_flow(q.id))
    expected_p = {
        (((4, True), (6, False)), 8),
        (((4, False), (6, True)), 7),
        (((4, False), (6, False)), 8),
    }
    expected_q = {
        (((4, False), (6, True)), 7),
        (((4, False), (6, False)), 8),
    }
    assert set(p_paths) == expected_p
    assert set(q_paths) == expected_q
    missing = copy.deepcopy(analysis.describe_call_flow(p.id))
    missing["control_flows"] = [
        flow for flow in missing["control_flows"]
        if not (flow["path"][0]["branch"] and flow["return"]["lineno"] == 8)
    ]
    assert set(cases_controls(missing)) != expected_p
    impossible = copy.deepcopy(analysis.describe_call_flow(q.id))
    extra = copy.deepcopy(impossible["control_flows"][0])
    extra["path"][0]["branch"] = True
    extra["path"][1]["branch"] = True
    extra["return"]["lineno"] = 7
    impossible["control_flows"].append(extra)
    assert set(cases_controls(impossible)) != expected_q
    assert all(count == 1 for count in p_paths.values())
    assert all(count == 1 for count in q_paths.values())
    q_detail = analysis.describe_call_flow(q.id)
    incoming_y, = [flow for flow in q_detail["argument_flows"]
                   if flow["kind"] == "parameter" and flow["source"] == "y"]
    assert any(condition["test"]["lineno"] == 4 and condition["branch"] is False
               for condition in incoming_y["conditions"])
    assert not any(condition["test"]["lineno"] == 4 and condition["branch"] is True
                   for condition in incoming_y["conditions"])
    if expression == "not x":
        incoming_x, = [flow for flow in q_detail["argument_flows"]
                       if flow["kind"] == "parameter" and flow["source"] == "x"]
        assert any(condition["test"]["lineno"] == 4 and condition["branch"] is True
                   for condition in incoming_x["conditions"])
        assert any(evidence["lineno"] == 5 for evidence in incoming_x["evidence"])
    command = [sys.executable, "-m", "pcresolve", "--source-file", str(source),
               "--import-root", str(tmp_path), "--value-flow", "--entry", "probe:entry",
               "--depth", "2", "--json"]
    assert json.loads(subprocess.check_output(command, encoding="utf-8")) == analysis.to_dict()


def test_negated_parameter_does_not_assume_unknown_objects_are_boolean(tmp_path):
    code = ("def p(x): return x is not False\n"
            "def q(y): return y is True\n"
            "def entry(x, y):\n"
            "    if p(x):\n"
            "        y = not x\n"
            "    if q(y):\n"
            "        return 1\n"
            "    return 0\n")
    source = tmp_path / "probe.py"
    source.write_text(code, encoding="utf-8")
    namespace = {}
    exec(code, namespace)
    assert namespace["entry"](None, False) == 1
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    q, = analysis.find_calls(callee_name="q")
    paths = cases_controls(analysis.describe_call_flow(q.id))
    assert (((4, True), (6, True)), 7) in paths


@pytest.mark.parametrize("case", RUNTIME)
def test_stage3_boolean_paths(case):
    replay_case(case)


@pytest.mark.parametrize("name", INJECTIONS)
def test_stage3_detects_boolean_path_regressions(name):
    case, _ = INJECTIONS[name]
    assert verify_injection(name, *replay_case(case))["detected"]


@pytest.mark.parametrize(("setup", "arguments"), [
    ("if flag: y = 0", (True, True)),
    ("y = not y", (True, False)),
    ("y = flag", (True, False)),
])
def test_changed_input_can_reverse_a_later_predicate(tmp_path, setup, arguments):
    code = (
        "def p(y): return y is True\n"
        "def q(y): return y is True\n"
        "def entry(y, flag):\n"
        "    if p(y):\n"
        f"        {setup}\n"
        "        if not q(y):\n"
        "            return 2\n"
        "    return 0\n"
    )
    source = tmp_path / "probe.py"
    source.write_text(code, encoding="utf-8")
    namespace = {}
    exec(code, namespace)
    assert namespace["entry"](*arguments) == 2
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    p, = analysis.find_calls(callee_name="p")
    assert any(flow["return"]["lineno"] == 7 for flow in p.control_flows)


@pytest.mark.parametrize(("first", "second", "expected"), [
    ("y is True", "False is not y", False),
    ("y is not True", "False is y", True),  # None satisfies neither identity test.
    ("False is y", "y is not True", False),
])
def test_singleton_tests_keep_python_identity_semantics(tmp_path, first, second, expected):
    code = (f"def p(y): return {first}\n"
            f"def q(y): return {second}\n"
            "def entry(y):\n"
            "    a = p(y)\n"
            "    alias = y\n"
            "    if a:\n"
            "        if not q(alias):\n"
            "            return 2\n"
            "    return 0\n")
    source = tmp_path / "probe.py"
    source.write_text(code, encoding="utf-8")
    namespace = {}
    exec(code, namespace)
    assert any(namespace["entry"](value) == 2 for value in (True, False, None)) == expected
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    call, = analysis.find_calls(callee_name="p")
    assert any(flow["return"]["lineno"] == 8 for flow in call.control_flows) == expected


def test_untracked_boolean_operand_does_not_hide_reachable_return(tmp_path):
    source = tmp_path / "probe.py"
    source.write_text(
        "def p(x): return x is True\n"
        "def entry(x):\n"
        "    a = p(x)\n"
        "    if a:\n"
        "        b = a and []\n"
        "        if not b:\n"
        "            return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    call, = analysis.find_calls(callee_name="p")
    assert any(flow["return"]["lineno"] == 7 for flow in call.control_flows)


@pytest.mark.parametrize("expression", ["b == False", "b or False", "(b,)[0]"])
def test_other_operations_do_not_reuse_negation_as_their_own_result(tmp_path, expression):
    source = tmp_path / "probe.py"
    code = ("def p(x): return x is True\n"
            "def entry(x):\n"
            "    b = not p(x)\n"
            f"    c = {expression}\n"
            "    if c:\n"
            "        return 1\n"
            "    return 0\n")
    source.write_text(code, encoding="utf-8")
    namespace = {}
    exec(code, namespace)
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    call, = analysis.find_calls(callee_name="p")
    # The analyzer may conservatively keep extra paths, but it must keep each
    # reachable return for the corresponding predicate result.
    paths = {(flow["branch"], flow["return"]["lineno"]) for flow in call.control_flows}
    for x in (False, True):
        returned = namespace["entry"](x)
        assert (bool(returned), 6 if returned else 7) in paths


def test_repeated_truth_testing_can_call_user_code(tmp_path):
    source = tmp_path / "probe.py"
    source.write_text(
        "def p(x): return x\n"
        "def entry(x):\n"
        "    a = p(x)\n"
        "    if a:\n"
        "        if not a:\n"
        "            return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )

    class ChangesTruth:
        results = iter((True, False))

        def __bool__(self):
            return next(self.results)

    namespace = {}
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    assert namespace["entry"](ChangesTruth()) == 1
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    call, = analysis.find_calls(callee_name="p")
    assert any(flow["return"]["lineno"] == 6 for flow in call.control_flows)


@pytest.mark.parametrize(("signature", "argument"), [("*y", "False"), ("**y", "item=False")])
def test_variadic_value_is_not_identical_to_one_of_its_arguments(tmp_path, signature, argument):
    source = tmp_path / "probe.py"
    source.write_text(
        f"def q({signature}): return y is False\n"
        "def reached(): return 0\n"
        "def entry():\n"
        f"    if q({argument}):\n"
        "        return 1\n"
        "    return reached()\n",
        encoding="utf-8",
    )
    analysis = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(
        FunctionRef(module="probe", qualname="entry"), max_depth=2)
    reached, = analysis.find_calls(callee_name="reached")
    assert reached.analysis_status == "analyzed"
