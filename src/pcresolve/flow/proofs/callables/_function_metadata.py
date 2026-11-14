## @package pcresolve.flow.proofs.callables._function_metadata
#  Default standard wraps on a fresh wrapper and proved plain-function metadata.
#  为新建包装函数和已证明的普通函数验证标准 wraps 元数据复制。

import ast

from pcresolve.flow.proofs.classes._class_partial import _namespace
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Bound default wraps metadata copying, separately from class attribute lookup.
## 有界验证默认 wraps 元数据复制，与类属性查找证明分离。
#
#  @param analyzer Fixed import/source snapshot; target modules are never imported.
#  @param ref Source decorator's identity and containing module.
#  @param scopes Enclosing execution scopes, including the private source factory.
#  @param expression Evaluated function-decorator expression.
#  @param fresh Predicate establishing an unescaped, fresh plain function binding.
#  @param class_read Optional independent plain source-class function lookup proof.
#  @return Metadata-only protocol premise, or None for unknown inputs or namespaces.
def fresh_function_wraps(analyzer, ref, scopes, expression, fresh, class_read=None):
    if (analyzer.index_boundaries or not isinstance(expression, ast.Call) or len(expression.args) != 1
            or expression.keywords
            or not isinstance(expression.func, (ast.Name, ast.Attribute))):
        return None
    wrapped = expression.args[0]
    lookup = None
    if isinstance(wrapped, ast.Name):
        if (not fresh(wrapped.id) or any(wrapped.id in analyzer._scope_facts(scope).bound
                                        for scope in scopes[1:])):
            return None
    elif class_read is None or (lookup := class_read(wrapped)) is None:
        return None

    # Require the exact unshadowed standard binding and stable module namespace.
    # 要求精确且未遮蔽的标准绑定，以及稳定的模块命名空间。
    head, dot, rest = ast.unparse(expression.func).partition('.')
    canonical = analyzer.imports.get(ref.module, {}).get(head, '') + (dot + rest if dot else '')
    if (canonical != 'functools.wraps' or any(head in analyzer._scope_facts(scope).bound
                                            for scope in scopes)
            or not analyzer._stable_import_name(ref.module + '.' + head)
            or not _namespace(analyzer, ('wraps', 'update_wrapper', 'partial',
                                        'WRAPPER_ASSIGNMENTS', 'WRAPPER_UPDATES'))):
        return None
    try:
        stable, _ = _stable_builtin_namespace(analyzer, ref,
            ('getattr', 'setattr', 'AttributeError', 'object', 'type', '__build_class__'))
    except _ClassEffectLimit:
        return None
    if not stable:
        return None

    # The premise describes metadata formation only, not later method effects.
    # 该前提仅描述元数据形成，不证明后续方法效果。
    fact = {'kind': 'standard_fresh_function_metadata_wrapper', 'status': 'source_bound',
        'wrapped_kind': 'source_plain_class_function' if lookup else 'fresh_source_function',
        'wrapper_kind': 'fresh_source_function',
        'completion': 'normal_return_only', 'future_method_effects': 'unmodeled',
        'decorator_evidence': {'file_path': ref.file_path, 'lineno': expression.lineno,
            'col_offset': expression.col_offset, 'end_lineno': expression.end_lineno,
            'end_col_offset': expression.end_col_offset},
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['standard_library_default_wraps_metadata_protocol',
                        'standard_builtin_namespace_preserved',
                        'no_unmodeled_indirect_builtin_mutation',
                        'no_unmodeled_indirect_module_mutation',
                        'no_external_monkeypatch_or_import_hook']}
    if lookup:
        fact['wrapped_lookup'] = lookup
        fact['assumptions'].extend(lookup['assumptions'])
    return fact
