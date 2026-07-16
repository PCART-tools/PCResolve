"""Test builtin function and container method classification (1.0.5 P0/P1)."""

import pytest
from pcresolve.cross_file import analyze_project
import os

FIXTURE = os.path.join(os.path.dirname(__file__),
                       "fixtures", "builtin_classification")


def _find_call(calls, expression_prefix):
    for c in calls:
        if c.expression.startswith(expression_prefix):
            return c
    return None


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE, scope_model="v2")


# --- P0: Builtin functions ---

def test_getattr_is_python(result):
    c = _find_call(result.all_api_calls, "getattr(")
    assert c is not None, "getattr call not found"
    assert c.top_library == "python", \
        f"getattr() should be python, got {c.top_library}"


def test_hasattr_is_python(result):
    c = _find_call(result.all_api_calls, "hasattr(")
    assert c is not None, "hasattr call not found"
    assert c.top_library == "python", \
        f"hasattr() should be python, got {c.top_library}"


def test_isinstance_is_python(result):
    c = _find_call(result.all_api_calls, "isinstance(")
    assert c is not None, "isinstance call not found"
    assert c.top_library == "python", \
        f"isinstance() should be python, got {c.top_library}"


# --- P1: List methods on local list ---

def test_list_append_is_python(result):
    c = _find_call(result.all_api_calls, "items.append(")
    assert c is not None, "items.append call not found"
    assert c.top_library == "python", \
        f"list.append should be python, got {c.top_library}"


def test_list_extend_is_python(result):
    c = _find_call(result.all_api_calls, "items.extend(")
    assert c is not None, "items.extend call not found"
    assert c.top_library == "python", \
        f"list.extend should be python, got {c.top_library}"


def test_list_index_is_python(result):
    c = _find_call(result.all_api_calls, "items.index(")
    assert c is not None, "items.index call not found"
    assert c.top_library == "python", \
        f"list.index should be python, got {c.top_library}"


# --- P1: Dict methods on local dict ---

def test_dict_get_is_python(result):
    c = _find_call(result.all_api_calls, "mapping.get(")
    assert c is not None, "mapping.get call not found"
    assert c.top_library == "python", \
        f"dict.get should be python, got {c.top_library}"


def test_error_messages_get_is_python(result):
    c = _find_call(result.all_api_calls, "error_messages.get(")
    assert c is not None, "error_messages.get call not found"
    assert c.top_library == "python", \
        f"dict.get should be python, got {c.top_library}"


# --- P1: Set methods on local set ---

def test_set_add_is_python(result):
    c = _find_call(result.all_api_calls, "vals.add(")
    assert c is not None, "vals.add call not found"
    assert c.top_library == "python", \
        f"set.add should be python, got {c.top_library}"


# --- P1: Constructor-created containers ---

def test_list_constructor_append_is_python(result):
    c = _find_call(result.all_api_calls, "xs.append(10)")
    assert c is not None, "xs.append call from list() not found"
    assert c.top_library == "python", \
        f"list().append should be python, got {c.top_library}"


def test_list_constructor_insert_is_python(result):
    c = _find_call(result.all_api_calls, "xs.insert(")
    assert c is not None, "xs.insert call from list() not found"
    assert c.top_library == "python", \
        f"list().insert should be python, got {c.top_library}"


def test_list_constructor_pop_is_python(result):
    c = _find_call(result.all_api_calls, "xs.pop(")
    assert c is not None, "xs.pop call from list() not found"
    assert c.top_library == "python", \
        f"list().pop should be python, got {c.top_library}"


def test_dict_constructor_get_is_python(result):
    c = _find_call(result.all_api_calls, "d_ctor.get(")
    assert c is not None, "d_ctor.get call from dict() not found"
    assert c.top_library == "python", \
        f"dict().get should be python, got {c.top_library}"


# --- P1: Comprehension containers ---

def test_comprehension_list_append_is_python(result):
    c = _find_call(result.all_api_calls, "comprehension_list.append(")
    assert c is not None, "comprehension_list.append call not found"
    assert c.top_library == "python", \
        f"list comprehension append should be python, got {c.top_library}"


# --- P1: Parameter-sourced containers ---

def test_append_from_param_is_python(result):
    """buf.append(x) belongs to Python after buf is bound to a list."""
    c = _find_call(result.all_api_calls, "buf.append(")
    assert c is not None, "buf.append call not found"
    assert c.top_library == "python", \
        f"buf.append on list should be python, got {c.top_library}"


# --- P1: String methods ---

def test_str_upper_is_python(result):
    c = _find_call(result.all_api_calls, "name.upper(")
    assert c is not None, "name.upper call not found"
    assert c.top_library == "python", \
        f"str.upper should be python, got {c.top_library}"


def test_str_replace_is_python(result):
    c = _find_call(result.all_api_calls, "name.replace(")
    assert c is not None, "name.replace call not found"
    assert c.top_library == "python", \
        f"str.replace should be python, got {c.top_library}"


def test_str_startswith_is_python(result):
    c = _find_call(result.all_api_calls, "name.startswith(")
    assert c is not None, "name.startswith call not found"
    assert c.top_library == "python", \
        f"str.startswith should be python, got {c.top_library}"


def test_str_isalpha_is_python(result):
    c = _find_call(result.all_api_calls, "name.isalpha(")
    assert c is not None, "name.isalpha call not found"
    assert c.top_library == "python", \
        f"str.isalpha should be python, got {c.top_library}"


def test_str_lower_is_python(result):
    c = _find_call(result.all_api_calls, "s_ctor.lower(")
    assert c is not None, "s_ctor.lower call not found"
    assert c.top_library == "python", \
        f"str.lower should be python, got {c.top_library}"


# --- P1: Tuple methods ---

def test_tuple_count_is_python(result):
    c = _find_call(result.all_api_calls, "t.count(")
    assert c is not None, "t.count call not found"
    assert c.top_library == "python", \
        f"tuple.count should be python, got {c.top_library}"


def test_tuple_index_is_python(result):
    c = _find_call(result.all_api_calls, "t.index(")
    assert c is not None, "t.index call not found"
    assert c.top_library == "python", \
        f"tuple.index should be python, got {c.top_library}"


# --- P1: Set literal methods ---

def test_set_add2_is_python(result):
    c = _find_call(result.all_api_calls, "s.add(")
    assert c is not None, "s.add call not found"
    assert c.top_library == "python", \
        f"set.add should be python, got {c.top_library}"


def test_set_discard_is_python(result):
    c = _find_call(result.all_api_calls, "s.discard(")
    assert c is not None, "s.discard call not found"
    assert c.top_library == "python", \
        f"set.discard should be python, got {c.top_library}"


# --- P1: Local class methods — should remain LOCAL ---

def test_bag_get_is_local(result):
    c = _find_call(result.all_api_calls, "b.get(")
    assert c is not None, "b.get call not found"
    assert c.top_library == "local", \
        f"Bag.get should be local, got {c.top_library}"


def test_bag_append_is_local(result):
    c = _find_call(result.all_api_calls, "b.append(")
    assert c is not None, "b.append call not found"
    assert c.top_library == "local", \
        f"Bag.append should be local, got {c.top_library}"


def test_bag_pop_is_local(result):
    c = _find_call(result.all_api_calls, "b.pop(")
    assert c is not None, "b.pop call not found"
    assert c.top_library == "local", \
        f"Bag.pop should be local, got {c.top_library}"


# --- Re-binding test ---

def test_rebind_first_append_is_python(result):
    """x.append(0) belongs to Python before x is rebound to Bag."""
    c = _find_call(result.all_api_calls, "x.append(0)")
    assert c is not None, "x.append(0) not found"
    assert c.top_library == "python", \
        f"x.append(0) on list should be python, got {c.top_library}"


def test_rebind_second_append_is_local(result):
    c = _find_call(result.all_api_calls, "x.append(1)")
    assert c is not None, "x.append(1) not found"
    assert c.top_library == "local", \
        f"x.append(1) on Bag should be local, got {c.top_library}"


# --- Unknown parameter test ---

def test_unknown_param_get_is_not_python(result):
    c = _find_call(result.all_api_calls, "obj.get(")
    assert c is not None, "obj.get not found"
    assert c.top_library in ("local", "unknown"), \
        f"obj.get on unknown param should be local/unknown, got {c.top_library}"


def test_unknown_param_append_is_not_python(result):
    c = _find_call(result.all_api_calls, "obj.append(")
    assert c is not None, "obj.append not found"
    assert c.top_library in ("local", "unknown"), \
        f"obj.append on unknown param should be local/unknown, got {c.top_library}"


def test_unknown_param_pop_is_not_python(result):
    c = _find_call(result.all_api_calls, "obj.pop(")
    assert c is not None, "obj.pop not found"
    assert c.top_library in ("local", "unknown"), \
        f"obj.pop on unknown param should be local/unknown, got {c.top_library}"


# --- P1+: defaultdict(list) item kind ---

def test_defaultdict_list_append_is_python(result):
    c = _find_call(result.all_api_calls, "d['x'].append(")
    assert c is not None, "d['x'].append(1) not found"
    assert c.top_library == "python", \
        f"defaultdict(list)[k].append should be python, got {c.top_library}"


def test_defaultdict_list_second_append_is_python(result):
    c = _find_call(result.all_api_calls, "d['y'].append(")
    assert c is not None, "d['y'].append(2) not found"
    assert c.top_library == "python", \
        f"defaultdict(list)[k].append should be python, got {c.top_library}"


def test_defaultdict_dict_get_is_python(result):
    c = _find_call(result.all_api_calls, "d2['x'].get(")
    assert c is not None, "d2['x'].get not found"
    assert c.top_library == "python", \
        f"defaultdict(dict)[k].get should be python, got {c.top_library}"


def test_unknown_factory_append_is_not_python(result):
    """defaultdict(factory) where factory is a variable — not forced python."""
    c = _find_call(result.all_api_calls, "d3['x'].append(")
    assert c is not None, "d3['x'].append not found"
    assert c.top_library != "python", \
        f"defaultdict(factory)[k].append should NOT be python, got {c.top_library}"


def test_defaultdict_bag_append_is_local(result):
    """defaultdict(Bag)[k].append — local class, not python."""
    c = _find_call(result.all_api_calls, "d4['x'].append(")
    assert c is not None, "d4['x'].append not found"
    assert c.top_library != "python", \
        f"defaultdict(Bag)[k].append should NOT be python, got {c.top_library}"


# --- Re-binding with defaultdict ---

def test_defaultdict_rebind_subscript_is_python(result):
    """defaultdict(list) items expose Python list methods before rebinding."""
    c = _find_call(result.all_api_calls, "d_rebind['a'].append(")
    assert c is not None, "d_rebind['a'].append(1) not found"
    assert c.top_library == "python", \
        f"defaultdict(list)[k].append should be python, got {c.top_library}"


def test_defaultdict_rebind_method_is_local(result):
    c = _find_call(result.all_api_calls, "d_rebind.append(2)")
    assert c is not None, "d_rebind.append(2) not found"
    assert c.top_library == "local", \
        f"d_rebind.append on Bag after rebind should be local, got {c.top_library}"


# --- Sanity ---

def test_getattr_json_is_python(result):
    c = _find_call(result.all_api_calls, "getattr(json,")
    assert c is not None, "getattr(json, ...) call not found"
    assert c.top_library == "python", \
        f"getattr(json) should be python, got {c.top_library}"
