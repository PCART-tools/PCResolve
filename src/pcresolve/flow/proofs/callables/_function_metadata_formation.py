## @package pcresolve.flow.proofs.callables._function_metadata_formation
#  Describe metadata formation after decoration.
#
#
#  Native function metadata immediately after bounded source decoration.
#  有界源码装饰完成后原生函数的初始元数据。



import ast
import copy
from dataclasses import asdict

from pcresolve.flow.proofs.classes._class_definition import _source_function_decoration, _namespace_syntax
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified


## Bound native metadata formation, separately from a current namespace lookup.
## 有界验证原生元数据形成，与当前命名空间查找分离。
#
#  @param analyzer Fixed source snapshot and existing decoration budgets.
#  @param target Exact source function declaration before its name is bound.
#  @return Formation evidence or None for open/non-native metadata effects.
#  @throws _ClassEffectLimit When declaration syntax or the shared budget is exhausted.
def metadata_formation(analyzer, target):
    ref, node = target
    if (analyzer.index_boundaries or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or analyzer._definition_index.find(ref.module, ref.qualname) != (target,)):
        return None
    module_bindings = analyzer.import_binding_facts.get(ref.module, [])
    if (len(module_bindings) != 1 or module_bindings[0].get('__name__')
            or not unmodified(analyzer, ref.module + '.__name__')):
        return None
    for count, _ in enumerate(_namespace_syntax(node), 1):
        analyzer._class_effect_fact_steps -= 1
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
        if count > 2000 or analyzer._class_effect_fact_steps < 0:
            raise _ClassEffectLimit()

    # Only constant annotations avoid unmodeled evaluation and callback effects.
    # 仅接受常量注解，避免未建模的求值和回调效果。
    annotations = [argument.annotation for argument in
        node.args.posonlyargs + node.args.args + node.args.kwonlyargs]
    annotations += [node.returns]
    if node.args.vararg:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg:
        annotations.append(node.args.kwarg.annotation)
    # Do not assume deferred annotation resolution is callback-free.
    if any(value is not None and not isinstance(value, ast.Constant) for value in annotations):
        return None
    documentation = {'NoneType'} if ast.get_docstring(node, clean=False) is None else {'str'}
    module = {'str'}
    assumptions = {'source_snapshot_bindings_hold', 'builtin_function_creation_and_metadata',
                   'fresh_source_function_before_name_binding', 'standard_source_module_name_binding',
                   'no_unmodeled_indirect_module_mutation', 'no_external_monkeypatch_or_import_hook'}
    paths = {ref.file_path}
    facts = []
    if node.decorator_list:
        # Require one complete decoration summary before using any write effects.
        # 使用任何写入效果之前，要求唯一且完整的装饰摘要。
        if _source_function_decoration(analyzer, target, paths, assumptions) is None:
            return None
        facts = analyzer._decoration_facts(target)
        if len(facts) == 1 and facts[0]['body_binding_status'] != 'preserved':
            facts = analyzer._fresh_decoration_facts(target) or facts
        if len(facts) != 1:
            return None
        for effect in facts[0]['effects']:
            if effect.get('operation') != 'attribute_write' or effect.get('target') != 'input_function':
                continue
            shape = set(effect.get('value_shapes', []))
            path = effect.get('element_path')
            if not shape or not shape <= {'str', 'NoneType'}:
                return None
            if path == ['__doc__']:
                documentation.update(shape)
            elif path == ['__module__']:
                module.update(shape)
            else:
                return None

    # Every premise path must have a version before evidence is published.
    # 发布证据前，每个前提源码路径都必须具有版本摘要。
    hashes = {**analyzer.hashes, **analyzer._supporting_source_hashes}
    if any(path not in hashes for path in paths):
        return None
    return {'kind': 'source_function_metadata_creation', 'status': 'source_bound',
        'target': asdict(ref), 'phase': 'before_name_binding',
        'result_kind': 'native_python_function',
        'metadata_shapes': {'documentation': sorted(documentation), 'module': sorted(module),
            'name': ['str'], 'qualname': ['str'], 'code': 'native_python_code',
            'signature': 'native_source_function_signature'},
        'decorations': copy.deepcopy(facts), 'completion': 'normal_return_only',
        'runtime_function_binding_confirmed': False, 'current_namespace_binding_confirmed': False,
        'definition_evidence': {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset},
        'source_hashes': {path: hashes[path] for path in sorted(paths)},
        'assumptions': sorted(assumptions)}
