## @package scripts.evaluate_stage3_boolean_paths
#  Replay the stage 3 Boolean path cases and deliberately corrupted results.
#  重放阶段 3 的布尔路径案例及包含故意注入错误的结果。

import argparse
import ast
import copy
import itertools
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys

from pcresolve import FlowAnalyzer, FunctionRef


FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/stage3_value_flow/boolean_paths"
RUNTIME = {
    "unused": [0, 1, 0, 1],
    "overwrite": [0, 1, 0, 0],
    "stored_q": [0, 1, 0, 0],
    "proven_parameter": [0, 1, 1, 1],
    "stored_negated": [0, 1, 0, 0],
    "stored_single_not": [1, 0, 1, 1],
    "repeated": [0, 1, 0, 1],
    "rebound": [0, 1, 2, 2],
    "independent_calls": [0, 1, 2, 1],
}
SPAN = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def cases_controls(call):
    return Counter(
        (tuple((guard["test"]["lineno"], guard["branch"]) for guard in flow["path"]),
         flow["return"]["lineno"])
        for flow in call["control_flows"]
    )


def check_case(case, code, calls):
    entry_node = next(node for node in ast.parse(code).body
                      if isinstance(node, ast.FunctionDef) and node.name == "entry")
    syntax = sorted((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset,
                     ast.unparse(node.func)) for node in ast.walk(entry_node)
                    if isinstance(node, ast.Call))
    assert syntax == sorted(tuple(call[field] for field in SPAN) + (call["callee_name"],)
                            for call in calls)
    p, q = calls[0], calls[-1]
    source = FIXTURES / case / "probe.py"
    observed_p, observed_q = cases_controls(p), cases_controls(q)
    if case == "unused":
        assert not observed_p, f"p at line 4 unexpectedly controls returns: {observed_p}"
        assert observed_q == Counter(
            {(((4, branch), (6, truth)), line): 1
             for branch, (truth, line) in itertools.product((True, False), ((True, 7), (False, 8)))}
        ), f"q at line 6 has incorrect return paths: {observed_q}"
        flow, = q["argument_flows"]
        assert flow["kind"] == "parameter" and flow["source"] == "y" and not flow["conditions"]
    elif case in ("overwrite", "stored_q", "proven_parameter", "stored_negated", "stored_single_not"):
        guard_line = 6 if case == "overwrite" else 7
        determined = case in ("proven_parameter", "stored_single_not")
        assert not any(path == ((4, True), (guard_line, not determined)) for path, _ in observed_p | observed_q), (
            f"guard p at line 4 true and guard at line {guard_line} {not determined} is infeasible")
        expected = Counter({(((4, False), (guard_line, truth)), line): 1 for truth, line in (
            (True, guard_line + 1), (False, guard_line + 2))})
        required = expected + Counter({(((4, True), (guard_line, determined)), guard_line + (1 if determined else 2)): 1})
        assert observed_p == required, f"p at line 4: required {required}, observed {observed_p}"
        assert observed_q == expected, f"q at line 6: required {expected}, observed {observed_q}"
        assert len(q["argument_flows"]) == 2
        for kind, branch in (("parameter", False), ("parameter" if case == "proven_parameter" else "literal", True)):
            flow, = [flow for flow in q["argument_flows"] if flow["kind"] == kind and
                     (kind != "parameter" or flow["source"] == ("x" if branch else "y"))]
            guards = [(guard["test"]["lineno"], guard["branch"]) for guard in flow["conditions"]]
            assert guards == [(4, branch)], f"q at line 6: {kind} source has incorrect guards {guards}"
            assert flow["target_parameter"] == "y" and flow["argument"] == {"position": 0}
            if kind == "parameter":
                assert flow["source"] == ("x" if branch else "y")
                if branch:
                    assert any(item["lineno"] == 5 and item["source_text"] == "y = x" for item in flow["evidence"])
            else:
                assert flow["literal"] == {"type": "bool", "value": False}
                assert any(item["lineno"] == 5 and item["source_text"] == "y = False"
                           for item in flow["evidence"])
    elif case == "repeated":
        assert all(flow["return"]["lineno"] != 7 for call in calls for flow in call["control_flows"]), (
            "conflicting guards at lines 5 and 6 make the return at line 7 unreachable")
        assert not observed_p, f"p at line 4 unexpectedly controls returns: {observed_p}"
        assert observed_q == Counter({
            (((5, True), (6, False), (8, True)), 9): 1,
            (((5, True), (6, False), (8, False)), 10): 1,
            (((5, False), (8, True)), 9): 1,
            (((5, False), (8, False)), 10): 1,
        }), f"q at line 8 has incorrect return paths: {observed_q}"
    elif case == "rebound":
        false_paths = Counter({(((5, False), (9, True)), 10): 1,
                               (((5, False), (9, False)), 11): 1})
        assert observed_p == false_paths + Counter({(((5, True), (7, True)), 8): 1})
        assert observed_q == false_paths
    elif case == "independent_calls":
        later = Counter({(((5, False), (8, True)), 9): 1, (((5, False), (8, False)), 10): 1})
        inner = Counter({(((5, True), (6, True)), 7): 1,
                         (((5, True), (6, False), (8, True)), 9): 1})
        for call, required in zip(calls, (inner + later, inner, later)):
            observed = cases_controls(call)
            assert observed == required, (
                f"call at line {call['lineno']}: missing {required - observed}, extra {observed - required}")

    predicates = {node.test.lineno: node.test for node in ast.walk(entry_node)
                  if isinstance(node, ast.If)}
    returns = {node.lineno: node for node in ast.walk(entry_node) if isinstance(node, ast.Return)}
    for call in calls:
        assert not call["return_flows"]
        assert max(cases_controls(call).values(), default=0) <= 1
        for flow in call["control_flows"]:
            assert flow["call_id"] == call["id"]
            check_span(flow["return"], returns, code, source)
            check_span(flow["predicate"], predicates, code, source)
            for guard in flow["path"]:
                test = guard["test"]
                node = predicates[test["lineno"]]
                check_span(test, predicates, code, source)
                operand = node.operand if isinstance(node, ast.UnaryOp) else node
                expected_ids = []
                if isinstance(operand, ast.Call):
                    expected_ids = [item["id"] for item in calls
                                    if all(item[field] == getattr(operand, field) for field in SPAN)]
                    assert len(expected_ids) == 1
                elif case in ("stored_q", "proven_parameter", "stored_negated", "stored_single_not") and node.lineno == 7:
                    expected_ids = [q["id"]]
                elif case != "rebound" or node.lineno == 5:
                    expected_ids = [p["id"]]
                assert guard["call_ids"] == expected_ids, f"wrong call identity at guard {test}"
            assert any(guard["test"] == flow["predicate"] and guard["branch"] == flow["branch"]
                       and call["id"] in guard["call_ids"] for guard in flow["path"])


def check_span(evidence, nodes, code, source):
    node = nodes[evidence["lineno"]]
    assert Path(evidence["file_path"]) == source
    assert evidence["source_text"] == ast.get_source_segment(code, node)
    assert tuple(evidence[field] for field in SPAN) == tuple(getattr(node, field) for field in SPAN)


## Record evaluated guards and the return site for each fixed Boolean input pair.
## 记录固定布尔输入组合下实际执行的守卫和返回位置。
#
#  @param code Trusted fixture source.
#  @param source Fixture path for compilation.
#  @return Four runtime observations with their ordered path witnesses.
def runtime_paths(code, source):
    tree = ast.parse(code)
    entry, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "entry"]
    for node in ast.walk(entry):
        if isinstance(node, (ast.If, ast.Return)):
            field = "test" if isinstance(node, ast.If) else "value"
            recorder = "record_guard" if field == "test" else "record_return"
            original = getattr(node, field)
            wrapped = ast.Call(func=ast.Name(id=recorder, ctx=ast.Load()),
                               args=[ast.Constant(node.lineno), original], keywords=[])
            setattr(node, field, ast.copy_location(wrapped, original))
    program = compile(ast.fix_missing_locations(tree), str(source), "exec")
    runtime = []
    for x, y in itertools.product((False, True), repeat=2):
        run = {"x": x, "y": y, "guards": []}

        def record_guard(line, value):
            run["guards"].append((line, bool(value)))
            return value

        def record_return(line, value):
            run["return_line"] = line
            return value

        namespace = {"record_guard": record_guard, "record_return": record_return}
        exec(program, namespace)
        run["returned"] = namespace["entry"](x, y)
        runtime.append(run)
    return runtime


def replay_case(case, run_cli=False):
    source = FIXTURES / case / "probe.py"
    code = source.read_text(encoding="utf-8")
    runtime = runtime_paths(code, source)
    assert [item["returned"] for item in runtime] == RUNTIME[case]
    entry = FunctionRef(module="probe", qualname="entry")
    analysis = FlowAnalyzer(source_files=[source], import_roots=[source.parent]).analyze(entry, max_depth=2)
    calls = [analysis.describe_call_flow(call.id) for call in analysis.find_calls(caller=entry)]
    assert not analysis.boundaries
    check_case(case, code, calls)
    feasible = {(tuple(run["guards"]), run["return_line"]) for run in runtime}
    for call in calls:
        unexpected = set(cases_controls(call)) - feasible
        assert not unexpected, f"{case} call at line {call['lineno']}: infeasible {unexpected}"
    public = analysis.to_dict()
    assert [call for call in public["calls"] if call["caller"]["qualname"] == "entry"] == calls
    report = {"source": code, "runtime": runtime, "api": public}
    if run_cli:
        command = ["-m", "pcresolve", "--source-file", str(source),
                   "--import-root", str(source.parent), "--value-flow",
                   "--entry", "probe:entry", "--depth", "2", "--json"]
        completed = subprocess.run([sys.executable, *command], check=True, capture_output=True, encoding="utf-8")
        cli = json.loads(completed.stdout)
        assert cli == public
        report.update(cli_command=["python", *command], cli=cli)
    return report, calls


INJECTIONS = {
    "missing_p_control": ("overwrite", "p at line 4: required"),
    "wrong_y_source": ("overwrite", "q at line 6: parameter source"),
    "impossible_q_branch": ("overwrite", "guard p at line 4 true and guard at line 6"),
    "contradictory_recheck": ("repeated", "return at line 7 unreachable"),
    "impossible_shared_input": ("independent_calls", "call at line 8: missing"),
    "parameter_impossible": ("proven_parameter", "guard p at line 4"),
    "negated_impossible": ("stored_negated", "guard p at line 4"),
    "parameter_missing_guard": ("proven_parameter", "parameter source"),
}


def inject(calls, name):
    mutated = copy.deepcopy(calls)
    p, q = mutated[0], mutated[-1]
    if name in ("parameter_impossible", "negated_impossible"):
        flow = copy.deepcopy(next(flow for flow in q["control_flows"] if flow["path"][-1]["branch"] == (name == "negated_impossible")))
        flow["path"][0]["branch"] = True
        q["control_flows"].append(flow)
    elif name == "parameter_missing_guard":
        source = next(flow for flow in q["argument_flows"] if flow["source"] == "y")
        source["conditions"] = []
    elif name == "missing_p_control":
        p["control_flows"].pop()
    elif name == "wrong_y_source":
        source = next(flow for flow in q["argument_flows"] if flow["kind"] == "parameter")
        source["conditions"][0]["branch"] = True
    elif name == "impossible_q_branch":
        impossible = copy.deepcopy(next(flow for flow in q["control_flows"] if flow["branch"]))
        impossible["path"][0]["branch"] = True
        q["control_flows"].append(impossible)
    elif name == "impossible_shared_input":
        flow = copy.deepcopy(next(flow for flow in p["control_flows"]
                                  if len(flow["path"]) == 3))
        negative = next(flow for flow in q["control_flows"] if not flow["branch"])
        flow["path"][-1]["branch"] = False
        flow.update(call_id=q["id"], predicate=flow["path"][-1]["test"], branch=False)
        flow["return"] = copy.deepcopy(negative["return"])
        q["control_flows"].append(flow)
    else:
        flow = copy.deepcopy(next(flow for flow in q["control_flows"] if len(flow["path"]) == 3))
        flow["path"][1]["branch"] = True
        flow["path"].pop()
        flow.update(call_id=p["id"], predicate=flow["path"][0]["test"], branch=True)
        flow["return"].update(lineno=7, col_offset=12, end_lineno=7, end_col_offset=20,
                              source_text="return 2")
        p["control_flows"].append(flow)
    return mutated


def verify_injection(name, report, calls):
    case, expected = INJECTIONS[name]
    mutated = inject(calls, name)
    try:
        check_case(case, report["source"], mutated)
    except AssertionError as error:
        assert expected in str(error), str(error)
        return {"case": case, "detected": True, "diagnostic": str(error)}
    raise AssertionError(f"{name} was not detected")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshots = {case: replay_case(case, run_cli=True) for case in RUNTIME}
    report = {"cases": {case: snapshot[0] for case, snapshot in snapshots.items()},
              "injections": {name: verify_injection(name, *snapshots[case])
                             for name, (case, _) in INJECTIONS.items()}}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(snapshots)} cases and {len(report['injections'])} injected errors verified")


if __name__ == "__main__":
    main()
