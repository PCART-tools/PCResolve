## Replay the four Stage 1 call-site cases on verified pandas source slices.
## 在校验过的 pandas 源码切片上重放阶段 1 的四组调用点。
import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

import pcresolve
from pcresolve import FlowAnalyzer, FunctionRef, ProjectAnalyzer

from scripts.evaluate_stage3_value_flow import (
    MANIFEST, ROOT, SPAN, analyze_case, compare_call, materialize_slice, normalize,
    relevant_boundaries,
)

CAST = "pandas/core/dtypes/cast.py"
TIMED = "pandas/core/tools/timedeltas.py"
OUTER = "maybe_infer_to_datetimelike"
INNER = OUTER + ".try_timedelta"


## Read the stable ownership result at each annotated expression span.
## 按标注表达式的完整范围读取稳定的调用归属结果。
#
#  @param root Isolated project directory.
#  @param file Source path relative to the project.
#  @param spans Annotated expression spans in source order.
#  @return Owner, reason and callee for every matching expression.
def ownership_at(root, file, spans):
    project = ProjectAnalyzer(str(root)).analyze()
    calls = [call for call in project.all_api_calls if Path(call.file_path) == root / file]
    return {"schema_version": project.schema_version, "calls": [
        [[c.top_library, c.reason, c.func_name] for c in calls
         if [getattr(c, key) for key in SPAN] == span] for span in spans
    ]}


## Check the identity and source evidence of every direct return witness.
## 核对每条直接返回证据的调用身份与源码位置。
#
#  @param call Normalized call-flow description.
#  @param line Expected return statement line, or None for no direct return.
#  @return Whether every reported return matches the annotation.
def direct_return(call, line):
    flows = call["return_flows"]
    if line is None:
        return not flows
    return bool(flows) and all(
        f["kind"] == "call_result" and f["relation"] == "direct" and f["source"] == call["id"]
        and any(e["file_path"] == call["caller"]["file_path"] and e["lineno"] == line
                and e["source_text"].startswith("return ") for e in f["evidence"])
        for f in flows)


## Collect exact call descriptions from one lexical caller.
## 按词法调用方收集具体调用点的值流描述。
#
#  @param analyzer Flow analyzer for the isolated slice.
#  @param root Slice root for normalizing paths.
#  @param entry Source function to query.
#  @param names Callees whose full descriptions are needed.
#  @return All lexical call identities and selected flow descriptions.
def call_records(analyzer, root, entry, names):
    result = analyzer.analyze(entry, **MANIFEST["query"])
    inventory = []
    details = []
    for call in result.find_calls(caller=entry):
        inventory.append({"id": call.id, "callee": call.callee_name,
                          "target": vars(call.target) if call.target else None})
        if call.callee_name in names:
            record = result.describe_call_flow(call.id)
            record["boundaries"] = list(relevant_boundaries(result, call))
            details.append(record)
    return {"entry": vars(entry), "schema_version": result.schema_version,
            "inventory": normalize(inventory, root),
            "calls": normalize(details, root)}


## Check conditions on a single source witness in the annotated file.
## 对照当前文件的标注核对单条来源证据的分支极性。
#
#  @param flow Source or return-flow record.
#  @param guards Required line-to-polarity mapping.
#  @return Whether each required guard occurs with exactly that polarity.
def has_guards(flow, guards):
    actual = {(g["test"]["lineno"], g["branch"]) for g in flow["conditions"]
              if "test" in g and "branch" in g and g["test"]["file_path"] == CAST}
    return all((line, branch) in actual and (line, not branch) not in actual
               for line, branch in guards.items())


## Compare both lexical levels against the two-file source slice.
## 对照双文件源码切片核对两个词法层次的调用。
#
#  @param records Outer and nested entry observations.
#  @return Named checks including exact call, argument and return expectations.
def nested_checks(records):
    outer, inner = records
    checks = {}
    module = "pandas.core.dtypes.cast"
    outer_spans = ["916:16:916:32", "928:20:928:36"]
    expected_ids = [CAST + ":" + span for span in outer_spans]
    calls = {c["id"]: c for c in outer["calls"]}
    checks["outer calls its local helper twice"] = sorted(calls) == expected_ids
    checks["outer has no direct to_timedelta edge"] = all(
        c["callee"] != "to_timedelta" and (c["target"] or {}).get("qualname") != "to_timedelta"
        for c in outer["inventory"])
    sources = {CAST + ":866:8:866:31": False, CAST + ":874:12:874:21": True}
    for index, call_id in enumerate(expected_ids):
        c = calls.get(call_id)
        if not c:
            continue
        guards = {911: False, 913: False, 915: index == 0}
        if index == 1:
            guards.update({917: True, 920: False})
        target = c["target"] or {}
        checks[call_id + " local target and formal"] = (
            c["caller"]["qualname"] == OUTER and c["caller"]["module"] == module
            and target == dict(module=module, qualname=INNER, file_path=CAST, lineno=899)
            and c["parameter_bindings"] == [{"argument": {"position": 0}, "parameter": "v",
                                             "status": "exact", "destination_kind": "parameter"}])
        flows = c["argument_flows"]
        checks[call_id + " argument origins and branches"] = (
            {f["source"] for f in flows} == set(sources) and all(
                f["argument"] == {"position": 0} and f["target_parameter"] == "v"
                and f["kind"] == "call_result" and f["relation"] == "direct"
                and has_guards(f, {**guards, 873: sources[f["source"]]}) for f in flows))
        if index == 1:
            guards[929] = False
        checks[call_id + " surviving result at return 932"] = (
            direct_return(c, 932) and all(has_guards(f, guards) for f in c["return_flows"]))

    inner_spans = ["905:19:905:34", "905:19:905:57", "907:19:907:35"]
    expected = [CAST + ":" + span for span in inner_spans]
    calls = {c["id"]: c for c in inner["calls"]}
    checks["inner call and two reshape expressions"] = set(calls) == set(expected)
    for call_id, reason, value, line in zip(
            expected, ("definition_unavailable", "receiver_unresolved", "receiver_unresolved"),
            ("v", "shape", "shape"), (None, 905, 907)):
        c = calls.get(call_id)
        if not c:
            continue
        checks[call_id + " scoped boundary"] = (
            c["caller"]["qualname"] == INNER and c["caller"]["module"] == module
            and c["target"] is None and not c["target_candidates"] and c["target_status"] == reason
            and any(b.get("call_id") == call_id and b["reason"] == reason
                    for b in c["boundaries"]))
        flows = c["argument_flows"]
        checks[call_id + " known actual, unresolved formal"] = (
            c["parameter_bindings"] == [{"argument": {"position": 0}, "parameter": None,
                                         "status": "unresolved", "destination_kind": "unresolved"}]
            and bool(flows) and all(
                f["source"] == value and f["kind"] == ("capture" if value == "shape" else "parameter")
                and f["relation"] == "direct" and f["target_parameter"] is None
                and f["argument"] == {"position": 0} for f in flows))
        checks[call_id + " direct return"] = direct_return(c, line)
    reshape = calls.get(expected[1], {})
    checks["converted result supplies reshape receiver"] = (
        [(f["source"], f["relation"]) for f in reshape.get("receiver_sources", [])]
        == [(expected[0], "derived")])
    return checks


## Check a method boundary and, for equals, distinguish its enclosing builtin.
## 检查方法边界，在 equals 案例中区分内层方法和外层内建调用。
#
#  @param case Annotated caller observations with optional ownership result.
#  @return Named comparisons for the dynamic method and its enclosing call.
def method_checks(case):
    dynamic = case["calls"][0]["observed"]
    checks = {"receiver boundary on this exact call": bool(dynamic) and (
        dynamic["target"] is None and not dynamic["target_candidates"]
        and any(b.get("call_id") == dynamic["id"] and b["reason"] == "receiver_unresolved"
                for b in dynamic["boundaries"]))}
    if case["id"] == "equals":
        outer = case["calls"][1]["observed"]
        checks["ownership by full expression span"] = (
            case["ownership"] == case["expected_ownership"])
        line = case["calls"][1]["expected"]["span"][0]
        checks["only the outer all result is returned"] = (
            bool(dynamic and outer) and direct_return(dynamic, None) and direct_return(outer, line))
    return checks


## Verify that corrupting a single observed fact fails the corresponding check.
## 验证单独破坏一项观测事实会触发对应的验收失败。
#
#  @param cases Real source observations.
#  @return Detection status for each injected error.
def verify_injections(cases):
    first = cases["frame"]["calls"][0]
    source = deepcopy(first["observed"])
    bad = next(f for f in source["argument_flows"] if f["target_parameter"] == "columns")
    bad["evidence"].append({"file_path": source["caller"]["file_path"], "lineno": 351})
    outcomes = {}
    for name, observed, reason in (
            ("sibling branch", source, "forbidden_source"),
            ("missing columns", {**first["observed"], "argument_flows": []}, "required_source_missing"),
            ("wrong helper", {**first["observed"], "target": {"qualname": "other"}}, "target")):
        outcomes[name] = any(c["status"] == "regression" and c["reason"] == reason
                             for c in compare_call(first["expected"], observed))
    equals = deepcopy(cases["equals"])
    equals["ownership"]["calls"][0] = [["python", "BUILTIN", "self._get_axis(a).equals"]]
    outcomes["inner builtin"] = not method_checks(equals)["ownership by full expression span"]
    equals["ownership"]["calls"][0][0][:2] = ["local", "LOCAL_DEFINITION"]
    outcomes["inner falsely resolved"] = not method_checks(equals)["ownership by full expression span"]
    inner, outer = [c["observed"] for c in equals["calls"]]
    inner["return_flows"] = outer["return_flows"]
    outcomes["outer return on inner call"] = not method_checks(equals)["only the outer all result is returned"]
    offset = deepcopy(cases["offset"])
    offset["calls"][0]["observed"]["target"] = {"qualname": "StringMethods.split"}
    outcomes["same-name split"] = not method_checks(offset)["receiver boundary on this exact call"]
    entries = deepcopy(cases["nested"]["entries"])
    entries[0]["inventory"].append({"callee": "to_timedelta", "target": None})
    outcomes["folded direct edge"] = not nested_checks(entries)["outer has no direct to_timedelta edge"]
    return outcomes


## Replay the source annotations and produce an auditable case report.
## 重放源码标注并生成可复核的案例报告。
#
#  @param archive Verified pandas source archive.
#  @return Source identities, query settings, observations and pass/fail checks.
def replay_stage1(archive):
    pandas = MANIFEST["pandas"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != pandas["archive_sha256"]:
        raise ValueError("Unexpected pandas source archive")
    files = dict(pandas["files"])
    files[TIMED] = "c7fca53501cfd3d50d011902d71caa5c8e6166ffbc747229dd301496d6445aa4"
    specs = {c["id"]: c for c in pandas["cases"]}
    cases = {}
    with tempfile.TemporaryDirectory() as work:
        for key in ("frame", "equals", "offset", "nested"):
            root = Path(work) / key
            spec = {"files": [CAST, TIMED]} if key == "nested" else specs[key]
            sources = materialize_slice(root, spec, archive, {**pandas, "files": files})
            if key == "nested":
                analyzer = FlowAnalyzer(source_files=sources, import_roots=[root])
                records = [call_records(analyzer, root, FunctionRef(module="pandas.core.dtypes.cast",
                           qualname=name), names) for name, names in (
                               (OUTER, ["try_timedelta", "to_timedelta"]),
                               (INNER, ["to_timedelta", "to_timedelta(v)._values.reshape", "v.reshape"]))]
                cases[key] = {"entries": records, "checks": nested_checks(records)}
            else:
                case = analyze_case(root, sources, spec, MANIFEST["query"])
                checks = {str(c["expected"]["span"]) + " " + check.get("slot", check["reason"]):
                          check["status"] in ("pass", "unknown")
                          for c in case["calls"] for check in c["checks"]}
                if key == "equals":
                    spans = [c["span"] for c in spec["calls"]]
                    case["ownership"] = ownership_at(root, spec["files"][0], spans)
                    case["expected_ownership"] = {
                        "schema_version": "1.0",
                        "calls": [[["unknown", "UNRESOLVED", spec["calls"][0]["callee"]]],
                                  [["python", "BUILTIN", "all"]]],
                    }
                if key in ("equals", "offset"):
                    checks.update(method_checks(case))
                case["stage1_checks"] = checks
                cases[key] = case
            cases[key]["source_sha256"] = {name: files[name] for name in spec["files"]}
    package = Path(pcresolve.__file__).resolve().parent
    package_hash = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        package_hash.update(path.relative_to(package).as_posix().encode() + b"\0")
        package_hash.update(hashlib.sha256(path.read_bytes()).digest())
    return {"pandas": pandas["version"], "archive_sha256": pandas["archive_sha256"],
            "analyzer_source_sha256": package_hash.hexdigest(),
            "commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                              text=True).strip(),
            "python": platform.python_version(), "query": MANIFEST["query"], "cases": cases,
            "injections_detected": verify_injections(cases) if all(
                all(c.get("stage1_checks", c.get("checks")).values()) for c in cases.values())
            else {}}


## Run the Stage 1 replay and return failure on any annotation mismatch.
## 执行阶段 1 重放，任一标注不符即返回失败。
#
#  @return Process exit code.
def main():
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument("--pandas-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay_stage1(args.pandas_archive)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = True
    for key, case in report["cases"].items():
        checks = case["checks"] if key == "nested" else case["stage1_checks"]
        print(key, sum(checks.values()), "/", len(checks), [name for name in checks if not checks[name]])
        passed = passed and all(checks.values())
    injections = report["injections_detected"]
    print("injections", sum(injections.values()), "/", len(injections))
    return int(not (passed and injections and all(injections.values())))


if __name__ == "__main__":
    raise SystemExit(main())
