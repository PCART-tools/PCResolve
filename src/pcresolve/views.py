## @package pcresolve.views
#  Output views for ProjectAnalysis facts.
#
#  Pure functions: take ProjectAnalysis, return dict/list/str.
#  Do NOT print, read files, or re-analyze.
#  All paths are returned as relative POSIX.
#  将项目分析结果转换为输出视图，不执行分析或读取文件。

import os

from .sources import source_to_legacy


## Build the summary view (small, stable, for CI/scripts).
## 构建供 CI 和脚本使用的精简稳定摘要视图。
#
#  @param result ProjectAnalysis result.
#  @param top Maximum entries in per-library detail (0 = unlimited).
#  @return Dict suitable for JSON serialization.
def build_summary_view(result, top=20):
    stats = result.stats.copy()
    stats["api_call_count"] = len(result.all_api_calls)
    stats["library_count"] = len(result.library_usage)
    diag_errors = sum(1 for d in result.diagnostics if d.severity == "error")
    diag_warnings = sum(1 for d in result.diagnostics if d.severity == "warning")
    stats["diagnostic_error_count"] = diag_errors
    stats["diagnostic_warning_count"] = diag_warnings

    libraries = {}
    for lib, u in result.library_usage.items():
        entry = {
            "api_call_count": u.api_call_count,
            "symbol_count": u.symbol_count,
            "file_count": len(u.files),
            "files": u.files[:top] if top > 0 else u.files,
            "imports": u.imports,
            "kind_counts": u.kind_counts,
            "reason_counts": u.reason_counts,
            "min_confidence": u.min_confidence,
            "max_confidence": u.max_confidence,
        }
        libraries[lib] = entry

    diags = []
    for d in result.diagnostics:
        diags.append({
            "code": d.code,
            "message": d.message,
            "severity": d.severity,
            "file_path": _relpath(d.file_path, result.project_root),
            "lineno": d.lineno,
            "col_offset": d.col_offset,
        })

    return {
        "schema_version": result.schema_version,
        "profile": "summary",
        "project_root": _relpath(result.project_root, result.project_root),
        "stats": stats,
        "diagnostics": diags,
        "libraries": libraries,
    }


## Build the full view (all facts, for debugging / golden regression).
## 构建包含全部输出事实的完整视图，用于调试和基准回归。
#
#  @param result ProjectAnalysis result.
#  @return Dict suitable for JSON serialization.
def build_full_view(result):
    root = result.project_root

    files = []
    for f in result.files:
        file_entry = {
            "file_path": _relpath(f.file_path, root),
            "module_name": f.module_name,
            "symbols": _json_value(f.symbols),
            "chains": _json_value(f.chains),
            "api_calls": [_full_api_call(c, root) for c in f.api_calls],
            "diagnostics": [_full_diagnostic(d, root) for d in f.diagnostics],
            "symbol_provenance": [_full_provenance(p, root) for p in f.symbol_provenance],
        }
        files.append(file_entry)

    all_calls = [_full_api_call(c, root) for c in result.all_api_calls]
    all_prov = [_full_provenance(p, root) for p in result.all_symbol_provenance]
    library_usage = {}
    for lib, u in result.library_usage.items():
        library_usage[lib] = _full_library_usage(u)

    diags = [_full_diagnostic(d, root) for d in result.diagnostics]

    return {
        "schema_version": result.schema_version,
        "profile": "full",
        "project_root": _relpath(root, root),
        "files": files,
        "all_api_calls": all_calls,
        "diagnostics": diags,
        "all_symbol_provenance": all_prov,
        "library_usage": library_usage,
        "stats": result.stats,
    }


## Build an explain library view.
## 构建库使用解释视图。
#
#  @param result ProjectAnalysis result.
#  @param library Library name to explain.
#  @param top Maximum calls/symbols to list (0 = unlimited).
#  @return Dict or None if library not found.
def build_explain_library_view(result, library, top=20):
    usage = result.library_usage.get(library)
    if not usage:
        return None
    calls = [c for c in result.all_api_calls if c.top_library == library]
    provs = [p for p in result.all_symbol_provenance if p.top_library == library]
    # Count all primary-owner matches before limiting displayed examples.
    # 限制展示样例前，先统计所有主归属匹配的每文件调用和符号。
    file_stats = {}
    for c in calls:
        fp = _relpath(c.file_path, result.project_root)
        if fp not in file_stats:
            file_stats[fp] = {"calls": 0, "symbols": 0}
        file_stats[fp]["calls"] += 1
    for p in provs:
        fp = _relpath(p.file_path, result.project_root)
        if fp not in file_stats:
            file_stats[fp] = {"calls": 0, "symbols": 0}
        file_stats[fp]["symbols"] += 1
    if top > 0:
        calls = calls[:top]
        provs = provs[:top]
    return {
        "library": library,
        "api_call_count": usage.api_call_count,
        "symbol_count": usage.symbol_count,
        "files": usage.files,
        "imports": usage.imports,
        "kind_counts": usage.kind_counts,
        "reason_counts": usage.reason_counts,
        "min_confidence": usage.min_confidence,
        "max_confidence": usage.max_confidence,
        "file_stats": file_stats,
        "top_calls": [_full_api_call(c, result.project_root) for c in calls],
        "top_symbols": [_full_provenance(p, result.project_root) for p in provs],
    }


## Build an explain symbol view.
## 构建符号来源解释视图。
#
#  @param result ProjectAnalysis result.
#  @param symbol Symbol name to search.
#  @param top Maximum matches (0 = unlimited).
#  @return Dict with matches list.
def build_explain_symbol_view(result, symbol, top=20):
    matches = [p for p in result.all_symbol_provenance if p.symbol == symbol]
    if top > 0:
        matches = matches[:top]
    # Find calls using the symbol itself or an attribute rooted at it.
    # 查找使用该符号本身或以其为根的属性调用。
    related = []
    for f in result.files:
        for c in f.api_calls:
            if c.func_name.startswith(symbol + ".") or c.func_name == symbol:
                related.append(c)
    if top > 0:
        related = related[:top]
    return {
        "symbol": symbol,
        "matches": [_full_provenance(m, result.project_root) for m in matches],
        "related_calls": [_full_api_call(c, result.project_root) for c in related],
    }


## Build an explain call view.
## 构建调用归属解释视图。
#
#  @param result ProjectAnalysis result.
#  @param query Exact callable name or dotted path suffix in func_name/resolved_func.
#  @param top Maximum matches (0 = unlimited).
#  @return Dict with matches list.
def build_explain_call_view(result, query, top=20):
    matches = []
    for f in result.files:
        for c in f.api_calls:
            if query and any(
                    name == query or name.endswith('.' + query)
                    for name in (c.func_name, c.resolved_func)):
                matches.append(c)
    count = len(matches)
    if top > 0:
        matches = matches[:top]
    return {
        "query": query,
        "count": count,
        "matches": [_full_api_call(c, result.project_root) for c in matches],
    }


# ── internal helpers ────────────────────────────────────────────────────

## Format a path relative to the project and mark external paths.
## 将路径格式化为项目相对路径，并标记外部路径。
#
#  @param file_path Source path, or an empty value.
#  @param project_root Root used for relative paths.
#  @return POSIX-style path or empty string.
def _relpath(file_path, project_root):
    """Return a relative POSIX path with <external>/ prefix for external paths."""
    if not file_path:
        return ""
    try:
        rel = os.path.relpath(file_path, project_root)
        if rel.startswith(".." + os.sep):
            rel = "<external>/" + rel
    except ValueError:
        rel = "<external>/" + str(file_path)
    result = rel.replace(os.sep, "/")
    if os.altsep:
        result = result.replace(os.altsep, "/")
    return result


## Serialize a call record for the full and explain views.
## 为完整视图和解释视图序列化调用记录。
#
#  @param c API call record.
#  @param root Project root for path formatting.
#  @return JSON-compatible call dictionary.
def _full_api_call(c, root):
    return {
        "expression": c.expression,
        "top_library": c.top_library,
        "base_symbol": _json_value(c.base_symbol),
        "chain": _json_value(c.chain),
        "file_path": _relpath(c.file_path, root),
        "lineno": c.lineno,
        "col_offset": c.col_offset,
        "end_lineno": c.end_lineno,
        "end_col_offset": c.end_col_offset,
        "func_name": c.func_name,
        "parameters": c.parameters,
        "resolved_func": c.resolved_func,
        "resolved_chain": _json_value(c.resolved_chain),
        "reason": c.reason,
        "confidence": c.confidence,
        "alternatives": c.alternatives,
        "decorated_by": c.decorated_by,
    }


## Serialize one symbol provenance record.
## 序列化单个符号来源记录。
#
#  @param p Symbol provenance record.
#  @param root Project root for path formatting.
#  @return JSON-compatible provenance dictionary.
def _full_provenance(p, root):
    return {
        "symbol": p.symbol,
        "kind": p.kind,
        "top_library": p.top_library,
        "top_libraries": p.top_libraries,
        "chain": _json_value(p.chain),
        "scope_name": p.scope_name,
        "file_path": _relpath(p.file_path, root),
        "lineno": p.lineno,
        "col_offset": p.col_offset,
        "reason": p.reason,
        "confidence": p.confidence,
        "alternatives": p.alternatives,
    }


## Serialize one diagnostic with a normalized path.
## 序列化单个诊断并规范化其路径。
#
#  @param d Diagnostic record.
#  @param root Project root for path formatting.
#  @return JSON-compatible diagnostic dictionary.
def _full_diagnostic(d, root):
    return {
        "code": d.code,
        "message": d.message,
        "severity": d.severity,
        "file_path": _relpath(d.file_path, root) if d.file_path else "",
        "lineno": d.lineno,
        "col_offset": d.col_offset,
        "end_lineno": d.end_lineno,
        "end_col_offset": d.end_col_offset,
        "module_name": d.module_name,
    }


## Serialize the aggregate usage evidence for one library.
## 序列化单个库的聚合使用证据。
#
#  @param u Library usage record.
#  @return JSON-compatible usage dictionary.
def _full_library_usage(u):
    return {
        "library": u.library,
        "api_call_count": u.api_call_count,
        "symbol_count": u.symbol_count,
        "files": u.files,
        "imports": u.imports,
        "kind_counts": u.kind_counts,
        "reason_counts": u.reason_counts,
        "has_evidence": u.has_evidence,
        "min_confidence": u.min_confidence,
        "max_confidence": u.max_confidence,
    }


## Recursively convert structured sources and containers to JSON-safe values.
## 递归转换结构化来源和容器为可 JSON 序列化的值。
#
#  @param value Value to convert.
#  @return Converted value with string dictionary keys and list sequences.
def _json_value(value):
    """Recursively convert Source IR and containers to JSON-safe values."""
    converted = source_to_legacy(value)
    if isinstance(converted, dict):
        return {
            str(key): _json_value(item)
            for key, item in converted.items()
        }
    if isinstance(converted, (list, tuple)):
        return [_json_value(item) for item in converted]
    return converted
