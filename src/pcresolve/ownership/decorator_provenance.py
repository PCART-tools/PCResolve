## @package pcresolve.ownership.decorator_provenance
#  Index decorator provenance.
#
#
#  Indexes decorator evidence and matches it to calls without importing
#  the project or single-file analyzer implementations.
#  建立装饰器证据索引并匹配调用，不依赖项目或单文件分析器实现。



## Build a decorator evidence index from SymbolProvenance records.
## 根据 SymbolProvenance 记录构建装饰器证据索引。
#
#  Keys are (file_path, scope_name, symbol) tuples; values are
#  lists of import-backed library names that decorate the symbol.
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
## 从索引中查找 API 调用的装饰器证据。
#
#  Matches by (file_path, scope_name, func_name).  Scope-aware
#  matching prevents cross-scope pollution in both directions.
#
#  For dotted func_names (e.g. "hello.main"), also tries the receiver
#  part ("hello") so that decorator evidence on the decorated callable
#  propagates to receiver method calls.  Does NOT guess libraries from
#  method names alone.
#
#  @param file_path  File path of the call.
#  @param func_name  Function name (or base name) of the call.
#  @param scope_name Scope where the call occurs ("" for module-level).
#  @param deco_by    Decorator evidence index from build_decorator_index().
#  @return List of library names that decorate the target.
def lookup_decorated_by(file_path, func_name, scope_name, deco_by):
    key = (file_path, scope_name or "", func_name or "")
    result = list(deco_by.get(key, []))
    # For dotted names, check the receiver only within the same file and scope.
    # 对点分隔名称，仅在同一文件和作用域中查找接收者的装饰器证据。
    if not result and func_name and '.' in func_name:
        receiver = func_name.split('.')[0]
        receiver_key = (file_path, scope_name or "", receiver)
        result = list(deco_by.get(receiver_key, []))
    return result
