## @package pcresolve._fresh_decoration
#  Metadata formatting isolated from an unescaped, freshly created function.
#  建模作用于尚未逃逸的新建函数的隔离式元数据格式化。

import ast
import builtins
from dataclasses import asdict

from ._class_type_tests import _namespace as builtin_namespace
from ._decorator_effects import _DecoratorEffects, _data
from ._function_observation import nonobserving_source
from .effect_facts import contains_yield


## Track decorator effects that operate on a fresh function object.
## 跟踪作用于新建函数对象的装饰器效果。
class _FreshMetadataEffects(_DecoratorEffects):
    ## Initialize the base effect analysis and fresh-function state.
    ## 初始化基础效果分析及新建函数状态。
    #
    #  @param args Positional arguments forwarded to the base analyzer.
    #  @return None; fresh-function tracking starts inactive.
    def __init__(self, *args):
        super().__init__(*args)
        self._fresh_active = False

    ## Run the base effect analysis with current function freshness tracked.
    ## 运行基础效果分析，并跟踪当前函数的新鲜状态。
    #
    #  @param target Decorated source function and identity.
    #  @param env Current decorator value environment.
    #  @param initializing Whether the analysis is in initialization mode.
    #  @return Effect result produced by the base analyzer.
    def run(self, target, env, initializing=False):
        previous = self._fresh_active
        self._fresh_active = previous or any(value.get('kind') == 'function' for value in env.values())

        # Restore the caller's freshness state even when effect evaluation fails.
        # 即使效果求值失败，也恢复调用者原有的新鲜状态。
        try:
            return super().run(target, env, initializing)
        finally:
            self._fresh_active = previous

    ## Model formatting into an isolated documentation mapping.
    ## 建模写入隔离文档映射的格式化操作。
    #
    #  @param node Formatting call syntax.
    #  @param left Provenance and shape of the formatting value.
    #  @param mapping Mapping source and owning class information.
    #  @param target Decorated function receiving the effect.
    #  @return Result data shape, delegating to the base model when not isolated.
    def format_mapping(self, node, left, mapping, target):
        if (not self._fresh_active or left.get('kind') != 'data'
                or left.get('python_shape') != 'str'):
            return super().format_mapping(node, left, mapping, target)
        proof = self.method_proof(mapping['class_ref'], '__getitem__')
        if proof is None:
            return _data()
        callback = None
        for ref, cls in self.analyzer._dict_subclass_hierarchy(mapping['class_ref']) or ():
            matches = self.analyzer._definition_index.find(ref.module, ref.qualname + '.__missing__')
            if matches:
                callback = matches[0] if len(matches) == 1 else None
                break
        if callback is None or not self.callback_structure(callback):
            self.issue('decorator_format_completion_unproven', target[0], node)
            return _data()
        self.extra_assumptions.extend(proof['assumptions'])

        # The cache predates this fresh function. Formatting receives a string
        # and keys/values, never the function object. Earlier escapes still
        # invalidate the enclosing proof; no callback purity is asserted.
        self.effects.append({'operation': 'isolated_documentation_format',
            'target': 'documentation_cache', 'impact': 'fresh_function_unreachable',
            'protocol': 'native_string_mapping_format', 'input_shape': 'str',
            'output_shape': 'str', 'input_function_passed': False,
            'object_source': mapping['source'],
            'completion': 'normal_return_only', 'method_binding': proof,
            'callback_guard': {'kind': 'source_metadata_callback_structure',
                'target': asdict(callback[0]), 'status': 'source_bound',
                'scope': 'no_known_invalid_slice_or_unbound_raise',
                'normal_completion_proven': False, 'evidence': self.evidence_at(*callback)},
            'function': asdict(target[0]), 'evidence': self.evidence_at(target[0], node),
            'conditions': list(self.conditions)})
        return dict(_data(), python_shape='str')

    ## Check that a missing-key callback has bounded structure and safe exceptions.
    ## 检查缺失键回调是否具有有界结构且只使用安全异常。
    #
    #  @param callback Source reference and AST node for the callback.
    #  @return True when the callback has a normal return and no invalid slice/raise.
    def callback_structure(self, callback):
        ref, function = callback
        if not isinstance(function, ast.FunctionDef) or contains_yield(function):
            return False
        returns = False
        pending = list(function.body)
        while pending:
            node = pending.pop()
            self.remaining -= 1

            # Enforce both local and shared budgets before analyzing child nodes.
            # 分析子节点前同时检查本地预算与共享预算。
            if self.remaining < 0:
                return False
            if self.analyzer._analysis_budget is not None:
                self.analyzer._analysis_budget.checkpoint()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice)
                    and isinstance(node.slice.step, ast.Constant) and node.slice.step.value == 0):
                return False
            if isinstance(node, ast.Return):
                returns = True
            if isinstance(node, ast.Raise):
                call = node.exc
                name = call.func.id if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) else ''
                exception = getattr(builtins, name, None)
                if (not isinstance(exception, type) or not issubclass(exception, BaseException)
                        or self.analyzer._builtin_name_status(ref, function, name) != 'confirmed_builtin'):
                    return False
            pending.extend(ast.iter_child_nodes(node))
        return returns


## Prove body preservation separately from the value of computed documentation.
## 将函数体身份保持证明与计算所得文档值分开处理。
#
#  @param analyzer Fixed source snapshot and default decoration evidence.
#  @param target Exact original source function declaration.
#  @param evidence Source span provider shared with the value-flow summary.
#  @param limit Existing per-decoration syntax budget.
#  @return One conditional fresh-function fact, or None outside the bounded model.
def fresh_decoration(analyzer, target, evidence, limit):
    ref, node = target
    if (not isinstance(node, ast.FunctionDef) or len(node.decorator_list) != 1
            or not builtin_namespace(analyzer, ref)):
        return None
    observers = nonobserving_source(analyzer)
    if observers is None:
        return None
    proof = _FreshMetadataEffects(analyzer, target, evidence, limit)
    fact = proof.fact(node.decorator_list[0])
    if (fact['identity_status'] != 'preserved' or fact['body_binding_status'] != 'preserved'
            or fact['boundaries'] or not any(effect['operation'] == 'isolated_documentation_format'
                                            for effect in fact['effects'])):
        return None

    # Attach freshness and observer premises only after the isolated format effect is proved.
    # 仅在隔离格式化效果得到证明后，才附加新鲜性与观察器前提。
    assumptions = ['fresh_source_function_before_name_binding',
        'fresh_function_metadata_noninterference', 'standard_builtin_namespace_preserved',
        'no_unmodeled_indirect_builtin_mutation'] + observers['assumptions']
    fact.update({'kind': 'source_fresh_function_decoration',
        'freshness': {'kind': 'source_function_creation', 'phase': 'before_name_binding',
            'function': asdict(ref), 'definition_evidence': evidence(ref, node),
            'input_function_unescaped': True, 'runtime_allocation_confirmed': False},
        'observation_guard': observers, 'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': sorted(set(fact['assumptions'] + assumptions))})
    return fact
