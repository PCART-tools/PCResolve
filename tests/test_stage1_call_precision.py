## Regressions for branch-specific source survival and nested call identities.
## 分支内来源保留和嵌套调用身份的回归测试。
from copy import deepcopy
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef
from scripts.evaluate_stage1_calls import method_checks, ownership_at
from scripts.evaluate_stage3_value_flow import MANIFEST, analyze_case


FIXTURE = Path(__file__).parent / "fixtures" / "stage3_value_flow"


## Require the surviving result to carry both subsequent branch decisions.
## 验证保留下来的返回来源携带后续分支的正确极性。
def test_rebinding_retains_only_the_branch_where_a_call_result_survives():
    source = FIXTURE / "surviving_binding.py"
    entry = FunctionRef(module=source.stem, qualname="entry")
    result = FlowAnalyzer(source_files=[source], import_roots=[FIXTURE]).analyze(entry)
    guards = {6: {(7, False), (9, True)}, 8: {(7, True), (9, True)}, 12: {(9, False)}}
    calls = result.find_calls(caller=entry, callee_name="helper")
    assert {call.lineno for call in calls} == set(guards)
    for call in calls:
        for flow in call.return_flows:
            assert flow["source"] == call.id
            actual = {(g["test"]["lineno"], g["branch"]) for g in flow["conditions"]}
            assert actual == guards[call.lineno]
        assert call.return_flows


## Verify ownership and flow independently at the nested expression spans.
## 分别按内外表达式的范围验证调用归属与值流。
def test_equals_and_all_keep_separate_owner_boundary_and_return():
    spec = next(case for case in MANIFEST["fixture"]["cases"] if case["id"] == "equals")
    case = analyze_case(FIXTURE, [FIXTURE / "probe.py"], spec, MANIFEST["query"])
    case["ownership"] = ownership_at(FIXTURE, "probe.py", [c["span"] for c in spec["calls"]])
    case["expected_ownership"] = {
        "schema_version": "1.0",
        "calls": [[["local", "LOCAL_DEFINITION", spec["calls"][0]["callee"]]],
                  [["python", "BUILTIN", "all"]]],
    }
    assert all(method_checks(case).values())

    wrong = deepcopy(case)
    wrong["ownership"]["calls"][0][0][:2] = ["python", "BUILTIN"]
    assert not method_checks(wrong)["ownership by full expression span"]
    wrong["ownership"]["calls"][0][0][:2] = ["unknown", "UNRESOLVED"]
    assert not method_checks(wrong)["ownership by full expression span"]
    inner, outer = [c["observed"] for c in case["calls"]]
    inner["return_flows"] = outer["return_flows"]
    assert not method_checks(case)["only the outer all result is returned"]
    inner["return_flows"] = []
    outer["return_flows"][0]["source"] = inner["id"]
    assert not method_checks(case)["only the outer all result is returned"]
