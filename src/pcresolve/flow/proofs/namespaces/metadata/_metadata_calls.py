## @package pcresolve.flow.proofs.namespaces.metadata._metadata_calls
#  Instantiate metadata-query input obligations at a class-creation call site.
#  在类创建调用点实例化元数据查询的输入义务。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.callables._function_factory import _canonical
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.namespaces.metadata._metadata_queries import metadata_query
from pcresolve.flow.proofs.namespaces.metadata._metadata_entry import entry as metadata_entry
from pcresolve.flow.proofs.namespaces.metadata._metadata_observer import observer_query
from pcresolve.flow.proofs.callables._function_metadata_formation import metadata_formation
from pcresolve.facts.scope_facts import statement_scope_facts


## Build a source span record for one query or definition node.
## 为一个查询或定义节点构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Collect private observer result projections for one source class.
## 收集针对一个源码类的私有观察器结果投影。
#
#  @param analyzer Analyzer providing class writes and observer evidence.
#  @param owner Selected observer class and its source definition.
#  @return Projected query records, or None if class identity may be invalidated.
def _private_results(analyzer, owner):
    # This is a projection for one observer class, not an exemption for class
    # construction in general. All actual argument escapes remain visible.
    records = {}
    observation = nonobserving_source(analyzer)
    if observation is None:
        return None

    ## Project a literal query result while preserving its call evidence.
    ## 投影字面量查询结果，并保留调用证据。
    #
    #  @param caller Source function containing the observer call.
    #  @param node Observer query call syntax.
    #  @param classes Classes that may escape through the call.
    #  @return True when the call is safely projected, otherwise False.
    def project(caller, node, classes):
        constructor = node.func.value
        if (classes != [owner[0]]
                or len(constructor.args) != 1 or constructor.keywords
                or isinstance(constructor.args[0], ast.Starred)):
            return False
        # Only literal data can enter a private query. Evaluated expressions,
        # expansions and duplicate keywords retain their ordinary escape guard.
        values = list(node.args) + [item.value for item in node.keywords]
        names = [item.arg for item in node.keywords]

        # Accept only immutable literal query inputs; expansions remain visible to escape checks.
        # 仅接受不可变字面量查询输入；展开参数仍交由逃逸检查处理。
        if (any(not isinstance(value, ast.Constant)
                or type(value.value) not in (str, int, bool, float, type(None))
                for value in values)
                or None in names or len(set(names)) != len(names)):
            return False
        key = caller, node.lineno, node.col_offset, node.end_lineno, node.end_col_offset
        if key in records:
            return True
        query = observer_query(analyzer, owner, node.func.attr,
            positional_literals=tuple(value.value for value in node.args),
            keyword_literals={item.arg: item.value.value for item in node.keywords})
        if query is None:
            return False
        assumptions = sorted(set(query['assumptions'] + observation['assumptions'] + [
            'source_private_observer_result_projection']))
        records[key] = {'kind': 'private_observer_data_result', 'basis': 'source_snapshot',
            'owner_class': asdict(owner[0]), 'caller': asdict(caller),
            'call_evidence': _span(caller, node), 'query': query,
            'scope': 'observer_class_identity_only',
            'observation_guard': observation, 'assumptions': assumptions,
            'runtime_execution_confirmed': False}
        return True

    # Audit every class write and escape, allowing only the exact observer projection above.
    # 审计所有类写入和逃逸，只放行上面精确识别的观察器投影。
    writes, truncated = analyzer._class_binding_writes(include_escapes=True, private_result=project)
    if truncated or any(written == owner[0] for written, _, _, _, _ in writes):
        return None
    return list(records.values())


## Resolve one metadata entry and attach private observer projections.
## 解析单个元数据入口，并附加私有观察器结果投影。
#
#  @param analyzer Analyzer providing metadata and class-effect facts.
#  @param selected Selected source class or method definition.
#  @param declaration_only Whether to inspect declaration effects only.
#  @return Metadata entry evidence, or None when entry premises are open.
def _entry(analyzer, selected, declaration_only=False):
    return metadata_entry(analyzer, selected, declaration_only=declaration_only,
                          private_result_reader=_private_results)


## Bind a query to a fresh function owned by the class currently being created.
## 将查询绑定到当前正在创建的类所拥有的新鲜函数。
#
#  @param analyzer Fixed source generation and query-local resource budget.
#  @param target New source class before its own class decorators.
#  @param caller Source hook or independently selected classmethod.
#  @param parameter Implicit class receiver name in that exact caller.
#  @param call Actual metadata-query invocation in the caller body.
#  @return Source call/input premises or None; no concrete scalar answer is invented.
def bind_metadata_call(analyzer, target, caller, parameter, call):
    if (not isinstance(call, ast.Call) or len(call.args) != 1 or call.keywords
            or not isinstance(call.args[0], ast.Attribute)
            or not isinstance(call.args[0].value, ast.Name)
            or call.args[0].value.id != parameter):
        return None
    canonical = _canonical(analyzer, caller[0], caller[1], call.func)
    if not canonical:
        return None
    selected = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if selected is None:
        return None
    query = metadata_query(analyzer, selected)
    entry = _entry(analyzer, selected) if query is not None else None
    if query is None or entry is None:
        return None
    name = call.args[0].attr
    owner, cls = target
    if name.startswith('__'):
        return None
    members = [node for node in cls.body if name in statement_scope_facts([node]).bound]
    if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
            or members[0].name != name):
        return None
    matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
    if len(matches) != 1 or matches[0][1] is not members[0]:
        return None
    function_ref, function = matches[0]
    formation = metadata_formation(analyzer, matches[0]) if function.decorator_list else None
    if function.decorator_list and formation is None:
        return None
    protocols = query['input_preconditions']['protocols']
    documentation = ast.get_docstring(function, clean=False)
    documentation_shapes = (formation['metadata_shapes']['documentation'] if formation is not None
                            else ['str' if type(documentation) is str else 'NoneType'])
    # A fresh native function with a literal doc string bypasses inspect's
    # inherited-documentation search. None is not presumed callback-free.
    # 新鲜原生函数的字面量文档字符串可绕过 inspect 的继承文档查找；None 不被假定为无回调。
    if ('native_documentation_resolution_without_user_callbacks' in protocols
            and documentation_shapes != ['str']):
        return None
    observation = nonobserving_source(analyzer)
    if observation is None:
        return None
    assumptions = sorted(set(query['assumptions'] + entry['assumptions'] + observation['assumptions'] + [
        'source_class_creation_callable_metadata_queries', 'builtin_function_creation_and_metadata',
        'fresh_source_class_function_before_class_decorators',
        'native_callable_metadata_input_protocols_discharged']))
    if formation is not None:
        assumptions = sorted(set(assumptions + formation['assumptions']))
    if 'native_documentation_resolution_without_user_callbacks' in protocols:
        assumptions.append('source_function_documentation_native_shape_preserved' if formation is not None
                           else 'source_function_docstrings_preserved')
        assumptions.sort()
    return {'kind': 'source_bound_callable_metadata_query', 'status': 'source_bound',
        'caller': asdict(caller[0]), 'parameter': parameter,
        'receiver_class': asdict(owner), 'phase': 'before_class_decorators',
        'call_evidence': _span(caller[0], call), 'entry_binding': entry, 'query': query,
        'input_binding': {'kind': 'fresh_source_class_function', 'status': 'source_bound',
            'receiver_class': asdict(owner), 'target': asdict(function_ref), 'attribute': name,
            'phase': 'before_class_decorators', 'input_kind': 'native_python_function',
            'documentation_shape': documentation_shapes[0] if len(documentation_shapes) == 1 else 'str_or_none',
            **({'metadata_formation': formation} if formation is not None else {}),
            'signature_metadata': 'native_fresh_function', 'hash_equality': 'builtin_function_identity',
            'protocols': list(protocols), 'definition_evidence': _span(function_ref, function),
            'runtime_input_confirmed': False},
        'observation_guard': observation, 'result_shapes': list(query['result_shapes']),
        'completion': 'normal_return_only', 'runtime_execution_confirmed': False,
        'source_hashes': dict(sorted(analyzer.hashes.items())), 'assumptions': assumptions}
