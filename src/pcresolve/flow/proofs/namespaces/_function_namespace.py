## @package pcresolve.flow.proofs.namespaces._function_namespace
#  Native function results during class formation, without original-body claims.
#  建模类创建期间产生的原生函数结果，不推断原函数体的执行效果。

import ast
import copy
from dataclasses import asdict

from pcresolve.flow.proofs.callables._function_metadata import fresh_function_wraps
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Build a source span record for one syntax node.
## 为一个语法节点构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Check whether a function declaration has no defaults or annotations.
## 检查函数声明是否不含默认值和注解。
#
#  @param node Function definition to inspect.
#  @return True when the declaration has only plain required parameters.
def _plain_declaration(node):
    args = node.args
    parameters = args.posonlyargs + args.args + args.kwonlyargs
    parameters += [arg for arg in (args.vararg, args.kwarg) if arg is not None]
    return (not args.defaults and not any(value is not None for value in args.kw_defaults)
            and not any(arg.annotation is not None for arg in parameters)
            and node.returns is None)


## Bound an ordinary wrapper's construction without evaluating its deferred body.
## 有界地建模普通包装函数的构造，不执行其延迟函数体。
#
#  @param analyzer Fixed source snapshot and shared query-local effect budget.
#  @param target Fresh function receiving exactly one direct source decorator.
#  @return Native-function namespace fact, or None for open immediate effects.
def wrapper_creation(analyzer, target):
    cache = analyzer._function_namespace_cache
    key = (target[0], id(target[1]))
    if key not in cache:
        # Seed the cache before resolving decorator source to guard against re-entry.
        # 解析装饰器源码前先写入缓存占位，防止递归重入。
        cache[key] = None
        cache[key] = _wrapper_creation(analyzer, target)
    return copy.deepcopy(cache[key])


## Verify the narrow source contract for a function-producing decorator.
## 验证产生函数的装饰器所满足的有限源码契约。
#
#  @param analyzer Fixed source snapshot and shared query-local effect budget.
#  @param target Fresh function receiving exactly one direct source decorator.
#  @return Native-function namespace fact, or None when a premise is unproven.
def _wrapper_creation(analyzer, target):
    ref, member = target
    if (analyzer.index_boundaries or not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], (ast.Name, ast.Attribute))):
        return None
    selected = analyzer._decorator_definition(target)
    if selected is None:
        return None
    owner, decorator = selected
    if (not isinstance(decorator, ast.FunctionDef) or '.' in owner.qualname
            or decorator.decorator_list or not _plain_declaration(decorator)
            or not unmodified(analyzer, owner.module + '.' + owner.qualname)):
        return None
    args = decorator.args
    parameters = args.posonlyargs + args.args
    if len(parameters) != 1 or args.vararg or args.kwarg or args.kwonlyargs:
        return None
    parameter = parameters[0].arg
    body = [statement for statement in decorator.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    if (len(body) < 2 or not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef))
            or not isinstance(body[-1], ast.Return)
            or not isinstance(body[-1].value, ast.Name)
            or body[-1].value.id != body[0].name or body[0].name == parameter):
        return None
    wrapper = body[0]
    if (not _plain_declaration(wrapper) or len(wrapper.decorator_list) != 1
            or analyzer._scope_facts(decorator).globals
            or analyzer._scope_facts(decorator).nonlocals):
        return None
    count = 0
    for _ in ast.walk(decorator):
        count += 1
        analyzer._class_effect_fact_steps -= 1
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
        # Keep both the local walk and shared class-effect budget bounded.
        # 同时限制本地遍历规模和共享类效果预算。
        if count > 2000 or analyzer._class_effect_fact_steps < 0:
            return None
    try:
        metadata = fresh_function_wraps(analyzer, owner, (decorator,),
            wrapper.decorator_list[0], lambda name: name == parameter)
    except _ClassEffectLimit:
        return None
    if metadata is None:
        return None
    observation = nonobserving_source(analyzer)
    if observation is None:
        return None
    writes = []
    for statement in body[1:-1]:
        if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(statement.targets[0], ast.Attribute)
                or not isinstance(statement.targets[0].value, ast.Name)
                or statement.targets[0].value.id != wrapper.name):
            return None
        attribute = statement.targets[0].attr
        # Plain function dictionaries have no custom attribute hooks. Restrict
        # special slots to metadata strings; code/default/closure slots stay open.
        # 普通函数字典没有自定义属性钩子；特殊槽只接受元数据字符串，代码/默认值/闭包槽保持未建模。
        if attribute.startswith('__'):
            if (attribute not in ('__doc__', '__name__', '__qualname__')
                    or not isinstance(statement.value, ast.Constant)
                    or type(statement.value.value) is not str):
                return None
        elif not isinstance(statement.value, ast.Constant) or type(statement.value.value) not in (
                str, int, bool, float, type(None)):
            return None
        writes.append({'attribute': attribute, 'evidence': _span(owner, statement)})
    return {'kind': 'source_function_wrapper_creation', 'status': 'source_bound',
        'function': asdict(ref), 'decorator': asdict(owner),
        'result_kind': 'native_function', 'identity_status': 'replaced',
        'body_binding_status': 'unmodeled', 'future_body_effects': 'unmodeled',
        'completion': 'normal_return_only', 'phase': 'before_class_namespace_store',
        'runtime_decorator_executed': False,
        'definition_evidence': _span(ref, member),
        'wrapper_evidence': _span(owner, wrapper),
        'metadata_wrapper': metadata, 'metadata_writes': writes,
        'observation_guard': observation,
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': sorted(set(metadata['assumptions'] + observation['assumptions'] + [
            'source_snapshot_bindings_hold', 'source_native_function_wrapper_creation',
            'builtin_function_creation_and_metadata',
            'no_unmodeled_indirect_function_mutation']))}
