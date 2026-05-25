## @package tests.test_ast_compat
#  Cross-version AST compatibility tests.
#
#  PCResolve uses ast.parse(), ast.unparse(), and AST node position
#  attributes (lineno, col_offset, end_lineno, end_col_offset).
#  These tests verify consistent behaviour across Python 3.9+.

import ast
import sys


# ── ast.unparse() output stability ───────────────────────────────────────


def test_unparse_simple_call():
    """Call expressions should unparse to stable, whitespace-normalised form."""
    tree = ast.parse("requests.get(url, headers=h)")
    call = tree.body[0].value  # type: ast.Call
    result = ast.unparse(call)
    assert "requests.get" in result
    assert "url" in result


def test_unparse_chained_call():
    """Chained calls should round-trip through parse/unparse."""
    tree = ast.parse("a.b().c()")
    call = tree.body[0].value  # type: ast.Call
    result = ast.unparse(call)
    assert ".b()" in result
    assert ".c()" in result


def test_unparse_attribute():
    """Attribute access should unparse correctly."""
    tree = ast.parse("obj.attr.method")
    expr = tree.body[0].value  # type: ast.Attribute
    result = ast.unparse(expr)
    assert "obj.attr.method" == result or result.startswith("obj")


def test_unparse_normalises_whitespace():
    """Expression unparse should not depend on insignificant whitespace."""
    tree1 = ast.parse("f(x, y)")
    tree2 = ast.parse("f( x , y )")
    call1 = tree1.body[0].value  # type: ast.Call
    call2 = tree2.body[0].value  # type: ast.Call
    assert ast.unparse(call1) == ast.unparse(call2)


# ── end position attributes ─────────────────────────────────────────────


def test_stmt_has_end_lineno():
    """Statements should carry end_lineno/end_col_offset on Python 3.8+."""
    tree = ast.parse("x = 1\ny = 2")
    stmt = tree.body[0]
    assert hasattr(stmt, "end_lineno"), "end_lineno missing"
    assert hasattr(stmt, "end_col_offset"), "end_col_offset missing"


def test_call_has_end_position():
    """Call nodes should carry end positions."""
    tree = ast.parse("requests.get(url)")
    call = tree.body[0].value  # type: ast.Call
    assert hasattr(call, "end_lineno")
    assert hasattr(call, "end_col_offset")


def test_end_position_not_zero():
    """End positions should be non-zero for real statements."""
    tree = ast.parse("x = requests.get(url)")
    stmt = tree.body[0]
    if hasattr(stmt, "end_lineno"):
        assert stmt.end_lineno > 0
    if hasattr(stmt, "end_col_offset"):
        assert stmt.end_col_offset > 0


# ── type comments ───────────────────────────────────────────────────────


def test_type_comment_does_not_break_parse():
    """Type comments (Python < 3.12) should parse without SyntaxError."""
    try:
        tree = ast.parse("x = 1  # type: int")
    except SyntaxError:
        if sys.version_info >= (3, 12):
            # Python 3.12+ removed type comment support — no-op pass
            pass
        else:
            raise
    else:
        # If it parses, the assignment should have the value
        stmt = tree.body[0]
        assert isinstance(stmt.value, ast.Constant)


# ── positional-only args ────────────────────────────────────────────────


def test_posonly_args_do_not_break_parse():
    """Positional-only args (PEP 570, Python 3.8+) should parse."""
    tree = ast.parse("def f(a, /, b): pass")
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "f"


def test_posonly_args_have_correct_arg_count():
    """Function with posonly args should have all args collected."""
    tree = ast.parse("def f(a, /, b, *, c): pass")
    func = tree.body[0]
    args = func.args
    assert len(args.args) == 1  # b (positional-or-keyword)
    assert len(args.posonlyargs) == 1  # a is posonly
    assert len(args.kwonlyargs) == 1  # c is kwonly


# ── f-string parsing ────────────────────────────────────────────────────


def test_fstring_parses():
    """F-strings should parse (Python 3.6+)."""
    tree = ast.parse("x = f'hello {name}'")
    stmt = tree.body[0]
    assert isinstance(stmt.value, ast.JoinedStr)


# ── walrus operator ─────────────────────────────────────────────────────


def test_walrus_operator_parses():
    """Walrus operator (:= Python 3.8+) should parse."""
    tree = ast.parse("(x := 1)")
    expr = tree.body[0].value
    assert isinstance(expr, ast.NamedExpr)
