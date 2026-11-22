## Replay the fixed pandas instance-field cases through the public value-flow API.
## 通过公开值流 API 重放固定 pandas 实例字段案例。

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pcresolve import FlowAnalyzer, FunctionRef
from scripts.evaluate_stage3_value_flow import MANIFEST, materialize_slice, normalize


ARCHIVE = ROOT / "PCResolve问题报告" / "stage3" / "pandas-0.21.0.tar.gz"
CASES = ("blocks", "fixed")


## Normalize temporary extraction paths in dictionary keys and values.
## 归一化字典键和值中的临时解压路径。
#
#  @param value JSON-safe report value.
#  @param root Temporary source root to remove.
#  @return Normalized value.
def normalize_path_keys(value, root):
    if isinstance(value, dict):
        return {normalize_path_keys(_normalize_path(key, root), root):
                normalize_path_keys(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_path_keys(item, root) for item in value]
    if isinstance(value, str):
        return _normalize_path(value, root)
    return value


## Remove one temporary source-root prefix from a string.
## 从字符串开头移除临时源码根路径。
#
#  @param value Candidate path or text.
#  @param root Temporary source root to remove.
#  @return Relative path or unchanged text.
def _normalize_path(value, root):
    value = value.replace("\\\\", "\\")
    for prefix in (str(root), root.as_posix()):
        if value.startswith((prefix + "/", prefix + "\\")):
            return value[len(prefix) + 1:].replace("\\", "/")
    for separator in ("/", "\\"):
        marker = separator + root.name + separator
        index = value.rfind(marker)
        if index >= 0:
            return value[index + len(marker):].replace("\\", "/")
        if value.endswith(separator + root.name):
            return "."
    return value


## Check exact field write sites and the related post-call read boundary.
## 核对字段写入位置，以及相关调用后读取边界。
#
#  @param case_id Fixed source-slice identifier.
#  @param report Public flow report converted to JSON-safe data.
#  @param expected Source-derived write and read expectations.
#  @return List of check records.
def check_case(case_id, report, expected):
    issues = []
    entry = expected["entry"]
    calls = [call for call in report["calls"]
             if call["caller"]["qualname"] == entry]
    if case_id == "blocks":
        write_call = next((call for call in calls
            if call["lineno"] == 3280 and call["callee_name"] == "self._consolidate_inplace"), None)
        if write_call is None:
            return ["missing call at pandas/core/internals.py:3280"]
        effects = [effect for effect in write_call["effects"]
                   if effect.get("kind") == "instance_field_write"]
        blocks = [effect for effect in effects if effect.get("field") == "blocks"]
        if len(blocks) != 1:
            issues.append("expected one blocks write effect")
        else:
            effect = blocks[0]
            if effect.get("evidence", [{}])[0].get("lineno") != 3826:
                issues.append("blocks write evidence must point to line 3826")
            guards = {(item.get("test", {}).get("lineno"), item.get("branch"))
                      for item in effect.get("conditions", [])}
            if guards != {(3279, True), (3825, True)}:
                issues.append("blocks write must retain both source guards")
            if effect.get("status") != "source_candidate":
                issues.append("dynamic method write must remain a source candidate")
            if effect.get("completion") != "unproven":
                issues.append("partial method summary must not claim write completion")
            if not any(item.get("kind") == "dynamic_method_dispatch_unproven"
                       and item.get("status") == "unproven"
                       for item in effect.get("non_write_alternatives", [])):
                issues.append("resolved method source must retain runtime dispatch boundary")
            if not any(item.get("kind") == "field_store_unproven"
                       for item in effect.get("non_write_alternatives", [])):
                issues.append("blocks write lost field storage boundary")
            if effect.get("preserved_value", {}).get("source") != (
                    "$instance-field:parameter:self:blocks"):
                issues.append("candidate write must identify the preserved old field")
            block_states = [item for item in write_call["effects"]
                            if item.get("kind") == "instance_field_state_candidates"
                            and item.get("field") == "blocks"]
            if len(block_states) != 1:
                issues.append("blocks write must have one candidate state record")
            else:
                state = block_states[0]
                candidates = state.get("candidate_values", [])
                if len(candidates) != 1 or candidates[0].get("write", {}).get(
                        "lineno") != 3826:
                    issues.append("blocks candidate state must identify the 3826 write")
                elif {(item.get("test", {}).get("lineno"), item.get("branch"))
                      for item in candidates[0].get("conditions", [])} != {
                          (3279, True), (3825, True)}:
                    issues.append("blocks candidate state lost either source guard")
                if state.get("completion") != "unproven":
                    issues.append("blocks candidate state must retain unproven completion")
            non_write_paths = {tuple((item.get("test", {}).get("lineno"),
                                      item.get("branch"))
                                     for item in alternative.get("guard_path", []))
                for alternative in effect.get("non_write_alternatives", [])
                if alternative.get("kind") == "guard_not_satisfied"}
            if non_write_paths != {((3279, False),), ((3279, True), (3825, False))}:
                issues.append("blocks guard complements are missing or imprecise")
            if not any(boundary.get("reason") == "instance_field_effect_partial"
                       for boundary in report["boundaries"]
                       if boundary.get("call_id") == write_call["id"]):
                issues.append("partial method summary boundary is missing")
            receiver = effect.get("receiver", {})
            if receiver.get("kind") != "parameter" or receiver.get("source") != "self":
                issues.append("blocks write must map to the apply receiver")
        dynamic = [call for call in calls
                   if call["lineno"] == 3324 and call["callee_name"] == "getattr"]
        if len(dynamic) != 1:
            issues.append("missing dynamic getattr call at line 3324")
        else:
            receiver_values = dynamic[0].get("receiver_sources", [])
            if not any(value.get("kind") == "instance_field"
                       and value.get("field") == "blocks"
                       and value.get("source") == "$instance-field:parameter:self:blocks"
                       and any(provenance.get("field") == "blocks"
                           and provenance.get("receiver", {}).get("kind") == "parameter"
                           and provenance.get("receiver", {}).get("source") == "self"
                           and provenance.get("write", {}).get("lineno") == 3826
                           and {(item.get("test", {}).get("lineno"), item.get("branch"))
                                for item in provenance.get("conditions", [])}
                               == {(3279, True), (3825, True)}
                           for provenance in value.get("container_provenance", []))
                       for value in receiver_values):
                issues.append("getattr receiver lacks the blocks write-to-element evidence")
            if not any(value.get("kind") == "instance_field"
                       and value.get("field") == "blocks"
                       and value.get("source") == "$instance-field:parameter:self:blocks"
                       and value.get("projection") == ["*"]
                       and value.get("instance_field_provenance", {}).get(
                           "read", {}).get("lineno") == 3309
                       and not any(provenance.get("write", {}).get("lineno") == 3826
                           for provenance in value.get("container_provenance", []))
                       for value in receiver_values):
                issues.append("pre-call field alternative was dropped")
            if dynamic[0].get("target_status") != "dynamic_attribute_lookup":
                issues.append("dynamic getattr target boundary was lost")
            if not any(boundary.get("reason") == "dynamic_attribute_lookup"
                       for boundary in report["boundaries"]
                       if boundary.get("call_id") == dynamic[0]["id"]):
                issues.append("dynamic getattr boundary evidence is missing")
    else:
        write_call = next((call for call in calls
            if call["lineno"] == 2270 and call["callee_name"] == "self.set_version"), None)
        if write_call is None:
            return ["missing call at pandas/io/pytables.py:2270"]
        writes = [effect for effect in write_call["effects"]
                  if effect.get("kind") == "instance_field_write"
                  and effect.get("field") == "version"]
        by_line = {effect.get("evidence", [{}])[0].get("lineno"): effect for effect in writes}
        if set(by_line) != {2241, 2243, 2245}:
            issues.append("version write sites must be exactly 2241, 2243 and 2245")
        expected_values = {2241: "tuple([int(x) for x in version.split('.')])",
                           2243: "self.version + (0,)", 2245: "(0, 0, 0)"}
        for line, expression in expected_values.items():
            effect = by_line.get(line)
            if effect and effect.get("value_expression", {}).get("source_text") != expression:
                issues.append("version write expression is wrong at line %d" % line)
            if effect and (effect.get("status") != "source_candidate"
                    or effect.get("completion") != "unproven"):
                issues.append("version write at line %d must remain unproven" % line)
            if effect and not any(item.get("kind") == "dynamic_method_dispatch_unproven"
                                  for item in effect.get("non_write_alternatives", [])):
                issues.append("version write at line %d lost runtime dispatch boundary" % line)
            if effect and not any(item.get("kind") == "field_store_unproven"
                                  for item in effect.get("non_write_alternatives", [])):
                issues.append("version write at line %d lost field storage boundary" % line)
            if effect and effect.get("preserved_value", {}).get("source") != (
                    "$instance-field:parameter:self:version"):
                issues.append("version write at line %d must identify its prior field" % line)
        if not any(boundary.get("reason") == "instance_field_effect_partial"
                   for boundary in report["boundaries"]
                   if boundary.get("call_id") == write_call["id"]):
            issues.append("partial set_version summary boundary is missing")
        if 2243 in by_line:
            guards = {(item.get("test", {}).get("lineno"), item.get("branch"))
                      for item in by_line[2243].get("conditions", [])}
            if guards != {(2242, True)}:
                issues.append("length-two normalization guard is missing")
            if by_line[2243].get("write_order") != 2 or not any(
                    item.get("lineno") == 2241
                    for item in by_line[2243].get("may_overwrite", [])):
                issues.append("normalization write must follow and overwrite the parsed tuple")
            non_write_paths = {
                tuple((item.get("test", {}).get("lineno"), item.get("branch"))
                      for item in alternative.get("guard_path", []))
                for alternative in by_line[2243].get("non_write_alternatives", [])
                if alternative.get("kind") == "guard_not_satisfied"}
            if non_write_paths != {((2242, False),)}:
                issues.append("length-two false path must preserve the parsed version")
            normalized_value = any(
                value.get("kind") == "derived_expression"
                and value.get("source") == expected_values[2241]
                and value.get("target_field") == "version"
                and any(item.get("lineno") == 2243
                    for item in value.get("evidence", []))
                and value.get("instance_field_provenance", {}).get(
                    "write", {}).get("lineno") == 2243
                and (value.get("instance_field_provenance", {}).get("prior") or {}).get(
                    "write", {}).get("lineno") == 2241
                for value in write_call.get("mutation_flows", []))
            if not normalized_value:
                issues.append("normalization must derive from the parsed version write")
        if 2241 in by_line and not any(
                value.get("kind") == "derived_expression"
                and value.get("source") == expected_values[2241]
                and value.get("target_field") == "version"
                and value.get("instance_field_provenance", {}).get(
                    "write", {}).get("lineno") == 2241
                for value in write_call.get("mutation_flows", [])):
            issues.append("parsed tuple expression must reach the version field")
        if 2245 in by_line and not any(
                value.get("kind") == "literal"
                and value.get("source") == "(0, 0, 0)"
                and value.get("target_field") == "version"
                and value.get("instance_field_provenance", {}).get(
                    "write", {}).get("lineno") == 2245
                for value in write_call.get("mutation_flows", [])):
            issues.append("exception fallback tuple must reach the version field")
        if 2245 in by_line and not any(context.get("kind") == "exception_handler"
                                      for context in by_line[2245].get("contexts", [])):
            issues.append("fallback write must be marked as an exception-handler write")
        if 2245 in by_line and (by_line[2245].get("write_order") != 3
                or {item.get("lineno") for item in by_line[2245].get("may_overwrite", [])}
                    != {2241, 2243}):
            issues.append("exception fallback must retain its later overwrite order")
        state_records = [effect for effect in write_call["effects"]
                         if effect.get("kind") == "instance_field_state_candidates"
                         and effect.get("field") == "version"]
        if len(state_records) != 1:
            issues.append("version write sites must form one candidate state record")
        else:
            state = state_records[0]
            candidates = {item.get("write", {}).get("lineno"): item
                          for item in state.get("candidate_values", [])}
            if set(candidates) != {2241, 2243, 2245}:
                issues.append("candidate state must distinguish all three version writes")
            if state.get("completion") != "unproven" or state.get("completeness") != "partial":
                issues.append("candidate state must retain partial completion boundary")
            required_uncertainties = {"dynamic_method_dispatch_unproven",
                                      "execution_completion_unproven",
                                      "method_effects_incomplete"}
            if not required_uncertainties <= set(state.get("uncertainty_reasons", [])):
                issues.append("candidate state must retain dispatch, completion and summary limits")
            if 2241 in candidates:
                overwrites = candidates[2241].get("later_same_route_writes", [])
                normalization = next((item for item in overwrites
                    if item.get("write", {}).get("lineno") == 2243), None)
                survives = {tuple((guard.get("test", {}).get("lineno"),
                                   guard.get("branch")) for guard in path)
                            for item in overwrites
                            for path in item.get("survives_when", [])}
                if normalization is None or survives != {((2242, False),)}:
                    issues.append("parsed version must survive when normalization guard is false")
            if 2243 in candidates and candidates[2243].get("conditions", [{}])[0].get(
                    "branch") is not True:
                issues.append("normalized version candidate must require the length-two guard")
            if 2245 in candidates and not any(context.get("kind") == "exception_handler"
                    for context in candidates[2245].get("contexts", [])):
                issues.append("fallback candidate must remain on the exception route")
        if any(effect.get("field") == "attrs.pandas_version" for effect in write_call["effects"]):
            issues.append("set_version effects must not absorb attrs.pandas_version")
        if write_call.get("result_sources"):
            issues.append("void set_version call must not gain a return-value source")
        if report.get("post_call_reads"):
            issues.append("Fixed.set_object_info must not invent a later version read")
    return issues


## Analyze one fixed slice through both public interfaces and check its field facts.
## 通过两个公开接口分析固定切片并核对字段事实。
#
#  @param case_id Fixed pandas source-slice identifier.
#  @param root Isolated source extraction directory.
#  @return Check record and public API/CLI equality result.
def replay_case(case_id, root):
    case = next(item for item in MANIFEST["pandas"]["cases"] if item["id"] == case_id)
    directory = root / case_id
    directory.mkdir()
    sources = materialize_slice(directory, case, ARCHIVE, MANIFEST["pandas"])
    entry = FunctionRef(module=case["module"], qualname=case["entry"])
    query = MANIFEST["query"]
    result = FlowAnalyzer(source_files=sources, import_roots=[directory]).analyze(entry, **query)
    command = [sys.executable, "-m", "pcresolve", "--value-flow", "--entry",
        case["module"] + ":" + case["entry"], "--depth", str(query["max_depth"]),
        "--max-functions", str(query["max_functions"]),
        "--max-call-contexts", str(query["max_call_contexts"]), "--json"]
    for source in sources:
        command.extend(("--source-file", str(source)))
    command.extend(("--import-root", str(directory)))
    cli = json.loads(subprocess.check_output(command, cwd=ROOT))
    public_api = result.to_dict()
    api = copy.deepcopy(public_api)
    if case_id == "fixed":
        tree = ast.parse(next(source.read_text(encoding="utf-8")
                              for source in sources if source.name == "pytables.py"))
        fixed = next(item for item in tree.body if isinstance(item, ast.ClassDef)
                     and item.name == "Fixed")
        method = next(item for item in fixed.body if isinstance(item, ast.FunctionDef)
                      and item.name == "set_object_info")
        call_line = next(item.lineno for item in ast.walk(method)
                         if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                         and item.func.attr == "set_version")
        api["post_call_reads"] = [node.lineno for node in ast.walk(method)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
            and node.attr == "version" and node.lineno > call_line]
    issues = check_case(case_id, api, case)
    if cli != public_api:
        issues.append("CLI JSON does not match FlowAnalyzer output")
    api = normalize_path_keys(normalize(api, directory), directory)
    issues.extend(check_case(case_id, api, case))
    return {"case": case_id, "entry": case["module"] + ":" + case["entry"],
            "passed": not issues, "issues": issues, "report": api}


## Replay both fixed cases from the verified release archive.
## 从已校验的发布源码包重放两个固定案例。
#
#  @return Reproducible manifest and both reports.
def evaluate(repeat=1):
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest != MANIFEST["pandas"]["archive_sha256"]:
        raise ValueError("pandas source archive SHA-256 mismatch")
    if repeat < 1:
        raise ValueError("repeat must be positive")
    runs = []
    for _ in range(repeat):
        with tempfile.TemporaryDirectory(prefix="pcresolve_stage4_") as directory:
            root = Path(directory)
            runs.append([replay_case(case_id, root) for case_id in CASES])
    stable = all(run == runs[0] for run in runs[1:])
    return {"archive_sha256": digest, "query": MANIFEST["query"],
            "repeat": repeat, "stable": stable, "cases": runs[0],
            "passed": stable and all(case["passed"] for case in runs[0])}


## Reject mutations that hide or invent a field effect or its evidence.
## 拒绝隐藏或虚构字段效果及其证据的变异报告。
#
#  @param report Correct evaluation report.
#  @return Diagnostics for each injected error.
def verify_injections(report):
    diagnostics = []
    for case_id in CASES:
        case_record = next(item for item in report["cases"] if item["case"] == case_id)
        expected = next(item for item in MANIFEST["pandas"]["cases"]
                        if item["id"] == case_id)
        original = case_record["report"]
        mutations = []
        if case_id == "blocks":
            write = next(call for call in original["calls"]
                         if call["lineno"] == 3280)
            effect = next(item for item in write["effects"]
                          if item.get("kind") == "instance_field_write"
                          and item.get("field") == "blocks")
            wrong_receiver = copy.deepcopy(original)
            target = next(item for item in wrong_receiver["calls"]
                          if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["receiver"]["source"] = "other"
            mutations.append(("wrong_receiver", wrong_receiver))
            wrong_field = copy.deepcopy(original)
            target = next(item for item in wrong_field["calls"] if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["field"] = "values"
            mutations.append(("wrong_field", wrong_field))
            wrong_write = copy.deepcopy(original)
            target = next(item for item in wrong_write["calls"] if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["evidence"][0]["lineno"] = 3827
            mutations.append(("wrong_write_site", wrong_write))
            missing_guard = copy.deepcopy(original)
            target = next(item for item in missing_guard["calls"] if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["conditions"].pop()
            mutations.append(("missing_guard", missing_guard))
            missing_guard_complements = copy.deepcopy(original)
            target = next(item for item in missing_guard_complements["calls"]
                          if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["non_write_alternatives"] = []
            mutations.append(("missing_guard_complements", missing_guard_complements))
            missing_store_boundary = copy.deepcopy(original)
            target = next(item for item in missing_store_boundary["calls"]
                          if item["lineno"] == 3280)
            field_effect = next(item for item in target["effects"]
                                if item.get("kind") == "instance_field_write"
                                and item.get("field") == "blocks")
            field_effect["non_write_alternatives"] = [item for item in
                field_effect["non_write_alternatives"]
                if item.get("kind") != "field_store_unproven"]
            mutations.append(("missing_field_storage_boundary", missing_store_boundary))
            false_completion = copy.deepcopy(original)
            target = next(item for item in false_completion["calls"] if item["lineno"] == 3280)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "blocks")["completion"] = "normal_return"
            mutations.append(("invented_write_completion", false_completion))
            missing_partial_boundary = copy.deepcopy(original)
            target = next(item for item in missing_partial_boundary["calls"]
                          if item["lineno"] == 3280)
            missing_partial_boundary["boundaries"] = [boundary for boundary in
                missing_partial_boundary["boundaries"]
                if not (boundary.get("call_id") == target["id"]
                        and boundary.get("reason") == "instance_field_effect_partial")]
            mutations.append(("missing_partial_boundary", missing_partial_boundary))
            missing_blocks_state = copy.deepcopy(original)
            target = next(item for item in missing_blocks_state["calls"]
                          if item["lineno"] == 3280)
            target["effects"] = [item for item in target["effects"]
                if not (item.get("kind") == "instance_field_state_candidates"
                        and item.get("field") == "blocks")]
            mutations.append(("missing_blocks_state_candidates", missing_blocks_state))
            wrong_read = copy.deepcopy(original)
            target = next(item for item in wrong_read["calls"]
                          if item["lineno"] == 3324 and item["callee_name"] == "getattr")
            target["receiver_sources"] = [dict(value,
                container_provenance=[]) if value.get("container_provenance")
                else value for value in target["receiver_sources"]]
            mutations.append(("missing_read_projection", wrong_read))
            missing_old = copy.deepcopy(original)
            target = next(item for item in missing_old["calls"]
                          if item["lineno"] == 3324 and item["callee_name"] == "getattr")
            target["receiver_sources"] = [value for value in target["receiver_sources"]
                if not (value.get("kind") == "instance_field"
                        and value.get("projection") == ["*"])]
            mutations.append(("missing_old_path", missing_old))
            wrong_target = copy.deepcopy(original)
            target = next(item for item in wrong_target["calls"]
                          if item["lineno"] == 3324 and item["callee_name"] == "getattr")
            target["target_status"] = "resolved"
            mutations.append(("invented_dynamic_target", wrong_target))
        else:
            missing_normalization_path = copy.deepcopy(original)
            target = next(item for item in missing_normalization_path["calls"]
                          if item["lineno"] == 2270)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "version"
                 and item.get("evidence", [{}])[0].get("lineno") == 2243)[
                     "non_write_alternatives"] = []
            mutations.append(("missing_normalization_false_path", missing_normalization_path))
            missing_prior_value = copy.deepcopy(original)
            target = next(item for item in missing_prior_value["calls"]
                          if item["lineno"] == 2270)
            normalized_flow = next(item for item in target["mutation_flows"]
                if item.get("target_field") == "version"
                and item.get("kind") == "derived_expression"
                and item.get("instance_field_provenance", {}).get(
                    "write", {}).get("lineno") == 2243)
            normalized_flow["instance_field_provenance"].pop("prior", None)
            mutations.append(("missing_parsed_version_to_normalization_flow",
                              missing_prior_value))
            missing_final_state_guard = copy.deepcopy(original)
            target = next(item for item in missing_final_state_guard["calls"]
                          if item["lineno"] == 2270)
            state = next(item for item in target["effects"]
                if item.get("kind") == "instance_field_state_candidates"
                and item.get("field") == "version")
            parsed = next(item for item in state["candidate_values"]
                          if item.get("write", {}).get("lineno") == 2241)
            next(item for item in parsed["later_same_route_writes"]
                 if item.get("write", {}).get("lineno") == 2243)["survives_when"] = []
            mutations.append(("missing_parsed_value_survival_guard",
                              missing_final_state_guard))
            missing_state_boundary = copy.deepcopy(original)
            target = next(item for item in missing_state_boundary["calls"]
                          if item["lineno"] == 2270)
            state = next(item for item in target["effects"]
                if item.get("kind") == "instance_field_state_candidates"
                and item.get("field") == "version")
            state["uncertainty_reasons"] = []
            mutations.append(("missing_candidate_state_boundaries", missing_state_boundary))
            false_completion = copy.deepcopy(original)
            target = next(item for item in false_completion["calls"] if item["lineno"] == 2270)
            next(item for item in target["effects"]
                 if item.get("kind") == "instance_field_write"
                 and item.get("field") == "version")["completion"] = "normal_return"
            mutations.append(("invented_version_completion", false_completion))
            missing_dispatch_boundary = copy.deepcopy(original)
            target = next(item for item in missing_dispatch_boundary["calls"]
                          if item["lineno"] == 2270)
            version_effect = next(item for item in target["effects"]
                if item.get("kind") == "instance_field_write"
                and item.get("field") == "version")
            version_effect["non_write_alternatives"] = [item for item in
                version_effect["non_write_alternatives"]
                if item.get("kind") != "dynamic_method_dispatch_unproven"]
            mutations.append(("missing_runtime_dispatch_boundary", missing_dispatch_boundary))
            missing_store_boundary = copy.deepcopy(original)
            target = next(item for item in missing_store_boundary["calls"]
                          if item["lineno"] == 2270)
            field_effect = next(item for item in target["effects"]
                                if item.get("kind") == "instance_field_write"
                                and item.get("field") == "version")
            field_effect["non_write_alternatives"] = [item for item in
                field_effect["non_write_alternatives"]
                if item.get("kind") != "field_store_unproven"]
            mutations.append(("missing_field_storage_boundary", missing_store_boundary))
            missing_partial_boundary = copy.deepcopy(original)
            target = next(item for item in missing_partial_boundary["calls"]
                          if item["lineno"] == 2270)
            missing_partial_boundary["boundaries"] = [boundary for boundary in
                missing_partial_boundary["boundaries"]
                if not (boundary.get("call_id") == target["id"]
                        and boundary.get("reason") == "instance_field_effect_partial")]
            mutations.append(("missing_partial_boundary", missing_partial_boundary))
            fake_read = copy.deepcopy(original)
            fake_read["post_call_reads"] = [2271]
            mutations.append(("invented_later_read", fake_read))
        for name, corrupted in mutations:
            issues = check_case(case_id, corrupted, expected)
            diagnostics.append({"case": case_id, "injection": name,
                                "detected": bool(issues), "issues": issues})
    return diagnostics


## Check exception-path reads against the fixed fixture's source-level cases.
## 对照固定样例的源码检查异常路径读取。
#
#  @param summaries Public function summaries indexed by fixture method name.
#  @return Diagnostics describing missing or invented field sources.
def check_exception_summaries(summaries):
    expectations = {
        "read_after_caught_write": ({"value"}, True),
        "read_after_caught_early_raise": (set(), False),
        "read_after_two_caught_writes": ({"first", "second"}, True),
        "read_other_after_caught_write": (set(), False),
        "read_after_tuple_assignment_exception": ({"value"}, True),
        "read_after_guard_exception": ({"value"}, True),
        "read_after_for_iterator_exception": ({"value"}, True),
        "read_after_while_guard_exception": ({"value"}, True),
        "read_after_earlier_argument_raises": (set(), False),
        "assign_after_earlier_argument_raises": (set(), False),
        "guard_after_earlier_argument_raises": (set(), False),
        "read_after_second_argument_raises": (set(), False),
        "read_after_runtime_argument_raises": (set(), False),
        "read_after_bare_argument_raises": (set(), False),
    }
    issues = []
    for name, (expected, needs_candidate) in expectations.items():
        values = summaries[name]["returns"]
        sources = {value.get("source") for value in values
                   if value.get("kind") == "parameter"
                   and value.get("source") in ("value", "first", "second")}
        if sources != expected:
            issues.append({"case": name, "issue": "wrong_reaching_sources"})
        if needs_candidate and not any(value.get("exception_write_candidate")
                                       and value.get("value_incomplete")
                                       for value in values):
            issues.append({"case": name, "issue": "missing_exception_uncertainty"})
    return issues


## Run the isolated stage 4 replay and optionally save its JSON report.
## 执行隔离的阶段 4 重放，并可选保存 JSON 报告。
#
#  @return Process status.
def main():
    parser = argparse.ArgumentParser(description="Replay stage 4 pandas field effects")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args()
    report = evaluate(args.repeat)
    injections = verify_injections(report)
    report["injections"] = injections
    report["injections_passed"] = all(item["detected"] for item in injections)
    report["passed"] = report["passed"] and report["injections_passed"]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({"passed": report["passed"],
        "cases": [(case["case"], case["passed"], case["issues"])
                  for case in report["cases"]]}, ensure_ascii=False))
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
