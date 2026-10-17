## @package pcresolve._decorator_text
#  Bounded immutable text inputs and builtin text operations for decoration proofs.

import ast
import string

from .scope_facts import statement_scope_facts

_TEXT_BINDING_NODE_LIMIT = 1000000


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
    writes = getattr(analyzer, '_decorator_literal_writes', None)
    if writes is None:
        writes, count = set(), 0
        for module_bodies in analyzer.module_bodies.values():
            for _, body in module_bodies:
                for statement in body:
                    for node in ast.walk(statement):
                        count += 1
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
        analyzer._decorator_literal_writes = writes
    if name in writes:
        return None
    # Dynamic names elsewhere are not assigned to this module without an alias
    # proof. The explicit source-binding premise excludes indirect mutation.
    proof.extra_assumptions.append('source_literal_binding_no_indirect_mutation')
    proof.evidence.append(proof.evidence_at(caller, bindings[0]))
    return {'kind': 'data', 'value': bindings[0].value.value, 'known': True,
            'python_shape': 'str'}


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
        if any(field is not None and (field and not field.isdecimal()
                or spec or conversion) for _, field, spec, conversion in fields):
            return None
        result = {'kind': 'data', 'known': False, 'python_shape': 'str'}
    else:
        return None
    proof.effects.append({'operation': 'builtin_call', 'target': 'str.' + method,
        'impact': 'data_only', 'element_path': [], 'receiver_shape': 'str',
        'protocol': 'finite_builtin_text',
        'argument_shapes': [['str'] for _ in arguments],
        'output_shape': 'list_of_str' if method == 'split' else 'str',
        'restriction': 'explicit_nonempty_separator' if method == 'split'
                       else 'no_attribute_or_item_fields',
        'function': dict(module=ref.module, qualname=ref.qualname,
                         file_path=ref.file_path, lineno=ref.lineno),
        'evidence': proof.evidence_at(ref, node),
        'conditions': list(proof.conditions), 'completion': 'normal_return'})
    return result
