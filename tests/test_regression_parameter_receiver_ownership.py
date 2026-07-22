## @package tests.test_regression_parameter_receiver_ownership
#  Regression tests for conservative parameter receiver ownership.

import os

from pcresolve import analyze_project


_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "parameter_receiver_ownership")


def _calls():
    result = analyze_project(_FIXTURE)
    return result.all_api_calls


def _calls_named(func_name):
    return [call for call in _calls() if call.func_name == func_name]


def _call(func_name, expression=None):
    matches = [call for call in _calls() if call.func_name == func_name]
    if expression is not None:
        matches = [
            call for call in matches if call.expression == expression
        ]
    assert len(matches) == 1, (func_name, matches)
    return matches[0]


def test_unconstrained_parameter_method_is_unknown():
    call = _call("out.write")
    assert call.top_library == "unknown"


def test_unique_local_call_site_preserves_local_owner():
    call = _call("sink.write", "sink.write('local')")
    assert call.top_library == "local"


def test_unique_library_call_site_propagates_receiver_owner():
    call = _call("decoder.decode", "decoder.decode('{}')")
    assert call.top_library == "json"


def test_conflicting_call_site_owners_are_unknown():
    call = _call("stream.close")
    assert call.top_library == "unknown"


def test_same_named_method_on_another_class_does_not_supply_arguments():
    call = _call(
        "decoder.decode", "decoder.decode('uncalled duplicate method')")
    assert call.top_library == "unknown"


def test_parameter_reassignment_uses_current_local_binding():
    call = _call("value.write")
    assert call.top_library == "local"


def test_unconstrained_parameter_items_are_unknown():
    calls = _calls()
    derived = [
        call for call in calls
        if call.expression in (
            "first.to('device')", "second.to('device')")
    ]
    assert len(derived) == 2
    assert all(call.top_library == "unknown" for call in derived)


def test_forward_local_call_site_preserves_local_owner():
    matches = _calls_named("sink.write")
    assert {candidate.top_library for candidate in matches} == {"local"}


def test_cross_file_call_site_propagates_receiver_owner():
    call = _call("decoder.decode", "decoder.decode('cross-file')")
    assert call.top_library == "json"


def test_self_method_identity_is_unchanged():
    calls = _calls()
    local_calls = [
        call for call in calls if call.expression == "LocalSink()"
    ]
    assert local_calls
    assert all(call.top_library == "local" for call in local_calls)


def test_constructor_argument_propagates_to_init_parameter():
    call = _call("world.add_bodies")
    assert call.top_library == "local"


def test_local_constructor_attribute_chain_preserves_local_owner():
    call = _call("holder.payload.ping")
    assert call.top_library == "local"


def test_parameter_attribute_alias_preserves_attribute_path():
    call = _call("payload.ping")
    assert call.top_library == "local"


def test_imported_local_constructor_attribute_propagates_owner():
    call = _call("decoder.decode", "decoder.decode('cross-file attribute')")
    assert call.top_library == "json"


def test_imported_local_constructor_parameter_preserves_local_owner():
    call = _call("receiver.ping")
    assert call.top_library == "local"


def test_parameter_attribute_alias_resolves_library_receiver():
    calls = _calls_named("world.CreateDynamicBody")
    assert len(calls) == 2
    assert all(call.top_library == "Box2D" for call in calls)


def test_explicit_method_result_contract_propagates_receiver_owner():
    call = _call("body.CreateFixture")
    assert call.top_library == "Box2D"


def test_method_result_contract_survives_self_attribute_binding():
    call = _call("self.body.CreateFixture")
    assert call.top_library == "Box2D"


def test_static_callback_table_propagates_argument_owner():
    call = _call("worker.expand")
    assert call.top_library == "local"


def test_pytest_parametrize_values_propagate_parameter_owner():
    call = _call("model.fit")
    assert call.top_library == "local"
