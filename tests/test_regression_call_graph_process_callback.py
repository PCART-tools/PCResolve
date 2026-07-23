## @package tests.test_regression_call_graph_process_callback
#  Regression coverage for multiprocessing.Process callback argument flow.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_process_callback")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def _call(calls, expression):
    matches = [call for call in calls if call.expression == expression]
    assert len(matches) == 1, (expression, [c.expression for c in calls])
    return matches[0]


def test_process_callback_queue_arguments_reach_worker(calls):
    assert _call(calls, "jobs_queue.get()").top_library == "multiprocessing"
    assert _call(calls, "output_queue.put((index, options))").top_library == (
        "multiprocessing")


def test_process_constructor_remains_import_backed(calls):
    assert _call(calls, "Process(target=worker, args=('options', 0, jobs_queue, output_queue))").top_library == (
        "multiprocessing")
