## @package pcresolve.flow.proofs.callables.decorators._decorator_text
#  Model text operations in decorator proofs.
#
#
#  Bounded immutable text inputs and builtin text operations for decoration proofs.
#  为装饰器证明提供有界不可变文本输入和内建文本操作模型。



import ast
import string

from pcresolve.facts.scope_facts import statement_scope_facts

_TEXT_BINDING_NODE_LIMIT = 1000000


## Resolve a text input only from a stable literal source binding.
## 仅从稳定的字面量源码绑定解析文本输入。
#
#  @param proof Current decoration proof collecting evidence and dependencies.
#  @param expression Candidate expression expected to name a literal string.
#  @param caller Source function containing the expression.
#  @return Known string data, or None when binding stability is unproven.
def literal_argument(proof, expression, caller):
    if not isinstance(expression, ast.Name):
        return None
    analyzer, name = proof.analyzer, expression.id
    owner = caller.qualname.rpartition('.')[0]
    if owner:
        if analyzer._definition_index.find(caller.module, owner):
            return None
        classes = analyzer._definition_index.find(caller.module, owner, kind='class')
        if len(classes) != 1:
            return None
        preceding = [n for n in classes[0][1].body if n.lineno < expression.lineno]
        if name in statement_scope_facts(preceding).bound:
            return None
    facts = analyzer.import_binding_facts.get(caller.module, [])
    bodies = analyzer.module_bodies.get(caller.module, [])
    if len(facts) != 1 or len(bodies) != 1:
        return None
    bindings = facts[0].get(name, [])
    if (len(bindings) != 1 or bindings[0] not in bodies[0][1]
            or not isinstance(bindings[0], ast.Assign) or len(bindings[0].targets) != 1
            or not isinstance(bindings[0].targets[0], ast.Name)
            or not isinstance(bindings[0].value, ast.Constant)
            or type(bindings[0].value.value) is not str
            or bindings[0].lineno >= expression.lineno):
        return None
    if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
           and node.id in ('exec', 'eval', 'globals', 'locals', 'vars', '__import__')
           for statement in bodies[0][1] for node in ast.walk(statement)):
        return None

    # Audit project-wide attribute and item writes once before reusing this literal.
    # 首次复用该字面量前，对项目级属性和下标写入进行一次审计。
    cached = getattr(analyzer, '_decorator_literal_writes', None)
    if cached is None:
        writes, paths, count = set(), set(), 0
        for module_bodies in analyzer.module_bodies.values():
            for path, body in module_bodies:
                paths.add(path)
                for statement in body:
                    for node in ast.walk(statement):
                        count += 1

                        # Keep the mutation audit bounded across all indexed modules.
                        # 限制对所有已索引模块进行的变更审计规模。
                        if count > _TEXT_BINDING_NODE_LIMIT:
                            return None
                        if analyzer._analysis_budget is not None:
                            analyzer._analysis_budget.checkpoint()
                        if (isinstance(node, ast.Attribute)
                                and isinstance(node.ctx, (ast.Store, ast.Del))):
                            writes.add(node.attr)
                        elif (isinstance(node, ast.Subscript)
                              and isinstance(node.ctx, (ast.Store, ast.Del))
                              and isinstance(node.slice, ast.Constant)
                              and type(node.slice.value) is str):
                            writes.add(node.slice.value)
                        elif (isinstance(node, ast.Call) and len(node.args) >= 2
                              and isinstance(node.func, (ast.Name, ast.Attribute))
                              and getattr(node.func, 'id', getattr(node.func, 'attr', ''))
                              in ('setattr', 'delattr')):
                            key = node.args[1]
                            writes.add(key.value if isinstance(key, ast.Constant)
                                       and type(key.value) is str else '*')
        cached = writes, paths
        analyzer._decorator_literal_writes = cached
    writes, paths = cached
    if name in writes:
        return None

    # Dynamic names elsewhere are not assigned to this module without an alias
    # proof. The explicit source-binding premise excludes indirect mutation.
    # 缺少别名证明时，其他位置的动态名称不会被视为写入本模块；显式源码绑定前提排除间接变更。
    proof.extra_assumptions.append('source_literal_binding_no_indirect_mutation')
    proof.dependency_paths.update(paths)
    proof.evidence.append(proof.evidence_at(caller, bindings[0]))
    return {'kind': 'data', 'value': bindings[0].value.value, 'known': True,
            'python_shape': 'str'}


## Model a small set of builtin string operations without invoking user protocols.
## 有限建模少数内建字符串操作，不调用用户自定义协议。
#
#  @param proof Current decoration proof collecting effects and evidence.
#  @param node AST call for the candidate string method.
#  @param receiver Provenance record for the method receiver.
#  @param arguments Provenance records for positional arguments.
#  @param ref Source function identity containing the call.
#  @return Result data shape and known value when available, or None.
def text_call(proof, node, receiver, arguments, ref):
    if not receiver or receiver.get('python_shape') != 'str' or node.keywords:
        return None
    method = node.func.attr
    if (method == 'split' and len(arguments) == 1 and arguments[0].get('known')
            and type(arguments[0].get('value')) is str and arguments[0]['value']):
        result = {'kind': 'data', 'known': False, 'sequence_shape': 'list',
                  'element_shape': 'str'}
    elif (method == 'format' and receiver.get('known')
          and type(receiver.get('value')) is str and len(receiver['value']) <= 10000
          and all(value.get('python_shape') == 'str' for value in arguments)):
        try:
            fields = list(string.Formatter().parse(receiver['value']))
        except ValueError:
            return None

        # No attribute/index traversal, conversion, nested format or user protocol.
        # 不允许属性/下标遍历、转换、嵌套格式化或用户自定义协议。
        if any(field is not None and (field and not field.isdecimal()
                or spec or conversion) for _, field, spec, conversion in fields):
            return None
        result = {'kind': 'data', 'known': False, 'python_shape': 'str'}
    elif (method == 'endswith' and len(arguments) == 1 and arguments[0].get('known')
          and type(arguments[0].get('value')) is str and len(arguments[0]['value']) <= 10000):
        result = {'kind': 'data', 'known': bool(receiver.get('known')), 'python_shape': 'bool'}
        if receiver.get('known') and type(receiver.get('value')) is str:
            result['value'] = receiver['value'].endswith(arguments[0]['value'])
    else:
        return None
    proof.effects.append({'operation': 'builtin_call', 'target': 'str.' + method,
        'impact': 'data_only', 'element_path': [], 'receiver_shape': 'str',
        'protocol': 'finite_builtin_text',
        'argument_shapes': [['str'] for _ in arguments],
        'output_shape': 'list_of_str' if method == 'split' else 'bool' if method == 'endswith' else 'str',
        'restriction': 'explicit_nonempty_separator' if method == 'split'
                       else 'literal_string_suffix' if method == 'endswith'
                       else 'no_attribute_or_item_fields',
        'function': dict(module=ref.module, qualname=ref.qualname,
                         file_path=ref.file_path, lineno=ref.lineno),
        'evidence': proof.evidence_at(ref, node),
        'conditions': list(proof.conditions), 'completion': 'normal_return'})
    return result
