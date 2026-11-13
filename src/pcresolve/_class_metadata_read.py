## @package pcresolve._class_metadata_read
#  Native function scalar metadata under a closed source class-use invariant.
#  在封闭源码类使用不变量下读取原生函数标量元数据。

import ast

from ._class_definition import namespace_issues
from ._function_metadata_formation import metadata_formation
from ._property_namespace import _stable_builtin_namespace
from .class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from .scope_facts import statement_scope_facts


## Recognize a scalar metadata read without discarding other class-use evidence.
## 识别标量元数据读取，同时保留其他类使用的独立检查。
#
#  @param analyzer Fixed source generation and shared class-effect budget.
#  @param expression Actual scalar field read from a directly selected source method.
#  @param resolve_class Scanner provider returning exact class references for an expression.
#  @return True for a native scalar field; all other class uses remain independently checked.
def native_function_scalar(analyzer, expression, resolve_class):
    fields = {'__doc__': 'documentation', '__name__': 'name',
              '__qualname__': 'qualname', '__module__': 'module'}
    if (not isinstance(expression, ast.Attribute) or not isinstance(expression.ctx, ast.Load)
            or expression.attr not in fields or not isinstance(expression.value, ast.Attribute)
            or not isinstance(expression.value.ctx, ast.Load)):
        return False
    lookup = expression.value
    owners = resolve_class(lookup.value)
    if len(owners) != 1:
        return False
    owner = owners[0]
    candidates = analyzer._definition_index.find(owner.module, owner.qualname, kind='class')
    if len(candidates) != 1 or candidates[0][0] != owner:
        return False
    cls = candidates[0][1]
    # No inherited hook or class decorator can replace this direct slot. Those
    # phases require an independent proof before their reads can be projected.
    # 继承钩子或类装饰器可能替换直接成员，须另行证明才能投影读取。
    if (cls.bases or cls.keywords or cls.decorator_list or analyzer.definition_conditions.get(owner)
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)):
        return False
    members = [node for node in cls.body if lookup.attr in statement_scope_facts([node]).bound]
    if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
            or members[0].name != lookup.attr or members[0].decorator_list):
        return False
    selected = analyzer._definition_index.find(owner.module, owner.qualname + '.' + lookup.attr)
    if len(selected) != 1 or selected[0][1] is not members[0]:
        return False
    inspected = 0
    for method in cls.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nodes = []
        for node in ast.walk(method):
            inspected += 1
            if inspected > 100000:
                return False
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            nodes.append(node)
        # Deferred bodies can mutate a function through an implicit class
        # receiver which the global class-name scanner cannot resolve. Do not
        # project a referenced method until those uses have an effect proof.
        # 延迟方法体可能通过隐式类接收者修改方法；缺少效果证明时不投影。
        if any(isinstance(node, ast.Attribute) and node.attr == lookup.attr for node in nodes):
            return False
        matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + method.name)
        if len(matches) != 1 or matches[0][1] is not method:
            return False
        implicit_class = (method.name in ('__init_subclass__', '__class_getitem__')
                          or analyzer._descriptor_kind(matches[0]) == 'classmethod')
        if implicit_class:
            parameters = method.args.posonlyargs + method.args.args
            if not parameters:
                return False

            ## Charge class-write analysis against the shared fact budget.
            ## 将类写入分析计入共享事实预算。
            #
            #  @param count Number of visited nodes to charge.
            #  @return None
            def charge(count):
                analyzer._class_effect_fact_steps -= count

            try:
                effect = class_attribute_writes(method, parameters[0].arg,
                    lambda name: analyzer._builtin_name_status(matches[0][0], method, name)
                        == 'confirmed_builtin', lambda value: False,
                    max_nodes=min(2000, max(0, analyzer._class_effect_fact_steps)), charge=charge)
            except _ClassEffectLimit:
                return False
            if (effect is None or set(effect.attributes) & {
                    lookup.attr, '*', '__class__', '__bases__', '__dict__'}):
                return False
    writes, truncated = analyzer._class_binding_writes()
    # Metadata writes through saved methods can affect the scalar's shape too.
    if truncated or any(written == owner for written, _, _, _, _ in writes):
        return False
    try:
        if (not _stable_builtin_namespace(analyzer, owner, ('type', '__build_class__', 'object'))[0]
                or namespace_issues(analyzer, candidates, assumptions=set())):
            return False
        formation = metadata_formation(analyzer, selected[0])
    except _ClassEffectLimit:
        return False
    return (formation is not None
            and set(formation['metadata_shapes'][fields[expression.attr]]) <= {'str', 'NoneType'})
