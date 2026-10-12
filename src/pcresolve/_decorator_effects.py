## @package pcresolve._decorator_effects
#  Private, bounded flow-adapter proof for one source decoration, not ownership.

import ast
import copy
from dataclasses import asdict

from .program_facts import FunctionSignature, bind_ast_call
from .scope_facts import statement_scope_facts
from .effect_facts import container_method_effect, contains_yield


def _data(value=None, known=False):
    result = {'kind': 'data', 'value': value, 'known': known}
    if known and type(value) in (str, int, bool, float, type(None)):
        result['python_shape'] = type(value).__name__
    return result


def _unique(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _data_shapes(value):
    if value['kind'] != 'data':
        return set()
    shape = value.get('python_shape')
    if shape == 'str_or_none':
        return {'str', 'NoneType'}
    if shape == 'scalar':
        return {'str', 'int', 'bool', 'float', 'NoneType'}
    if shape in ('str', 'int', 'bool', 'float', 'NoneType'):
        return {shape}
    return set(value.get('python_shapes', ()))


def _shaped_data(shapes):
    value = _data()
    if len(shapes) == 1:
        value['python_shape'] = next(iter(shapes))
    elif shapes == {'str', 'NoneType'}:
        value['python_shape'] = 'str_or_none'
    elif shapes:
        value['python_shapes'] = tuple(sorted(shapes))
    return value


def _truth(value):
    if not _data_shapes(value):
        return None
    if value.get('known'):
        return bool(value['value'])
    return value.get('truthiness')


def _join_values(values):
    if values and all(value == values[0] for value in values):
        return values[0]
    shapes = [_data_shapes(value) for value in values]
    result = _shaped_data(set().union(*shapes)) if shapes and all(shapes) else _data()
    truths = [_truth(value) for value in values]
    if truths and truths[0] is not None and all(truth == truths[0] for truth in truths):
        result['truthiness'] = truths[0]
    return result


## A finite syntax proof of function-object effects for a single decoration.
class _DecoratorEffects:
    def __init__(self, analyzer, definition, evidence, limit):
        self.analyzer = analyzer
        self.ref, self.node = definition
        self.evidence_at = evidence
        self.remaining = limit
        self.stack = []
        self.effects, self.boundaries, self.evidence = [], [], []
        self.state = {}
        self.receiver_class = None
        self.dispatch_unconfirmed = False
        self.construction = None
        self.conditions = []
        self.documentation = dict(_data(), python_shape=(
            'str' if ast.get_docstring(self.node, clean=False) is not None else 'str_or_none'))
        self.extra_assumptions = []

    def issue(self, reason, ref, node, **details):
        self.boundaries.append({'reason': reason, 'function': asdict(ref),
                                'evidence': self.evidence_at(ref, node),
                                'conditions': copy.deepcopy(self.conditions), **details})

    def builtin(self, name, ref, node):
        return (name not in self.analyzer._scope_facts(node).bound
                and not any(name in bindings for bindings in
                            self.analyzer.import_binding_facts.get(ref.module, [])))

    def binding(self, target, call, receiver=False, call_ref=None):
        ref, node = target
        call_ref = call_ref or self.ref
        parameters = node.args.posonlyargs + node.args.args
        signature = FunctionSignature.from_ast(node.args, parameters[1:] if receiver else parameters)
        records, reasons = bind_ast_call(call, signature)
        if reasons or any(item['status'] != 'exact' for item in records):
            self.issue('decorator_binding_unconfirmed', call_ref, call)
            return {}
        env = {name: _data(value.value, True) if isinstance(value, ast.Constant) else _data()
               for name, value in signature.defaults}
        bound = {item['parameter'] for item in records}
        for name, value in signature.defaults:
            if name not in bound and not isinstance(value, ast.Constant):
                self.issue('decorator_default_unproven', ref, value)
        for item in records:
            expression = item['node']
            env[item['parameter']] = (_data(expression.value, True)
                if isinstance(expression, ast.Constant) else _data())
            if not isinstance(expression, ast.Constant):
                self.issue('decorator_argument_unproven', call_ref, expression)
        if receiver:
            self.construction['parameter_bindings'] = [
                {'parameter': item['parameter'], 'argument': item['argument'],
                 'status': item['status'], 'evidence': self.evidence_at(call_ref, item['node'])}
                for item in records]
        return env

    def instance(self, class_target, constructor, module_ref=None, assignment=None):
        class_ref, cls = class_target
        previous_issues = len(self.boundaries)
        self.receiver_class = class_ref
        self.construction = {'class': asdict(class_ref),
            'expression': self.evidence_at(module_ref or self.ref, constructor),
            'parameter_bindings': []}
        self.evidence.append(self.evidence_at(class_ref, cls))
        if assignment is not None:
            self.evidence.append(self.evidence_at(module_ref, assignment))
        hierarchy = self.analyzer._class_mro(class_ref.module, class_ref.qualname)
        if not self.analyzer._ordinary_construction(class_ref) or hierarchy is None:
            self.issue('decorator_construction_unconfirmed', class_ref, cls)
            return None
        for base_ref, base in hierarchy:
            if any(member.name in ('__getattr__', '__getattribute__', '__setattr__',
                                   '__delattr__', '__init_subclass__')
                   for member in base.body if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))):
                self.issue('decorator_receiver_customization', base_ref, base)
            if any(isinstance(member, (ast.Assign, ast.AnnAssign)) and not (
                    isinstance(member, ast.AnnAssign) and member.value is None) for member in base.body):
                self.issue('decorator_instance_descriptor_unconfirmed', base_ref, base)
            if any(member.decorator_list for member in base.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))):
                self.issue('decorator_instance_descriptor_unconfirmed', base_ref, base)
            if any(isinstance(member, (ast.If, ast.Try, ast.For, ast.While, ast.With))
                   for member in base.body):
                self.issue('decorator_member_binding_unconfirmed', base_ref, base)
            for name in ('__call__', '__init__'):
                members = [member for member in base.body if name in statement_scope_facts([member]).bound]
                if members and (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)):
                    self.issue('decorator_member_binding_unconfirmed', base_ref, base)
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            self.issue('decorator_effect_budget', class_ref, cls)
        identities = {(item.module, item.qualname) for item, _ in hierarchy}
        for written, attribute, _, source_ref, source_node in writes:
            if (written.module, written.qualname) in identities:
                self.issue('decorator_class_write', source_ref, source_node)
        target = self.analyzer._definition_index.find(class_ref.module, class_ref.qualname + '.__call__')
        target = target[0] if len(target) == 1 else self.analyzer._inherited_method(
            class_ref.module, class_ref.qualname, '__call__')
        init = self.analyzer._definition_index.find(class_ref.module, class_ref.qualname + '.__init__')
        init = init[0] if len(init) == 1 else self.analyzer._inherited_method(
            class_ref.module, class_ref.qualname, '__init__')
        if init:
            env = self.binding(init, constructor, receiver=True, call_ref=module_ref)
            parameters = init[1].args.posonlyargs + init[1].args.args
            if parameters:
                env[parameters[0].arg] = {'kind': 'receiver'}
                self.run(init, env, initializing=True)
        elif constructor.args or constructor.keywords:
            self.issue('decorator_binding_unconfirmed', class_ref, constructor)
        self.dispatch_unconfirmed = len(self.boundaries) != previous_issues
        return target

    def resolve(self, expression):
        probe = copy.copy(self.node)
        probe.decorator_list = [expression.func if isinstance(expression, ast.Call) else expression]
        resolved = self.analyzer._decorator_definition((self.ref, probe))
        captures = {}
        if isinstance(expression, ast.Call):
            class_target = self.analyzer._decorator_definition((self.ref, probe), kind='class')
            if class_target:
                return self.instance(class_target, expression), captures
            if resolved and isinstance(resolved[1], ast.FunctionDef):
                factory_ref, factory = resolved
                captures = self.binding(resolved, expression)
                body = [item for item in factory.body if not (isinstance(item, ast.Expr)
                    and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str))]
                if (len(body) == 2 and isinstance(body[0], ast.FunctionDef)
                        and not body[0].decorator_list and isinstance(body[1], ast.Return)
                        and isinstance(body[1].value, ast.Name) and body[1].value.id == body[0].name):
                    matches = self.analyzer._definition_index.find(factory_ref.module,
                        factory_ref.qualname + '.' + body[0].name)
                    if len(matches) == 1:
                        nested = body[0]
                        if (nested.args.defaults or any(value is not None for value in nested.args.kw_defaults)
                                or nested.returns is not None or any(argument.annotation is not None
                                    for argument in nested.args.posonlyargs + nested.args.args + nested.args.kwonlyargs
                                    + [item for item in (nested.args.vararg, nested.args.kwarg) if item is not None])):
                            self.issue('decorator_factory_definition_effects_unproven', factory_ref, nested)
                        self.evidence.extend([self.evidence_at(self.ref, expression),
                                              self.evidence_at(factory_ref, body[1])])
                        return matches[0], captures
                self.issue('decorator_factory_unproven', factory_ref, factory)
                return None, {}
        elif resolved and isinstance(resolved[1], ast.FunctionDef):
            return resolved, captures
        if isinstance(expression, (ast.Name, ast.Attribute)):
            name = ast.unparse(expression)
            target, facts, cause = self.analyzer._module_callable_instance(self.ref, name, None)
            if facts:
                matches = self.analyzer._definition_index.find(facts['class_ref'].module,
                    facts['class_ref'].qualname, kind='class')
                if len(matches) == 1:
                    return self.instance(matches[0], facts['constructor'], facts['module_ref'],
                                         facts['assignment']), captures
            # Same unique module assignment, allowing a source-inherited initializer.
            first, dot, rest = name.partition('.')
            imported = self.analyzer.imports.get(self.ref.module, {}).get(first)
            qualified = (imported + (dot + rest if dot else '') if imported
                         else self.ref.module + '.' + name)
            module, _, variable = qualified.rpartition('.')
            bindings = self.analyzer.import_binding_facts.get(module, [])
            bodies = self.analyzer.module_bodies.get(module, [])
            if (len(bindings) == len(bodies) == 1
                    and (not imported or self.analyzer._stable_import_name(self.ref.module + '.' + first))):
                statements = bindings[0].get(variable, [])
                if (len(statements) == 1 and statements[0] in bodies[0][1]
                        and isinstance(statements[0], (ast.Assign, ast.AnnAssign))
                        and isinstance(statements[0].value, ast.Call)
                        and cause in (None, 'dynamic_constructor')):
                    assignment = statements[0]
                    module_ref = type(self.ref)(module, '', bodies[0][0])
                    class_target = self.analyzer._class_symbol(module + '.' + ast.unparse(assignment.value.func))
                    if class_target is None:
                        class_target = self.analyzer._resolve_class(module_ref, ast.unparse(assignment.value.func))
                    if class_target:
                        return self.instance(class_target, assignment.value, module_ref, assignment), captures
        self.issue('decorator_target_unresolved', self.ref, expression)
        return None, {}

    def method_proof(self, class_ref, method):
        proof = self.analyzer._dict_method_binding(class_ref, method)
        if proof is None:
            return None
        if proof['status'] != 'source_bound':
            target = self.analyzer._definition_index.find(class_ref.module, class_ref.qualname, kind='class')[0]
            self.issue('decorator_effect_budget', *target, cause=proof['reason'])
            return None
        proof = dict(proof)
        proof['evidence'] = [self.evidence_at(ref, cls) for ref, cls in proof.pop('hierarchy')]
        self.evidence.extend(proof['evidence'])
        return proof

    def data_instance(self, selected, node, target):
        ref, cls = selected
        proof = self.method_proof(ref, 'setdefault')
        hierarchy = self.analyzer._dict_subclass_hierarchy(ref)
        if (proof is None or node.args or node.keywords or any(
                not (isinstance(member, ast.FunctionDef) and member.name == '__missing__'
                     and not member.decorator_list and not member.args.defaults
                     and not any(value is not None for value in member.args.kw_defaults)
                     and member.returns is None and not any(argument.annotation is not None
                         for argument in member.args.posonlyargs + member.args.args + member.args.kwonlyargs
                         + [item for item in (member.args.vararg, member.args.kwarg) if item is not None])
                     or isinstance(member, ast.Pass) or isinstance(member, ast.Expr)
                     and isinstance(member.value, ast.Constant) and isinstance(member.value.value, str))
                for _, base in hierarchy or () for member in base.body)):
            self.issue('decorator_data_construction_unproven', target[0], node)
            return _data()
        value = {'kind': 'data', 'category': 'documentation_cache', 'class_ref': ref,
                 'known': False, 'allocation': self.evidence_at(target[0], node),
                 'source': '$documentation_cache:%s:%s:%s' % (target[0].file_path, node.lineno, node.col_offset)}
        self.effects.append({'operation': 'construction', 'target': 'documentation_cache',
            'impact': 'data_only', 'element_path': [], 'class': asdict(ref), 'method_binding': proof,
            'object_source': value['source'],
            'function': asdict(target[0]), 'evidence': value['allocation'],
            'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
        self.extra_assumptions.append('documentation_cache_not_externally_mutated')
        return value

    def source_call(self, selected, node, arguments, receiver=None, initializing=False):
        ref, definition = selected
        params = definition.args.posonlyargs + definition.args.args
        signature = FunctionSignature.from_ast(definition.args, params[1:] if receiver else params)
        records, reasons = bind_ast_call(node, signature)
        if (reasons or any(isinstance(item, ast.Starred) for item in node.args)
                or any(keyword.arg is None for keyword in node.keywords)
                or any(item['status'] != 'exact' or item['destination_kind'] != 'parameter' for item in records)):
            return None
        incoming = {}
        for name, default in signature.defaults:
            if name not in {item['parameter'] for item in records}:
                if not isinstance(default, ast.Constant):
                    self.issue('decorator_default_unproven', ref, default)
                incoming[name] = _data(default.value, True) if isinstance(default, ast.Constant) else _data()
        if receiver and params:
            incoming[params[0].arg] = receiver
        for item, value in zip(records, arguments):
            incoming[item['parameter']] = value
        self.evidence.append(self.evidence_at(ref, definition))
        self.effects.append({'operation': 'helper_call', 'target': asdict(ref),
            'impact': 'analyzed_source', 'element_path': [], 'evidence': self.evidence_at(self.stack[-1], node),
            'function': asdict(self.stack[-1]),
            'parameter_bindings': [{key: item[key] for key in ('parameter', 'argument', 'status')}
                                   for item in records],
            'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
        returns, falls = self.run(selected, incoming, initializing)
        values = returns + ([_data(None, True)] if falls else [])
        if values and all(value == values[0] for value in values):
            return values[0]
        if any(value['kind'] != 'data' for value in values):
            self.issue('decorator_helper_return_unproven', ref, definition)
        shapes = {value.get('python_shape') for value in values}
        return dict(_data(), python_shape=next(iter(shapes))) if len(shapes) == 1 and None not in shapes else _data()

    def format_mapping(self, node, left, mapping, target):
        ref, _ = target
        proof = self.method_proof(mapping['class_ref'], '__getitem__')
        if proof is None:
            self.issue('decorator_format_protocol_unproven', ref, node)
            return _data()
        if left.get('python_shape') != 'str':
            self.issue('decorator_format_protocol_unproven', ref, node)
        self.effects.append({'operation': 'mapping_lookup', 'target': 'documentation_cache',
            'impact': 'data_protocol', 'element_path': ['*'], 'method_binding': proof,
            'object_source': mapping['source'],
            'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
            'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
        hierarchy = self.analyzer._dict_subclass_hierarchy(mapping['class_ref'])
        missing = None
        for class_ref, cls in hierarchy:
            if '__missing__' not in statement_scope_facts(cls.body).bound:
                continue
            matches = self.analyzer._definition_index.find(class_ref.module, class_ref.qualname + '.__missing__')
            missing = matches[0] if len(matches) == 1 else None
            break
        if missing is not None:
            parameters = missing[1].args.posonlyargs + missing[1].args.args
            if (len(parameters) != 2 or missing[1].args.vararg or missing[1].args.kwarg
                    or missing[1].args.kwonlyargs or missing[1].args.defaults):
                self.issue('decorator_format_protocol_unproven', ref, node)
                return _data()
            self.conditions.append({'mapping_membership': {'object_source': mapping['source'],
                'element_path': ['*'], 'state': 'absent'}, 'evidence': self.evidence_at(ref, node)})
            self.evidence.append(self.evidence_at(*missing))
            try:
                values, falls = self.run(missing, {parameters[0].arg: mapping,
                    parameters[1].arg: dict(_data(), python_shape='str')})
            finally:
                self.conditions.pop()
            if falls or not values or any(value.get('python_shape') not in ('str', 'int', 'bool', 'float', 'NoneType', 'scalar')
                                          for value in values):
                self.issue('decorator_format_value_unproven', missing[0], missing[1])
        else:
            self.issue('decorator_format_value_unproven', ref, node)
        return dict(_data(), python_shape='str')

    ## Split only proved builtin scalar shapes by their short-circuit truth value.
    #  @param value Operand value; unknown protocols retain a boundary.
    #  @param ref Source function containing the operand.
    #  @param node Operand source expression.
    #  @return Reachable truth cases with bounded value refinements.
    def truth_cases(self, value, ref, node):
        truth = _truth(value)
        if truth is not None:
            return {truth: value}
        shapes = _data_shapes(value)
        if not shapes:
            self.issue('decorator_truth_protocol_unproven', ref, node)
            return {False: value, True: value}
        falsy = {'str': '', 'int': 0, 'bool': False, 'float': 0.0, 'NoneType': None}
        cases = {False: _join_values([_data(falsy[shape], True) for shape in sorted(shapes)])}
        if shapes - {'NoneType'}:
            cases[True] = dict(_shaped_data(shapes - {'NoneType'}), truthiness=True)
        return cases

    ## Refine direct local/documentation reads within a reachable expression path.
    #  @param node Operand expression being tested.
    #  @param value Truth-refined value, not a runtime object identity.
    #  @param env Path-local name bindings.
    def refine_truth(self, node, value, env):
        if isinstance(node, ast.Name) and node.id in env:
            env[node.id] = value
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            receiver = env.get(node.value.id, {})
            if receiver.get('kind') == 'function' and node.attr == '__doc__':
                self.documentation = value
            elif receiver.get('kind') == 'receiver' and node.attr in self.state:
                self.state[node.attr] = value

    ## Join short-circuit results and object states without evaluating skipped calls.
    #  @param node Boolean expression.
    #  @param env Incoming name bindings.
    #  @param target Source definition being analyzed.
    #  @param initializing Whether receiver state is being constructed.
    #  @return Finite result shape, or unknown with retained protocol/effect issues.
    def boolean(self, node, env, target, initializing):
        ref, _ = target
        stop = isinstance(node.op, ast.Or)
        proceed = not stop
        local = dict(env)
        results, states = [], []
        condition_count = len(self.conditions)
        try:
            for index, child in enumerate(node.values):
                value = self.expression(child, local, target, initializing)
                if value['kind'] != 'data':
                    self.issue('decorator_operation_unproven', ref, child)
                if index == len(node.values) - 1:
                    results.append(value)
                    states.append((self.documentation, dict(self.state)))
                    break
                cases = self.truth_cases(value, ref, child)
                documentation, state = self.documentation, dict(self.state)
                if stop in cases:
                    self.refine_truth(child, cases[stop], local)
                    results.append(cases[stop])
                    states.append((self.documentation, dict(self.state)))
                if proceed not in cases:
                    break
                self.documentation, self.state = documentation, state
                self.refine_truth(child, cases[proceed], local)
                if len(cases) > 1:
                    self.conditions.append({'test': self.evidence_at(ref, child), 'branch': proceed})
        finally:
            del self.conditions[condition_count:]
        self.documentation = _join_values([documentation for documentation, _ in states])
        self.state = {name: _join_values([state.get(name, _data()) for _, state in states])
                      for name in set().union(*(state.keys() for _, state in states))}
        return _join_values(results)

    def expression(self, node, env, target, initializing=False):
        ref, definition = target
        if node is None:
            return _data(None, True)
        if isinstance(node, ast.Constant):
            return _data(node.value, True)
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            self.issue('decorator_value_unproven', ref, node)
            return _data()
        if isinstance(node, ast.Attribute):
            value = self.expression(node.value, env, target, initializing)
            if value['kind'] == 'function' and node.attr == '__doc__':
                return self.documentation
            if value['kind'] == 'receiver' and node.attr in self.state:
                return self.state[node.attr]
            self.issue('decorator_attribute_unproven', ref, node)
            return _data()
        if isinstance(node, ast.IfExp):
            test = self.expression(node.test, env, target, initializing)
            if test.get('known'):
                return self.expression(node.body if test['value'] else node.orelse, env, target, initializing)
            values = [self.expression(item, env, target, initializing) for item in (node.body, node.orelse)]
            if values[0] != values[1] and any(value['kind'] != 'data' for value in values):
                self.issue('decorator_object_escape', ref, node)
            return values[0] if values[0] == values[1] else _data()
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            children = (node.elts if not isinstance(node, ast.Dict) else node.keys + node.values)
            values = [self.expression(item, env, target, initializing) for item in children if item]
            if any(item['kind'] in ('function', 'receiver', 'closure') for item in values):
                self.issue('decorator_object_escape', ref, node)
            return _data()
        if isinstance(node, ast.BoolOp):
            return self.boolean(node, env, target, initializing)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare)):
            children = [item for item in ast.iter_child_nodes(node) if isinstance(item, ast.expr)]
            values = [self.expression(item, env, target, initializing) for item in children]
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and len(values) == 2
                    and values[1].get('category') == 'documentation_cache'):
                return self.format_mapping(node, values[0], values[1], target)
            if any(item['kind'] != 'data' for item in values):
                self.issue('decorator_operation_unproven', ref, node)
            elif isinstance(node, ast.BinOp):
                if all(value.get('python_shape') == 'str' for value in values) and isinstance(node.op, ast.Add):
                    return dict(_data(), python_shape='str')
                if not all(value.get('python_shape') in ('str', 'int', 'bool', 'float', 'NoneType') for value in values):
                    self.issue('decorator_data_protocol_unproven', ref, node)
            return _data()
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == 'isinstance'
                    and self.builtin('isinstance', ref, definition) and self.builtin('type', ref, definition)
                    and len(node.args) == 2 and not node.keywords
                    and isinstance(node.args[1], ast.Name) and node.args[1].id == 'type'
                    and isinstance(node.args[0], ast.Name)
                    and env.get(node.args[0].id, {}).get('kind') == 'function'):
                return _data(False, True)
            arguments = [self.expression(item, env, target, initializing) for item in node.args]
            arguments.extend(self.expression(item.value, env, target, initializing) for item in node.keywords)
            data_receiver = None
            if isinstance(node.func, ast.Attribute) and (isinstance(node.func.value, ast.Name)
                    and node.func.value.id in env or isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name) and node.func.value.value.id in env):
                data_receiver = self.expression(node.func.value, env, target, initializing)
            if data_receiver and data_receiver.get('category') == 'documentation_cache':
                contract = container_method_effect(node.func.attr, ('dict',), len(node.args))
                proof = self.method_proof(data_receiver['class_ref'], node.func.attr)
                if (node.func.attr == 'setdefault' and contract and proof and not node.keywords
                        and not any(isinstance(item, ast.Starred) for item in node.args)):
                    key = arguments[0]
                    default = arguments[1] if len(arguments) == 2 else _data(None, True)
                    if key.get('python_shape') not in ('str', 'int') or default.get('python_shape') not in (
                            'str', 'int', 'bool', 'float', 'NoneType', 'scalar'):
                        self.issue('decorator_cache_value_unproven', ref, node)
                    if any(value['kind'] != 'data' for value in arguments):
                        self.issue('decorator_object_escape', ref, node)
                    self.effects.append({'operation': 'setdefault', 'target': 'documentation_cache',
                        'impact': 'data_only', 'element_path': [key['value']] if key.get('known') else ['*'],
                        'object_source': data_receiver['source'],
                        'state_before': 'unknown', 'insertion': 'conditional', 'method_binding': proof,
                        'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                        'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
                    # This is not an alias or insertion proof; any existing entry
                    # must also have come from the checked cache's scalar writes.
                    return dict(_data(), python_shape='scalar')
                self.issue('decorator_cache_protocol_unproven', ref, node)
                return _data()
            selected, imported, qualified, first = None, None, None, ''
            if (self.receiver_class is not None and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Call) and node.func.attr == '__call__'
                    and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'super'
                    and not node.func.value.args and not node.func.value.keywords
                    and self.builtin('super', ref, definition)):
                hierarchy = self.analyzer._class_mro(self.receiver_class.module, self.receiver_class.qualname)
                owner = (ref.module, ref.qualname.rpartition('.')[0])
                position = next((index for index, (class_ref, _) in enumerate(hierarchy or ())
                                 if (class_ref.module, class_ref.qualname) == owner), None)
                if position is not None:
                    for class_ref, cls in hierarchy[position + 1:]:
                        if '__call__' not in statement_scope_facts(cls.body).bound:
                            continue
                        matches = self.analyzer._definition_index.find(class_ref.module,
                                                                      class_ref.qualname + '.__call__')
                        selected = matches[0] if len(matches) == 1 else None
                        break
            elif isinstance(node.func, (ast.Name, ast.Attribute)):
                name = ast.unparse(node.func)
                first, dot, rest = name.partition('.')
                imported = self.analyzer.imports.get(ref.module, {}).get(first)
                qualified = (imported + (dot + rest if dot else '') if imported else ref.module + '.' + name)
                if first not in self.analyzer._scope_facts(definition).bound:
                    selected = self.analyzer._resolve_import_binding(qualified)
                    class_target = self.analyzer._class_symbol(qualified)
                    if class_target:
                        return self.data_instance(class_target, node, target)
            if selected and isinstance(selected[1], ast.FunctionDef):
                receiver = ({'kind': 'receiver'} if isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Call) else None)
                result = self.source_call(selected, node, arguments, receiver, initializing)
                if result is not None:
                    return result
            imported_target = None
            if (isinstance(node.func, (ast.Name, ast.Attribute)) and imported
                    and first not in self.analyzer._scope_facts(definition).bound
                    and self.analyzer._stable_import_name(ref.module + '.' + first)):
                imported_target = qualified
            self.issue('decorator_call_unresolved', ref, node,
                **({'source_target': imported_target, 'source_available': False,
                    'affected_roles': ['documentation_data'] if all(value['kind'] == 'data' for value in arguments)
                                      else ['input_function_or_receiver']}
                   if imported_target else {}))
            if any(value['kind'] in ('function', 'receiver', 'closure') for value in arguments):
                self.issue('decorator_object_escape', ref, node)
            return _data()
        self.issue('decorator_expression_unsupported', ref, node)
        return _data()

    def assign(self, node, value, env, target, initializing):
        ref, _ = target
        if isinstance(node, ast.Name):
            env[node.id] = value
            return
        if isinstance(node, ast.Attribute):
            receiver = self.expression(node.value, env, target, initializing)
            if receiver['kind'] == 'function':
                impact = ('documentation' if node.attr == '__doc__' else
                          'execution_binding' if node.attr in ('__code__', '__defaults__', '__kwdefaults__') else
                          'signature_metadata' if node.attr in ('__signature__', '__annotations__', '__wrapped__') else
                          'unmodeled_attribute')
                self.effects.append({'operation': 'attribute_write', 'target': 'input_function',
                    'element_path': [node.attr], 'impact': impact,
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions)})
                if impact == 'execution_binding':
                    self.issue('decorator_execution_binding_write', ref, node)
                elif impact != 'documentation':
                    self.issue('decorator_attribute_effect_unproven', ref, node)
                if value['kind'] == 'function':
                    self.issue('decorator_object_escape', ref, node)
                if impact == 'documentation':
                    self.documentation = value
                return
            if receiver['kind'] == 'receiver' and value['kind'] == 'data':
                if initializing:
                    self.state[node.attr] = value
                    return
                self.issue('decorator_instance_state_write', ref, node)
                return
        self.issue('decorator_write_unproven', ref, node)
        if value['kind'] in ('function', 'closure', 'receiver'):
            self.issue('decorator_object_escape', ref, node)

    def statements(self, body, env, target, initializing):
        ref, definition = target
        returns = []
        for statement in body:
            self.evidence.append(self.evidence_at(ref, statement))
            if isinstance(statement, ast.Return):
                returns.append(self.expression(statement.value, env, target, initializing))
                return returns, False
            if isinstance(statement, ast.Pass):
                continue
            if isinstance(statement, ast.Expr):
                self.expression(statement.value, env, target, initializing)
            elif isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                value = self.expression(statement.value, env, target, initializing)
                if isinstance(statement, ast.AugAssign):
                    previous = self.expression(statement.target, env, target, initializing)
                    if value['kind'] != 'data' or previous['kind'] != 'data':
                        self.issue('decorator_operation_unproven', ref, statement)
                    value = _data()
                destinations = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                for destination in destinations:
                    self.assign(destination, value, env, target, initializing)
            elif isinstance(statement, ast.If):
                test = self.expression(statement.test, env, target, initializing)
                if initializing and not test.get('known'):
                    self.issue('decorator_constructor_branch_unproven', ref, statement)
                branches = ([(statement.body, True)] if test.get('known') and test['value']
                            else [(statement.orelse, False)] if test.get('known')
                            else [(statement.body, True), (statement.orelse, False)])
                continuing = []
                initial_doc = self.documentation
                continuing_docs = []
                for branch, selected in branches:
                    local = dict(env)
                    self.documentation = initial_doc
                    if (selected and isinstance(statement.test, ast.Attribute) and statement.test.attr == '__doc__'
                            and isinstance(statement.test.value, ast.Name)
                            and env.get(statement.test.value.id, {}).get('kind') == 'function'):
                        self.documentation = dict(initial_doc, python_shape='str')
                    self.conditions.append({'test': self.evidence_at(ref, statement.test), 'branch': selected})
                    try:
                        values, falls = self.statements(branch, local, target, initializing)
                    finally:
                        self.conditions.pop()
                    returns.extend(values)
                    if falls:
                        continuing.append(local)
                        continuing_docs.append(self.documentation)
                self.documentation = (continuing_docs[0] if continuing_docs and all(
                    value == continuing_docs[0] for value in continuing_docs) else initial_doc)
                if not continuing:
                    return returns, False
                env.clear()
                for name in set().union(*(local.keys() for local in continuing)):
                    values = [local.get(name, _data()) for local in continuing]
                    env[name] = values[0] if all(item == values[0] for item in values) else _data()
            elif isinstance(statement, ast.FunctionDef):
                evaluations = list(statement.decorator_list) + list(statement.args.defaults)
                evaluations.extend(item for item in statement.args.kw_defaults if item is not None)
                evaluations.extend(argument.annotation for argument in statement.args.posonlyargs
                    + statement.args.args + statement.args.kwonlyargs
                    + [item for item in (statement.args.vararg, statement.args.kwarg) if item is not None]
                    if argument.annotation is not None)
                if statement.returns is not None:
                    evaluations.append(statement.returns)
                for evaluation in evaluations:
                    self.expression(evaluation, env, target, initializing)
                reads = self.analyzer._scope_facts(statement).loaded
                if any(name in reads and value['kind'] == 'function' for name, value in env.items()):
                    self.issue('decorator_function_capture', ref, statement)
                    env[statement.name] = {'kind': 'closure'}
                else:
                    env[statement.name] = {'kind': 'replacement'}
            else:
                self.issue('decorator_statement_unsupported', ref, statement)
                return returns + [_data()], True
        return returns, True

    def run(self, target, env, initializing=False):
        ref, node = target
        if ref in self.stack or len(self.stack) >= 8:
            self.issue('decorator_effect_recursion', ref, node)
            return [], True
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or contains_yield(node):
            self.issue('decorator_callable_unproven', ref, node)
            return [], True
        for _ in ast.walk(node):
            self.remaining -= 1
            if self.remaining < 0:
                self.issue('decorator_effect_budget', ref, node)
                return [], True
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint(force=True)
        self.stack.append(ref)
        try:
            return self.statements(node.body, dict(env), target, initializing)
        finally:
            self.stack.pop()

    def fact(self, expression, multiple=False):
        target, captures = self.resolve(expression)
        returns, falls = [], True
        if target:
            parameters = target[1].args.posonlyargs + target[1].args.args
            receiver = target[0].qualname.endswith('.__call__') and self.receiver_class is not None
            ordinary = parameters[1:] if receiver else parameters
            if (len(ordinary) != 1 or target[1].args.vararg or target[1].args.kwarg
                    or target[1].args.kwonlyargs or target[1].args.defaults):
                self.issue('decorator_binding_unconfirmed', target[0], target[1])
            else:
                env = dict(captures)
                env[ordinary[0].arg] = {'kind': 'function'}
                if receiver:
                    env[parameters[0].arg] = {'kind': 'receiver'}
                returns, falls = self.run(target, env)
        if multiple:
            self.issue('decorator_composition_unsupported', self.ref, expression)
        identity = ('preserved' if returns and not falls and all(value['kind'] == 'function' for value in returns)
                    else 'replaced' if returns and not falls and all(value['kind'] == 'replacement' for value in returns)
                    else 'unknown')
        if multiple or self.dispatch_unconfirmed:
            identity = 'unknown'
        if identity == 'unknown':
            self.issue('decorator_return_identity_unproven', self.ref, expression)
        if identity == 'replaced':
            self.issue('decorator_callable_replaced', self.ref, expression)
        modified = identity == 'replaced' or any(item['impact'] == 'execution_binding' for item in self.effects)
        body = 'modified' if modified else 'preserved' if identity == 'preserved' and not self.boundaries else 'unknown'
        evidence = _unique([self.evidence_at(self.ref, expression)] + self.evidence)
        return {'function': asdict(self.ref), 'expression': self.evidence_at(self.ref, expression),
                'target': asdict(target[0]) if target else None,
                'target_candidates': [asdict(target[0])] if target else [],
                'receiver_class': asdict(self.receiver_class) if self.receiver_class else None,
                'construction': self.construction,
                'identity_status': identity, 'body_binding_status': body,
                'effects': _unique(self.effects), 'boundaries': _unique(self.boundaries),
                'evidence': evidence, 'completion': 'normal_return', 'basis': 'source_snapshot',
                'runtime_target_confirmed': False,
                'source_hashes': {path: self.analyzer.hashes[path] for path in sorted({
                    item['file_path'] for item in evidence}) if path in self.analyzer.hashes},
                'assumptions': ['source_snapshot_bindings_hold', 'builtin_function_attribute_semantics',
                                'no_external_monkeypatch_or_import_hook'] + _unique(self.extra_assumptions)}
