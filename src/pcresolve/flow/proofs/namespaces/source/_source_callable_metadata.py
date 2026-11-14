## @package pcresolve.flow.proofs.namespaces.source._source_callable_metadata
#  Finite custom function metadata installed by a source wrapper decorator.
#  源码包装装饰器设置的有限自定义函数元数据。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.callables._function_factory import _canonical
from pcresolve.flow.proofs.callables._function_metadata import fresh_function_wraps
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified


## Prove a literal custom attribute installed on a returned source wrapper.
## 证明返回的源码包装函数上设置了字面量自定义属性。
#
#  @param analyzer Flow analyzer with indexed source and stable-import facts.
#  @param target Pair of decorated function identity and AST node.
#  @param attribute Custom attribute name to prove.
#  @return Versioned evidence dictionary, or None when the shape is unsupported.
def wrapper_metadata(analyzer, target, attribute):
    """Prove one literal attribute on a returned functools.wraps wrapper.

    The decorator must take one source function, define exactly one nested
    wrapper decorated with functools.wraps(input), assign one literal custom
    attribute to that wrapper, and return it. The wrapper body is deferred and
    is not interpreted as part of metadata formation.
    """
    ref, function = target
    if (not isinstance(function, ast.FunctionDef) or len(function.decorator_list) != 1
            or type(attribute) is not str or not attribute or attribute.startswith('__')):
        return None
    canonical = _canonical(analyzer, ref, function, function.decorator_list[0])
    if not canonical or not unmodified(analyzer, canonical):
        return None
    selected = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if selected is None or not isinstance(selected[1], ast.FunctionDef):
        return None

    # Match the whole wrapper-formation shape before asserting metadata.
    # 断言元数据前先匹配完整的包装函数形成过程。
    decorator_ref, decorator = selected
    parameters = decorator.args.posonlyargs + decorator.args.args
    body = decorator.body[1:] if (decorator.body and isinstance(decorator.body[0], ast.Expr)
        and isinstance(decorator.body[0].value, ast.Constant)
        and type(decorator.body[0].value.value) is str) else decorator.body
    if (decorator.decorator_list or len(parameters) != 1 or decorator.args.defaults
            or decorator.args.kwonlyargs or decorator.args.vararg or decorator.args.kwarg
            or decorator.returns is not None or len(body) != 3):
        return None
    parameter = parameters[0].arg
    wrapper, assignment, returned = body
    if (not isinstance(wrapper, ast.FunctionDef) or len(wrapper.decorator_list) != 1
            or wrapper.args.defaults or wrapper.args.kwonlyargs or wrapper.args.vararg
            or wrapper.args.kwarg or wrapper.returns is not None
            or any(argument.annotation is not None for argument in
                   wrapper.args.posonlyargs + wrapper.args.args + wrapper.args.kwonlyargs)
            or any(isinstance(node, ast.Name) and node.id == wrapper.name
                   for statement in wrapper.body for node in ast.walk(statement))):
        return None
    wraps = fresh_function_wraps(analyzer, decorator_ref, (decorator,), wrapper.decorator_list[0],
        lambda name: name == parameter)
    if wraps is None:
        return None
    if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
            or not isinstance(assignment.targets[0], ast.Attribute)
            or not isinstance(assignment.targets[0].value, ast.Name)
            or assignment.targets[0].value.id != wrapper.name
            or assignment.targets[0].attr != attribute
            or not isinstance(assignment.value, ast.Constant)
            or type(assignment.value.value) not in (str, int, bool, float, type(None))
            or not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Name)
            or returned.value.id != wrapper.name):
        return None

    # Bind the evidence to all source versions used to establish the proof.
    # 将证据绑定到证明过程中使用的所有源码版本。
    hashes = dict(wraps['source_hashes'])
    hashes.update(analyzer.hashes)
    return {'kind': 'source_wrapper_custom_function_metadata', 'status': 'source_bound',
        'decorator': asdict(decorator_ref), 'decorated_function': asdict(ref),
        'wrapper_name': wrapper.name, 'attribute': attribute,
        'value': assignment.value.value, 'formation_phase': 'class_body_function_decoration',
        'wrapper_metadata_protocol': wraps, 'completion': 'normal_return_only',
        'runtime_metadata_confirmed': False,
        'evidence': {'file_path': decorator_ref.file_path, 'lineno': assignment.lineno,
            'col_offset': assignment.col_offset, 'end_lineno': assignment.end_lineno,
            'end_col_offset': assignment.end_col_offset},
        'source_hashes': dict(sorted(hashes.items())),
        'assumptions': sorted(set(wraps['assumptions'] + [
            'source_snapshot_bindings_hold', 'source_decorator_returns_fresh_wrapper',
            'wrapper_body_deferred_during_metadata_formation',
            'no_external_monkeypatch_or_import_hook']))}
