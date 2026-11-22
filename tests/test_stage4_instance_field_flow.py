import ast
import copy
import runpy
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.facts.effect_facts import instance_field_write_sites
from scripts.evaluate_stage4_instance_fields import (
    ARCHIVE, check_exception_summaries, evaluate, verify_injections,
)


FIXTURE = Path(__file__).parent / "fixtures" / "stage4_instance_field_flow" / "main.py"


def _summary(name):
    entry = FunctionRef(module="main", qualname="Receiver." + name)
    result = FlowAnalyzer(source_files=[FIXTURE], import_roots=[FIXTURE.parent]).analyze(
        entry, max_depth=2)
    function = next(item for item in result.to_dict()["functions"]
                    if item["function"]["qualname"] == entry.qualname)
    calls = result.find_calls(caller=entry)
    return function, [result.describe_call_flow(call.id) for call in calls]


@pytest.fixture(scope="module")
def pandas_reports():
    if not ARCHIVE.is_file():
        pytest.skip("Optional pandas 0.21.0 source archive is unavailable")
    return evaluate(repeat=2)


def test_same_receiver_field_write_flows_to_later_read():
    function, calls = _summary("read_after_write")
    writes = [call for call in calls if call["callee_name"] == "self.set_payload"]
    assert len(writes) == 1
    assert any(effect.get("kind") == "instance_field_write"
               and effect.get("field") == "payload"
               for effect in writes[0]["effects"])
    assert any(value.get("source") == "value" for value in function["returns"])


def test_field_assignment_reports_unmodeled_descriptor_effects():
    entry = FunctionRef(module="main", qualname="Receiver.set_payload")
    result = FlowAnalyzer(source_files=[FIXTURE], import_roots=[FIXTURE.parent]).analyze(entry)
    assert any(boundary.get("reason") == "unsupported_assignment"
               and boundary.get("partial_support") == "instance_field_state"
               and boundary.get("evidence", {}).get("source_text") == "self.payload = value"
               for boundary in result.boundaries)


def test_unknown_receiver_descriptor_may_leave_old_field_value():
    namespace = runpy.run_path(str(FIXTURE))
    instance = namespace["IgnoredWrite"]()
    namespace["write_payload"](instance, "new")
    assert instance.payload == "old"
    result, calls = _summary("unknown_receiver_write")
    assert any(value.get("kind") == "instance_field"
               and value.get("field") == "payload" for value in result["returns"])
    write, = [call for call in calls if call["callee_name"] == "write_payload"]
    effect, = [item for item in write["effects"]
               if item.get("kind") == "instance_field_write"]
    assert effect["status"] == "source_candidate"


def test_direct_write_on_unknown_receiver_keeps_old_field_candidate():
    result, _ = _summary("direct_write_read")
    assert any(value.get("kind") == "instance_field"
               and value.get("field") == "payload" for value in result["returns"])
    assert any(value.get("source") == "value" for value in result["returns"])


def test_proven_plain_receiver_overwrite_discards_previous_value():
    namespace = runpy.run_path(str(FIXTURE))
    assert namespace["Receiver"]().fresh_plain_overwrite("first", "second") == "second"
    result, calls = _summary("fresh_plain_overwrite")
    writes = [call for call in calls if call["callee_name"] == "write_payload"]
    assert len(writes) == 2
    assert all(any(effect.get("kind") == "instance_field_write"
                   and effect.get("status") == "exact"
                   and effect.get("store_proof", {}).get("kind")
                   == "fresh_plain_receiver_straight_line" for effect in call["effects"])
               for call in writes)
    sources = {value.get("source") for value in result["returns"]
               if value.get("kind") == "parameter"}
    assert sources == {"second"}


@pytest.mark.parametrize("entry", ["fresh_descriptor_write", "fresh_custom_store_write",
                                  "fresh_escaped_write"])
def test_fresh_field_store_proof_rejects_open_cases(entry):
    _, calls = _summary(entry)
    write, = [call for call in calls if call["callee_name"] == "write_payload"]
    effects = [effect for effect in write["effects"]
               if effect.get("kind") == "instance_field_write"]
    assert not any(effect.get("status") == "exact" for effect in effects)


def test_fresh_field_store_proof_rejects_builtin_descriptor():
    _, calls = _summary("fresh_special_field_write")
    write, = [call for call in calls if call["callee_name"] == "write_class"]
    effects = [effect for effect in write["effects"]
               if effect.get("kind") == "instance_field_write"]
    assert effects and all(effect.get("status") != "exact" for effect in effects)


def test_fresh_field_store_proof_checks_actual_receiver():
    result, calls = _summary("fresh_mismatched_receiver")
    write, = [call for call in calls if call["callee_name"] == "write_second"]
    effects = [effect for effect in write["effects"]
               if effect.get("kind") == "instance_field_write"]
    assert effects and all(effect.get("status") != "exact" for effect in effects)
    assert any(value.get("kind") == "instance_field"
               and value.get("field") == "payload" for value in result["returns"])


def test_resolved_class_method_does_not_prove_runtime_dispatch_or_completion():
    function, calls = _summary("read_after_write")
    write, = [call for call in calls if call["callee_name"] == "self.set_payload"]
    effect, = [item for item in write["effects"]
               if item.get("kind") == "instance_field_write"]

    assert write["target_status"] == "instance_method"
    assert effect["status"] == "source_candidate"
    assert effect["completion"] == "unproven"
    assert any(item.get("kind") == "dynamic_method_dispatch_unproven"
               for item in effect["non_write_alternatives"])
    assert any(value.get("source") == "value" for value in function["returns"])
    assert any(value.get("kind") == "instance_field"
               and value.get("field") == "payload" for value in function["returns"])


def test_conditional_field_write_keeps_old_value_on_unwritten_path():
    function, calls = _summary("conditional_write")
    writes = [call for call in calls if call["callee_name"] == "self.set_payload"]
    assert len(writes) == 1
    effect, = [item for item in writes[0]["effects"]
               if item.get("kind") == "instance_field_write"]
    assert effect["conditions"][-1]["branch"] is True
    assert effect["conditions"][-1]["test"]["source_text"] == "enabled"
    assert any(value.get("source") == "value" for value in function["returns"])
    assert any(value.get("kind") == "instance_field" and value.get("field") == "payload"
               for value in function["returns"])


def test_overwrite_and_read_order_select_the_reaching_field_write():
    overwritten, calls = _summary("exact_overwrite")
    writes = [call for call in calls if call["callee_name"] == "write_payload"]
    assert len(writes) == 2
    def keeps_both_candidates(summary):
        sources = {value.get("source") for value in summary["returns"]
                   if value.get("kind") == "parameter"}
        return sources == {"first", "second"}

    assert keeps_both_candidates(overwritten)
    assert all(effect["status"] == "source_candidate"
               for call in writes for effect in call["effects"]
               if effect.get("kind") == "instance_field_write")
    corrupted = copy.deepcopy(overwritten)
    corrupted["returns"] = [value for value in corrupted["returns"]
                            if value.get("source") != "first"]
    assert not keeps_both_candidates(corrupted)

    before, _ = _summary("read_before_write")
    assert not any(value.get("source") == "value" for value in before["returns"])

    dynamic, calls = _summary("overwrite")
    dynamic_writes = [call for call in calls if call["callee_name"] == "self.set_payload"]
    assert len(dynamic_writes) == 2
    assert all(effect["status"] == "source_candidate"
               for call in dynamic_writes for effect in call["effects"]
               if effect.get("kind") == "instance_field_write")
    assert {value.get("source") for value in dynamic["returns"]
            if value.get("kind") == "parameter"} == {"first", "second"}


def test_field_and_receiver_identity_prevent_cross_object_flow():
    wrong_field, _ = _summary("write_other_read_payload")
    other_receiver, _ = _summary("write_payload_read_other")
    assert not any(value.get("source") == "value"
                   for value in wrong_field["returns"])
    assert not any(value.get("source") == "value"
                   for value in other_receiver["returns"])

    alias, _ = _summary("alias_write")
    assert any(value.get("source") == "value" for value in alias["returns"])

    other, _ = _summary("other_object_read")
    assert not any(value.get("source") == "value" for value in other["returns"])

    other_field, _ = _summary("exact_other_field_write")
    assert not any(value.get("source") == "value" for value in other_field["returns"])


def test_method_internal_guard_is_preserved_on_field_write():
    function, calls = _summary("internal_conditional_write")
    write, = [call for call in calls if call["callee_name"] == "write_when"]
    effect, = [item for item in write["effects"]
               if item.get("kind") == "instance_field_write"]
    assert effect["status"] == "source_candidate"
    assert effect["conditions"][-1]["branch"] is True
    assert effect["conditions"][-1]["test"]["source_text"] == "enabled"
    assert any(value.get("source") == "value" for value in function["returns"])
    assert any(value.get("kind") == "instance_field" for value in function["returns"])


def test_exception_order_does_not_invent_a_write_after_raise():
    source = """\
def before(receiver, value, fail):
    if fail:
        raise ValueError()
    receiver.payload = value
def after(receiver, value):
    receiver.payload = value
    raise ValueError()
    receiver.other = value
"""
    before, after = ast.parse(source).body
    before_write, = instance_field_write_sites(before)
    assert before_write.attribute == "payload"
    assert len(before_write.conditions) == 1
    assert before_write.conditions[0][1] is False
    after_writes = instance_field_write_sites(after)
    assert [effect.attribute for effect in after_writes] == ["payload"]


def test_caught_exception_read_uses_only_writes_completed_before_raise():
    after_write, calls = _summary("read_after_caught_write")
    write_call, = [call for call in calls if call["callee_name"] == "self.write_then_raise"]
    write_effect, = [item for item in write_call["effects"]
                     if item.get("kind") == "instance_field_write"]
    assert write_effect["evidence"][0]["source_text"] == "self.payload = value"
    assert any(value.get("source") == "value"
               and value.get("kind") == "parameter"
               and value.get("value_incomplete")
               and value.get("exception_write_candidate")
               and value.get("instance_field_provenance", {}).get(
                   "write", {}).get("source_text") == "self.payload = value"
               for value in after_write["returns"])
    assert any(value.get("kind") == "instance_field"
               and value.get("field") == "payload"
               for value in after_write["returns"])

    before_write, calls = _summary("read_after_caught_early_raise")
    early_call, = [call for call in calls if call["callee_name"] == "self.raise_then_write"]
    assert not any(item.get("kind") == "instance_field_write"
                   for item in early_call["effects"])
    assert not any(value.get("source") == "value" for value in before_write["returns"])


def test_caught_exception_keeps_prior_write_and_receiver_identity():
    result, _ = _summary("read_after_two_caught_writes")
    sources = {value.get("source") for value in result["returns"]
               if value.get("kind") == "parameter"}
    assert sources == {"first", "second"}
    other, _ = _summary("read_other_after_caught_write")
    assert not any(value.get("source") == "value" for value in other["returns"])


def test_caught_exception_from_tuple_assignment_keeps_possible_write():
    result, _ = _summary("read_after_tuple_assignment_exception")
    assert any(value.get("source") == "value"
               and value.get("exception_write_candidate")
               for value in result["returns"])


def test_caught_exception_from_guard_keeps_possible_write():
    result, _ = _summary("read_after_guard_exception")
    assert any(value.get("source") == "value"
               and value.get("exception_write_candidate")
               for value in result["returns"])


@pytest.mark.parametrize("entry", ["read_after_earlier_argument_raises",
                                  "assign_after_earlier_argument_raises",
                                  "guard_after_earlier_argument_raises",
                                  "read_after_second_argument_raises",
                                  "read_after_runtime_argument_raises",
                                  "read_after_bare_argument_raises"])
def test_later_argument_write_is_unreachable_after_definite_raise(entry):
    result, _ = _summary(entry)
    assert not any(value.get("source") == "value" for value in result["returns"])


def test_later_argument_write_remains_possible_after_conditional_raise():
    result, _ = _summary("read_after_maybe_raising_argument")
    assert any(value.get("source") == "value" for value in result["returns"])


@pytest.mark.parametrize("entry", ["read_after_for_iterator_exception",
                                  "read_after_while_guard_exception"])
def test_caught_exception_from_loop_head_keeps_possible_write(entry):
    result, _ = _summary(entry)
    assert any(value.get("source") == "value"
               and value.get("exception_write_candidate")
               for value in result["returns"])


def test_exception_comparator_rejects_source_and_uncertainty_injections():
    names = ["read_after_caught_write", "read_after_caught_early_raise",
             "read_after_two_caught_writes", "read_other_after_caught_write",
             "read_after_tuple_assignment_exception", "read_after_guard_exception",
             "read_after_for_iterator_exception", "read_after_while_guard_exception",
             "read_after_earlier_argument_raises", "assign_after_earlier_argument_raises",
             "guard_after_earlier_argument_raises", "read_after_second_argument_raises",
             "read_after_runtime_argument_raises", "read_after_bare_argument_raises"]
    summaries = {name: _summary(name)[0] for name in names}
    assert not check_exception_summaries(summaries)
    corruptions = []
    missing = copy.deepcopy(summaries)
    missing["read_after_caught_write"]["returns"] = []
    corruptions.append((missing, "read_after_caught_write"))
    invented = copy.deepcopy(summaries)
    invented["read_after_caught_early_raise"]["returns"].append(
        {"kind": "parameter", "source": "value"})
    corruptions.append((invented, "read_after_caught_early_raise"))
    later_argument = copy.deepcopy(summaries)
    later_argument["read_after_earlier_argument_raises"]["returns"].append(
        {"kind": "parameter", "source": "value", "exception_write_candidate": True})
    corruptions.append((later_argument, "read_after_earlier_argument_raises"))
    wrong_receiver = copy.deepcopy(summaries)
    wrong_receiver["read_other_after_caught_write"]["returns"].append(
        {"kind": "parameter", "source": "value"})
    corruptions.append((wrong_receiver, "read_other_after_caught_write"))
    lost_prior = copy.deepcopy(summaries)
    lost_prior["read_after_two_caught_writes"]["returns"] = [
        value for value in lost_prior["read_after_two_caught_writes"]["returns"]
        if value.get("source") != "first"]
    corruptions.append((lost_prior, "read_after_two_caught_writes"))
    certainty = copy.deepcopy(summaries)
    for value in certainty["read_after_caught_write"]["returns"]:
        value.pop("value_incomplete", None)
    corruptions.append((certainty, "read_after_caught_write"))
    for report, name in corruptions:
        assert any(issue["case"] == name for issue in check_exception_summaries(report))


def test_fixed_pandas_field_cases_match_public_api_and_cli(pandas_reports):
    assert pandas_reports["passed"]
    assert pandas_reports["stable"]
    assert [case["case"] for case in pandas_reports["cases"]] == ["blocks", "fixed"]


def test_field_report_comparator_detects_precision_errors(pandas_reports):
    diagnostics = verify_injections(pandas_reports)
    assert len(diagnostics) == 21
    assert all(item["detected"] for item in diagnostics)
