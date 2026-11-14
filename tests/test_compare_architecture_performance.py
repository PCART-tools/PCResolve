## @package tests.test_compare_architecture_performance
#  Performance comparison aggregates every paired sample for a size.

import importlib.util
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).parents[1] / 'scripts' /
         'compare_architecture_performance.py')
SPEC = importlib.util.spec_from_file_location('architecture_performance', SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_medians_aggregates_paired_samples_for_same_size():
    report = {'samples': [
        {'modules': 101, 'outputs_equal': True, 'runs': [
            {'peak_rss_bytes': 100, 'rows': [
                {'variant': 'flow_cold', 'wall': 1.0}] }]},
        {'modules': 101, 'outputs_equal': True, 'runs': [
            {'peak_rss_bytes': 200, 'rows': [
                {'variant': 'flow_cold', 'wall': 3.0}] }]},
    ]}

    result = RUNNER.medians(report)[101]

    assert result == {
        'wall': {'flow_cold': 2.0},
        'peak_rss_bytes': 150,
        'outputs_equal': True,
    }


def test_paired_delta_uses_each_baseline_candidate_sample_pair():
    delta, samples = RUNNER.paired_median_delta(
        [0.404, 0.223, 0.230, 0.247, 0.326],
        [0.384, 0.260, 0.330, 0.328, 0.251])

    assert samples == pytest.approx([-0.020, 0.037, 0.100, 0.081, -0.075])
    assert delta == pytest.approx(0.037)
    assert delta <= 0.050
