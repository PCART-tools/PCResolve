"""Regression tests for group_ground_truth_annotations.py."""

import os
import sys
import textwrap
import ast

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
from group_ground_truth_annotations import (
    _propose_gt, _RETURN_TYPE_RULES,
    BindingVisitor, _find_binding_before, _resolve_owner,
    _is_import_binding, _import_module, _extract_source_evidence,
    _scope_identity, _group_key, _receiver_root, KIND_CLASS,
)


def _visit_source(source):
    src = textwrap.dedent(source)
    v = BindingVisitor(src)
    v.visit(ast.parse(src))
    return v


def _call_frame(v, lineno):
    for (cl, _), fp in v.scope_of_call.items():
        if cl == lineno:
            return fp
    return None


# -- proposal rules --

def test_seaborn_barplot_returns_matplotlib():
    assert _RETURN_TYPE_RULES.get(("seaborn", "barplot")) == "matplotlib"


def test_seaborn_stripplot_returns_matplotlib():
    assert _RETURN_TYPE_RULES.get(("seaborn", "stripplot")) == "matplotlib"


def _ev(value, owner=None, needs=True):
    return {"receiver": "x", "binding_value": value, "binding_file": "t.py",
            "binding_line": 1, "owner": owner,
            "needs_human_from_resolve": needs, "all_bindings": set()}


def test_list_literal_proposes_python():
    k, t, _, n = _propose_gt({}, _ev("[]"))
    assert k == "python" and t == "python" and not n


def test_dict_literal_proposes_python():
    k, t, _, n = _propose_gt({}, _ev("{}"))
    assert k == "python" and t == "python" and not n


def test_non_empty_list_not_confused_as_literal():
    """AST-based: [x, y] is not an empty list, should not match literal rule."""
    k, t, _, n = _propose_gt({}, _ev("[x, y]"))
    assert not (k == "python" and t == "python" and not n), \
        "non-empty list should not be auto-confirmed as python literal"


def test_defaultdict_string_match_no_longer_auto_confirms():
    """No broad 'defaultdict' in value check; needs human."""
    k, t, _, n = _propose_gt({}, _ev("defaultdict(list)"))
    assert n, "defaultdict should need human, got {}/{}".format(k, t)


def test_import_proposes_library():
    _, top, _, needs = _propose_gt({}, _ev("import matplotlib.pyplot"))
    assert top == "matplotlib" and not needs


def test_no_evidence_needs_human():
    _, _, _, needs = _propose_gt({}, None)
    assert needs


def test_stripplot_with_seaborn_owner_resolves_matplotlib():
    _, top, _, needs = _propose_gt({}, _ev("sns.stripplot(...)", "seaborn", False))
    assert top == "matplotlib" and not needs


# -- parameter shadows import --

def test_parameter_shadows_module_import():
    src = '''
    import numpy as data
    def f(data):
        data.get()
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 4)
    owner, needs = _resolve_owner("data", v.bindings, fp, 4, 0)
    assert needs, f"parameter should block import, got owner={owner}"


# -- for target shadows import --

def test_for_target_shadows_import():
    src = '''
    import numpy as x
    for x in range(3):
        x.sum()
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 4)
    owner, needs = _resolve_owner("x", v.bindings, fp, 4, 0)
    assert needs, f"for target should block import, got owner={owner}"


# -- method bare name skips class namespace --

def test_method_bare_name_skips_class_namespace():
    src = '''
    import pandas as x
    class C:
        import numpy as x
        def f(self):
            x.DataFrame()
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 6)
    # x.DataFrame at line 6: bare name should resolve module-level x = pandas
    owner, needs = _resolve_owner("x", v.bindings, fp, 6, 0)
    assert owner == "pandas", f"bare name should skip class x, got {owner}"


# -- missing call position unresolved --

def test_missing_call_position_is_unresolved():
    """A record with no matching ast.Call gets None evidence."""
    rec = {"file": "nonexistent.py", "pcresolve_func_name": "x.foo",
           "lineno": 999, "col_offset": 0}
    import tempfile, json
    with tempfile.TemporaryDirectory() as tmp:
        # Create a minimal project
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        with open(os.path.join(src, "real.py"), "w") as f:
            f.write("x = 1\n")
        rec2 = {"file": "real.py", "pcresolve_func_name": "x.foo",
                "lineno": 2, "col_offset": 0}
        ev = _extract_source_evidence(src, rec2)
        # line 2 has no ast.Call -> None
        assert ev is None, f"no call at line 2, should be None, got {ev}"


# -- scope correctness --

def test_call_after_function_gets_module_scope():
    src = '''
    def f():
        x = []
    x = make_local()
    x.run()
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 5)
    assert fp == [("module", "<module>")], f"got {fp}"


def test_self_referential_resolves_prior():
    src = '''
    import pandas as pd
    df = pd.read_csv("d.csv")
    df_freq = df.iloc[:, :-13].copy().dropna()
    df_freq = df_freq.merge(df_p, on='b', how='inner')
    df_freq.to_csv('out.csv')
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 6)
    owner, needs = _resolve_owner("df_freq", v.bindings, fp, 6, 0)
    assert owner == "pandas" and not needs


def test_sibling_functions_isolated():
    src = '''
    import pandas as pd
    def foo():
        x = pd.DataFrame()
        x.head()
    def bar():
        x = []
        x.append(1)
    '''
    v = _visit_source(src)
    fp_foo = _call_frame(v, 5)
    b = _find_binding_before(v.bindings["x"], fp_foo, 5, 0)
    assert b is not None and "pd.DataFrame" in b.value
    fp_bar = _call_frame(v, 8)
    b2 = _find_binding_before(v.bindings["x"], fp_bar, 8, 0)
    assert b2 is not None and "[]" in b2.value


def test_call_before_later_assignment():
    src = '''
    import numpy as np
    x = []
    x.append(1)
    x = np.array(x)
    x.reshape((3,3))
    '''
    v = _visit_source(src)
    b = _find_binding_before(v.bindings["x"], _call_frame(v, 4), 4, 0)
    assert b is not None and "[]" in b.value
    b6 = _find_binding_before(v.bindings["x"], _call_frame(v, 6), 6, 0)
    assert b6 is not None and "np.array" in b6.value


# -- comprehensions --

def test_dict_comp_does_not_crash():
    """DictComp must not crash on missing .elt attribute."""
    src = '''d = {k: v for k, v in rows}'''
    v = _visit_source(src)
    # Should parse and visit without error
    assert "k" in v.bindings
    assert any(b.is_opaque for b in v.bindings["k"])


def test_comprehension_target_does_not_leak():
    """Comprehension target isolated in comprehension frame."""
    src = '''
    import numpy as x
    [x.sum() for x in rows]
    x.array([1])
    '''
    v = _visit_source(src)
    # x.array at line 4: should resolve module x = numpy
    fp = _call_frame(v, 4)
    owner, needs = _resolve_owner("x", v.bindings, fp, 4, 0)
    assert owner == "numpy", f"comprehension target must not leak, got {owner}"


def test_comprehension_target_registered_as_opaque():
    """Comprehension target is registered as opaque binding."""
    src = '''
    import numpy as x
    [x.sum() for x in rows]
    '''
    v = _visit_source(src)
    # Comprehension target x has an opaque binding
    assert "x" in v.bindings
    opaque = [b for b in v.bindings["x"] if b.is_opaque]
    assert len(opaque) >= 1, "comprehension target should be opaque"


def test_class_method_default_resolves_class_scope():
    """Default argument evaluates in class scope, should resolve class binding."""
    src = '''
    import pandas as x
    class C:
        import numpy as x
        def f(y=x.array([1])):
            pass
    '''
    v = _visit_source(src)
    # x.array at line 5: default value, evaluated in class scope where x = numpy
    for (cl, _), fp in v.scope_of_call.items():
        if cl == 5:
            owner, needs = _resolve_owner("x", v.bindings, fp, 5, 0)
            assert owner == "numpy", f"default should see class x=numpy, got {owner}"


def test_with_alias_shadows_import():
    src = '''
    import numpy as f
    with open("x") as f:
        f.read()
    '''
    v = _visit_source(src)
    fp = _call_frame(v, 4)
    owner, needs = _resolve_owner("f", v.bindings, fp, 4, 0)
    assert needs, f"with alias should block import, got {owner}"


# -- scope isolation --

def test_two_classes_self_method_not_merged():
    """self.method() in different classes must produce different group keys."""
    src = '''
    class A:
        def run(self):
            self.do_work()
    class B:
        def run(self):
            self.do_work()
    '''
    v = _visit_source(src)
    # Build records for each class's self.do_work()
    a_rec = {"_evidence": {
        "receiver_path": "self", "call_frame_path": [],
        "binding_value": "parameter self",
    }, "pcresolve_reason": "LOCAL_DEFINITION",
       "_proposed_kind": "?", "_proposed_top": "?", "_needs_human": True,
       "pcresolve_func_name": "self.do_work",
    }
    b_rec = {"_evidence": {
        "receiver_path": "self", "call_frame_path": [],
        "binding_value": "parameter self",
    }, "pcresolve_reason": "LOCAL_DEFINITION",
       "_proposed_kind": "?", "_proposed_top": "?", "_needs_human": True,
       "pcresolve_func_name": "self.do_work",
    }
    # Populate call_frame_path from actual visitor
    for (cl, _), fp in v.scope_of_call.items():
        if cl == 4:
            a_rec["_evidence"]["call_frame_path"] = list(fp)
        elif cl == 7:
            b_rec["_evidence"]["call_frame_path"] = list(fp)
    # Group keys must differ because class frames differ
    assert _group_key(a_rec) != _group_key(b_rec), \
        f"different classes must produce different group keys: " \
        f"{_group_key(a_rec)} vs {_group_key(b_rec)}"


# -- markdown encoding --

def test_pipe_in_expression_escaped():
    """Expression with | must be escaped for markdown table."""
    from group_ground_truth_annotations import _md_text, _md_code
    result = _md_code("re.split('_|-', x)")
    assert "&#124;" in result, f"pipe must be escaped, got {result}"
    assert result.startswith("<code>") and result.endswith("</code>")


def test_string_literal_whitespace_preserved():
    """Internal whitespace in string literals must not be collapsed."""
    from group_ground_truth_annotations import _md_code
    result = _md_code('"a  b"')
    assert "a  b" in result, f"whitespace preserved: {result}"


def test_markdown_does_not_double_wrap_backticks():
    """_md_code already wraps in <code>, no extra backticks in output."""
    from group_ground_truth_annotations import _md_code
    result = _md_code("foo.bar()")
    assert "`" not in result, f"no backticks in code output: {result}"


# -- binding isolation across functions --

def test_all_bindings_do_not_include_sibling_function():
    """all_bindings in evidence must not include bindings from other functions."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "main.py")
        with open(src, "w") as f:
            f.write("import pandas as pd\n"
                    "def foo():\n"
                    "    x = pd.DataFrame()\n"
                    "    x.head()\n"
                    "def bar():\n"
                    "    x = []\n"
                    "    x.append(1)\n")
        rec = {"file": "main.py", "lineno": 7, "col_offset": 4,
               "pcresolve_func_name": "x.append"}
        ev = _extract_source_evidence(tmp, rec)
        assert ev is not None, "should find evidence"
        # all_bindings must only contain the selected binding ([] at line 6)
        for fname, bline, bval in ev["all_bindings"]:
            assert "pd.DataFrame" not in bval, \
                f"foo() binding leaked: {bval} at line {bline}"
            assert "[]" in bval or bline == 7, \
                f"unexpected binding: {bval}"


# -- manual_reasoned group completeness --

def test_manual_group_shows_all_records():
    """Manual groups must show all records, not just first 5."""
    import tempfile, os
    import group_ground_truth_annotations as gg
    recs = []
    for i in range(8):
        r = {
            "_proposed_kind": "?", "_proposed_top": "?",
            "_proposed_notes": "test", "_needs_human": True,
            "_evidence": None,
            "expression": "expr_%d()" % i,
            "file": "f.py", "lineno": i + 1,
            "pcresolve_reason": "UNRESOLVED",
            "pcresolve_func_name": "x.foo",
            "annotation_status": "draft",
        }
        recs.append(r)
    key = ("x.foo", ("global", "", ()), "", "UNRESOLVED", "?", "?", True)
    data = {
        "project": "testproj", "total_drafts": 10, "unlabeled": 8,
        "awaiting_review_recs": [], "groups": {key: recs},
    }
    with tempfile.TemporaryDirectory() as tmp:
        old = gg.REVIEW_DIR
        gg.REVIEW_DIR = tmp
        try:
            gg.write_group_md(data)
            md_path = os.path.join(tmp, "testproj", "annotation_groups.md")
            with open(md_path) as f:
                content = f.read()
            for i in range(8):
                assert "expr_%d()" % i in content, \
                    f"expr_{i}() missing from manual group output"
        finally:
            gg.REVIEW_DIR = old


# -- parse failure caching --

def test_parse_failure_cached():
    """Failed parse result is cached, not re-parsed."""
    import tempfile, os
    from group_ground_truth_annotations import _load_source_analysis
    with tempfile.TemporaryDirectory() as tmp:
        bad = os.path.join(tmp, "bad.py")
        with open(bad, "w") as f:
            f.write("def broken(:\n    pass\n")
        cache = {}
        r1 = _load_source_analysis(bad, cache)
        assert r1 is None
        r2 = _load_source_analysis(bad, cache)
        assert r2 is None
        assert len(cache) == 1, "failed parse must be cached"


# -- generated file integrity --

def test_generated_file_is_utf8():
    path = os.path.join(os.path.dirname(__file__), "..",
                        "ground_truth", "review", "giantpopflucts",
                        "annotation_groups.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        assert "�" not in f.read()


def test_total_matches_title():
    path = os.path.join(os.path.dirname(__file__), "..",
                        "ground_truth", "review", "giantpopflucts",
                        "annotation_groups.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        content = f.read()
    import re
    m = re.search(r'\|\s+\*\*Total\*\*\s+\|\s+\*\*(\d+)\*\*\s+\|\s+\*\*(\d+)\*\*\s+\|\s+\*\*(\d+)\*\*', content)
    if m:
        tm = re.search(r'(\d+) records', content.split('\n')[0])
        if tm:
            assert int(tm.group(1)) == int(m.group(2))
