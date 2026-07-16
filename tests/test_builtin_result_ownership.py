## @package tests.test_builtin_result_ownership
#  Regression tests for builtin call/result ownership separation.

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project


def _calls_by_expr(result, expr_substring):
    return [c for c in result.all_api_calls if expr_substring in c.expression]


def _write_and_analyze(code, scope_model="v2"):
    tmpdir = tempfile.mkdtemp()
    test_file = os.path.join(tmpdir, "test_mod.py")
    with open(test_file, "w") as f:
        f.write(code)
    result = analyze_project(tmpdir, scope_model=scope_model)
    import shutil
    shutil.rmtree(tmpdir)
    return result


# ── eval contamination ────────────────────────────────────────────────

def test_eval_call_owner_is_python():
    result = _write_and_analyze("eval('1+1')")
    calls = _calls_by_expr(result, "eval")
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_eval_result_factory_is_unknown():
    result = _write_and_analyze("""
class A: pass
factory = eval('A')
factory()
""")
    calls = _calls_by_expr(result, "factory()")
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"


# ── builtin shadow detection ──────────────────────────────────────────

def test_shadowed_open_does_not_get_python_result():
    result = _write_and_analyze("""
class A:
    def method(self): pass
def open(path):
    return A()
f = open('x')
f.method()
""")
    calls = _calls_by_expr(result, "f.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


# ── element-derived result semantics ──────────────────────────────────

def test_min_of_strings_gives_python_element():
    result = _write_and_analyze("""
items = ['a', 'b']
x = min(items)
x.split()
""")
    calls = _calls_by_expr(result, "x.split")
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_min_of_locals_gives_local_element():
    result = _write_and_analyze("""
class A:
    def method(self): pass
value = min([A(), A()])
value.method()
""")
    calls = _calls_by_expr(result, "value.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


def test_type_of_local_constructor_gives_local():
    result = _write_and_analyze("""
class A: pass
cls = type(A())
cls()
""")
    calls = _calls_by_expr(result, "cls()")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


# ── __import__ constant ───────────────────────────────────────────────

def test_next_of_locals_gives_local():
    result = _write_and_analyze("""
class A:
    def method(self): pass
it = iter([A(), A()])
value = next(it)
value.method()
""")
    calls = _calls_by_expr(result, "value.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


def test_next_of_inline_local_iterable_gives_local():
    result = _write_and_analyze("""
class A:
    def method(self): pass
value = next(iter([A()]))
value.method()
""")
    calls = _calls_by_expr(result, "value.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


def test_max_self_rebinding_does_not_recurse_in_either_scope_model():
    code = """
def clamp(process_count):
    process_count = max(1, process_count)
    return process_count
"""
    for scope_model in ("v1", "v2"):
        result = _write_and_analyze(code, scope_model=scope_model)
        calls = _calls_by_expr(result, "max(1, process_count)")
        assert len(calls) == 1
        assert calls[0].top_library == "python"


def test_max_of_multiple_library_candidates_is_unknown_with_alternatives():
    result = _write_and_analyze("""
import json
import os
x = max(json, os, key=lambda module: module.__name__)
x.dumps({})
""")
    calls = _calls_by_expr(result, "x.dumps")
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"
    assert set(calls[0].alternatives) == {"json", "os"}


def test_next_with_default_tracks_element_and_default_candidates():
    result = _write_and_analyze("""
import json
class A:
    def method(self): pass
items = [A()]
x = next(iter(items), json)
x.method()
""")
    calls = _calls_by_expr(result, "x.method")
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"
    # alternatives exposes import-backed candidates only; local remains
    # represented by the unknown primary result.
    assert set(calls[0].alternatives) == {"json"}


def test___import___constant_resolves_to_module():
    result = _write_and_analyze("mod = __import__('os'); mod.getcwd()")
    calls = _calls_by_expr(result, "mod.getcwd")
    assert len(calls) == 1
    assert calls[0].top_library == "os"


def test___import___dotted_normalizes_to_top():
    result = _write_and_analyze("mod = __import__('os.path'); mod.getcwd()")
    calls = _calls_by_expr(result, "mod.getcwd")
    assert len(calls) == 1
    assert calls[0].top_library == "os"


# ── super() method resolution ─────────────────────────────────────────

def test_bare_super_is_python():
    result = _write_and_analyze("""
class A: pass
class B(A):
    def __init__(self):
        super()
""")
    super_calls = _calls_by_expr(result, "super()")
    bare = [c for c in super_calls if c.expression.strip() == "super()"]
    assert len(bare) == 1
    assert bare[0].top_library == "python"


def test_super_init_from_local_base_is_local():
    result = _write_and_analyze("""
class A:
    def __init__(self): pass
class B(A):
    def __init__(self):
        super().__init__()
""")
    calls = _calls_by_expr(result, "super().__init__")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


def test_super_get_config_result_not_inherited():
    result = _write_and_analyze("""
class Base:
    def get_config(self):
        return {}
class Child(Base):
    def get_config(self):
        config = super().get_config()
        config.update({'key': 'val'})
        return config
""")
    super_calls = _calls_by_expr(result, "super().get_config")
    assert len(super_calls) == 1
    assert super_calls[0].top_library == "local"

    update_calls = _calls_by_expr(result, "config.update")
    assert len(update_calls) == 1
    assert update_calls[0].top_library == "unknown"


def test_super_method_on_import_base_is_library():
    result = _write_and_analyze("""
import json
class MyDecoder(json.JSONDecoder):
    def decode(self, s):
        return super().decode(s)
""")
    calls = _calls_by_expr(result, "super().decode")
    assert len(calls) == 1
    assert calls[0].top_library == "json"


# ── enumerate / zip for-loop decontamination ──────────────────────────

def test_enumerate_local_list_element_not_python():
    result = _write_and_analyze("""
class MyObj:
    def method(self): pass
items = [MyObj(), MyObj()]
for i, x in enumerate(items):
    x.method()
""")
    calls = _calls_by_expr(result, "x.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


def test_enumerate_string_elements_unknown_or_python():
    result = _write_and_analyze("""
lines = ['hello', 'world']
for _, fn in enumerate(lines):
    fn.split()
""")
    calls = _calls_by_expr(result, "fn.split")
    assert len(calls) == 1
    assert calls[0].top_library in ("python", "unknown")


def test_indexed_str_split_result_preserves_string_item_kind():
    result = _write_and_analyze("""
import os
for _, _, files in os.walk('.'):
    for fn in files:
        fn.split('.')[0].replace('sample', 'result')
""")
    calls = _calls_by_expr(result, ".replace")
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_local_split_method_result_does_not_claim_python_string():
    result = _write_and_analyze("""
class Tokenizer:
    def split(self):
        return [self]

tokenizer = Tokenizer()
tokenizer.split()[0].replace('sample', 'result')
""")
    calls = _calls_by_expr(result, ".replace")
    assert len(calls) == 1
    assert calls[0].top_library != "python"


def test_parameter_unpack_does_not_borrow_module_binding():
    result = _write_and_analyze("""
fn = 'module.txt'

def handle(t):
    fn, payload = t
    fn.split('.')
""")
    calls = _calls_by_expr(result, "fn.split")
    assert len(calls) == 1
    assert calls[0].top_library in ("local", "unknown")


def test_zip_for_loop_positional():
    result = _write_and_analyze("""
class X: pass
class Y: pass
list_a = [X(), X()]
list_b = [Y(), Y()]
for a, b in zip(list_a, list_b):
    a.method()
""")
    calls = _calls_by_expr(result, "a.method")
    assert len(calls) == 1
    assert calls[0].top_library == "local"


# ── file handle / open() result ───────────────────────────────────────

def test_open_result_is_python():
    result = _write_and_analyze("f = open('test.txt'); f.write('data')")
    calls = _calls_by_expr(result, "f.write")
    assert len(calls) == 1
    assert calls[0].top_library == "python"
