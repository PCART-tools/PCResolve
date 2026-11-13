## @package pcresolve._metadata_creation
#  Native descriptor/data formation used by source metadata observers.
#  为源码元数据观察器提供原生描述符和数据对象的构造模型。

import ast
import re
from dataclasses import asdict

from ._function_factory import _canonical
from ._metadata_namespace import namespace, builtin_namespace
from .class_attribute_effects import _ClassEffectLimit


## Build a source span record for one definition or expression.
## 为一个定义或表达式构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Bound literal native string-set formation without asserting its later binding.
## 有界地建模字面量原生字符串集合的创建，但不推断其后续绑定。
#
#  @param analyzer Fixed source generation.
#  @param owner Exact lexical class containing the assignment.
#  @param expression Source initializer; no target expression is executed.
#  @return Conditional native set creation evidence or None.
def string_set(analyzer, owner, expression):
    if (not isinstance(expression, ast.Set) or len(expression.elts) > 2000
            or any(not isinstance(item, ast.Constant) or type(item.value) is not str
                   or len(item.value) > 2000 for item in expression.elts)):
        return None
    return {'kind': 'literal_native_string_set_creation', 'status': 'source_bound',
        'result_kind': 'native_string_set', 'set_name_protocol': 'absent',
        'completion': 'normal_return_only', 'runtime_creation_confirmed': False,
        'evidence': _span(owner, expression),
        'source_hashes': {owner.file_path: analyzer.hashes[owner.file_path]},
        'assumptions': ['source_snapshot_bindings_hold', 'source_literal_native_string_set_creation']}


## Bound fresh staticmethod/cache construction without interpreting future calls.
## 有界地建模新鲜 staticmethod/cache 的创建，不解释后续调用。
#
#  @param analyzer Fixed source/import snapshot.
#  @param owner Lexical class containing the fresh function.
#  @param member Undecorated source definition plus its actual decorator syntax.
#  @param shadowed Names already bound in the class namespace.
#  @return Native descriptor creation record, or None for open bindings/arguments.
def static_cache(analyzer, owner, member, shadowed):
    decorators = member.decorator_list
    if (member.name in ('__init__', '__new__') or len(decorators) != 2
            or not isinstance(decorators[0], ast.Name) or decorators[0].id != 'staticmethod'
            or 'staticmethod' in shadowed
            or analyzer._builtin_name_status(owner, member, 'staticmethod') != 'confirmed_builtin'
            or not isinstance(decorators[1], ast.Call)):
        return None
    call = decorators[1]
    root = call.func
    while isinstance(root, ast.Attribute):
        root = root.value
    if not isinstance(root, ast.Name) or root.id in shadowed:
        return None
    if (_canonical(analyzer, owner, ast.Module(body=[], type_ignores=[]), call.func)
            != 'functools.lru_cache' or call.args
            or any(item.arg not in ('maxsize', 'typed') or not isinstance(item.value, ast.Constant)
                   for item in call.keywords)
            or len({item.arg for item in call.keywords}) != len(call.keywords)):
        return None
    values = {item.arg: item.value.value for item in call.keywords}

    # Accept only literal cache options, preserving the standard defaults.
    # 仅接受字面量缓存选项，并保留标准默认值。
    maximum, typed = values.get('maxsize', 128), values.get('typed', False)
    if (maximum is not None and type(maximum) is not int or type(typed) is not bool):
        return None
    try:
        stable, builtin_paths = builtin_namespace(analyzer, owner)
    except _ClassEffectLimit:
        return None
    if not stable:
        return None

    # Require both the local builtin descriptor premises and imported cache namespace.
    # 同时要求本地内建描述符前提和导入缓存命名空间都已得到证明。
    paths = namespace(analyzer, 'functools', ('lru_cache',))
    if paths is None:
        return None
    return {'kind': 'standard_library_staticmethod_cache_creation', 'status': 'source_bound',
        'result_kind': 'native_staticmethod', 'completion': 'normal_return_only',
        'future_body_effects': 'unmodeled', 'runtime_creation_confirmed': False,
        'owner_class': asdict(owner), 'function_name': member.name,
        'evidence': [_span(owner, expression) for expression in decorators],
        'maxsize': maximum, 'typed': typed,
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(set(paths) | set(builtin_paths))},
        'assumptions': ['standard_library_staticmethod_cache_creation',
            'standard_library_default_wraps_metadata_protocol', 'builtin_staticmethod_descriptor',
            'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
            'source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_module_mutation', 'no_unmodeled_indirect_function_mutation']}


## Bound a literal regex-pattern creation as native non-descriptor class data.
## 将字面量正则模式创建限定为原生、非描述符类数据。
#
#  @param analyzer Fixed source/import snapshot.
#  @param owner Lexical class containing the creation expression.
#  @param expression Actual source initializer.
#  @param shadowed Class-local names preceding the initializer.
#  @return Native pattern creation record, or None for unsupported sources/flags.
def regex_pattern(analyzer, owner, expression, shadowed):
    if (not isinstance(expression, ast.Call) or not 1 <= len(expression.args) <= 2
            or expression.keywords or any(not isinstance(value, ast.Constant)
                                          for value in expression.args)
            or type(expression.args[0].value) not in (str, bytes)
            or len(expression.args[0].value) > 65536):
        return None
    root = expression.func
    while isinstance(root, ast.Attribute):
        root = root.value
    if (not isinstance(root, ast.Name) or root.id in shadowed
            or _canonical(analyzer, owner, ast.Module(body=[], type_ignores=[]), expression.func)
                != 're.compile'):
        return None
    flags = expression.args[1].value if len(expression.args) == 2 else 0
    if type(flags) is not int or flags & int(re.DEBUG):
        return None
    try:
        stable, builtin_paths = builtin_namespace(analyzer, owner)
    except _ClassEffectLimit:
        return None
    if not stable:
        return None
    paths = namespace(analyzer, 're', ('compile',))
    if paths is None:
        return None
    # Host stdlib validation uses literal data only. This never imports a target
    # package or evaluates a source expression. Target semantics stay an explicit
    # standard-regex premise and only normal construction returns are modeled.
    # 宿主标准库验证只使用字面量数据，不导入目标包或执行源码表达式。
    # 目标语义仍是显式的标准正则前提，且仅建模正常构造返回。
    try:
        re.compile(expression.args[0].value, flags)
    except (re.error, ValueError, OverflowError, RecursionError):
        return None
    return {'kind': 'standard_library_native_regex_pattern_creation', 'status': 'source_bound',
        'result_kind': 'native_regex_pattern', 'set_name_protocol': 'absent',
        'completion': 'normal_return_only', 'runtime_creation_confirmed': False,
        'evidence': _span(owner, expression),
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(set(paths) | set(builtin_paths))},
        'assumptions': ['standard_library_native_regex_pattern_creation',
            'standard_regex_pattern_has_no_set_name', 'source_snapshot_bindings_hold',
            'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_module_mutation']}
