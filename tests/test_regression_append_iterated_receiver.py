import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "append_iterated_receiver_ownership")


def test_import_backed_append_item_owner_survives_iteration():
    result = analyze_project(FIXTURE)
    calls = [
        call
        for file_result in result.files
        for call in file_result.api_calls
        if call.expression == "worker.join()"
    ]
    assert len(calls) == 2
    assert calls[0].lineno == 12
    assert calls[0].top_library == "multiprocessing"


def test_conflicting_append_item_owner_is_not_propagated():
    result = analyze_project(FIXTURE)
    calls = [
        call
        for file_result in result.files
        for call in file_result.api_calls
        if call.expression == "worker.join()"
    ]
    assert len(calls) == 2
    assert calls[1].lineno == 20
    assert calls[1].top_library != "multiprocessing"
