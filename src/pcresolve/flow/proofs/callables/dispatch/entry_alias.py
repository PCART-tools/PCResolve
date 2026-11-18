## @package pcresolve.flow.proofs.callables.dispatch.entry_alias
#  Trace entry-point aliases.
#
#
#  Bounded lexical references for API selection, separate from runtime binding.
#  为 API 选择提供有界词法引用，并与运行时绑定区分开。



import ast
import copy
import os
from dataclasses import asdict

from pcresolve.facts.scope_facts import statement_scope_facts


_MAX_ENTRY_ALIAS_MODULE_NODES = 20000


## Signal that bounded source alias lookup exhausted its analysis budget.
## 表示有界源码别名查找已耗尽分析预算。
class _AliasLimit(ValueError):
    pass


## Check whether evaluating a definition can execute a call.
## 检查求值定义时是否可能执行调用。
#
#  @param node Syntax node whose definition-time expressions are inspected.
#  @return True when a call may execute while creating the definition.
def _definition_calls(node):
    if isinstance(node, ast.Call):
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.decorator_list:
            return True
        expressions = node.decorator_list + node.args.defaults + [
            value for value in node.args.kw_defaults if value is not None]
        arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs + [
            value for value in (node.args.vararg, node.args.kwarg) if value is not None]
        expressions += [argument.annotation for argument in arguments if argument.annotation]
        if node.returns is not None:
            expressions.append(node.returns)
        return any(isinstance(child, ast.Call) for value in expressions for child in ast.walk(value))
    if isinstance(node, ast.ClassDef):
        return (bool(node.bases or node.keywords or node.decorator_list)
                or any(_definition_calls(statement) for statement in node.body))
    return any(_definition_calls(child) for child in ast.iter_child_nodes(node))


## Locate a captured plain source function in one module or plain class namespace.
## 在单个模块或普通类命名空间中定位已捕获的源码函数。
#
#  @param analyzer Fixed source index and class-write facts.
#  @param requested FunctionRef selecting an alias rather than its old definition name.
#  @return Definition pair and source-reference evidence, or None outside the bounded subset.
def reference(analyzer, requested):
    owner, _, name = requested.qualname.rpartition('.')
    if owner:
        classes = analyzer._definition_index.find(requested.module, owner, kind='class')
        if len(classes) != 1:
            return None
        class_ref, cls = classes[0]
        if cls.bases or cls.keywords or cls.decorator_list:
            return None
        if not analyzer._stable_import_name(requested.module + '.' + owner):
            # A conditional definition may be selected under its recorded
            # activation condition. A competing write is not such a condition.
            # 条件定义可依据记录的激活条件选择；竞争写入不构成这类条件。
            sources = analyzer.import_binding_facts.get(requested.module, [])
            sites = sources[0].get(owner, []) if len(sources) == 1 else []
            if ('.' in owner or not analyzer.definition_conditions.get(class_ref)
                    or len(sites) != 1):
                return None
            nodes = list(ast.walk(sites[0]))
            if (len(nodes) > 20000 or cls not in nodes
                    or sum(isinstance(node, ast.ClassDef) and node.name == owner
                           for node in nodes) != 1
                    or any(isinstance(node, ast.Name) and node.id == owner
                           and isinstance(node.ctx, (ast.Store, ast.Del))
                           or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and node.name == owner
                           or isinstance(node, ast.ExceptHandler) and node.name == owner
                           or isinstance(node, (ast.Import, ast.ImportFrom))
                           and owner in statement_scope_facts([node]).bound for node in nodes)):
                return None
        if any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
               and item.name in ('__getattribute__', '__getattr__') for item in cls.body):
            return None
        body, path = cls.body, class_ref.file_path
        writes, truncated = analyzer._class_binding_writes()
        if truncated or any(written == class_ref and attribute in (
                name, '*', '__class__', '__bases__', '__getattribute__', '__getattr__')
                for written, attribute, _, _, _ in writes):
            return None
    else:
        bodies = analyzer.module_bodies.get(requested.module, [])
        if len(bodies) != 1:
            return None
        path, body = bodies[0]
    if requested.file_path and os.path.abspath(requested.file_path) != os.path.abspath(path):
        return None
    # The supported alias must end in a direct name-to-name assignment. If
    # there is no such candidate, the module-wide mutation audit is unnecessary.
    # 支持的别名必须以直接名称赋值结束；没有此类候选时无需审计整个模块的变更。
    if not any(isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Name)
               and any(isinstance(target, ast.Name) and target.id == name
                       for target in statement.targets) for statement in body):
        return None
    nodes = 0

    # Reject reflective namespace access before trusting lexical assignments.
    # 在信任词法赋值前，先排除反射式命名空间访问。
    for _, module_body in analyzer.module_bodies.get(requested.module, []):
        for statement in module_body:
            for child in ast.walk(statement):
                nodes += 1
                if nodes > _MAX_ENTRY_ALIAS_MODULE_NODES:
                    raise _AliasLimit('Source entry alias lookup budget exhausted')
                if (isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
                        and child.id in ('globals', 'vars', 'eval', 'exec')):
                    return None
    values = {}

    # Replay statements in order so later rebinding invalidates earlier aliases.
    # 按语句顺序重放，使后续重绑定能够使之前建立的别名失效。
    for count, statement in enumerate(body):
        if count >= 2000:
            raise _AliasLimit('Source entry alias statement budget exhausted')
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _definition_calls(statement):
                values.clear()
            matches = analyzer._definition_index.find(requested.module,
                (owner + '.' if owner else '') + statement.name)
            if len(matches) == 1 and not statement.decorator_list:
                values[statement.name] = (matches[0], [])
            else:
                values.pop(statement.name, None)
            continue
        if (isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Name)
                and statement.value.id in values
                and all(isinstance(target, ast.Name) for target in statement.targets)):
            target, chain = values[statement.value.id]
            if len(chain) >= 64:
                raise _AliasLimit('Source entry alias chain budget exhausted')
            for destination in statement.targets:
                evidence = {'file_path': path, 'lineno': statement.lineno,
                    'col_offset': statement.col_offset, 'end_lineno': statement.end_lineno,
                    'end_col_offset': statement.end_col_offset}
                values[destination.id] = (target, chain + [{'name': destination.id,
                    'source_name': statement.value.id, 'evidence': evidence}])
            continue
        if isinstance(statement, ast.Delete):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    values.pop(target.id, None)
                else:
                    values.clear()
            continue
        if _definition_calls(statement):
            values.clear()

        # Attribute writes through any retained function alias invalidate all
        # references to that same function object, including earlier aliases.
        # 通过保留函数别名执行属性写入时，同一函数对象的全部引用（包括旧别名）均失效。
        for child in ast.walk(statement):
            if (isinstance(child, ast.Attribute) and isinstance(child.ctx, (ast.Store, ast.Del))
                    and isinstance(child.value, ast.Name) and child.value.id in values):
                affected = values[child.value.id][0][0]
                values = {key: value for key, value in values.items() if value[0][0] != affected}
        for bound in statement_scope_facts([statement]).bound:
            values.pop(bound, None)
    selected = values.get(name)
    if selected is None or not selected[1]:
        return None
    target, chain = selected
    if not owner:
        bindings = analyzer.import_binding_facts.get(requested.module, [])
        if len(bindings) != 1 or len(bindings[0].get(name, [])) != 1:
            return None
    if requested.lineno and requested.lineno != chain[-1]['evidence']['lineno']:
        return None
    return target, {'kind': 'source_entry_alias', 'status': 'source_reference',
        'basis': 'source_snapshot', 'requested': asdict(requested), 'target': asdict(target[0]),
        'runtime_target_confirmed': False, 'scope': 'definition_selection',
        'assignments': copy.deepcopy(chain),
        'conditions': copy.deepcopy(analyzer.definition_conditions.get(target[0], [])),
        'source_hashes': dict(analyzer.hashes),
        'assumptions': ['source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
                        'no_unmodeled_indirect_function_mutation']}
