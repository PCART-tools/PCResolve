## @package pcresolve._source_callable_metadata
#  Finite custom function metadata installed by a source wrapper decorator.

import ast
from dataclasses import asdict

from ._class_partial import _namespace as functools_namespace
from ._function_factory import _canonical
from ._function_metadata import fresh_function_wraps
from ._runtime_namespace import unmodified


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
    matplotlib = _matplotlib_rasterization_metadata(analyzer, target, attribute)
    if matplotlib is not None:
        return matplotlib
    canonical = _canonical(analyzer, ref, function, function.decorator_list[0])
    if not canonical or not unmodified(analyzer, canonical):
        return None
    selected = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if selected is None or not isinstance(selected[1], ast.FunctionDef):
        return None
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


def _matplotlib_rasterization_metadata(analyzer, target, attribute):
    """Prove Matplotlib's fixed rasterization wrapper installs its marker."""
    ref, function = target
    if (attribute != '_supports_rasterization' or ref.module != 'matplotlib.patches'
            or function.name != 'draw' or len(function.decorator_list) != 1):
        return None
    canonical = _canonical(analyzer, ref, function, function.decorator_list[0])
    if canonical != 'matplotlib.artist.allow_rasterization':
        return None
    selected = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if selected is None or not isinstance(selected[1], ast.FunctionDef):
        return None
    decorator_ref, decorator = selected
    args = decorator.args
    parameters = args.posonlyargs + args.args
    body = [statement for statement in decorator.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    if (decorator.decorator_list or len(parameters) != 1 or parameters[0].arg != 'draw'
            or args.defaults or args.kwonlyargs or args.vararg or args.kwarg
            or parameters[0].annotation is not None or args.kw_defaults
            or decorator.returns is not None or len(body) != 3):
        return None
    wrapper, assignment, returned = body
    if (not isinstance(wrapper, ast.FunctionDef) or wrapper.name != 'draw_wrapper'
            or len(wrapper.decorator_list) != 1
            or not isinstance(wrapper.decorator_list[0], ast.Call)
            or not isinstance(wrapper.decorator_list[0].func, ast.Name)
            or wrapper.decorator_list[0].func.id != 'wraps'
            or len(wrapper.decorator_list[0].args) != 1
            or not isinstance(wrapper.decorator_list[0].args[0], ast.Name)
            or wrapper.decorator_list[0].args[0].id != 'draw'
            or wrapper.decorator_list[0].keywords
            or [arg.arg for arg in wrapper.args.posonlyargs + wrapper.args.args] != [
                'artist', 'renderer']
            or wrapper.args.defaults or wrapper.args.kwonlyargs or wrapper.args.vararg
            or wrapper.args.kwarg or wrapper.args.kw_defaults or wrapper.returns is not None
            or any(arg.annotation is not None for arg in
                   wrapper.args.posonlyargs + wrapper.args.args + wrapper.args.kwonlyargs)):
        return None
    if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
            or not isinstance(assignment.targets[0], ast.Attribute)
            or not isinstance(assignment.targets[0].value, ast.Name)
            or assignment.targets[0].value.id != 'draw_wrapper'
            or assignment.targets[0].attr != attribute
            or not isinstance(assignment.value, ast.Constant)
            or assignment.value.value is not True
            or not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Name)
            or returned.value.id != 'draw_wrapper'):
        return None
    if (analyzer.imports.get(decorator_ref.module, {}).get('wraps') != 'functools.wraps'
            or not analyzer._stable_import_name(decorator_ref.module + '.wraps')
            or not functools_namespace(analyzer, ('wraps', 'WRAPPER_ASSIGNMENTS',
                                                   'WRAPPER_UPDATES'))
            or not unmodified(analyzer, canonical)):
        return None
    hashes = dict(sorted(analyzer.hashes.items()))
    wraps = {'kind': 'standard_functools_wraps', 'status': 'source_bound',
        'source_hashes': hashes,
        'assumptions': ['standard_library_functools_wraps_protocol',
                        'no_external_monkeypatch_or_import_hook']}
    return {'kind': 'source_matplotlib_rasterization_wrapper_metadata',
        'status': 'source_bound', 'decorator': asdict(decorator_ref),
        'decorated_function': asdict(ref), 'wrapper_name': wrapper.name,
        'attribute': attribute, 'value': True,
        'formation_phase': 'class_body_function_decoration',
        'wrapper_metadata_protocol': wraps, 'completion': 'normal_return_only',
        'runtime_metadata_confirmed': False,
        'evidence': {'file_path': decorator_ref.file_path, 'lineno': assignment.lineno,
            'col_offset': assignment.col_offset, 'end_lineno': assignment.end_lineno,
            'end_col_offset': assignment.end_col_offset},
        'source_hashes': hashes,
        'assumptions': ['source_snapshot_bindings_hold', 'source_decorator_returns_fresh_wrapper',
            'wrapper_body_deferred_during_metadata_formation',
            'standard_library_functools_wraps_protocol',
            'no_external_monkeypatch_or_import_hook']}
