#!/usr/bin/env python3
## @package scripts.static_boundary_reviews
#  Validate independently reviewed pure-static ownership boundaries.

import ast
import hashlib
import json
import os


## Return a stable key for one canonical or reviewed call record.
#
#  @param record Ground-truth or boundary-review record.
#  @param project Optional project supplied by a containing review group.
#  @return Tuple identifying the exact call expression.
def boundary_record_key(record, project=""):
    return (
        project or record.get("project", ""),
        record.get("file", "").replace("\\", "/"),
        record.get("lineno", 0),
        record.get("col_offset", 0),
        record.get("expression", ""),
    )


## Hash every Python source path and normalized source body in a project.
#
#  New, removed, renamed, or edited Python sources invalidate an earlier
#  boundary review. Newline normalization keeps the digest stable across
#  Windows and POSIX checkouts.
#  @param project_root Absolute project directory.
#  @return Hexadecimal SHA-256 digest.
def project_source_digest(project_root):
    sources = []
    for dir_path, dir_names, file_names in os.walk(project_root):
        dir_names.sort()
        for file_name in sorted(file_names):
            if not file_name.endswith((".py", ".pyi")):
                continue
            path = os.path.join(dir_path, file_name)
            relative = os.path.relpath(path, project_root).replace("\\", "/")
            with open(path, "rb") as stream:
                source = stream.read().decode("utf-8")
            source = source.replace("\r\n", "\n").replace("\r", "\n")
            sources.append((relative, source))

    digest = hashlib.sha256()
    for relative, source in sources:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


## Load the canonical static-boundary review document.
#
#  @param path JSON document path.
#  @return Parsed review document.
def load_static_boundary_reviews(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _expression_ast(expression):
    try:
        return ast.dump(
            ast.parse(expression, mode="eval").body,
            include_attributes=False,
        )
    except SyntaxError:
        return ""


def _source_has_exact_call(project_root, record, source_cache):
    relative = record.get("file", "").replace("\\", "/")
    path = os.path.normpath(os.path.join(project_root, relative))
    if path not in source_cache:
        try:
            with open(path, encoding="utf-8") as stream:
                source = stream.read()
            source_cache[path] = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            source_cache[path] = None
    tree = source_cache[path]
    if tree is None:
        return False
    expected = _expression_ast(record.get("expression", ""))
    if not expected:
        return False
    return any(
        isinstance(node, ast.Call)
        and node.lineno == record.get("lineno", 0)
        and node.col_offset == record.get("col_offset", 0)
        and ast.dump(node, include_attributes=False) == expected
        for node in ast.walk(tree)
    )


## Validate reviewed boundaries against current source, GT, and predictions.
#
#  A review can waive only a current ``unknown/unknown`` primary mismatch.
#  Correctly resolved records may remain in the document for audit history but
#  no longer appear in the returned active-review mapping.
#  @param document Parsed review document.
#  @param records Canonical ground-truth records.
#  @param project_paths Mapping of project names to source roots.
#  @return Pair of active record-key mapping and validation error list.
def validate_static_boundary_reviews(document, records, project_paths):
    errors = []
    active = {}
    if document.get("schema_version") != 1:
        errors.append("unsupported static boundary review schema")
        return active, errors

    canonical = {}
    for record in records:
        key = boundary_record_key(record)
        if key in canonical:
            errors.append("duplicate canonical GT record: %r" % (key,))
        canonical[key] = record

    seen_ids = set()
    seen_records = set()
    digest_cache = {}
    source_cache = {}
    for review in document.get("reviews", []):
        review_id = review.get("id", "")
        project = review.get("project", "")
        prefix = review_id or "<missing-id>"
        if not review_id or review_id in seen_ids:
            errors.append("duplicate or missing review id: %s" % prefix)
        seen_ids.add(review_id)
        if not all(review.get(name) for name in (
                "reviewed_by", "reviewed_at", "reason")):
            errors.append("%s: incomplete review metadata" % prefix)

        project_root = project_paths.get(project)
        if not project_root or not os.path.isdir(project_root):
            errors.append("%s: missing project source: %s" % (
                prefix, project))
            continue
        if project not in digest_cache:
            try:
                digest_cache[project] = project_source_digest(project_root)
            except (OSError, UnicodeDecodeError) as error:
                errors.append("%s: source digest failed: %s" % (
                    prefix, error))
                continue
        if digest_cache[project] != review.get("project_source_sha256"):
            errors.append("%s: project source digest changed" % prefix)
            continue

        for reviewed in review.get("records", []):
            key = boundary_record_key(reviewed, project)
            if key in seen_records:
                errors.append("duplicate reviewed record: %r" % (key,))
                continue
            seen_records.add(key)
            record = canonical.get(key)
            if record is None:
                errors.append("%s: canonical GT record is missing: %r" % (
                    prefix, key))
                continue
            expected = (
                reviewed.get(
                    "expected_kind", review.get("expected_kind", "")),
                reviewed.get(
                    "expected_top_library",
                    review.get("expected_top_library", "")),
            )
            canonical_expected = (
                record.get("expected_kind", ""),
                record.get("expected_top_library", ""),
            )
            if expected != canonical_expected:
                errors.append("%s: expected owner changed for %r" % (
                    prefix, key))
                continue
            if not _source_has_exact_call(
                    project_root, reviewed, source_cache):
                errors.append("%s: source call no longer matches %r" % (
                    prefix, key))
                continue

            actual = (
                record.get("pcresolve_kind", ""),
                record.get("pcresolve_top_library", ""),
            )
            if actual == canonical_expected:
                continue
            if actual != ("unknown", "unknown"):
                errors.append(
                    "%s: reviewed mismatch must remain unknown/unknown: %r"
                    % (prefix, key))
                continue
            active[key] = {
                "id": review_id,
                "reason": review.get("reason", ""),
                "reviewed_by": review.get("reviewed_by", ""),
                "reviewed_at": review.get("reviewed_at", ""),
            }
    return active, errors
