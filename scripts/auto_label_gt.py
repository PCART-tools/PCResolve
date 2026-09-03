#!/usr/bin/env python3
## @package scripts.auto_label_gt
#  Auto-label GT JSONL records with high-confidence rules only.
#
#  Fills expected_kind, expected_top_library, category,
#  verification_level, and status for records whose pcresolve_*
#  fields provide mechanically-confirmable evidence.
#  Ambiguous records (transitive receiver, parameter propagation,
#  conversion boundary, etc.) stay draft for human review.
#
#  High-confidence rules (priority order):
#
#    DIRECT_IMPORT + source import binding
#                         -> expected=pcresolve, category=direct_import,
#                            verification_level=static_obvious
#    BUILTIN + literal receiver
#                         -> expected=python/python, category=builtin,
#                            verification_level=static_obvious
#    decorated_by non-empty
#       + top=local       -> expected=local/local,
#                            category=decorated_callable_receiver,
#                            verification_level=static_context
#    LOCAL_DEFINITION
#       + top=local       -> expected=local/local, category=local_call,
#                            verification_level=static_obvious
#
#  NOT auto-labeled (stay draft for human review):
#    - DIRECT_IMPORT reason without a matching source import binding
#    - Bare or dotted builtin names without independent scope evidence
#    - TRANSITIVE_IMPORT
#    - RETURN_PROPAGATION / PARAMETER_PROPAGATION
#    - LOCAL_DEFINITION + top!=local
#    - Receiver method calls on transitively-traced objects
#    - Conversion boundaries
#    - Manual GT entries
#    - Unknown / empty pcresolve_reason
#
#  Usage:
#    python scripts/auto_label_gt.py                        # draft evaluation projects
#    python scripts/auto_label_gt.py --all                   # all evaluation projects
#    python scripts/auto_label_gt.py --project django        # single project
#    python scripts/auto_label_gt.py --dry-run               # preview only

import ast
import json
import os
import sys

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")

ANNOTATION_AUTO = "auto_labeled"


def _kind_from_top(top):
    if top in ("local", "python", "unknown", ""):
        return top
    return "library"


## Collect unambiguous, file-wide import bindings from a Python source file.
#
#  Any non-import binding of the same name removes the alias from the result.
#  This deliberately under-labels when scope or assignment order would require
#  deeper reasoning; such records belong in the grouped review queue.
#  @param source_path Python source path.
#  @return Dict mapping source alias to imported top-level module.
def _collect_import_bindings(source_path):
    try:
        with open(source_path, encoding="utf-8") as stream:
            tree = ast.parse(stream.read(), filename=source_path)
    except (OSError, SyntaxError, UnicodeError):
        return {}

    candidates = {}
    shadowed = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                top = alias.name.split(".")[0]
                candidates.setdefault(bound, set()).add(top)
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if not top:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                candidates.setdefault(bound, set()).add(top)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            shadowed.add(node.id)
        elif isinstance(node, ast.arg):
            shadowed.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            shadowed.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            shadowed.add(node.name)

    return {
        name: next(iter(tops))
        for name, tops in candidates.items()
        if name not in shadowed and len(tops) == 1
    }


## Check that a callable root is independently bound by an import statement.
#  @param func_name Resolved callable display name.
#  @param top Expected import-backed top-level module.
#  @param import_bindings Dict returned by _collect_import_bindings().
#  @return True when the source import independently supports the owner.
def _has_import_binding(func_name, top, import_bindings):
    if not import_bindings or not func_name or not top:
        return False
    root = func_name.split(".")[0].split("(")[0]
    return import_bindings.get(root) == top


## Clear fields produced by an earlier auto-label pass.
#  @param rec Ground-truth record to reset to draft state.
def _clear_previous_auto_label(rec):
    if rec.get("annotation_status") != ANNOTATION_AUTO:
        return
    rec["expected_kind"] = ""
    rec["expected_top_library"] = ""
    rec["expected_alternatives"] = []
    rec["expected_decorated_by"] = []
    rec["status"] = ""
    rec["annotation_status"] = "draft"
    rec["category"] = ""
    rec["verification_level"] = ""
    rec["verification_notes"] = ""


def _auto_label(rec, import_bindings=None):
    """Apply high-confidence auto-label rules. Returns True if labeled."""
    _clear_previous_auto_label(rec)
    reason = rec.get("pcresolve_reason", "") or ""
    top = rec.get("pcresolve_top_library", "") or ""
    decorated_by = rec.get("pcresolve_decorated_by", []) or []

    # -- Rule 1a: Import-backed dotted module call --------------------------
    # e.g. tornado.gen.Callback(cb_id) — the func_name is a fully-qualified
    # import chain (tornado.gen.Callback) and the top is tornado.  Safe to
    # auto-label as library.  Must precede Rule 1 to catch these before the
    # generic TRANSITIVE_IMPORT draft decision.
    #
    # Distinguished from receiver methods (self.r.set, stream.read_until)
    # by checking that func_name starts with top_library + ".".
    func_name = rec.get("pcresolve_func_name", "") or ""
    if (reason == "TRANSITIVE_IMPORT"
            and _kind_from_top(top) == "library"
            and func_name.startswith(top + ".")
            and _has_import_binding(func_name, top, import_bindings)):
        rec["expected_kind"] = "library"
        rec["expected_top_library"] = top
        # Chained calls through method results (e.g.
        # tornado.ioloop.IOLoop.instance().start()) are import-backed
        # chains, not pure direct imports.
        if "()" in func_name:
            rec["category"] = "transitive_method"
            rec["verification_level"] = "static_context"
            rec["annotation_status"] = "draft"  # static_context → needs human review
        else:
            rec["category"] = "direct_import"
            rec["verification_level"] = "static_obvious"
            rec["annotation_status"] = ANNOTATION_AUTO
        rec["verification_notes"] = (
            "import-backed dotted module call: %s" % func_name)
        rec["status"] = "positive"
        return True

    # -- Rule 1b: DIRECT_IMPORT ----------------------------------------------
    if (reason == "DIRECT_IMPORT"
            and _kind_from_top(top) == "library"
            and _has_import_binding(func_name, top, import_bindings)):
        rec["expected_kind"] = "library"
        rec["expected_top_library"] = top
        rec["category"] = "direct_import"
        rec["verification_level"] = "static_obvious"
        rec["verification_notes"] = "direct import-backed API call"
        rec["status"] = "positive"
        rec["annotation_status"] = ANNOTATION_AUTO
        return True

    # -- Rule 2: BUILTIN — independent evidence required --------------------
    #  Only a literal receiver is independent of PCResolve's own scope and
    #  reason output.  Bare names such as open() and dotted names such as
    #  object.__new__ may be shadowed, so they remain draft until a separate
    #  scope-evidence verifier confirms the binding.
    if reason == "BUILTIN":
        func_name = rec.get("pcresolve_func_name", "") or ""
        first_token = func_name.split(".")[0] if func_name else ""

        # Literal string receiver, e.g. "{}".format(...).
        if first_token and (first_token.startswith("'") or first_token.startswith('"')):
            rec["expected_kind"] = "python"
            rec["expected_top_library"] = "python"
            rec["category"] = "builtin"
            rec["verification_level"] = "static_obvious"
            rec["verification_notes"] = "Python string literal method call"
            rec["status"] = "positive"
            rec["annotation_status"] = ANNOTATION_AUTO
            return True
        return False

    # -- Rule 3: decorated_by non-empty, top=local ---------------------------
    # Must precede LOCAL_DEFINITION — a decorated local callable needs
    # decorated_callable_receiver, not plain local_call.
    if decorated_by and top == "local":
        rec["expected_kind"] = "local"
        rec["expected_top_library"] = "local"
        rec["expected_decorated_by"] = list(decorated_by)
        rec["category"] = "decorated_callable_receiver"
        rec["verification_level"] = "static_context"
        rec["verification_notes"] = (
            "decorated local callable; primary identity is local, "
            "decorator evidence in decorated_by")
        rec["status"] = "positive"
        rec["annotation_status"] = "draft"  # static_context → needs human review
        return True

    # -- Rule 4: LOCAL_DEFINITION + top=local, bare-name call ---------------
    # Only auto-label bare-name calls (no dot in func_name).
    # Dotted receiver calls (stream.read_until, self.dispatch,
    # line.split, msg.format) stay draft — the receiver may come
    # from a parameter, framework object, or container whose
    # ownership needs human confirmation.
    if reason == "LOCAL_DEFINITION" and top == "local":
        func_name = rec.get("pcresolve_func_name", "") or ""
        if "." not in func_name:
            rec["expected_kind"] = "local"
            rec["expected_top_library"] = "local"
            rec["category"] = "local_call"
            rec["verification_level"] = "static_obvious"
            rec["verification_notes"] = "project-local function/method call"
            rec["status"] = "positive"
            rec["annotation_status"] = ANNOTATION_AUTO
            return True
        # Dotted receiver: stay draft for human review.
        return False

    # -- No high-confidence rule matched: stay draft -------------------------
    return False


def load_manifest():
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return json.load(f)["projects"]


def main():
    manifest = load_manifest()
    args = sys.argv[1:]

    selected = set()
    all_projects = "--all" in args
    dry_run = "--dry-run" in args
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--project="):
            selected.add(a.split("=", 1)[1])
        elif a == "--project":
            if i + 1 < len(args):
                i += 1
                selected.add(args[i])
        elif a in ("--all", "--dry-run"):
            pass
        elif a in ("-h", "--help"):
            print("Usage: python scripts/auto_label_gt.py [--all] [--project NAME] [--dry-run]")
            return 0
        i += 1

    pilot_names = [n for n, info in manifest.items()
                   if info.get("tier") == "pilot"]
    if not all_projects and not selected:
        # Default: only draft evaluation projects.
        target_names = [n for n in pilot_names
                        if manifest.get(n, {}).get("status") != "locked"]
    elif selected:
        target_names = [n for n in pilot_names if n in selected]
    else:
        target_names = list(pilot_names)

    total_labeled = 0
    total_kept_draft = 0

    for name in sorted(target_names):
        path = os.path.join(CALLS_DIR, name + ".jsonl")
        if not os.path.exists(path):
            print("SKIP %s: JSONL not found" % name, file=sys.stderr)
            continue

        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        project_root = os.path.abspath(os.path.join(
            GT_DIR, "..", manifest.get(name, {}).get("path", "")))
        import_cache = {}
        labeled = 0
        kept = 0
        for rec in records:
            if rec.get("annotation_status") in ("reviewed", "locked"):
                continue  # Don't touch already-reviewed records
            if rec.get("source") == "manual_gt":
                continue  # Manual entries need human review
            rel_path = rec.get("file", "")
            if rel_path not in import_cache:
                import_cache[rel_path] = _collect_import_bindings(
                    os.path.join(project_root, rel_path))
            if _auto_label(rec, import_cache[rel_path]):
                labeled += 1
            else:
                kept += 1

        if not dry_run:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        print("%-22s %3d auto-labeled  %3d kept draft"
              % (name, labeled, kept))
        total_labeled += labeled
        total_kept_draft += kept

    print("\nTotal: %d auto-labeled, %d kept draft"
          % (total_labeled, total_kept_draft))
    if dry_run:
        print("(dry run — no files written)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
