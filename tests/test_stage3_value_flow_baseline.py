import ast
import copy
import json

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from scripts.evaluate_stage3_value_flow import MANIFEST, SPAN, compare_call, replay


@pytest.fixture(scope="module")
def observations():
    return replay(MANIFEST, "fixture")


def test_quick_stage3_cases(observations):
    assert len(observations) == 7
    assert not [check for case in observations for call in case["calls"]
                for check in call["checks"] if check["status"] == "regression"]
    frame = next(case for case in observations if case["id"] == "frame")
    checks = [check for call in frame["calls"] for check in call["checks"]]
    assert sum(c["reason"] == "target" and c["status"] == "pass" for c in checks) == 5
    assert sum(c["reason"] == "required_source_found" and c["status"] == "pass"
               for c in checks) == 10


def test_direct_predicate_control_flow_names_both_returns(tmp_path):
    source = tmp_path / "control.py"
    source.write_text(
        "def predicate(value):\n"
        "    return bool(value)\n"
        "def entry(value):\n"
        "    if predicate(value):\n"
        "        return [value]\n"
        "    else:\n"
        "        return [0]\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert {(flow["branch"], flow["return"]["lineno"])
            for flow in predicate.control_flows} == {(True, 5), (False, 7)}
    assert all(flow["predicate"]["lineno"] == 4 for flow in predicate.control_flows)


def test_control_paths_survive_join_and_nested_guards(tmp_path):
    source = tmp_path / "control.py"
    source.write_text(
        "def predicate(value):\n"
        "    return bool(value)\n"
        "def entry(values, numeric):\n"
        "    selected = any(predicate(value) for value in values)\n"
        "    if selected:\n"
        "        if numeric:\n"
        "            return object\n"
        "    return float\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    aggregate, = result.find_calls(caller=entry, callee_name="any")
    paths = {(flow["return"]["lineno"], tuple(
        (condition["test"]["lineno"], condition["branch"])
        for condition in flow["path"])) for flow in aggregate.control_flows}
    assert paths == {(7, ((5, True), (6, True))),
                     (8, ((5, False),)), (8, ((5, True), (6, False)))}


def test_reassigned_condition_does_not_retain_old_call_control(tmp_path):
    source = tmp_path / "control.py"
    source.write_text(
        "def predicate(value):\n"
        "    return bool(value)\n"
        "def entry(value):\n"
        "    selected = predicate(value)\n"
        "    selected = False\n"
        "    if selected:\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.control_flows == []


@pytest.mark.parametrize(("override", "decision"), [
    ("replace_it", "selected"),
    ("switch(replace_it)", "selected"),
    ("replace_it", "not selected"),
    ("switch(replace_it)", "not selected"),
])
def test_conditional_rebinding_keeps_the_binding_guard(tmp_path, override, decision):
    source = tmp_path / "control.py"
    program = (
        "def old(value): return value > 0\n"
        "def new(value): return value < 0\n"
        "def switch(flag): return flag\n"
        "def entry(value, replace_it):\n"
        "    selected = old(value)\n"
        f"    if {override}:\n        selected = new(value)\n"
        f"    if {decision}:\n        return 1\n"
        "    return 0\n"
    )
    source.write_text(program, encoding="utf-8")
    assignment, replace, select, fallback = ast.parse(program).body[-1].body

    def evidence(node):
        return dict({key: getattr(node, key) for key in SPAN}, file_path=str(source),
                    source_text=ast.get_source_segment(program, node))

    def identity(node):
        return ":".join([str(source)] + [str(getattr(node, key)) for key in SPAN])

    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    snapshot = json.loads(json.dumps(result.to_dict()))
    assert snapshot["schema_version"] == "flow-0.2"
    calls = {record["id"]: record for record in snapshot["calls"]}
    overwrite_calls = [identity(replace.test)] if isinstance(replace.test, ast.Call) else []
    for binding, overwrite_branch in ((assignment, False), (replace.body[0], True)):
        call_id = identity(binding.value)
        expected = []
        for branch, returned in ((True, select.body[0]), (False, fallback)):
            expected.append({
                "call_id": call_id, "predicate": evidence(select.test), "branch": branch,
                "path": [
                    {"test": evidence(replace.test), "branch": overwrite_branch,
                     "call_ids": overwrite_calls},
                    {"test": evidence(select.test), "branch": branch, "call_ids": [call_id]},
                ],
                "return": evidence(returned),
            })
        for actual in (result.describe_call_flow(call_id)["control_flows"],
                       calls[call_id]["control_flows"]):
            assert sorted(actual, key=lambda flow: flow["return"]["lineno"]) == expected


@pytest.mark.parametrize("nested", [False, True])
def test_rebinding_guards_keep_source_order_across_joins(tmp_path, nested):
    source = tmp_path / "control.py"
    program = (
        "def old(x): return x > 0\n"
        "def new(x): return x < 0\n"
        "def switch(x): return x\n"
        "def entry(x, replace_it):\n"
        "    selected = old(x)\n"
        "    if replace_it:\n"
    )
    if nested:
        program += ("        if switch(x):\n"
                    "            selected = new(x)\n"
                    "    if selected:\n"
                    "        return 1\n")
    else:
        program += ("        selected = new(x)\n"
                    "    if switch(x):\n"
                    "        if selected:\n"
                    "            return 1\n")
    source.write_text(program + "    return 0\n", encoding="utf-8")
    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)

    switch_true = ("switch(x)", True)
    for name, override in (("old", False), ("new", True)):
        call, = result.find_calls(caller=entry, callee_name=name)
        if nested and name == "old":
            prefixes = [(("replace_it", False),), (("replace_it", True), ("switch(x)", False))]
        else:
            prefixes = [(("replace_it", override), switch_true)]
        expected = sorted(prefix + (("selected", branch),)
                          for prefix in prefixes for branch in (True, False))
        actual = sorted(tuple((guard["test"]["source_text"], guard["branch"])
                              for guard in flow["path"]) for flow in call.control_flows)
        assert actual == expected


@pytest.fixture
def pandas_control_record():
    case = next(case for case in MANIFEST["pandas"]["cases"] if case["id"] == "common-type")
    expected = next(call for call in case["calls"] if call["span"][0] == 1088
                    and call["callee"] == "any")
    file = "pandas/core/dtypes/cast.py"

    def evidence(span):
        return dict(zip(SPAN, span), file_path=file)

    def call_id(span):
        return ":".join((file, *(str(coordinate) for coordinate in span)))

    prefix = [
        {"test": evidence(span), "branch": False, "call_ids": [call_id(span)]}
        for span in [(1074, 7, 1074, 55), (1077, 7, 1077, 56),
                     (1081, 7, 1081, 49), (1083, 7, 1083, 50)]
    ]
    observed = {"id": file + ":1088:16:1088:52", "caller": {"file_path": file}, "target": None,
                "return_flows": [], "control_flows": []}
    for path in expected["gaps"][0]["control_paths"]:
        guards = [{"test": evidence(span), "branch": condition[1],
                   "call_ids": [observed["id"]] if span[0] == 1089 else []}
                  for span, condition in zip(path["condition_spans"], path["conditions"])]
        observed["control_flows"].append({
            "call_id": observed["id"], "predicate": guards[0]["test"],
            "branch": guards[0]["branch"], "path": copy.deepcopy(prefix) + guards,
            "return": dict(evidence(path["return_span"]), source_text=path["return_text"]),
        })
    return expected, observed


@pytest.mark.parametrize("extra_line", [1077, 1088])
def test_pandas_comparator_rejects_early_source_location_appended_to_path(
        pandas_control_record, extra_line):
    expected, observed = pandas_control_record
    assert compare_call(expected, observed)[-1]["status"] == "pass"
    rejected = next(flow for flow in observed["control_flows"] if flow["return"]["lineno"] == 1094)
    span = (1077, 7, 1077, 56) if extra_line == 1077 else expected["span"]
    injected = dict(zip(SPAN, span), file_path=observed["caller"]["file_path"])
    rejected["path"].append({"test": injected, "branch": True})
    check = compare_call(expected, observed)[-1]
    assert check["status"] == "regression"
    assert check["extra"][0][-1][-1] == (tuple(injected[key] for key in SPAN), True)


@pytest.mark.parametrize("corruption", ["wrong_call", "empty", "duplicate", "unexpected"])
def test_pandas_comparator_checks_guard_call_sources(pandas_control_record, corruption):
    expected, observed = pandas_control_record
    assert compare_call(expected, observed)[-1]["status"] == "pass"
    path = next(flow["path"] for flow in observed["control_flows"]
                if flow["return"]["lineno"] == 1094)
    guard_line = 1093 if corruption == "unexpected" else 1089
    guard = next(guard for guard in path if guard["test"]["lineno"] == guard_line)
    other_guard = next(guard for guard in path if guard["test"]["lineno"] == 1077)
    original = guard["call_ids"]
    guard["call_ids"] = {
        "wrong_call": other_guard["call_ids"], "empty": [],
        "duplicate": original * 2, "unexpected": [observed["id"]],
    }[corruption]
    check = compare_call(expected, observed)[-1]
    assert check["status"] == "regression"
    assert {"field": "path.call_ids", "guard": guard["test"],
            "expected": original, "actual": guard["call_ids"]} in check["contradictions"]


@pytest.mark.parametrize("corruption", ["return_file", "extra_call", "extra_guard"])
def test_control_comparator_rejects_extra_or_misplaced_evidence(observations, corruption):
    case = next(item for item in observations if item["id"] == "common-type")
    call = next(item for item in case["calls"] if item["expected"]["callee"] == "any")
    candidate = copy.deepcopy(call["observed"])
    flow = candidate["control_flows"][0]
    if corruption == "return_file":
        flow["return"]["file_path"] = "wrong.py"
    elif corruption == "extra_call":
        extra = copy.deepcopy(flow)
        extra["call_id"] = "another-call"
        candidate["control_flows"].append(extra)
    else:
        guard = copy.deepcopy(flow["path"][-1])
        guard["test"].update(lineno=40, end_lineno=40, col_offset=0, end_col_offset=1)
        flow["path"].append(guard)
    assert any(check["status"] == "regression"
               for check in compare_call(call["expected"], candidate))


@pytest.mark.parametrize("separate_returns", [False, True])
def test_predicate_controls_only_distinct_return_positions(tmp_path, separate_returns):
    source = tmp_path / "control.py"
    branch_body = ("        return 0\n    return 0\n" if separate_returns else
                   "        value = 1\n    else:\n        value = 2\n    return 0\n")
    source.write_text("def predicate(value):\n    return bool(value)\n"
                      "def entry(value):\n    if predicate(value):\n" + branch_body,
                      encoding="utf-8")
    entry = FunctionRef(module="control", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    if separate_returns:
        assert {(item["branch"], item["return"]["lineno"])
                for item in predicate.control_flows} == {(True, 5), (False, 6)}
    else:
        assert predicate.control_flows == []


@pytest.mark.parametrize(("inner", "expected_paths"), [
    ("assigned = 1", ()),
    ("return 1", ((5, (True, True)), (6, (True, False)), (6, (False,)))),
    ("raise ValueError", ((6, (True, False)), (6, (False,)))),
    ("return 0", ((5, (True, True)), (6, (True, False)), (6, (False,)))),
])
def test_nested_predicate_controls_return_only_if_outcomes_differ(tmp_path, inner, expected_paths):
    source = tmp_path / "probe.py"
    program = ("def p(x): return x\n"
               "def entry(x, flag):\n"
               "    if p(x):\n"
               "        if flag:\n"
               f"            {inner}\n"
               "    return 0\n")
    source.write_text(program, encoding="utf-8")
    outer, fallback = ast.parse(program).body[-1].body
    nested = outer.body[0]
    returns = {5: nested.body[0], 6: fallback}
    entry = FunctionRef(module="probe", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="p")

    def evidence(node):
        return dict({key: getattr(node, key) for key in SPAN}, file_path=str(source),
                    source_text=ast.get_source_segment(program, node))

    expected = [{
        "call_id": predicate.id, "predicate": evidence(outer.test), "branch": branches[0],
        "path": [
            {"test": evidence(test), "branch": branch, "call_ids": ids}
            for test, branch, ids in zip((outer.test, nested.test), branches, ([predicate.id], []))
        ],
        "return": evidence(returns[line]),
    } for line, branches in expected_paths]
    serialized = json.loads(json.dumps(result.to_dict()))
    call = next(call for call in serialized["calls"] if call["id"] == predicate.id)
    for flows in (result.describe_call_flow(predicate.id)["control_flows"], call["control_flows"]):
        assert sorted(flows, key=lambda flow: (
            flow["return"]["lineno"], not flow["branch"])) == expected


@pytest.mark.parametrize(("nested", "implicit", "early"), [
    (False, False, False),
    (True, False, False),
    (False, True, False),
    (True, True, False),
    (True, False, True),
])
def test_predicate_does_not_control_returns_selected_after_its_join(tmp_path, nested, implicit, early):
    source = tmp_path / "probe.py"
    program = ("def p(x): return x\n"
               "def q(y): return y\n"
               "def entry(x, flag, y):\n"
               "    if p(x):\n")
    if nested:
        program += "        if flag:\n"
    program += ("            " if nested else "        ") + (
        "return 2\n" if early else "assigned = 1\n")
    program += "    if q(y):\n        return 1\n"
    if not implicit:
        program += "    return 0\n"
    source.write_text(program, encoding="utf-8")
    outer, later, *fallback = ast.parse(program).body[-1].body
    entry = FunctionRef(module="probe", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    first, second = result.find_calls(caller=entry)
    assert (first.callee_name, second.callee_name) == ("p", "q")

    def evidence(node):
        return dict({key: getattr(node, key) for key in SPAN}, file_path=str(source),
                    source_text=ast.get_source_segment(program, node))

    def guard(node, branch, *call_ids):
        return {"test": evidence(node), "branch": branch, "call_ids": list(call_ids)}

    def control(call, test, branch, path, returned):
        return {"call_id": call.id, "predicate": evidence(test), "branch": branch,
                "path": path, "return": evidence(returned)}

    prefixes = [[guard(outer.test, False, first.id)]]
    if nested:
        inner = outer.body[0]
        prefixes.extend([guard(outer.test, True, first.id), guard(inner.test, branch)]
                        for branch in ([False] if early else [True, False]))
    else:
        prefixes.append([guard(outer.test, True, first.id)])

    returns = [(True, later.body[0])] + [(False, statement) for statement in fallback]
    paths = [(prefix + [guard(later.test, branch, second.id)], branch, returned)
             for prefix in prefixes for branch, returned in returns]
    later_controls = [control(second, later.test, branch, path, returned)
                      for path, branch, returned in paths]
    outer_controls = []
    if early:
        path = [guard(outer.test, True, first.id), guard(inner.test, True)]
        outer_controls = [control(first, outer.test, True, path, inner.body[0])]
        outer_controls.extend(control(first, outer.test, path[0]["branch"], path, returned)
                              for path, _, returned in paths)

    snapshot = json.loads(json.dumps(result.to_dict()))
    assert snapshot["schema_version"] == "flow-0.2"
    serialized = {call["id"]: call["control_flows"] for call in snapshot["calls"]}
    for call, expected in ((first, outer_controls), (second, later_controls)):
        for actual in (result.describe_call_flow(call.id)["control_flows"], serialized[call.id]):
            assert sorted(actual, key=str) == sorted(expected, key=str)


def test_wrong_branch_source_and_missing_positive(observations):
    frame = observations[0]["calls"][0]
    corrupted = copy.deepcopy(frame["observed"])
    next(f for f in corrupted["argument_flows"]
         if f["target_parameter"] == "columns")["evidence"].append(
             {"lineno": 12, "file_path": "probe.py"})
    assert {(c["slot"], c["reason"]) for c in compare_call(frame["expected"], corrupted)
            if c["status"] == "regression"} == {("columns", "forbidden_source")}

    tolist = next(case for case in observations if case["id"] == "tolist")["calls"][0]
    corrupted = {**tolist["observed"], "argument_flows": []}
    assert {(c["slot"], c["reason"]) for c in compare_call(tolist["expected"], corrupted)
            if c["status"] == "regression"} == {("arr", "required_source_missing")}


@pytest.mark.parametrize("target", [
    {"module": "probe", "qualname": "OtherClass.unrelated"},
    {"module": "other", "qualname": "sink"},
    None,
])
def test_frame_rejects_wrong_or_missing_target(observations, target):
    frame = next(case for case in observations if case["id"] == "frame")["calls"][0]
    corrupted = {**frame["observed"], "target": target}
    check, = compare_call(frame["expected"], corrupted)
    assert check == {"status": "regression", "reason": "target",
                     "expected_target": {"module": "probe", "qualname": "sink"},
                     "actual": target}


@pytest.fixture
def generator_example():
    case = next(case for case in MANIFEST["fixture"]["cases"] if case["id"] == "common-type")
    return case["calls"][0], {
        "caller": {"file_path": "probe.py"},
        "analysis_status": "analyzed",
        "target": {"module": "probe", "qualname": "predicate"},
        "boundaries": [],
        "argument_flows": [{"argument": {"position": 0}, "target_parameter": "arr",
                            "kind": "parameter", "source": "types",
                            "relation": "derived", "projection": ["*"],
                            "evidence": [
                                {"lineno": 39, "col_offset": column,
                                 "end_lineno": 39, "end_col_offset": column + 1,
                                 "file_path": "probe.py", "source_text": "t"}
                                for column in (37, 30)
                            ],
                            "conditions": [{"consumer_kind": "any",
                                            "execution": "may_execute",
                                            "later_iterations_may_be_skipped": True,
                                            "consumer": {"file_path": "probe.py", "lineno": 39,
                                                         "col_offset": 16, "end_lineno": 39,
                                                         "end_col_offset": 48},
                                            "generator_iteration": {
                                                "file_path": "probe.py", "lineno": 39,
                                                "col_offset": 19, "end_lineno": 39,
                                                "end_col_offset": 48}}]}],
    }


def test_generator_boundary_is_unknown(generator_example):
    expected, candidate = generator_example
    candidate.update(analysis_status="not_analyzed", target=None, argument_flows=[],
                     boundaries=[{"reason": "flow_not_analyzed"}])
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == ("unknown", "flow_not_analyzed")


def test_generator_predicate_uses_the_projected_element_binding(observations):
    case = next(case for case in observations if case["id"] == "common-type")
    predicate = case["calls"][0]["observed"]
    assert predicate["analysis_status"] == "analyzed"
    assert (predicate["target"]["module"], predicate["target"]["qualname"]) == (
        "probe", "predicate")
    flow, = predicate["argument_flows"]
    assert flow["source"] == "types"
    assert flow["projection"] == ["*"]
    assert flow["target_parameter"] == "arr"
    assert flow["argument"] == {"position": 0}
    assert {item["col_offset"] for item in flow["evidence"]
            if item["source_text"] == "t"} == {30, 37}
    condition, = [item for item in flow["conditions"]
                  if item.get("consumer_kind") == "any"]
    assert condition["consumer_kind"] == "any"
    assert condition["execution"] == "may_execute"
    assert condition["later_iterations_may_be_skipped"] is True
    assert condition["generator_iteration"]["lineno"] == 39


def test_generator_is_not_eagerly_analyzed_without_a_confirmed_consumer(tmp_path):
    source = tmp_path / "deferred.py"
    source.write_text(
        "def predicate(item):\n"
        "    return bool(item)\n"
        "def entry(items):\n"
        "    generated = (predicate(item) for item in items)\n"
        "    return generated\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="deferred", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.analysis_status == "not_analyzed"
    assert any(boundary["reason"] == "unsupported_expression"
               and boundary.get("evidence", {}).get("lineno") == 4
               for boundary in result.boundaries)


def test_rebound_any_does_not_trigger_builtin_generator_consumption(tmp_path):
    source = tmp_path / "rebound.py"
    source.write_text(
        "def predicate(item):\n"
        "    return bool(item)\n"
        "def entry(items, any):\n"
        "    return any(predicate(item) for item in items)\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="rebound", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.analysis_status == "not_analyzed"
    assert any(boundary["reason"] == "unsupported_expression"
               for boundary in result.boundaries)


def test_locally_rebound_any_does_not_trigger_builtin_generator_consumption(tmp_path):
    source = tmp_path / "local_rebound.py"
    source.write_text(
        "def predicate(item):\n"
        "    return bool(item)\n"
        "def consume(iterable):\n"
        "    return False\n"
        "def entry(items):\n"
        "    any = consume\n"
        "    return any(predicate(item) for item in items)\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="local_rebound", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.analysis_status == "not_analyzed"
    assert any(boundary["reason"] == "unsupported_expression"
               for boundary in result.boundaries)


def test_all_generator_predicate_is_marked_as_may_execute(tmp_path):
    source = tmp_path / "all_case.py"
    source.write_text(
        "def predicate(item):\n"
        "    return bool(item)\n"
        "def entry(items):\n"
        "    return all(predicate(item) for item in items)\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="all_case", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    flow, = predicate.argument_flows
    condition = next(item for item in flow["conditions"]
                     if item.get("consumer_kind") == "all")
    assert condition["consumer_kind"] == "all"
    assert condition["execution"] == "may_execute"
    assert condition["later_iterations_may_be_skipped"] is True


@pytest.mark.parametrize(("consumer", "predicate_result", "expected_sources"), [
    ("any", True, {"first"}),
    ("all", False, {"first"}),
    ("any", False, {"first", "later"}),
    ("all", True, {"first", "later"}),
])
def test_generator_short_circuit_keeps_only_reachable_predicate_arguments(
        tmp_path, consumer, predicate_result, expected_sources):
    source = tmp_path / "short_circuit.py"
    source.write_text(
        "def predicate(item):\n"
        "    return " + repr(predicate_result) + "\n"
        "def entry(first, later):\n"
        "    return " + consumer + "(predicate(item) for item in (first, later))\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="short_circuit", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    sources = {flow["source"] for flow in predicate.argument_flows
               if flow.get("kind") == "parameter"}
    assert sources == expected_sources


@pytest.mark.parametrize(("definitions", "parameters", "setup", "expression", "sources"), [
    ("def predicate(x):\n    return True\ndef keep_going(x):\n    return False\n",
     "first, later", "    predicate = keep_going\n",
     "any(predicate(t) for t in (first, later))", {"first", "later"}),
    ("def predicate(x):\n    return True\n", "first, choice, flag, later", "",
     "any(predicate(t) for t in (first if flag else choice, later))", {"first", "choice"}),
    ("async def predicate(x):\n    return False\n", "first, later", "",
     "all(predicate(t) for t in (first, later))", {"first", "later"}),
    ("def predicate(x):\n    return bool(x)\n", "first, later", "",
     "any(predicate(t) for t in (first, later))", {"first", "later"}),
    ("def predicate(x):\n    return False\ndef stop(x):\n    return True\n",
     "first, later", "    predicate = stop\n",
     "any(predicate(t) for t in (first, later))", {"first"}),
])
def test_generator_actual_target_and_element_alternatives(
        tmp_path, definitions, parameters, setup, expression, sources):
    source = tmp_path / "probe.py"
    source.write_text(definitions + "def entry(" + parameters + "):\n" + setup
                      + "    return " + expression + "\n", encoding="utf-8")
    entry = FunctionRef(module="probe", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert {flow["source"] for flow in predicate.argument_flows
            if flow.get("kind") == "parameter"} == sources


def test_generator_evaluates_later_tuple_expression_before_short_circuit(tmp_path):
    source = tmp_path / "probe.py"
    source.write_text(
        "def predicate(x):\n    return True\n"
        "def produce(x):\n    return x\n"
        "def entry(first, later):\n"
        "    return any(predicate(t) for t in (first, produce(later)))\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="probe", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    produce, = result.find_calls(caller=entry, callee_name="produce")
    assert {flow["source"] for flow in predicate.argument_flows} == {"first"}
    assert produce.analysis_status == "analyzed"
    assert {flow["source"] for flow in produce.argument_flows} == {"later"}


@pytest.mark.parametrize("delimiters", ["()", "[]"], ids=["tuple", "list"])
@pytest.mark.parametrize(("items", "truth", "sources"), [
    ("first, later", True, {("first", ())}),
    ("first[0], later", True, {("first", (0,))}),
    ("0, later", True, set()),
    ("0, later", False, {("later", ())}),
    ("0, produce(later)", True, set()),
])
def test_generator_preserves_literal_sequence_element_paths(
        tmp_path, delimiters, items, truth, sources):
    source = tmp_path / "probe.py"
    sequence = delimiters[0] + items + delimiters[1]
    source.write_text(
        f"def predicate(x):\n    return {truth}\n"
        "def produce(x):\n    return x\n"
        "def entry(first, later):\n"
        f"    return any(predicate(t) for t in {sequence})\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="probe", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.analysis_status == "analyzed"
    assert (predicate.target.module, predicate.target.qualname) == ("probe", "predicate")
    assert predicate.parameter_bindings == [
        {"argument": {"position": 0}, "parameter": "x",
         "destination_kind": "parameter", "status": "exact"},
    ]
    assert {(flow["source"], tuple(flow.get("projection", [])))
            for flow in predicate.argument_flows if flow["kind"] == "parameter"} == sources
    if truth and items.startswith("0,"):
        assert not predicate.argument_flows
    if "produce" in items:
        produce, = result.find_calls(caller=entry, callee_name="produce")
        assert produce.analysis_status == "analyzed"
        assert {flow["source"] for flow in produce.argument_flows} == {"later"}


@pytest.mark.parametrize("consumer", ["any", "all"])
def test_empty_generator_input_does_not_report_predicate_execution(tmp_path, consumer):
    source = tmp_path / "empty_generator.py"
    source.write_text(
        "def predicate(item):\n"
        "    return bool(item)\n"
        "def entry():\n"
        "    return " + consumer + "(predicate(item) for item in [])\n",
        encoding="utf-8",
    )
    entry = FunctionRef(module="empty_generator", qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[tmp_path]).analyze(entry)
    predicate, = result.find_calls(caller=entry, callee_name="predicate")
    assert predicate.analysis_status == "not_analyzed"
    assert not predicate.argument_flows
    assert any(boundary["reason"] == "generator_empty_input"
               and boundary.get("consumer", {}).get("source_text", "").startswith(consumer + "(")
               for boundary in result.boundaries)


def test_generator_element_evidence_is_improved(generator_example):
    expected, candidate = generator_example
    check, = compare_call(expected, candidate)
    assert check["status"] == "improved"
    assert check["actual"][0]["projection"] == ["*"]
    candidate["argument_flows"][0]["evidence"].pop(0)
    assert compare_call(expected, candidate)[0]["status"] == "regression"


@pytest.mark.parametrize(("mutation", "reason"), [
    ("conditions", "generator_execution_condition_missing"),
    ("execution", "generator_execution_condition_invalid"),
    ("short_circuit", "generator_short_circuit_condition_invalid"),
])
def test_generator_comparator_rejects_missing_or_corrupt_conditions(
        generator_example, mutation, reason):
    expected, candidate = generator_example
    flow = candidate["argument_flows"][0]
    if mutation == "conditions":
        flow["conditions"] = []
    elif mutation == "execution":
        flow["conditions"][0]["execution"] = "always"
    else:
        flow["conditions"][0]["later_iterations_may_be_skipped"] = False
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == ("regression", reason)


@pytest.mark.parametrize(("field", "key", "value", "reason"), [
    ("consumer", "lineno", 42, "consumer_location_invalid"),
    ("consumer", "col_offset", 17, "consumer_location_invalid"),
    ("generator_iteration", "lineno", 42, "generator_iteration_location_invalid"),
    ("generator_iteration", "col_offset", 20, "generator_iteration_location_invalid"),
    (None, "consumer_kind", "all", "generator_consumer_kind_invalid"),
])
def test_generator_comparator_rejects_wrong_consumer_location(
        generator_example, field, key, value, reason):
    expected, candidate = generator_example
    condition = candidate["argument_flows"][0]["conditions"][0]
    (condition[field] if field else condition)[key] = value
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == ("regression", reason)


@pytest.mark.parametrize("outer_first", [False, True])
def test_generator_comparator_scopes_checks_to_inner_consumer(generator_example, outer_first):
    expected, candidate = generator_example
    flow, = candidate["argument_flows"]
    inner, = flow["conditions"]
    outer = copy.deepcopy(inner)
    outer["consumer_kind"] = "all"
    for field in ("consumer", "generator_iteration"):
        outer[field].update(lineno=38, end_lineno=40)
    flow["conditions"] = [outer, inner] if outer_first else [inner, outer]
    check, = compare_call(expected, candidate)
    assert check["status"] == "improved"
    inner["consumer"]["col_offset"] += 1
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == ("regression", "consumer_location_invalid")
    flow["conditions"] = [outer]
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == (
        "regression", "generator_execution_condition_missing")


@pytest.mark.parametrize(("change", "reason"), [
    ("container", "generator_element_evidence_missing"),
    ("wrong_target", "generator_target_mismatch"),
    ("wrong_formal", "generator_slot_mismatch"),
    ("wrong_position", "generator_slot_mismatch"),
])
def test_generator_rejects_invalid_flow(generator_example, change, reason):
    expected, candidate = generator_example
    flow = candidate["argument_flows"][0]
    if change == "container":
        flow.update(projection=[], relation="direct")
    elif change == "wrong_target":
        candidate["target"]["qualname"] = "another_predicate"
    elif change == "wrong_formal":
        flow["target_parameter"] = "other"
    elif change == "wrong_position":
        flow["argument"]["position"] = 1
    check, = compare_call(expected, candidate)
    assert (check["status"], check["reason"]) == ("regression", reason)


def test_unresolved_receiver_rejects_wrong_target(observations):
    split = next(case for case in observations if case["id"] == "offset")["calls"][0]
    wrong = {**split["observed"], "target": {"qualname": "StringMethods.split"}}
    assert compare_call(split["expected"], wrong)[0]["status"] == "regression"


def test_mixed_branch_alternatives_are_a_regression(observations):
    frame = observations[0]["calls"][0]
    corrupted = copy.deepcopy(frame["observed"])
    source = next(f for f in corrupted["argument_flows"] if f["target_parameter"] == "columns")
    impossible = copy.deepcopy(source)
    for condition in impossible["conditions"]:
        if condition["test"]["lineno"] == 11:
            condition["branch"] = True
    corrupted["argument_flows"].append(impossible)
    assert {(c["slot"], c["reason"]) for c in compare_call(frame["expected"], corrupted)
            if c["status"] == "regression"} == {("columns", "incompatible_branch")}
