## @package pcresolve.keyword_validation
#  Source obligations for mapping-key attribute validation, never runtime facts.

import ast
from dataclasses import asdict


def _nodes(root):
    pending = [root]
    while pending:
        item = pending.pop()
        if item is not root and isinstance(item, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield item
        pending.extend(reversed(list(ast.iter_child_nodes(item))))


def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Describe bounded source guards requiring independently observed lookup values.
#  @param analyzer Fixed source analyzer, used only for lexical builtin binding.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Neutral guard obligations; no conclusion about a particular argument.
def checks(analyzer, ref, node):
    nodes = []
    for item in _nodes(node):
        nodes.append(item)
        if len(nodes) > 2000:
            break
    if len(nodes) > 2000:
        return []
    parameters = {arg.arg for arg in node.args.posonlyargs + node.args.args}
    if not all(analyzer._builtin_name_status(ref, node, name) == 'confirmed_builtin'
               for name in ('getattr', 'callable', 'AttributeError')):
        return []
    result = []
    for loop in nodes:
        if not (isinstance(loop, ast.For) and isinstance(loop.target, (ast.Tuple, ast.List))
                and len(loop.target.elts) == 2
                and all(isinstance(value, ast.Name) for value in loop.target.elts)
                and isinstance(loop.iter, ast.Call) and not loop.iter.args
                and not loop.iter.keywords and isinstance(loop.iter.func, ast.Attribute)
                and loop.iter.func.attr == 'items' and isinstance(loop.iter.func.value, ast.Name)
                and loop.iter.func.value.id in parameters):
            continue
        key, value = (item.id for item in loop.target.elts)
        for branch in [loop.body] + [part for child in _nodes(loop)
                                     if isinstance(child, ast.If) for part in (child.body, child.orelse)]:
            for assignment, guard in zip(branch, branch[1:]):
                if not (isinstance(assignment, ast.Assign) and len(assignment.targets) == 1
                        and isinstance(assignment.targets[0], ast.Name)
                        and isinstance(assignment.value, ast.Call)
                        and isinstance(assignment.value.func, ast.Name)
                        and assignment.value.func.id == 'getattr'
                        and len(assignment.value.args) == 3 and not assignment.value.keywords
                        and isinstance(assignment.value.args[0], ast.Name)
                        and assignment.value.args[0].id in parameters
                        and isinstance(assignment.value.args[2], ast.Constant)
                        and assignment.value.args[2].value is None
                        and isinstance(guard, ast.If) and len(guard.body) == 1
                        and isinstance(guard.body[0], ast.Raise) and guard.body[0].cause is None):
                    continue
                lookup = assignment.targets[0].id
                template = assignment.value.args[1]
                if not isinstance(template, ast.JoinedStr):
                    continue
                fields = [v for v in template.values if isinstance(v, ast.FormattedValue)]
                if (len(fields) != 1 or not isinstance(fields[0].value, ast.Name)
                        or fields[0].value.id != key or fields[0].conversion != -1
                        or fields[0].format_spec is not None
                        or any(not isinstance(v, (ast.Constant, ast.FormattedValue))
                               or isinstance(v, ast.Constant) and type(v.value) is not str
                               for v in template.values)):
                    continue
                predicate = guard.test
                if not (isinstance(predicate, ast.UnaryOp) and isinstance(predicate.op, ast.Not)
                        and isinstance(predicate.operand, ast.Call)
                        and isinstance(predicate.operand.func, ast.Name)
                        and predicate.operand.func.id == 'callable'
                        and len(predicate.operand.args) == 1 and not predicate.operand.keywords
                        and isinstance(predicate.operand.args[0], ast.Name)
                        and predicate.operand.args[0].id == lookup):
                    continue
                raised = guard.body[0]
                if not (isinstance(raised.exc, ast.Call) and isinstance(raised.exc.func, ast.Name)
                        and raised.exc.func.id == 'AttributeError'):
                    continue
                position = template.values.index(fields[0])
                result.append({'kind': 'mapping_member_validation', 'status': 'requires_observation',
                    'function': asdict(ref), 'mapping_parameter': loop.iter.func.value.id,
                    'key_variable': key, 'value_variable': value, 'lookup_variable': lookup,
                    'receiver_parameter': assignment.value.args[0].id,
                    'attribute_template': {
                        'prefix': ''.join(v.value for v in template.values[:position]),
                        'suffix': ''.join(v.value for v in template.values[position + 1:])},
                    'lookup_missing_value': None, 'exception': 'AttributeError',
                    'runtime_rejection_confirmed': False,
                    'lookup_evidence': _span(ref, assignment),
                    'guard_evidence': _span(ref, guard.test), 'raise_evidence': _span(ref, raised),
                    'iteration_evidence': _span(ref, loop),
                    'source_hash': analyzer.hashes.get(ref.file_path)})
    return result
