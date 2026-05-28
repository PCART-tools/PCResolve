## @package pcresolve.decorator_provenance
#  Decorator provenance index and evidence helpers (Phase 9-lite PR2).
#
#  Extracted from cross_file.ProjectAnalyzer so decorator evidence
#  matching (_build_decorator_index, _lookup_decorated_by) lives in
#  one place.  Does not import ProjectAnalyzer or SingleFileAnalyzer.


## Build a decorator evidence index from SymbolProvenance records.
#
#  Keys are (file_path, scope_name, symbol) tuples; values are
#  lists of third-party library names that decorate the symbol.
#  Local/python/unknown/empty top_library entries are excluded.
#
#  @param all_provenance List of SymbolProvenance records.
#  @return Dict of (file_path, scope_name, symbol) -> [library, ...].
def build_decorator_index(all_provenance):
    index = {}
    for prov in all_provenance:
        if prov.kind == "decorated_by":
            if prov.top_library in ("", "local", "python", "unknown"):
                continue
            key = (prov.file_path, prov.scope_name or "", prov.symbol)
            if prov.top_library not in index.setdefault(key, []):
                index[key].append(prov.top_library)
    return index


## Look up decorator evidence for an ApiCall from the index.
#
#  Matches by (file_path, scope_name, func_name).  Scope-aware
#  matching prevents cross-scope pollution in both directions.
#
#  @param file_path  File path of the call.
#  @param func_name  Function name (or base name) of the call.
#  @param scope_name Scope where the call occurs ("" for module-level).
#  @param deco_by    Decorator evidence index from build_decorator_index().
#  @return List of library names that decorate the target.
def lookup_decorated_by(file_path, func_name, scope_name, deco_by):
    key = (file_path, scope_name or "", func_name or "")
    return list(deco_by.get(key, []))
