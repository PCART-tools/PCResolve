#!/usr/bin/env python3
## @package scripts.group_ground_truth_annotations
#  Group draft GT records by receiver-binding evidence for batch review.

import argparse
import ast
import html as _html
import json
import os
import re
import sys

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
REVIEW_DIR = os.path.join(GT_DIR, "review")

DRAFT_PROJECTS = [
    "giantpopflucts", "MAHE_OD_DATASET", "polire",
    "AIBO", "greenbenchmark", "allnews",
]

KIND_MODULE = "module"
KIND_CLASS = "class"
KIND_FUNCTION = "function"


# ---------------------------------------------------------------------------
# Scope frame + binding
# ---------------------------------------------------------------------------

class Frame:
    __slots__ = ("kind", "name", "start_lineno", "end_lineno")
    def __init__(self, kind, name, start_lineno):
        self.kind = kind
        self.name = name
        self.start_lineno = start_lineno
        self.end_lineno = None


class Binding:
    __slots__ = ("frame_path", "lineno", "col_offset", "value", "is_opaque")
    def __init__(self, frame_path, lineno, col_offset, value, is_opaque=False):
        self.frame_path = tuple(frame_path)
        self.lineno = lineno
        self.col_offset = col_offset
        self.value = value
        self.is_opaque = is_opaque


class BindingVisitor(ast.NodeVisitor):
    """Extract all variable bindings with frame-aware scope.

    - Records precise scope for every Call site.
    - Parameters, for-targets, with-aliases, except-names,
      and comprehension targets are opaque bindings that
      block resolution through enclosing scopes.
    - Method body bare-name lookup skips class frames.
    """

    def __init__(self, source_text=""):
        self.bindings = {}
        self.scope_of_call = {}
        self._frames = [Frame(KIND_MODULE, "<module>", 0)]
        self._source = source_text

    def _top_frame(self):
        return self._frames[-1]

    def _push_frame(self, kind, name, lineno):
        f = Frame(kind, name, lineno)
        self._frames.append(f)
        return f

    def _pop_frame(self, end_lineno):
        self._frames.pop().end_lineno = end_lineno

    def _frame_path(self):
        return [(f.kind, f.name) for f in self._frames]

    def _add(self, name, value, lineno, col_offset, opaque=False):
        b = Binding(self._frame_path(), lineno, col_offset, value, opaque)
        self.bindings.setdefault(name, []).append(b)

    # -- opaque bindings --

    def _add_opaque(self, name, source, lineno, col_offset=0):
        self._add(name, source, lineno, col_offset, opaque=True)

    def _visit_opaque_targets(self, targets, source, lineno):
        for t in targets:
            if isinstance(t, ast.Name):
                self._add_opaque(t.id, source, lineno)
            elif isinstance(t, (ast.Tuple, ast.List)):
                self._visit_opaque_targets(t.elts, source, lineno)

    # -- visitors --

    def visit_Call(self, node):
        self.scope_of_call[(node.lineno, node.col_offset)] = \
            self._frame_path()
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self._add(name, "import %s" % alias.name,
                      node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self._add(name, "from %s import %s" % (node.module or "", alias.name),
                      node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Decorators, defaults, annotations evaluate in ENCLOSING scope
        for deco in node.decorator_list:
            self.visit(deco)
        if node.returns:
            self.visit(node.returns)
        for d in node.args.defaults:
            self.visit(d)
        for d in node.args.kw_defaults:
            if d is not None:
                self.visit(d)
        # Function name binding in enclosing scope
        self._add(node.name, "def %s" % node.name,
                  node.lineno, node.col_offset)
        # Enter function frame
        self._push_frame(KIND_FUNCTION, node.name, node.lineno)
        for arg in (getattr(node.args, "posonlyargs", [])
                    + node.args.args
                    + getattr(node.args, "kwonlyargs", [])):
            self._add_opaque(arg.arg, "parameter %s" % arg.arg, node.lineno)
        if node.args.vararg:
            self._add_opaque(node.args.vararg.arg, "parameter *args", node.lineno)
        if node.args.kwarg:
            self._add_opaque(node.args.kwarg.arg, "parameter **kwargs", node.lineno)
        for stmt in node.body:
            self.visit(stmt)
        self._pop_frame(node.end_lineno or node.lineno)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        # Bases, keywords, decorators evaluate in ENCLOSING scope
        for deco in node.decorator_list:
            self.visit(deco)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw.value)
        # Class name binding in enclosing scope
        self._add(node.name, "class %s" % node.name,
                  node.lineno, node.col_offset)
        # Enter class frame
        self._push_frame(KIND_CLASS, node.name, node.lineno)
        for stmt in node.body:
            self.visit(stmt)
        self._pop_frame(node.end_lineno or node.lineno)

    def visit_Assign(self, node):
        rhs = self._expr_text(node.value)
        for target in node.targets:
            self._bind_target(target, rhs, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value:
            rhs = self._expr_text(node.value)
            self._bind_target(node.target, rhs, node)
        self.generic_visit(node)

    def visit_For(self, node):
        # Visit iter first, then bind target, then body
        self.visit(node.iter)
        self._visit_opaque_targets(
            [node.target] if isinstance(node.target, ast.Name)
            else node.target.elts if isinstance(node.target, (ast.Tuple, ast.List))
            else [],
            "for target", node.lineno)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_With(self, node):
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._visit_opaque_targets(
                    [item.optional_vars] if isinstance(item.optional_vars, ast.Name)
                    else item.optional_vars.elts if isinstance(
                        item.optional_vars, (ast.Tuple, ast.List)) else [],
                    "with alias", node.lineno)
        for stmt in node.body:
            self.visit(stmt)

    def visit_ExceptHandler(self, node):
        if node.type:
            self.visit(node.type)
        if node.name:
            self._add_opaque(node.name, "except handler", node.lineno)
        for stmt in node.body:
            self.visit(stmt)

    def visit_NamedExpr(self, node):
        # Visit value first, then bind target
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self._add_opaque(node.target.id, "named expression", node.lineno)

    def _visit_comprehension(self, node, result_exprs):
        """Shared comprehension handler with isolated frame."""
        first = node.generators[0]
        # First iterable evaluates in enclosing scope
        self.visit(first.iter)
        # Comprehension frame isolates targets
        name = "<comp>@L%d" % node.lineno
        self._push_frame(KIND_FUNCTION, name, node.lineno)
        self._visit_opaque_targets(
            [first.target] if isinstance(first.target, ast.Name)
            else first.target.elts if isinstance(first.target, (ast.Tuple, ast.List))
            else [],
            "comprehension target", first.target.lineno)
        for cond in first.ifs:
            self.visit(cond)
        for gen in node.generators[1:]:
            self.visit(gen.iter)
            self._visit_opaque_targets(
                [gen.target] if isinstance(gen.target, ast.Name)
                else gen.target.elts if isinstance(gen.target, (ast.Tuple, ast.List))
                else [],
                "comprehension target", gen.target.lineno)
            for cond in gen.ifs:
                self.visit(cond)
        for expr in result_exprs:
            self.visit(expr)
        self._pop_frame(node.end_lineno or node.lineno)

    def visit_ListComp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_SetComp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_GeneratorExp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_DictComp(self, node):
        self._visit_comprehension(node, [node.key, node.value])

    def _bind_target(self, target, rhs, node):
        if isinstance(target, ast.Name):
            self._add(target.id, rhs, node.lineno, node.col_offset)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    self._add(elt.id, "(tuple) " + rhs, node.lineno, node.col_offset)

    def _expr_text(self, node):
        """Return source text for an AST node, stable across Python versions.

        Uses ast.get_source_segment for the exact original source.
        Escapes control characters for single-line Markdown display
        but preserves internal whitespace (string literal content).
        """
        try:
            text = ast.get_source_segment(self._source, node)
            if text is not None:
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                return text.replace("\n", "\\n").replace("\t", "\\t")
        except Exception:
            pass
        try:
            return ast.unparse(node)
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Scope lookup
# ---------------------------------------------------------------------------

def _visible_frames(frame_path, for_bare_name=True):
    """Yield (kind, name) frames visible for lookup, innermost first.

    When for_bare_name is True (method body bare-name lookup),
    class frames are skipped — Python does not resolve bare names
    through enclosing class scopes.
    """
    rev = list(frame_path)
    rev.reverse()
    for i, (kind, name) in enumerate(rev):
        if i == 0:
            yield (kind, name)
        elif kind == KIND_CLASS and for_bare_name:
            continue  # skip class for bare-name resolution
        else:
            yield (kind, name)


def _is_import_binding(value):
    return bool(re.match(r'(import |from \S+ import)', value))


def _import_module(value):
    m = re.match(r'import (\S+)', value)
    if m:
        return m.group(1)
    m = re.match(r'from (\S+) import', value)
    if m:
        return m.group(1)
    return None


def _find_binding_before(bindings_list, call_frame_path, rec_lineno, rec_col):
    """Find the most recent binding before the call site in visible frames.

    Searches from innermost visible frame outward.
    Bindings at the same line and column (e.g. comprehension targets)
    are treated as active for calls visited later on the same line.
    """
    for fkind, fname in _visible_frames(call_frame_path, for_bare_name=True):
        candidates = [
            b for b in bindings_list
            if tuple(b.frame_path) == tuple(call_frame_path[:len(b.frame_path)])
            and b.frame_path[-1] == (fkind, fname)
            and (b.lineno, b.col_offset) < (rec_lineno, rec_col)
        ]
        if candidates:
            return max(candidates, key=lambda b: (b.lineno, b.col_offset))
    return None


def _resolve_owner(name, bindings_by_name, call_frame_path,
                   rec_lineno, rec_col):
    """Recursively resolve a variable name to its library owner."""
    visited = set()
    current_name = name
    search_lineno = rec_lineno
    search_col = rec_col

    for _ in range(20):
        if current_name not in bindings_by_name:
            break

        binding = _find_binding_before(
            bindings_by_name[current_name],
            call_frame_path, search_lineno, search_col)
        if binding is None:
            break

        # Opaque bindings (parameters etc.) block resolution
        if binding.is_opaque:
            return None, True

        pos_key = (current_name, binding.lineno, binding.col_offset)
        if pos_key in visited:
            break
        visited.add(pos_key)

        value = binding.value

        if _is_import_binding(value):
            mod = _import_module(value)
            if mod:
                return mod.split(".")[0], False
            break

        # Constructor: library.Class() or alias.Class()
        m = re.match(r'(\w+)\.(\w+)\(', value)
        if m:
            lib_alias = m.group(1)
            owner, needs = _resolve_owner(
                lib_alias, bindings_by_name, call_frame_path,
                binding.lineno, binding.col_offset)
            if owner and not needs:
                return owner, False
            break

        # Chained: var.method()...
        m = re.match(r'(\w+)\.', value)
        if m:
            current_name = m.group(1)
            search_lineno = binding.lineno
            search_col = binding.col_offset
            continue

        # Bare call, literal, tuple unpack: unresolvable
        break

    return None, True


_PARSE_FAILED = object()  # sentinel for cached parse failures


def _load_source_analysis(src_path, cache):
    """Load and parse a source file, cached by path."""
    if src_path in cache:
        v = cache[src_path]
        return None if v is _PARSE_FAILED else v
    try:
        with open(src_path, encoding="utf-8") as f:
            source_text = f.read()
        tree = ast.parse(source_text, filename=src_path)
        visitor = BindingVisitor(source_text)
        visitor.visit(tree)
        cache[src_path] = visitor
        return visitor
    except Exception:
        cache[src_path] = _PARSE_FAILED
        return None


def _extract_source_evidence(proj_root, rec, analysis_cache=None):
    """Extract call-site-aware source-code evidence for a receiver."""
    if analysis_cache is None:
        analysis_cache = {}
    rel_file = rec.get("file", "")
    func_name = rec.get("pcresolve_func_name", "") or ""
    root = func_name.split(".")[0] if func_name else ""
    if not root:
        return None

    src_path = os.path.join(proj_root, rel_file)
    if not os.path.exists(src_path):
        return None

    visitor = _load_source_analysis(src_path, analysis_cache)
    if visitor is None:
        return None

    rec_lineno = rec.get("lineno", 0)
    rec_col = rec.get("col_offset", 0)
    call_frame_path = visitor.scope_of_call.get((rec_lineno, rec_col))
    if call_frame_path is None:
        return None  # no precise call position -> unresolved

    if root not in visitor.bindings:
        return None

    binding = _find_binding_before(
        visitor.bindings[root], call_frame_path, rec_lineno, rec_col)
    if binding is None:
        return None

    owner, needs_human = _resolve_owner(
        root, visitor.bindings, call_frame_path, rec_lineno, rec_col)

    # Only record the actually-selected binding; the group renderer
    # merges bindings from all records in the group.
    all_unique = {(rel_file, binding.lineno, binding.value[:80])}

    return {
        "receiver": root,
        "receiver_path": func_name.rsplit(".", 1)[0] if "." in func_name else root,
        "binding_value": binding.value,
        "binding_line": binding.lineno,
        "binding_file": rel_file,
        "call_frame_path": list(call_frame_path),
        "owner": owner,
        "needs_human_from_resolve": needs_human,
        "all_bindings": sorted(all_unique),
    }


# ---------------------------------------------------------------------------
# GT proposal
# ---------------------------------------------------------------------------

_RETURN_TYPE_RULES = {
    ("seaborn", "barplot"): "matplotlib",
    ("seaborn", "stripplot"): "matplotlib",
    ("seaborn", "swarmplot"): "matplotlib",
    ("seaborn", "boxplot"): "matplotlib",
    ("seaborn", "violinplot"): "matplotlib",
    ("seaborn", "pointplot"): "matplotlib",
    ("seaborn", "countplot"): "matplotlib",
    ("seaborn", "scatterplot"): "matplotlib",
    ("seaborn", "lineplot"): "matplotlib",
    ("seaborn", "histplot"): "matplotlib",
    ("seaborn", "kdeplot"): "matplotlib",
    ("seaborn", "heatmap"): "matplotlib",
    ("pystan", "sampling"): "pystan",
}


def _propose_gt(rec, evidence):
    if evidence is None:
        return ("?", "?", "no source evidence found", True)

    value = evidence.get("binding_value", "")
    owner = evidence.get("owner")
    needs_resolve = evidence.get("needs_human_from_resolve", True)

    # AST-based container literal detection
    try:
        expr = ast.parse(value.strip(), mode="eval").body
    except Exception:
        expr = None

    if isinstance(expr, ast.List) and not expr.elts:
        return ("python", "python", "empty list literal []", False)
    if isinstance(expr, ast.Dict) and not expr.keys:
        return ("python", "python", "empty dict literal {}", False)

    if _is_import_binding(value):
        mod = _import_module(value)
        if mod:
            return ("library", mod.split(".")[0], "import %s" % mod, False)

    if owner and not needs_resolve:
        m = re.match(r'(\w+)\.(\w+)\(', value)
        if m:
            alias, method = m.group(1), m.group(2)
            for (lib, meth), actual in _RETURN_TYPE_RULES.items():
                if owner == lib and method == meth:
                    return ("library", actual,
                            "%s.%s() returns %s" % (alias, method, actual), False)
        return ("library", owner, "resolved via %s" % value[:60], False)

    return ("?", "?", "unresolved receiver: %s" % value[:60], True)


# ---------------------------------------------------------------------------
# Grouping & rendering
# ---------------------------------------------------------------------------

def _receiver_root(rec):
    func = rec.get("pcresolve_func_name", "") or ""
    return func.split(".")[0] if func else "?"


def _scope_identity(ev):
    """Return a tuple discriminating receiver scope for grouping."""
    rp = ev.get("receiver_path", "")
    frame_path = tuple(tuple(f) for f in ev.get("call_frame_path", []))
    if rp == "self" or rp.startswith("self."):
        class_frames = tuple(f for f in frame_path if f[0] == KIND_CLASS)
        return ("class", ev.get("binding_file", ""), class_frames)
    if (ev.get("binding_value") or "").startswith("parameter "):
        return ("param", ev.get("binding_file", ""), frame_path)
    return ("global", ev.get("binding_file", ""), ())


def _group_key(rec):
    """Return a 7-tuple for grouping records by evidence identity."""
    ev = rec.get("_evidence") or {}
    return (
        ev.get("receiver_path", _receiver_root(rec)),
        _scope_identity(ev),
        ev.get("binding_value", ""),
        rec.get("pcresolve_reason", ""),
        rec.get("_proposed_kind", "?"),
        rec.get("_proposed_top", "?"),
        rec.get("_needs_human", True),
    )


def group_project(proj_name, proj_info):
    path = os.path.join(CALLS_DIR, proj_name + ".jsonl")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        records = [json.loads(l) for l in f if l.strip()]

    proj_root = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", proj_info.get("path", "")))

    drafts = [r for r in records if r.get("annotation_status") == "draft"]
    awaiting_review = [r for r in drafts if r.get("expected_kind")]
    unlabeled = [r for r in drafts if not r.get("expected_kind")]

    analysis_cache = {}
    for r in unlabeled:
        evidence = _extract_source_evidence(proj_root, r, analysis_cache)
        r["_evidence"] = evidence
        pk, pt, pn, nh = _propose_gt(r, evidence)
        r["_proposed_kind"] = pk
        r["_proposed_top"] = pt
        r["_proposed_notes"] = pn
        r["_needs_human"] = nh

    groups = {}
    for r in unlabeled:
        key = _group_key(r)
        groups.setdefault(key, []).append(r)

    return {
        "project": proj_name, "total_drafts": len(drafts),
        "unlabeled": len(unlabeled),
        "awaiting_review_recs": awaiting_review, "groups": groups,
    }


def _group_evidence_level(recs):
    sample = recs[0]
    if sample.get("_needs_human", True):
        return "manual_reasoned"
    if sample.get("pcresolve_reason") == "TRANSITIVE_IMPORT":
        return "static_obvious"
    return "static_context"


def _md_text(value):
    """Escape text for use in Markdown (table cells or body)."""
    return _html.escape(str(value), quote=False).replace("|", "&#124;")

def _md_code(value):
    """Escape and wrap text as inline code (handles pipes correctly)."""
    return "<code>%s</code>" % _md_text(value)


def write_group_md(data):
    proj = data["project"]
    out_dir = os.path.join(REVIEW_DIR, proj)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "annotation_groups.md")

    lines = []
    total_groups = len(data["groups"])
    total_all = data["total_drafts"]
    total_awaiting = len(data["awaiting_review_recs"])

    lines.append("# %s -- Annotation Groups (%d groups, %d records)" % (
        proj, total_groups, total_all))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Evidence | Groups | Records | Needs Human |")
    lines.append("|----------|--------|---------|-------------|")

    by_evidence = {}
    for key, recs in data["groups"].items():
        level = _group_evidence_level(recs)
        nh_count = sum(1 for r in recs if r.get("_needs_human", True))
        by_evidence.setdefault(level, {"groups": 0, "records": 0, "needs": 0})
        by_evidence[level]["groups"] += 1
        by_evidence[level]["records"] += len(recs)
        by_evidence[level]["needs"] += nh_count

    for level in ("static_obvious", "static_context", "manual_reasoned"):
        if level in by_evidence:
            e = by_evidence[level]
            lines.append("| %s | %d | %d | %d |" % (
                level, e["groups"], e["records"], e["needs"]))
    if total_awaiting > 0:
        lines.append("| awaiting_review | -- | %d | %d |" % (
            total_awaiting, total_awaiting))

    total_needs = sum(
        1 for recs in data["groups"].values()
        for r in recs if r.get("_needs_human", True))
    lines.append("| **Total** | **%d** | **%d** | **%d** |" % (
        total_groups, total_all, total_needs + total_awaiting))
    lines.append("")

    sorted_groups = sorted(data["groups"].items(),
                           key=lambda x: (-len(x[1]), x[0][5], x[0][0]))
    gid = 0
    for key, recs in sorted_groups:
        gid += 1
        recv_path, scope_id, binding_val, reason, pk, pt, nh = key
        sample = recs[0]
        evidence = sample.get("_evidence")
        level = _group_evidence_level(recs)
        nh_count = sum(1 for r in recs if r.get("_needs_human", True))

        lines.append("## Group %d: %s -> %s/%s (%d records)" % (
            gid, _md_text(recv_path), _md_text(pk), _md_text(pt), len(recs)))
        lines.append("")
        lines.append("| Evidence | %s |" % level)
        lines.append("| Needs human | %s (%d/%d) |" % (
            "yes" if nh else "no", nh_count, len(recs)))
        lines.append("| Reason | %s |" % _md_text(reason))
        if evidence:
            lines.append("| Key binding | %s @ %s:%d |" % (
                _md_code(evidence.get("binding_value", "?")[:80]),
                _md_text(evidence.get("binding_file", "?")),
                evidence.get("binding_line", 0)))
            lines.append("| Owner | %s |" % (
                _md_text(str(evidence.get("owner", "unresolved")))))
        lines.append("| Proposed GT | %s / %s |" % (
            _md_text(pk), _md_text(pt)))
        lines.append("")

        lines.append("**All expressions:**" if nh else
                     "**Representative expressions:**")
        lines.append("")
        visible = recs if nh else recs[:5]
        for r in visible:
            lines.append("- %s -- %s:%d" % (
                _md_code(r.get("expression", "")[:100]),
                _md_text(r.get("file", "")),
                r.get("lineno", 0)))
        if not nh and len(recs) > 5:
            lines.append("- ... and %d more" % (len(recs) - 5))
        lines.append("")

        all_unique = set()
        for r in recs:
            ev = r.get("_evidence")
            if ev and ev.get("all_bindings"):
                all_unique.update(ev["all_bindings"])
        if all_unique:
            lines.append("**All bindings (%d unique):**" % len(all_unique))
            for fname, bline, bval in sorted(all_unique):
                lines.append("- %s L%d: %s" % (
                    _md_code(fname), bline, _md_code(bval)))
        lines.append("")

    if data["awaiting_review_recs"]:
        arecs = data["awaiting_review_recs"]
        lines.append("## Awaiting Review (%d records)" % len(arecs))
        lines.append("")
        lines.append("| Expression | File:Line | GT | Notes |")
        lines.append("|------------|-----------|----|-------|")
        for r in arecs:
            lines.append("| %s | %s:%d | %s/%s | %s |" % (
                _md_code(r.get("expression", "")[:60]),
                _md_text(r.get("file", "")),
                r.get("lineno", 0),
                _md_text(r.get("expected_kind", "")),
                _md_text(r.get("expected_top_library", "")),
                _md_text(r.get("verification_notes", "")[:60])))
        lines.append("")

    while lines and not lines[-1]:
        lines.pop()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Group draft GT records by receiver-binding evidence")
    parser.add_argument("--project", action="append", dest="projects")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    projects = DRAFT_PROJECTS if args.all else (args.projects or [])
    if not projects:
        print("Usage: --project NAME or --all")
        sys.exit(1)

    manifest_path = os.path.join(GT_DIR, "projects.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)["projects"]

    for proj in projects:
        proj_info = manifest.get(proj, {})
        data = group_project(proj, proj_info)
        if data is None:
            print("SKIP %s: no JSONL" % proj)
            continue
        path = write_group_md(data)
        print("%s: %d groups, %d unlabeled + %d awaiting = %d total -> %s" % (
            proj, len(data["groups"]), data["unlabeled"],
            len(data["awaiting_review_recs"]),
            data["total_drafts"], path))


if __name__ == "__main__":
    main()
