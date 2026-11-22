## Replay and compare the Stage 0 pandas value-flow cases.
## 重放并比较阶段 0 的 pandas 值流案例。
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen

import pcresolve
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/fixtures/stage3_value_flow/manifest.json")
                      .read_text(encoding="utf-8"))
SPAN = ("lineno", "col_offset", "end_lineno", "end_col_offset")
CALL_ID = re.compile(r"^(.*):([0-9]+):[0-9]+:[0-9]+:[0-9]+$")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def materialize_slice(directory, case, archive, pandas):
    if archive is None:
        return [ROOT / "tests/fixtures/stage3_value_flow" / name for name in case["files"]]
    sources = []
    with tarfile.open(archive, "r:gz") as source:
        for name in case["files"]:
            member = source.getmember("pandas-" + pandas["version"] + "/" + name)
            if not member.isfile():
                raise ValueError("Expected regular source file: " + name)
            with source.extractfile(member) as stream:
                data = stream.read()
            if hashlib.sha256(data).hexdigest() != pandas["files"][name]:
                raise ValueError("Source SHA-256 mismatch: " + name)
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            sources.append(path)
            for parent in path.relative_to(directory).parents:
                if parent != Path("."):
                    init = directory / parent / "__init__.py"
                    init.touch()
                    sources.append(init)
    return sorted(set(sources))


def normalize(value, root, field=None):
    if isinstance(value, dict):
        return {key: normalize(item, root, key) for key, item in value.items()}
    if isinstance(value, list):
        items = [normalize(item, root, field) for item in value]
        if field in {"conditions", "argument_flows", "target_candidates", "boundaries"}:
            return [item for _, item in sorted({canonical(x): x for x in items}.items())]
        return items
    if isinstance(value, str) and field != "source_text":
        for prefix in (str(root), root.as_posix()):
            if value.startswith((prefix + "/", prefix + "\\")):
                return value[len(prefix) + 1:].replace("\\", "/")
    return value


def matching_source(flow, selector, file):
    keys = ("kind", "source", "relation", "projection")
    if any(flow.get(key) != selector[key] for key in keys if key in selector):
        return False
    evidence = [row for row in flow.get("evidence", []) if row.get("file_path") == file]
    expected = set(selector.get("evidence_lines", []))
    actual = {row.get("lineno") for row in evidence}
    if selector.get("any_evidence_line"):
        if not expected & actual:
            return False
    elif not expected <= actual:
        return False
    if "text" in selector and not any(e.get("source_text") == selector["text"] for e in evidence):
        return False
    if "evidence_spans" in selector:
        spans = {tuple(row.get(key) for key in SPAN) for row in evidence
                 if "text" not in selector or row.get("source_text") == selector["text"]}
        if not {tuple(span) for span in selector["evidence_spans"]} <= spans:
            return False
    if "source_line" in selector or "source_span" in selector:
        match = CALL_ID.fullmatch(str(flow.get("source")))
        if not match or match[1] != file:
            return False
        if "source_span" in selector:
            return flow["source"] == file + ":" + ":".join(map(str, selector["source_span"]))
        return int(match[2]) == selector["source_line"]
    return True


def flow_guards(flow, file):
    return {(item["test"]["lineno"], item["branch"])
            for item in flow.get("conditions", []) if "branch" in item
            and isinstance(item.get("test"), dict) and item["test"].get("file_path") == file
            and "lineno" in item["test"]}


def target_identity(target):
    if target is None:
        return None
    return {"module": target.get("module"), "qualname": target.get("qualname")}


## Compare path predicates that reach each annotated return statement.
## 比较到达每条标注返回语句的路径条件。
#
#  @param gap Source-derived paths and guard sources for this call.
#  @param observed Public call-flow record.
#  @param call_span Source range of the queried call.
#  @return One comparison result for the complete path set.
def check_control_paths(gap, observed, call_span):
    file = gap["control_file"]
    call_id = ":".join([file] + list(map(str, call_span)))
    guard_calls = {
        tuple(item["guard"]): [":".join([file] + list(map(str, span))) for span in item["calls"]]
        for item in gap["control_guard_calls"]
    }
    actual = []
    required_prefix = tuple((tuple(guard["span"]), guard["branch"])
                            for guard in gap.get("control_prefix", []))
    contradictions = []
    if observed.get("id") != call_id:
        contradictions.append({"field": "id", "expected": call_id, "actual": observed.get("id")})
    for flow in observed.get("control_flows", []):
        if flow.get("call_id") != call_id:
            contradictions.append({"field": "call_id", "expected": call_id,
                                   "actual": flow.get("call_id")})
            continue
        for field in ("predicate", "return"):
            if flow.get(field, {}).get("file_path") != file:
                contradictions.append({"field": field + ".file_path", "expected": file,
                                       "actual": flow.get(field, {}).get("file_path")})
        predicate = flow.get("predicate", {})
        matching_guards = [condition for condition in flow.get("path", [])
                           if condition.get("test") == predicate]
        if (len(matching_guards) != 1 or matching_guards[0].get("branch") != flow.get("branch")):
            contradictions.append({"call_id": flow.get("call_id"),
                                   "predicate": predicate, "branch": flow.get("branch"),
                                   "matching_guards": matching_guards})
        path = tuple((tuple(condition.get("test", {}).get(key) for key in SPAN),
                      condition.get("branch"))
                     for condition in flow.get("path", []))
        for condition in flow.get("path", []):
            test = condition.get("test", {})
            if test.get("file_path") != file:
                contradictions.append({"field": "path.test.file_path", "expected": file,
                                       "actual": test.get("file_path")})
            span = tuple(test.get(key) for key in SPAN)
            expected_ids = guard_calls.get(span, [])
            actual_ids = condition.get("call_ids")
            if (not isinstance(actual_ids, list)
                    or any(not isinstance(source, str) for source in actual_ids)
                    or Counter(actual_ids) != Counter(expected_ids)):
                contradictions.append({"field": "path.call_ids", "guard": test,
                                       "expected": expected_ids, "actual": actual_ids})
        returned = flow.get("return", {})
        predicate_span = tuple(flow.get("predicate", {}).get(key) for key in SPAN)
        return_span = tuple(returned.get(key) for key in SPAN)
        actual.append((predicate_span, return_span, returned.get("source_text"), path))
    required = [(tuple(item["predicate_span"]), tuple(item["return_span"]), item["return_text"],
                 required_prefix + tuple((tuple(span), branch) for span, (_, branch)
                                         in zip(item["condition_spans"], item["conditions"])))
                for item in gap["control_paths"]]
    injected_sources = [flow for flow in observed.get("return_flows", [])
                        if flow.get("kind") == "call_result"
                        and flow.get("source") == observed.get("id")]
    actual_counts, required_counts = Counter(actual), Counter(required)
    if actual_counts == required_counts and not contradictions and not injected_sources:
        return {"status": "pass", "reason": "required_control_paths_found",
                "expected": sorted(required), "actual": sorted(actual)}
    missing = sorted((required_counts - actual_counts).elements())
    extra = sorted((actual_counts - required_counts).elements())
    return {"status": "regression", "reason": "control_path_mismatch",
            "missing": missing, "extra": extra, "contradictions": contradictions,
            "forbidden_return_sources": injected_sources}


## Check a generator element's argument flow and its destination binding.
## 核对生成器元素的实参流及其目标绑定。
def check_generator_slot(slot, observed):
    gap = slot["gap"]
    target = target_identity(observed["target"])
    flows = observed["argument_flows"]
    record = {"slot": slot["formal"], "argument": slot["argument"],
              "expected_target": gap["expected_target"], "actual_target": observed["target"],
              "actual": flows}
    if target is not None and target != gap["expected_target"]:
        return {**record, "status": "regression", "reason": "generator_target_mismatch"}
    if not flows and any(b["reason"] == gap["reason"] for b in observed["boundaries"]):
        return {**record, "status": "unknown", "reason": gap["reason"]}
    if target != gap["expected_target"] or observed["analysis_status"] != "analyzed":
        return {**record, "status": "regression", "reason": "generator_target_unconfirmed"}
    if not flows:
        return {**record, "status": "regression", "reason": "required_source_missing"}

    file = observed["caller"]["file_path"]
    for flow in flows:
        if (flow["argument"] != slot["argument"] or flow["target_parameter"] != slot["formal"]
                or flow.get("target_path")):
            return {**record, "status": "regression", "reason": "generator_slot_mismatch"}
        if not matching_source(flow, slot["required"], file):
            return {**record, "status": "regression", "reason": "generator_element_evidence_missing"}
        reason = check_generator_condition(flow.get("conditions", []),
                                           gap["consumer_evidence"], file)
        if reason:
            return {**record, "status": "regression", "reason": reason}
    return {**record, "status": "improved", "reason": "required_source_found"}


## Check the execution condition belonging to the annotated generator consumption.
## 核对属于标注生成器消费位置的执行条件。
#
#  @param conditions Conditions attached to one argument flow.
#  @param expected Annotated consumer kind and source spans.
#  @param file Expected source file for both spans.
#  @return Regression reason or None if one matching condition is valid.
def check_generator_condition(conditions, expected, file):
    locations = ("consumer", "generator_iteration")
    identified = []
    for condition in conditions:
        matches = []
        for field in locations:
            evidence = condition.get(field, {})
            if (evidence.get("file_path") == file
                    and [evidence.get(key) for key in SPAN] == expected[field]):
                matches.append(field)
        if matches:
            identified.append((matches, condition))
    if not identified:
        return "generator_execution_condition_missing"
    for field in locations:
        identified = [(matches, condition) for matches, condition in identified
                      if field in matches]
        if not identified:
            return field + "_location_invalid"
    for field, value, reason in (
        ("consumer_kind", expected["kind"], "generator_consumer_kind_invalid"),
        ("execution", "may_execute", "generator_execution_condition_invalid"),
        ("later_iterations_may_be_skipped", True, "generator_short_circuit_condition_invalid"),
    ):
        identified = [(matches, condition) for matches, condition in identified
                      if type(condition.get(field)) is type(value) and condition[field] == value]
        if not identified:
            return reason
    return None


def check_slot(slot, call, observed):
    if "gap" in slot:
        return check_generator_slot(slot, observed)
    flows = [f for f in observed["argument_flows"] if f["argument"] == slot["argument"]]
    name = slot["formal"]
    file = observed["caller"]["file_path"]
    guards = {tuple(guard) for guard in call.get("guards", [])}
    opposites = {(line, not branch) for line, branch in guards}
    for forbidden in slot["forbidden"]:
        matches = [f for f in flows if matching_source(f, forbidden, file)]
        if matches:
            return {"slot": name, "status": "regression", "reason": "forbidden_source",
                    "expected_exclusion": forbidden, "actual": matches}
    contradicted = [f for f in flows if opposites & flow_guards(f, file)]
    if contradicted:
        return {"slot": name, "status": "regression", "reason": "incompatible_branch",
                "actual": contradicted}
    required = slot["required"]
    matches = [f for f in flows if f["target_parameter"] == name
               and matching_source(f, required, file)
               and guards <= flow_guards(f, file)]
    if matches:
        return {"slot": name, "status": "pass",
                "reason": "required_source_found", "actual": matches,
                "excluded": slot["forbidden"]}
    return {"slot": name, "status": "regression", "reason": "required_source_missing",
            "actual": flows}


## Compare a call against the source-derived expectations for its exact slots.
## 将调用的具体参数槽位与源码标注进行比较。
def compare_call(expected, observed):
    if observed is None:
        return [{"status": "regression", "reason": "call_site_missing"}]
    checks = []
    target = target_identity(observed["target"])
    if "target" in expected:
        matches = expected["target"] == target
        checks.append({"status": "pass" if matches else "regression", "reason": "target",
                       "expected_target": expected["target"], "actual": observed["target"]})
        if not matches:
            return checks
    checks.extend(check_slot(slot, expected, observed) for slot in expected.get("slots", []))
    if "unconfirmed_target" in expected:
        reason = expected["unconfirmed_target"]["reason"]
        unresolved = target is None and any(b["reason"] == reason for b in observed["boundaries"])
        checks.append({"status": "unknown" if unresolved else "regression",
                       "reason": reason if unresolved else "unexpected_target_or_missing_boundary",
                       "actual": target, "candidates": observed["target_candidates"]})
    if expected.get("return_flow"):
        checks.append({"status": "pass" if observed["return_flows"] else "regression",
                       "reason": "return_flow"})
    for gap in expected.get("gaps", []):
        if "control_paths" in gap:
            checks.append(check_control_paths(gap, observed, expected["span"]))
        else:
            evidence = {key: observed[key] for key in gap["review_fields"] if observed.get(key)}
            checks.append({"status": "review" if evidence else "unknown", "reason": gap["reason"],
                           "capability": gap["capability"], "actual": evidence})
    return checks


def relevant_boundaries(result, call):
    for boundary in result.boundaries:
        if boundary.get("call_id") == call.id:
            yield boundary
        elif not boundary.get("call_id"):
            evidence = boundary.get("evidence", {})
            if isinstance(evidence, dict) and evidence.get("file_path") == call.caller.file_path:
                if ((evidence.get("lineno", 0), evidence.get("col_offset", 0))
                        <= (call.lineno, call.col_offset)
                        and (call.end_lineno, call.end_col_offset)
                        <= (evidence.get("end_lineno", -1), evidence.get("end_col_offset", -1))):
                    yield boundary
            elif not evidence:
                if boundary.get("function") in (None, result.entry.__dict__):
                    yield boundary


def analyze_case(root, sources, case, query):
    analyzer = FlowAnalyzer(source_files=sources, import_roots=[root])
    entry = FunctionRef(module=case["module"], qualname=case["entry"])
    result = analyzer.analyze(entry, **query)
    calls = {(c.callee_name, tuple(getattr(c, key) for key in SPAN)): c
             for c in result.find_calls(caller=entry)}
    records = []
    for expected in case["calls"]:
        call = calls.get((expected["callee"], tuple(expected["span"])))
        observed = None
        if call is not None:
            details = result.describe_call_flow(call.id)
            keys = ("id", "caller", "target", "target_candidates", "target_status",
                    "analysis_status", "argument_flows", "parameter_bindings", "conditions",
                    "receiver_sources", "return_flows", "mutation_flows", "effects")
            observed = normalize({**{k: details[k] for k in keys},
                                  "control_flows": details.get("control_flows", []),
                                  "boundaries": list(relevant_boundaries(result, call))}, root)
        records.append({"expected": expected, "observed": observed,
                        "checks": compare_call(expected, observed)})
    return {"id": case["id"], "entry": case["module"] + ":" + case["entry"],
            "source_files": [path.relative_to(root).as_posix() for path in sources],
            "import_root": ".", "schema_version": result.schema_version, "calls": records}


## Replay all cases from an isolated, verified source slice or the local fixture.
## 从隔离并校验的源码切片或本地 fixture 重放全部案例。
def replay(manifest, group, archive=None):
    if group == "pandas":
        archive = Path(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["pandas"]["archive_sha256"]:
            raise ValueError("pandas source archive SHA-256 mismatch")
    with tempfile.TemporaryDirectory(prefix="pcresolve_stage3_") as workspace:
        records = []
        for case in manifest[group]["cases"]:
            directory = Path(workspace) / case["id"]
            sources = materialize_slice(directory, case, archive, manifest["pandas"])
            root = directory if archive is not None else sources[0].parent
            records.append(analyze_case(root, sources, case, manifest["query"]))
    return records


def verify_injections(records, group):
    frame = next(case for case in records if case["id"] == "frame")["calls"][0]
    tolist = next(case for case in records if case["id"] == "tolist")["calls"][0]
    wrong_line = 351 if group == "pandas" else 12
    contaminated = deepcopy(frame["observed"])
    source = next((f for f in (contaminated or {}).get("argument_flows", [])
                   if f["target_parameter"] == "columns"), None)
    if source is None or tolist["observed"] is None:
        return [{"detected": False, "reason": "injection_input_missing"}]
    source["evidence"].append({"file_path": contaminated["caller"]["file_path"],
                               "lineno": wrong_line})
    erased = {**tolist["observed"], "argument_flows": []}
    results = []
    for record, injected, reason in [(frame, contaminated, "forbidden_source"),
                                     (tolist, erased, "required_source_missing")]:
        failures = [check for check in compare_call(record["expected"], injected)
                    if check["status"] == "regression"]
        results.append({"caller": injected["caller"], "span": record["expected"]["span"],
                        "expected_reason": reason, "failures": failures,
                        "detected": [check["reason"] for check in failures] == [reason]})
    return results


## Check nested consumption against a copy of the observed generator flow.
## 在生成器实测值流副本中核对嵌套消费条件。
#
#  @param records Replayed case records.
#  @return Named positive and negative checks with expected and actual verdicts.
def verify_generator_conditions(records):
    case = next(case for case in records if case["id"] == "common-type")
    call = case["calls"][0]
    observed = call["observed"]
    if not observed or not observed["argument_flows"]:
        return [{"case": "observed_generator_flow", "passed": False}]
    observed_conditions = observed["argument_flows"][0].get("conditions", [])
    condition = next((row for row in observed_conditions
                      if "generator_iteration" in row and "consumer" in row), None)
    if condition is None:
        return [{"case": "observed_generator_condition", "passed": False}]
    outer = deepcopy(condition)
    outer["consumer_kind"] = "all"
    for field in ("consumer", "generator_iteration"):
        outer[field].update(lineno=condition[field]["lineno"] - 1,
                            end_lineno=condition[field]["end_lineno"] + 1)

    cases = [
        ("original", observed_conditions, "improved", "required_source_found"),
        ("outer_first", [outer, condition], "improved", "required_source_found"),
        ("inner_first", [condition, outer], "improved", "required_source_found"),
        ("outer_only", [outer], "regression", "generator_execution_condition_missing"),
    ]
    for field, value, reason in (
        ("consumer_kind", "all", "generator_consumer_kind_invalid"),
        ("execution", "always", "generator_execution_condition_invalid"),
        ("later_iterations_may_be_skipped", False, "generator_short_circuit_condition_invalid"),
    ):
        cases.append((field, [outer, dict(condition, **{field: value})], "regression", reason))
    split_spans = []
    for field in ("consumer", "generator_iteration"):
        for coordinate in ("lineno", "col_offset"):
            corrupted = deepcopy(condition)
            corrupted[field][coordinate] += 1
            cases.append((field + "." + coordinate, [outer, corrupted], "regression",
                          field + "_location_invalid"))
            if coordinate == "col_offset":
                split_spans.append(corrupted)
    cases.append(("split_spans", [outer] + split_spans, "regression",
                  "generator_iteration_location_invalid"))
    checks = []
    for name, conditions, status, reason in cases:
        candidate = deepcopy(observed)
        candidate["argument_flows"][0]["conditions"] = conditions
        actual = [(entry["status"], entry["reason"])
                  for entry in compare_call(call["expected"], candidate)]
        checks.append({"case": name, "expected": [status, reason], "actual": actual,
                       "passed": actual == [(status, reason)]})
    return checks


## Inject corruptions into annotated control paths and require rejection.
## 对标注的控制路径注入错误并要求比较器拒绝。
#
#  @param records Replayed case records.
#  @return Injection outcomes with expected and actual decisions.
def verify_control_path_injections(records):
    checks = []
    for case in records:
        for call in case["calls"]:
            expected = call["expected"]
            observed = call["observed"]
            if observed is None:
                continue
            for gap in expected.get("gaps", []):
                if "control_paths" not in gap:
                    continue
                flows = [flow for flow in observed.get("control_flows", [])
                         if flow.get("call_id") == observed.get("id")]
                if not flows:
                    checks.append({"case": case["id"], "call": expected["callee"],
                                   "injection": "baseline_paths_missing", "detected": False})
                    continue
                mutations = {
                    "drop_path": lambda rows: rows[:-1],
                    "branch_path_conflict": lambda rows: [dict(rows[0], branch=not rows[0]["branch"])] + rows[1:],
                    "predicate_column": lambda rows: [dict(rows[0], predicate=dict(
                        rows[0]["predicate"], col_offset=rows[0]["predicate"]["col_offset"] + 1))]
                        + rows[1:],
                    "return_column": lambda rows: [dict(rows[0], **{"return": dict(
                        rows[0]["return"], col_offset=rows[0]["return"]["col_offset"] + 1)})]
                        + rows[1:],
                    "flip_polarity": lambda rows: [dict(row, path=[dict(
                        condition, branch=not condition["branch"])
                        for condition in row["path"]]) for row in rows],
                    "wrong_return": lambda rows: [dict(rows[0], **{"return": dict(
                        rows[0]["return"], lineno=1078 if case["id"] == "common-type"
                        else rows[0]["return"]["lineno"] + 1)})] + rows[1:],
                    "wrong_condition": lambda rows: [dict(rows[0], path=[dict(
                        rows[0]["path"][0], test=dict(rows[0]["path"][0]["test"],
                        lineno=rows[0]["path"][0]["test"]["lineno"] + 1))])] + rows[1:],
                    "wrong_call": lambda rows: [dict(rows[0], call_id="wrong-call")] + rows[1:],
                    "fake_return_value_source": lambda rows: rows,
                    "wrong_return_file": lambda rows: [dict(rows[0], **{"return": dict(
                        rows[0]["return"], file_path="wrong.py")})] + rows[1:],
                    "extra_call": lambda rows: rows + [dict(rows[0], call_id="another-call")],
                    "duplicate_record": lambda rows: rows + [deepcopy(rows[0])],
                    "extra_guard": lambda rows: [dict(rows[0], path=rows[0]["path"] + [dict(
                        rows[0]["path"][-1], test=dict(rows[0]["path"][-1]["test"],
                        lineno=1092, end_lineno=1092))])] + rows[1:],
                    "drop_inner_condition": lambda rows: [dict(row, path=[condition
                        for condition in row["path"]
                        if condition["test"].get("lineno") != 1093]) for row in rows],
                    "force_skipped_inner_condition": lambda rows: [dict(row, path=row["path"] + [
                        next(condition for candidate in rows for condition in candidate["path"]
                             if condition["test"].get("lineno") == 1093
                             and condition.get("branch") is True)])
                        if any(condition["test"].get("lineno") == 1089
                               and condition.get("branch") is False for condition in row["path"])
                        else row for row in rows],
                }
                for name, mutate in mutations.items():
                    if (name == "drop_inner_condition"
                            and not observed["caller"]["file_path"].endswith("pandas/core/dtypes/cast.py")):
                        continue
                    if (name == "force_skipped_inner_condition"
                            and not observed["caller"]["file_path"].endswith("pandas/core/dtypes/cast.py")):
                        continue
                    corrupted = deepcopy(observed)
                    matched = [flow for flow in corrupted["control_flows"]
                               if flow.get("call_id") == corrupted["id"]]
                    rest = [flow for flow in corrupted["control_flows"]
                            if flow.get("call_id") != corrupted["id"]]
                    corrupted["control_flows"] = rest + mutate(matched)
                    if name == "fake_return_value_source":
                        corrupted["return_flows"].append({
                            "kind": "call_result", "source": corrupted["id"]})
                    expectation = dict(expected, gaps=[gap])
                    result = compare_call(expectation, corrupted)
                    detected = any(row.get("status") == "regression"
                                   and row.get("reason") == "control_path_mismatch" for row in result)
                    checks.append({"case": case["id"], "call": expected["callee"],
                                   "injection": name, "detected": detected, "actual": result})
                if gap.get("control_prefix"):
                    for line in (1077, 1088):
                        corrupted = deepcopy(observed)
                        path = next(flow["path"] for flow in corrupted["control_flows"]
                                    if flow["return"]["lineno"] == 1094)
                        if line == 1077:
                            test = next(guard["test"] for guard in path
                                        if guard["test"]["lineno"] == line)
                        else:
                            test = dict(zip(SPAN, expected["span"]),
                                        file_path=observed["caller"]["file_path"],
                                        source_text="any(is_bool_dtype(t) for t in types)")
                        path.append({"test": test, "branch": True})
                        result = compare_call(expected, corrupted)
                        detected = any(row.get("status") == "regression"
                                       and row.get("reason") == "control_path_mismatch"
                                       and any(extra[-1][-1] == (
                                           tuple(test[key] for key in SPAN), True)
                                               for extra in row["extra"])
                                       for row in result)
                        checks.append({"case": case["id"], "call": expected["callee"],
                                       "injection": f"append_{line}_after_1093",
                                       "detected": detected, "actual": result})
                if gap.get("control_file") == "pandas/core/dtypes/cast.py":
                    wrong_id = gap["control_file"] + ":1077:7:1077:56"
                    for name, sources in (("wrong_guard_call", [wrong_id]),
                                          ("missing_guard_call", [])):
                        corrupted = deepcopy(observed)
                        flow = next(flow for flow in corrupted["control_flows"]
                                    if flow["return"]["lineno"] == 1094)
                        guard = next(guard for guard in flow["path"]
                                     if guard["test"]["lineno"] == 1089)
                        guard["call_ids"] = sources
                        result = compare_call(expected, corrupted)
                        difference = {"field": "path.call_ids", "guard": guard["test"],
                                      "expected": [observed["id"]], "actual": sources}
                        detected = any(row.get("status") == "regression"
                                       and difference in row.get("contradictions", [])
                                       for row in result)
                        checks.append({"case": case["id"], "call": expected["callee"],
                                       "injection": name, "detected": detected, "actual": result})
    return checks


def main():
    parser = argparse.ArgumentParser(description="Replay the Stage 0 value-flow precision baseline")
    parser.add_argument("--suite", choices=("fixture", "pandas"), default="fixture")
    parser.add_argument("--pandas-archive", type=Path,
                        help="Local pandas source archive. Suite pandas downloads it if omitted.")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--verify-injections", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeat < 1 or (args.pandas_archive and args.suite != "pandas"):
        parser.error("Use a positive repeat count and select suite pandas for a source archive")
    with tempfile.TemporaryDirectory(prefix="pcresolve_stage3_archive_") as temp:
        archive = args.pandas_archive
        if args.suite == "pandas" and archive is None:
            archive = Path(temp) / "pandas.tar.gz"
            with urlopen(MANIFEST["pandas"]["archive_url"], timeout=30) as remote:
                with archive.open("wb") as local:
                    shutil.copyfileobj(remote, local)
        observations = replay(MANIFEST, args.suite, archive)
        repeated = [replay(MANIFEST, args.suite, archive) for _ in range(args.repeat - 1)]
    stable = all(run == observations for run in repeated)
    counts = Counter(check["status"] for case in observations for call in case["calls"]
                     for check in call["checks"])
    injections = verify_injections(observations, args.suite) if args.verify_injections else []
    condition_checks = verify_generator_conditions(observations) if args.verify_injections else []
    control_checks = verify_control_path_injections(observations) if args.verify_injections else []
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                     text=True).strip()
    report = {"suite": args.suite, "python": platform.python_version(), "commit": commit,
              "reference_commit": MANIFEST["baseline_commit"],
              "analyzer": Path(pcresolve.__file__).resolve().relative_to(ROOT).as_posix(),
              "query": MANIFEST["query"], "repeat": args.repeat, "stable": stable,
              "counts": dict(counts), "cases": observations, "injections": injections,
              "generator_condition_checks": condition_checks,
              "control_path_injections": control_checks}
    if args.suite == "pandas":
        report["pandas"] = {key: value for key, value in MANIFEST["pandas"].items()
                            if key != "cases"}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(f"{args.suite}: {len(observations)} cases, {dict(counts)}, "
          f"repeat={args.repeat}, stable={stable}, injections={sum(i['detected'] for i in injections)}"
          f"/{len(injections)}, generator conditions="
          f"{sum(check['passed'] for check in condition_checks)}/{len(condition_checks)}, "
          f"control injections={sum(check['detected'] for check in control_checks)}"
          f"/{len(control_checks)}")
    for case in observations:
        for call in case["calls"]:
            for check in call["checks"]:
                if check["status"] in {"regression", "improved", "review"}:
                    print(canonical({"case": case["id"], "caller": case["entry"],
                                     "expected": call["expected"], "check": check,
                                     "observed": call["observed"]}))
    return int(not stable or counts["regression"] > 0 or any(not i["detected"] for i in injections)
               or any(not check["passed"] for check in condition_checks)
               or any(not check["detected"] for check in control_checks))


if __name__ == "__main__":
    raise SystemExit(main())
