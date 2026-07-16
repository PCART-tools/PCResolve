## @package tests.test_regression_giantpop_ownership
#  Regression coverage for ownership boundaries found in giantpopflucts.

import os

from pcresolve import analyze_project


FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "fixtures", "giantpop_ownership")


def _call(result, expression, lineno=None):
    matches = [
        call for call in result.all_api_calls
        if call.expression == expression
        and (lineno is None or call.lineno == lineno)
    ]
    assert len(matches) == 1, (
        "Expected one call for %r at line %r, got %d"
        % (expression, lineno, len(matches)))
    return matches[0]


def test_local_lambda_keeps_callable_identity_and_result_owner():
    for scope_model in ("v1", "v2"):
        result = analyze_project(FIXTURE_DIR, scope_model=scope_model)

        assert _call(
            result, "transform(np.array([1.0]))").top_library == "local"
        assert _call(result, "transformed.flatten()").top_library == "numpy"


def test_function_local_builtin_containers_are_python_owned():
    result = analyze_project(FIXTURE_DIR)

    assert _call(
        result, "items.append(1)", 12).top_library == "python"
    assert _call(
        result, "grouped[key].append(2)",
        16).top_library == "python"
    assert _call(result, "typed_items.append(3)").top_library == "python"


def test_local_class_method_is_not_promoted_by_method_name():
    result = analyze_project(FIXTURE_DIR)

    assert _call(
        result, "items.append(1)", 26).top_library == "local"


def test_builtin_instance_attributes_keep_concrete_container_owner():
    result = analyze_project(FIXTURE_DIR)

    assert _call(result, "self.items.append(1)", 51).top_library == "python"
    assert _call(
        result, "self.grouped[key].append(2)", 52).top_library == "python"
    assert _call(result, "self.items.append(1)", 60).top_library == "local"


def test_annotated_builtin_instance_attribute_is_python_owned():
    result = analyze_project(FIXTURE_DIR)

    assert _call(result, "self.typed.append(4)").top_library == "python"


def test_seaborn_axes_and_patch_results_are_matplotlib_owned():
    result = analyze_project(FIXTURE_DIR)

    assert _call(
        result, "axes.get_legend_handles_labels()").top_library == "matplotlib"
    assert _call(result, "patch.get_x()").top_library == "matplotlib"
    assert _call(
        result,
        "strip_axes.get_legend_handles_labels()").top_library == "matplotlib"
    assert _call(
        result,
        "swarm_axes.get_legend_handles_labels()").top_library == "matplotlib"
