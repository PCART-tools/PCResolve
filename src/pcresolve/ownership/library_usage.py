## @package pcresolve.ownership.library_usage
#  Build library usage views.
#
#
#  Aggregates call and provenance evidence into per-library usage records.
#  根据调用和来源证据聚合各库的使用记录。



import os

from pcresolve.ownership.types import LibraryUsage


## Check whether a library name string is suitable for library_usage.
## 检查字符串是否适合作为 library_usage 中的库名称。
#
#  @param name Candidate library name.
#  @return True if not a dataclass repr or structured source display.
def _is_legal_library_name(name):
    if not isinstance(name, str):
        return False
    if name.startswith("InstanceMethod("):
        return False
    if name.startswith("ContainerItem("):
        return False
    if name.startswith("ContainerIter("):
        return False
    if name.startswith("CallResult("):
        return False
    if name.startswith("UnknownSource("):
        return False
    if name.startswith("SourceSet("):
        return False
    if name.startswith("[") and name.endswith("]"):
        return False
    return True


## Normalize a file path to a relative POSIX path for library usage reporting.
## 将文件路径规范化为库使用报告中的相对 POSIX 路径。
#
#  @param file_path Absolute file path.
#  @param project_root Root directory to make relative.
#  @return Relative POSIX path, or empty string.
def _normalize_path_for_usage(file_path, project_root):
    if not file_path:
        return ""
    try:
        rel = os.path.relpath(file_path, project_root)
    except ValueError:
        rel = file_path
    result = rel.replace(os.sep, "/")
    if os.altsep:
        result = result.replace(os.altsep, "/")
    return result


## Build a library usage index from calls and provenance.
## 根据调用和符号来源构建库使用索引。
#
#  This is a module-level function extracted from
#  ProjectAnalyzer._build_library_usage().  It takes a
#  project_root for path normalization and returns a sorted
#  dict of library_name -> LibraryUsage.
#
#  @param project_root  Project root directory.
#  @param all_api_calls List of ApiCall records.
#  @param all_provenance List of SymbolProvenance records.
#  @return Dict of library_name -> LibraryUsage.
def build_library_usage(project_root, all_api_calls, all_provenance):
    usage = {}

    ## Create or update the shared evidence envelope for one library.
    ## 创建或更新单个库的共享证据范围。
    #
    #  @param lib Import-backed top-level library name.
    #  @param confidence Evidence confidence.
    #  @param file_path File containing the evidence.
    #  @return Mutable library usage entry.
    def _ensure_usage(lib, confidence, file_path):
        if lib not in usage:
            usage[lib] = LibraryUsage(library=lib)
        u = usage[lib]
        u.has_evidence = True
        u.min_confidence = min(u.min_confidence or 1.0, confidence or 1.0)
        u.max_confidence = max(u.max_confidence, confidence or 1.0)
        fp = _normalize_path_for_usage(file_path, project_root)
        if fp and fp not in u.files:
            u.files.append(fp)
        return u

    for call in all_api_calls:
        libs = _collect_usage_libs(
            call.top_library, getattr(call, 'alternatives', None))
        for lib in libs:
            u = _ensure_usage(lib, getattr(call, 'confidence', 1.0),
                              call.file_path)
            u.api_call_count += 1
            reason = getattr(call, 'reason', '') or ''
            if reason:
                u.reason_counts[reason] = u.reason_counts.get(reason, 0) + 1

    # Count symbol evidence separately from call-site evidence.
    # 分别统计符号证据和调用点证据。
    for prov in all_provenance:
        libs = _collect_usage_libs(
            prov.top_library,
            getattr(prov, 'alternatives', None),
            getattr(prov, 'top_libraries', None))
        for lib in libs:
            u = _ensure_usage(lib, getattr(prov, 'confidence', 1.0),
                              prov.file_path)
            u.symbol_count += 1
            if prov.kind == "import":
                if prov.symbol not in u.imports:
                    u.imports.append(prov.symbol)
            kind = prov.kind if prov.kind else "unknown"
            u.kind_counts[kind] = u.kind_counts.get(kind, 0) + 1
            reason = getattr(prov, 'reason', '') or ''
            if reason:
                u.reason_counts[reason] = u.reason_counts.get(reason, 0) + 1

    for u in usage.values():
        u.files.sort()
        u.imports.sort()
    return {k: u for k, u in sorted(usage.items())}


## Check whether a name should be counted as a usage library.
## 判断名称是否应计入库使用统计。
#
#  @param name Candidate library name.
#  @return True if the name is a valid import-backed library owner.
def _is_usage_library(name):
    if name in ("", None, "local", "python", "unknown"):
        return False
    if not _is_legal_library_name(name):
        return False
    return True


## Collect a library name and its alternatives for usage aggregation.
## 收集主库名称及其候选项，供使用统计聚合。
#
#  @param primary Primary top library from evidence.
#  @param alternatives List of alternative top libraries.
#  @param top_libraries Optional list of top_libraries (provenance).
#  @return Deduplicated list of library names passing _is_usage_library.
def _collect_usage_libs(primary, alternatives=None, top_libraries=None):
    libs = []
    for lib in (top_libraries or []):
        if _is_usage_library(lib) and lib not in libs:
            libs.append(lib)
    if _is_usage_library(primary) and primary not in libs:
        libs.append(primary)
    for alt in (alternatives or []):
        if _is_usage_library(alt) and alt not in libs:
            libs.append(alt)
    return libs
