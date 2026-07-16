## @package tests.test_regression_source_contamination
#  1.0.5 P0: container methods on local builtin receivers must not
#  inherit argument/element provenance as ApiCall.top_library.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_source_contamination")


def _calls_by_name(result, suffix):
    return [c for c in result.all_api_calls
            if c.func_name.endswith(suffix)]


# ── list ──────────────────────────────────────────────────────────

def test_list_append_not_contaminated_to_numpy():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".append"):
        assert c.top_library != "numpy", \
            f"list.append must not be numpy, got {c.top_library}"


def test_list_append_is_python():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".append"):
        assert c.top_library == "python", \
            f"list.append should be python, got {c.top_library}"


def test_list_extend_not_contaminated_to_numpy():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".extend"):
        assert c.top_library != "numpy", \
            f"list.extend must not be numpy, got {c.top_library}"
        assert c.top_library == "python", \
            f"list.extend should be python, got {c.top_library}"


# ── dict ──────────────────────────────────────────────────────────

def test_dict_update_not_contaminated_to_pandas():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".update"):
        if "df.update" in c.func_name:
            continue  # negative: df.update SHOULD be pandas
        assert c.top_library == "python", \
            f"dict.update should be python, got {c.top_library}"


def test_dict_get_not_contaminated():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".get"):
        if "df.get" in c.func_name or "dict.get" in c.func_name:
            continue
        assert c.top_library == "python", \
            f"dict.get should be python, got {c.top_library}"


# ── set ───────────────────────────────────────────────────────────

def test_set_add_not_contaminated_to_numpy():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".add"):
        if "set.add" in c.func_name or "df.add" in c.func_name:
            continue
        assert c.top_library == "python", \
            f"set.add should be python, got {c.top_library}"


# ── tuple ─────────────────────────────────────────────────────────

def test_tuple_count_not_contaminated():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".count"):
        if "df.count" in c.func_name:
            continue
        assert c.top_library == "python", \
            f"tuple.count should be python, got {c.top_library}"


# ── iteration contamination ───────────────────────────────────────

def test_iteration_element_not_contaminate_list_append():
    r = analyze_project(_FIXTURE)
    words_appends = [c for c in r.all_api_calls
                     if "words.append" in c.func_name]
    for c in words_appends:
        assert c.top_library == "python", \
            f"words.append should be python, got {c.top_library}"


# ── negative: third-party receiver must still work ─────────────────

def test_numpy_reshape_still_numpy():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".reshape"):
        assert c.top_library == "numpy", \
            f"arr2.reshape must be numpy, got {c.top_library}"


def test_pandas_update_still_pandas():
    r = analyze_project(_FIXTURE)
    for c in _calls_by_name(r, ".update"):
        if "df.update" in c.func_name:
            assert c.top_library == "pandas", \
                f"df.update must be pandas, got {c.top_library}"
