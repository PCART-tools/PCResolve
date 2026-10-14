## @package pcresolve._callable_instance_binding
#  Narrow snapshot bindings for direct module-level, data-only constructions.
import ast
import copy
import hashlib
import json
from dataclasses import asdict

from .program_facts import FunctionSignature


NODE_LIMIT = 1000000
STATE_LIMIT = 2000


def snapshot_digest(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode('utf-8')).hexdigest()


def finite(node, values):
    if isinstance(node, ast.Constant) and type(node.value) in (
            str, int, float, bool, type(None)):
        return {'kind': 'literal', 'value': node.value}
    if isinstance(node, ast.Name):
        return copy.deepcopy(values.get(node.id))
    if isinstance(node, ast.Dict) and len(node.keys) <= STATE_LIMIT:
        items = {}
        for key, value in zip(node.keys, node.values):
            fact = finite(value, values)
            if (not isinstance(key, ast.Constant) or type(key.value) is not str
                    or fact is None):
                return None
            items[key.value] = fact
        return {'kind': 'mapping', 'items': items}
    if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) <= STATE_LIMIT:
        items = [finite(item, values) for item in node.elts]
        if all(item is not None for item in items):
            return {'kind': 'tuple' if isinstance(node, ast.Tuple) else 'list', 'items': items}
    return None


## Explain a saved source candidate without promoting runtime dispatch.
#  @param summary Current value-flow summary and its source snapshot.
#  @param facts Direct module constructor provenance.
#  @param target Exact source __call__ definition.
#  @return Conditional binding and closed finite initial state, or explicit issues.
def source_binding(summary, facts, target):
    analyzer = summary.analyzer
    key = facts['qualified_name'], target[0]
    cache = analyzer._callable_instance_binding_cache
    if key in cache:
        return copy.deepcopy(cache[key])
    ref, method = target
    module_ref = facts['module_ref']
    class_ref = facts['class_ref']
    issues, evidence, approved = [], [], set()
    values, state = {}, {}
    parameters = method.args.posonlyargs + method.args.args

    def issue(reason, owner=None, node=None):
        item = {'reason': reason}
        if node is not None:
            item['evidence'] = summary.evidence_at(owner or module_ref, node)
        if item not in issues:
            issues.append(item)

    def permit(owner, statement):
        evidence.append(summary.evidence_at(owner, statement))
        approved.update(id(node) for node in ast.walk(statement))

    matches = analyzer._definition_index.find(class_ref.module, class_ref.qualname, kind='class')
    cls = matches[0][1] if len(matches) == 1 else None
    if cls is None or cls.bases or cls.decorator_list or cls.keywords:
        issue('callable_instance_class_lookup_unconfirmed')
    methods = [member for member in cls.body if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))] if cls else []
    initializers = [(r, n) for r, n in analyzer._definition_index.find(
        class_ref.module, class_ref.qualname + '.__init__') if isinstance(n, ast.FunctionDef)]
    init = initializers[0] if len(initializers) == 1 else None
    custom = {'__getattribute__', '__getattr__', '__setattr__', '__delattr__', '__new__', '__slots__'}
    if (not parameters or not isinstance(method, ast.FunctionDef) or method.decorator_list
            or any(member.name in custom or member.decorator_list for member in methods)):
        issue('callable_instance_protocol_unconfirmed')
    if init is None or init[1].decorator_list:
        issue('callable_instance_constructor_unconfirmed')

    argument_names = {record['node'].id for record in facts['arguments']
                      if isinstance(record.get('node'), ast.Name)}
    watched = {facts['qualified_name']} | {module_ref.module + '.' + name for name in argument_names}
    watched_modules = {name.rpartition('.')[0] for name in watched}
    for statement in facts['source_body']:
        if statement is facts['assignment']:
            permit(module_ref, statement)
            break
        targets = (statement.targets if isinstance(statement, ast.Assign) else
                   [statement.target] if isinstance(statement, ast.AnnAssign) else [])
        for destination in targets:
            root = destination
            while isinstance(root, (ast.Attribute, ast.Subscript)):
                root = root.value
            if not isinstance(root, ast.Name) or root.id not in argument_names:
                continue
            value = finite(statement.value, values)
            if isinstance(destination, ast.Name) and value is not None:
                values[destination.id] = value
                permit(module_ref, statement)
            elif (isinstance(destination, ast.Subscript) and isinstance(destination.value, ast.Name)
                    and isinstance(destination.slice, ast.Constant)
                    and type(destination.slice.value) is str and value is not None
                    and values.get(root.id, {}).get('kind') == 'mapping'):
                values[root.id]['items'][destination.slice.value] = value
                permit(module_ref, statement)
            else:
                issue('callable_instance_state_unconfirmed', node=statement)
    if init:
        init_ref, initializer = init
        args = initializer.args.posonlyargs + initializer.args.args
        defaults = dict(FunctionSignature.from_ast(initializer.args).defaults)
        constructor_values = {}
        for record in facts['arguments']:
            constructor_values[record['parameter']] = finite(record['node'], values)
        for name, default in defaults.items():
            if name not in constructor_values:
                constructor_values[name] = finite(default, {})
        if (not args or initializer.args.vararg or initializer.args.kwarg
                or any(value is None for value in constructor_values.values())):
            issue('callable_instance_state_unconfirmed')
        init_name = args[0].arg if args else ''
        for statement in initializer.body:
            if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and type(statement.value.value) is str):
                continue
            destinations = statement.targets if isinstance(statement, ast.Assign) else []
            value = finite(statement.value, constructor_values) if destinations else None
            if (len(destinations) != 1 or not isinstance(destinations[0], ast.Attribute)
                    or not isinstance(destinations[0].value, ast.Name)
                    or destinations[0].value.id != init_name or value is None
                    or destinations[0].attr.startswith('__')):
                issue('callable_instance_constructor_effects_unmodeled', init_ref, statement)
                continue
            state[destinations[0].attr] = value
            evidence.append(summary.evidence_at(init_ref, statement))
        if cls:
            for member in cls.body:
                if not isinstance(member, (ast.FunctionDef, ast.Assign, ast.AnnAssign, ast.Pass)) and not (
                        isinstance(member, ast.Expr) and isinstance(member.value, ast.Constant)
                        and type(member.value.value) is str):
                    issue('callable_instance_class_effects_unmodeled', class_ref, member)
                if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                       and node.id in custom for node in ast.walk(member)):
                    issue('callable_instance_protocol_unconfirmed', class_ref, member)
                if getattr(member, 'name', None) in state or (not isinstance(
                        member, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                            isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                            and node.id in state for node in ast.walk(member))):
                    issue('callable_instance_state_descriptor_unconfirmed', class_ref, member)
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member is not initializer:
                    receiver = (member.args.posonlyargs + member.args.args)
                    receiver = receiver[0].arg if receiver else ''
                    for node in ast.walk(member):
                        if isinstance(node, (ast.Attribute, ast.Subscript)):
                            root = node
                            while isinstance(root, (ast.Attribute, ast.Subscript)):
                                root = root.value
                            if isinstance(root, ast.Name) and root.id == receiver and isinstance(
                                    node.ctx, (ast.Store, ast.Del)):
                                issue('callable_instance_state_write', class_ref, node)
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                            root = node.func.value
                            while isinstance(root, (ast.Attribute, ast.Subscript)):
                                root = root.value
                            if isinstance(root, ast.Name) and root.id == receiver:
                                issue('callable_instance_state_protocol_unmodeled', class_ref, node)
                    for node in ast.walk(member):
                        for child in ast.iter_child_nodes(node):
                            if (isinstance(child, ast.Name) and child.id == receiver
                                    and isinstance(child.ctx, ast.Load) and not isinstance(node, ast.Attribute)):
                                issue('callable_instance_receiver_escape', class_ref, node)

    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    if truncated:
        issue('callable_instance_binding_budget')
    for written, attribute, reason, owner, node in writes:
        if written == class_ref and attribute in {'__call__', '__init__', '*', '__bases__', '__class__'} | custom | set(state):
            issue(reason, owner, node)

    remaining = NODE_LIMIT
    for module, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            owner = type(module_ref)(module, '', path)
            imports = analyzer.imports.get(module, {})
            for statement in body:
                pending = [(statement, None)]
                while pending:
                    node, parent = pending.pop()
                    remaining -= 1
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    if remaining < 0:
                        issue('callable_instance_binding_budget')
                        break
                    if id(node) not in approved and isinstance(node, (ast.Name, ast.Attribute)):
                        spelling = ast.unparse(node)
                        first, dot, rest = spelling.partition('.')
                        qualified = imports.get(first, module + '.' + first) + dot + rest
                        if qualified in watched:
                            direct_call = (qualified == facts['qualified_name']
                                           and isinstance(parent, ast.Call) and parent.func is node)
                            if not direct_call:
                                issue('callable_instance_visible_write_or_escape', owner, node)
                        elif qualified in watched_modules and not isinstance(parent, ast.Attribute):
                            issue('callable_instance_module_alias_or_escape', owner, node)
                    pending.extend((child, node) for child in ast.iter_child_nodes(node))
                if remaining < 0:
                    break
            if remaining < 0:
                break
        if remaining < 0:
            break
    evidence.extend([summary.evidence_at(class_ref, cls)] if cls else [])
    evidence.append(summary.evidence_at(ref, method))
    if len(approved) + (sum(1 for _ in ast.walk(init[1])) if init else 0) > STATE_LIMIT:
        issue('callable_instance_state_budget')
    result = {'status': 'unconfirmed' if issues else 'source_bound',
              'basis': 'source_snapshot', 'runtime_target_confirmed': False,
              'target': asdict(ref), 'instance_type': asdict(class_ref),
              'definition': summary.evidence_at(ref, method),
              'implicit_binding': {'parameter': parameters[0].arg if parameters else None,
                                   'status': 'unconfirmed' if issues else 'static_bound'},
              'receiver_state': state if not issues else {}, 'issues': issues,
              'evidence': evidence, 'source_hashes': {path: analyzer.hashes[path] for path in
                  {ref.file_path, class_ref.file_path, module_ref.file_path} if path in analyzer.hashes},
              'source_hash_policy': 'utf-8-sig-universal-newlines',
              'snapshot_sha256': snapshot_digest(analyzer.hashes),
              'assumptions': ['source_snapshot_bindings_hold', 'standard_instance_construction_and_lookup',
                              'no_external_monkeypatch_or_import_hook',
                              'no_unmodeled_indirect_instance_or_state_mutation']}
    cache[key] = copy.deepcopy(result)
    return result
