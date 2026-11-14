## @package pcresolve.flow.proofs.callables.decorators._decorator_effects
#  Private, bounded flow-adapter proof for one source decoration, not ownership.
#  对单个源码装饰执行私有、有界的 flow adapter 证明，不分析归属。

import ast
import copy
import operator
from dataclasses import asdict

from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.facts.effect_facts import container_method_effect, contains_yield
from pcresolve.flow.proofs.callables.decorators._decorator_text import literal_argument, text_call
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.flow.proofs.callables.decorators._decorator_imports import cached_import as decorator_cached_import
from pcresolve.flow.proofs.callables.decorators._decorator_exceptions import builtin_raise, translate as translate_exceptions
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified as namespace_unmodified


## Construct one abstract data value with optional known literal content.
## 构造可选包含已知字面量内容的抽象数据值。
#
#  @param value Concrete literal when known.
#  @param known Whether value is statically known.
#  @return Abstract data mapping with its supported Python shape.
def _data(value=None, known=False):
    result = {'kind': 'data', 'value': value, 'known': known}
    if known and type(value) in (str, int, bool, float, type(None)):
        result['python_shape'] = type(value).__name__
    return result


## Deduplicate values while preserving their first-seen order.
## 按首次出现顺序去重。
#
#  @param items Candidate values.
#  @return Ordered list of unique values.
def _unique(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


## Return the possible Python scalar shapes represented by an abstract value.
## 返回抽象值可能表示的 Python 标量结构类型。
#
#  @param value Abstract data mapping.
#  @return Set of supported Python shape names.
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


## Construct an abstract unknown value constrained to the supplied shapes.
## 构造受给定结构类型约束的抽象未知值。
#
#  @param shapes Possible Python shape names.
#  @return Abstract data mapping constrained to those shapes.
def _shaped_data(shapes):
    value = _data()
    if len(shapes) == 1:
        value['python_shape'] = next(iter(shapes))
    elif shapes == {'str', 'NoneType'}:
        value['python_shape'] = 'str_or_none'
    elif shapes:
        value['python_shapes'] = tuple(sorted(shapes))
    return value


## Resolve known truthiness without invoking an unknown user protocol.
## 在不调用未知用户协议的前提下解析已知真值。
#
#  @param value Abstract scalar value.
#  @return Boolean truth value, or None when truthiness is unresolved.
def _truth(value):
    if not _data_shapes(value):
        return None
    if value.get('known'):
        return bool(value['value'])
    return value.get('truthiness')


## Join alternative abstract values while retaining only common facts.
## 合并备选抽象值，并仅保留共同事实。
#
#  @param values Abstract values from reachable branches.
#  @return Conservative joined abstract value.
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
## 对单个装饰执行有限语法范围内的函数对象效果证明。
class _DecoratorEffects:
    ## Initialize source, evidence, and bounded proof state.
    ## 初始化源码、证据和有界证明状态。
    #
    #  @param self Decorator effect proof state.
    #  @param analyzer Source analyzer providing definitions and namespaces.
    #  @param definition Exact decorated source definition pair.
    #  @param evidence Callback producing source evidence records.
    #  @param limit Maximum proof operations.
    #  @return None.
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
        self.dependency_paths = set()

    ## Record a conservative boundary with its source location and conditions.
    ## 记录保守边界及其源码位置和条件。
    #
    #  @param self Current decorator proof state.
    #  @param reason Boundary reason identifier.
    #  @param ref Source definition reference.
    #  @param node AST node supporting the boundary.
    #  @param details Additional structured boundary fields.
    #  @return None; appends the boundary in place.
    def issue(self, reason, ref, node, **details):
        self.boundaries.append({'reason': reason, 'function': asdict(ref),
                                'evidence': self.evidence_at(ref, node),
                                'conditions': copy.deepcopy(self.conditions), **details})

    ## Confirm a name resolves to an unmodified builtin in its source scope.
    ## 确认名称在源码作用域中解析为未修改的内建对象。
    #
    #  @param self Decorator proof state.
    #  @param name Builtin identifier to check.
    #  @param ref Scope source reference.
    #  @param node Scope AST node used for shadowing checks.
    #  @return True when builtin identity is confirmed.
    def builtin(self, name, ref, node):
        return (namespace_unmodified(self.analyzer, ref.module + '.' + name)
                and name not in self.analyzer._scope_facts(node).bound
                and not any(name in bindings for bindings in
                            self.analyzer.import_binding_facts.get(ref.module, [])))

    ## Require stable builtin bindings for scalar decorator operations.
    ## 要求标量装饰操作使用稳定的内建绑定。
    #
    #  @param self Decorator proof state and dependency collector.
    #  @param ref Source reference whose namespace is checked.
    #  @param node AST node supporting the namespace proof.
    #  @return True when the required builtin namespace is stable.
    def scalar_builtin_namespace(self, ref, node):
        if self.analyzer.index_boundaries:
            self.issue('decorator_builtin_namespace_unproven', ref, node)
            return False
        try:
            stable, paths = _stable_builtin_namespace(self.analyzer, ref,
                ('len', 'KeyError', 'TypeError', 'ValueError', 'AttributeError',
                 'isinstance', 'type', 'super'))
        except _ClassEffectLimit:
            self.issue('decorator_effect_budget', ref, node)
            return False
        self.dependency_paths.update(paths)
        if not stable:
            self.issue('decorator_builtin_namespace_unproven', ref, node)
            return False
        self.extra_assumptions.extend(['standard_builtin_namespace_preserved',
                                       'no_unmodeled_indirect_builtin_mutation'])
        return True

    ## Read documentation only from a unique, undecorated source function binding.
    ## 仅从唯一且未装饰的源码函数绑定读取文档字符串。
    #
    #  @param expression Constructor/factory argument in its defining scope.
    #  @param caller Source scope containing the argument.
    #  @return Builtin str-or-None data and source provenance, or None.
    def document_argument(self, expression, caller):
        if not (isinstance(expression, ast.Attribute) and expression.attr == '__doc__'
                and isinstance(expression.value, (ast.Name, ast.Attribute))):
            return None
        probe = copy.copy(self.node)
        probe.decorator_list = [expression.value]
        selected = self.analyzer._decorator_definition((caller, probe))
        if selected is None:
            return None
        ref, node = selected
        owner = ref.qualname.rpartition('.')[0]
        if owner:
            classes = self.analyzer._definition_index.find(ref.module, owner, kind='class')
            hierarchy = (self.analyzer._class_mro(ref.module, owner) if len(classes) == 1 else None)
            if hierarchy is None or any(cls.keywords or cls.decorator_list for _, cls in hierarchy):
                return None
        self.remaining -= 1
        if self.remaining < 0:
            self.issue('decorator_effect_budget', caller, expression)
            return None
        self.evidence.append(self.evidence_at(ref, node))
        return dict(_data(), python_shape='str_or_none', value_provenance={
            'kind': 'source_function_documentation', 'function': asdict(ref),
            'python_shape': 'str_or_none', 'evidence': self.evidence_at(caller, expression)})

    ## Bind call arguments to source parameters and retain only proven values.
    ## 将调用实参绑定到源码形参，并仅保留已证明的值。
    #
    #  @param self Decorator proof state.
    #  @param target Resolved source function pair.
    #  @param call Call expression being bound.
    #  @param receiver Whether the first parameter is the receiver.
    #  @param call_ref Source scope where the call occurs.
    #  @return Parameter-name environment containing abstract argument values.
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
            value = (_data(expression.value, True) if isinstance(expression, ast.Constant)
                     else self.document_argument(expression, call_ref)
                     or literal_argument(self, expression, call_ref))
            if item['destination_kind'] == 'var_positional':
                sequence = env.setdefault(item['parameter'], dict(
                    _data(), sequence_shape='tuple', elements=[]))
                sequence['elements'].append(value or _data())
            else:
                env[item['parameter']] = value or _data()
            if value is None:
                self.issue('decorator_argument_unproven', call_ref, expression)
        if node.args.vararg:
            env.setdefault(node.args.vararg.arg, dict(_data(), sequence_shape='tuple', elements=[]))
        if receiver:
            self.construction['parameter_bindings'] = [
                {'parameter': item['parameter'], 'argument': item['argument'],
                 'status': item['status'], 'evidence': self.evidence_at(call_ref, item['node']),
                 **({'value_provenance': env[item['parameter']]['value_provenance']}
                    if 'value_provenance' in env[item['parameter']] else {})}
                for item in records]
        return env

    ## Analyze one decorator instance constructed from a source class.
    ## 分析由源码类构造的装饰器实例。
    #
    #  @param self Decorator proof state.
    #  @param class_target Resolved class source pair.
    #  @param constructor Constructor call expression.
    #  @param module_ref Optional module reference for shared instances.
    #  @param assignment Optional module assignment creating the instance.
    #  @return Resolved __call__ method pair, or None when unavailable.
    def instance(self, class_target, constructor, module_ref=None, assignment=None):
        class_ref, cls = class_target
        previous_issues = len(self.boundaries)
        self.receiver_class = class_ref
        self.construction = {'class': asdict(class_ref),
            'expression': self.evidence_at(module_ref or self.ref, constructor),
            'lifetime': 'single_decoration' if module_ref is None and assignment is None
                        else 'shared_source_instance',
            'parameter_bindings': []}
        self.evidence.append(self.evidence_at(class_ref, cls))
        if assignment is not None:
            self.evidence.append(self.evidence_at(module_ref, assignment))
        hierarchy = self.analyzer._class_mro(class_ref.module, class_ref.qualname)
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            self.issue('decorator_effect_budget', class_ref, cls)
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

    ## Resolve a decorator expression to a source function or class instance.
    ## 将装饰器表达式解析为源码函数或类实例。
    #
    #  @param self Decorator proof state.
    #  @param expression Decorator AST expression.
    #  @return Target pair and captured values, or None with an empty capture map.
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

    ## Prove binding of one builtin-compatible method in a class hierarchy.
    ## 证明类继承层次中一个内建兼容方法的绑定。
    #
    #  @param self Decorator proof state.
    #  @param class_ref Source reference for the class.
    #  @param method Method name to validate.
    #  @return Method binding proof, or None when it is not closed.
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

    ## Model construction of a bounded documentation-cache instance.
    ## 对有界文档缓存实例的构造进行建模。
    #
    #  @param self Decorator proof state.
    #  @param selected Selected data class and source node.
    #  @param node Constructor expression.
    #  @param target Decorated function reference and node.
    #  @return Abstract data-instance value.
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

    ## Analyze a direct source-function call and its bounded effects.
    ## 分析直接源码函数调用及其有界效果。
    #
    #  @param self Decorator proof state collecting effects and boundaries.
    #  @param selected Resolved source function pair.
    #  @param node Call expression.
    #  @param arguments Abstract argument values.
    #  @param receiver Optional abstract receiver value.
    #  @param initializing Whether the call initializes a decorator receiver.
    #  @return Abstract return value, or None for unresolved argument binding.
    def source_call(self, selected, node, arguments, receiver=None, initializing=False):
        ref, definition = selected
        if not namespace_unmodified(self.analyzer, ref.module + '.' + ref.qualname):
            self.issue('decorator_helper_namespace_unproven', ref, node)
            return _data()
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

    ## Model a bounded documentation-cache lookup during string formatting.
    ## 建模字符串格式化期间对有界文档缓存的查找。
    #
    #  @param self Decorator proof state collecting mapping effects.
    #  @param node Formatting expression or lookup node.
    #  @param left Abstract format key value.
    #  @param mapping Abstract documentation-cache instance.
    #  @param target Source function reference and AST node.
    #  @return Abstract formatted value.
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
    ## 仅按已证明的内建标量结构类型拆分短路真值路径。
    #
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
    ## 在可达表达式路径中收窄直接局部值或文档读取。
    #
    #  @param node Operand expression being tested.
    #  @param value Truth-refined value, not a runtime object identity.
    #  @param env Path-local name bindings.
    #  @return None; updates path-local bindings or receiver metadata in place.
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
    ## 合并短路结果与对象状态，不会求值被跳过的调用。
    #
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

    ## Evaluate one supported expression and record effects or proof boundaries.
    ## 求值一个受支持的表达式并记录效果或证明边界。
    #
    #  @param self Decorator effect proof state.
    #  @param node Expression AST node.
    #  @param env Current abstract name bindings.
    #  @param target Source definition being analyzed.
    #  @param initializing Whether receiver initialization is in progress.
    #  @return Abstract data value for the expression.
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
            if value['kind'] == 'function' and node.attr == '__qualname__':
                # The fresh function starts with an exact string. Writes and
                # escaping calls retain their own effect boundaries; this is
                # not a general claim about arbitrary function metadata reads.
                self.extra_assumptions.append('fresh_source_function_metadata_binding')
                return dict(_data(), python_shape='str')
            if value['kind'] == 'receiver' and node.attr in self.state:
                return self.state[node.attr]
            self.issue('decorator_attribute_unproven', ref, node)
            return _data()
        if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and type(node.slice.value) is int):
            value = self.expression(node.value, env, target, initializing)
            if value.get('sequence_shape') in ('list', 'tuple'):
                if value.get('element_shape') == 'str':
                    return dict(_data(), python_shape='str')
                elements = value.get('elements', [])
                if -len(elements) <= node.slice.value < len(elements):
                    return elements[node.slice.value]
            self.issue('decorator_projection_unproven', ref, node)
            return _data()
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            value = self.expression(node.value, env, target, initializing)
            limits = [self.expression(item, env, target, initializing)
                      if item is not None else _data(None, True)
                      for item in (node.slice.lower, node.slice.upper, node.slice.step)]
            if (_data_shapes(value) == {'str'} and all(item.get('known')
                    and type(item.get('value')) in (int, type(None)) for item in limits)
                    and limits[2]['value'] != 0):
                bounds = [item['value'] for item in limits]
                self.effects.append({'operation': 'builtin_call', 'target': 'str.__getitem__',
                    'impact': 'data_only', 'element_path': [],
                    'protocol': 'finite_builtin_text_slice', 'receiver_shape': 'str',
                    'bounds': bounds, 'output_shape': 'str', 'completion': 'normal_return',
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions)})
                return (_data(value['value'][slice(*bounds)], True) if value.get('known')
                        else dict(_data(), python_shape='str'))
            self.issue('decorator_text_slice_unproven', ref, node)
            return _data()
        if isinstance(node, ast.IfExp):
            test = self.expression(node.test, env, target, initializing)
            cases = self.truth_cases(test, ref, node.test)
            values, states = [], []
            documentation, state = self.documentation, dict(self.state)
            for selected, refined in cases.items():
                self.documentation, self.state = documentation, dict(state)
                local = dict(env)
                self.refine_truth(node.test, refined, local)
                if len(cases) > 1:
                    self.conditions.append({'test': self.evidence_at(ref, node.test), 'branch': selected})
                try:
                    values.append(self.expression(node.body if selected else node.orelse,
                                                  local, target, initializing))
                    states.append((self.documentation, dict(self.state)))
                finally:
                    if len(cases) > 1:
                        self.conditions.pop()
            self.documentation = _join_values([doc for doc, _ in states])
            self.state = {name: _join_values([state.get(name, _data()) for _, state in states])
                          for name in set().union(*(state.keys() for _, state in states))}
            if any(value != values[0] for value in values[1:]) and any(
                    value['kind'] != 'data' for value in values):
                self.issue('decorator_object_escape', ref, node)
            return _join_values(values)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            children = (node.elts if not isinstance(node, ast.Dict) else node.keys + node.values)
            values = [self.expression(item, env, target, initializing) for item in children if item]
            if any(item['kind'] in ('function', 'receiver', 'closure') for item in values):
                self.issue('decorator_object_escape', ref, node)
            return (dict(_data(), sequence_shape=type(node).__name__.lower(), elements=values)
                    if isinstance(node, (ast.List, ast.Tuple))
                    and not any(isinstance(item, ast.Starred) for item in children) else _data())
        if isinstance(node, ast.BoolOp):
            return self.boolean(node, env, target, initializing)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare)):
            children = [item for item in ast.iter_child_nodes(node) if isinstance(item, ast.expr)]
            values = [self.expression(item, env, target, initializing) for item in children]
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and _data_shapes(values[0]):
                truth = _truth(values[0])
                return _data(not truth, True) if truth is not None else _shaped_data({'bool'})
            if (isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub))
                    and _data_shapes(values[0]) == {'int'}):
                operation = operator.pos if isinstance(node.op, ast.UAdd) else operator.neg
                return (_data(operation(values[0]['value']), True) if values[0].get('known')
                        else _shaped_data({'int'}))
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], (ast.Is, ast.IsNot))
                    and isinstance(node.comparators[0], ast.Constant)
                    and node.comparators[0].value is None and _data_shapes(values[0])
                    and 'NoneType' not in _data_shapes(values[0])):
                return _data(isinstance(node.ops[0], ast.IsNot), True)
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and all(value.get('known') and type(value['value']) in (
                        str, int, bool, float, type(None)) for value in values)):
                comparison = {ast.Eq: operator.eq, ast.NotEq: operator.ne,
                    ast.Lt: operator.lt, ast.LtE: operator.le,
                    ast.Gt: operator.gt, ast.GtE: operator.ge}.get(type(node.ops[0]))
                if comparison is not None:
                    try:
                        return _data(comparison(values[0]['value'], values[1]['value']), True)
                    except TypeError:
                        self.issue('decorator_data_protocol_unproven', ref, node)
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
            if (isinstance(node.func, ast.Name) and node.func.id == 'len'
                    and len(node.args) == 1 and not node.keywords
                    and _data_shapes(arguments[0]) == {'str'}
                    and self.analyzer._builtin_name_status(ref, definition, 'len') == 'confirmed_builtin'
                    and self.scalar_builtin_namespace(ref, node)):
                self.effects.append({'operation': 'builtin_call', 'target': 'len',
                    'impact': 'data_only', 'element_path': [],
                    'protocol': 'exact_builtin_string_length', 'input_shapes': [['str']],
                    'output_shape': 'int', 'completion': 'normal_return',
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions)})
                return (_data(len(arguments[0]['value']), True) if arguments[0].get('known')
                        else _shaped_data({'int'}))
            data_receiver = None
            if isinstance(node.func, ast.Attribute) and (isinstance(node.func.value, ast.Constant)
                    or isinstance(node.func.value, ast.Name)
                    and node.func.value.id in env or isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name) and node.func.value.value.id in env):
                data_receiver = self.expression(node.func.value, env, target, initializing)
            text_result = (text_call(self, node, data_receiver, arguments, ref)
                           if isinstance(node.func, ast.Attribute) else None)
            if text_result is not None:
                return text_result
            if (data_receiver and data_receiver.get('python_shape') == 'str'
                    and node.func.attr == 'join' and len(node.args) == 1 and not node.keywords
                    and arguments[0].get('sequence_shape') in ('list', 'tuple')
                    and 'elements' in arguments[0]
                    and all(_data_shapes(value) == {'str'} for value in arguments[0]['elements'])):
                self.effects.append({'operation': 'builtin_call', 'target': 'str.join',
                    'impact': 'data_only', 'element_path': [], 'receiver_shape': 'str',
                    'sequence_shape': arguments[0]['sequence_shape'],
                    'element_shapes': [['str'] for _ in arguments[0]['elements']],
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
                return dict(_data(), python_shape='str')
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
                local_import = env.get(first, {})
                if local_import.get('category') == 'source_import':
                    qualified = local_import['qualified'] + (dot + rest if dot else '')
                    selected = self.analyzer._resolve_import_binding(qualified)
                    class_target = self.analyzer._class_symbol(qualified)
                    if class_target:
                        return self.data_instance(class_target, node, target)
                elif first not in self.analyzer._scope_facts(definition).bound:
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
            # Finite standard-library protocols, with exact builtin string input.
            # They do not grant arbitrary imported helpers an effect-free model.
            if (qualified in ('inspect.cleandoc', 'textwrap.dedent') and imported
                    and first not in self.analyzer._scope_facts(definition).bound
                    and qualified.partition('.')[0] not in self.analyzer.module_bodies
                    and self.analyzer._stable_import_name(ref.module + '.' + first)
                    and all(self.analyzer._stable_import_name(module + '.' + alias)
                        for module, imports in self.analyzer.imports.items()
                        for alias, canonical in imports.items()
                        if canonical in (qualified, qualified.partition('.')[0]))
                    and len(arguments) == 1 and not node.keywords
                    and not any(isinstance(arg, ast.Starred) for arg in node.args)
                    and _data_shapes(arguments[0]) == {'str'}):
                self.effects.append({'operation': 'builtin_call', 'target': qualified,
                    'impact': 'data_only', 'element_path': [],
                    'protocol': 'stdlib_text_normalization',
                    'input_shapes': [['str']], 'output_shape': 'str',
                    'completion': 'normal_return', 'function': asdict(ref),
                    'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions)})
                self.extra_assumptions.append('standard_library_text_protocols_hold')
                return dict(_data(), python_shape='str')
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

    ## Apply a supported assignment to local or receiver abstract state.
    ## 将受支持的赋值应用于局部或接收者抽象状态。
    #
    #  @param self Decorator effect proof state.
    #  @param node Assignment AST node.
    #  @param value Abstract value being assigned.
    #  @param env Mutable path-local name bindings.
    #  @param target Source definition being analyzed.
    #  @param initializing Whether receiver initialization is in progress.
    #  @return None; updates the abstract environment and effects in place.
    def assign(self, node, value, env, target, initializing):
        ref, _ = target
        if isinstance(node, ast.Name):
            env[node.id] = value
            return
        if isinstance(node, ast.Attribute):
            receiver = self.expression(node.value, env, target, initializing)
            if receiver['kind'] == 'function':
                module_shapes = _data_shapes(value)
                module_metadata = (node.attr == '__module__' and bool(module_shapes)
                                   and module_shapes <= {'str', 'NoneType'})
                impact = ('documentation' if node.attr == '__doc__' else
                          'module_metadata' if module_metadata else
                          'execution_binding' if node.attr in ('__code__', '__defaults__', '__kwdefaults__') else
                          'signature_metadata' if node.attr in ('__signature__', '__annotations__', '__wrapped__') else
                          'unmodeled_attribute')
                self.effects.append({'operation': 'attribute_write', 'target': 'input_function',
                    'element_path': [node.attr], 'impact': impact,
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                    'conditions': copy.deepcopy(self.conditions)})
                if impact == 'documentation':
                    self.effects[-1].update(value_shapes=sorted(module_shapes),
                        protocol='builtin_function_documentation_attribute',
                        execution_fields_unchanged=True, runtime_write_confirmed=False)
                if module_metadata:
                    self.effects[-1].update(protocol='builtin_function_module_attribute',
                        value_shapes=sorted(module_shapes), execution_fields_unchanged=True,
                        runtime_write_confirmed=False)
                    self.extra_assumptions.append('builtin_function_module_attribute')
                if impact == 'execution_binding':
                    self.issue('decorator_execution_binding_write', ref, node)
                elif impact not in ('documentation', 'module_metadata'):
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
                previous = self.state.get(node.attr, _data())
                if (self.construction and self.construction['lifetime'] == 'single_decoration'
                        and not node.attr.startswith('__')
                        and _data_shapes(previous) and _data_shapes(value)):
                    self.state[node.attr] = value
                    self.effects.append({'operation': 'attribute_write', 'target': 'decorator_instance',
                        'impact': 'data_only', 'element_path': [node.attr],
                        'before_shapes': sorted(_data_shapes(previous)),
                        'after_shapes': sorted(_data_shapes(value)),
                        'function': asdict(ref), 'evidence': self.evidence_at(ref, node),
                        'conditions': copy.deepcopy(self.conditions), 'completion': 'normal_return'})
                    if self.conditions:
                        self.issue('decorator_conditional_instance_state_write', ref, node)
                    return
                self.issue('decorator_instance_state_write', ref, node)
                return
        self.issue('decorator_write_unproven', ref, node)
        if value['kind'] in ('function', 'closure', 'receiver'):
            self.issue('decorator_object_escape', ref, node)

    ## Interpret a statement sequence while preserving bounded control paths.
    ## 解释语句序列并保留有界控制流路径。
    #
    #  @param self Decorator effect proof state.
    #  @param body Ordered source statements.
    #  @param env Mutable path-local name bindings.
    #  @param target Source definition being analyzed.
    #  @param initializing Whether receiver initialization is in progress.
    #  @return Return abstract values and normal-fallthrough status.
    def statements(self, body, env, target, initializing):
        ref, definition = target
        returns = []
        for statement in body:
            self.evidence.append(self.evidence_at(ref, statement))
            if isinstance(statement, ast.Return):
                returns.append(self.expression(statement.value, env, target, initializing))
                return returns, False
            if isinstance(statement, ast.Raise):
                if builtin_raise(self, statement, env, target, initializing, _data_shapes):
                    return returns, False
                return returns + [_data()], True
            if isinstance(statement, ast.Pass):
                continue
            if isinstance(statement, ast.ImportFrom):
                fact = decorator_cached_import(self, ref, statement)
                if fact is None:
                    self.issue('decorator_cached_import_unproven', ref, statement)
                    return returns + [_data()], True
                self.dependency_paths.update(fact['source_hashes'])
                self.extra_assumptions.extend(fact['assumptions'])
                self.effects.append({'operation': 'cached_import', 'target': 'source_module',
                    'impact': 'conditional_import_binding', 'element_path': [], 'binding': fact,
                    'function': asdict(ref), 'evidence': self.evidence_at(ref, statement),
                    'conditions': copy.deepcopy(self.conditions),
                    'completion': 'normal_cached_import_return'})
                for item in fact['bindings']:
                    env[item['name']] = dict(_data(), category='source_import',
                        qualified=item['module'] + '.' + item['attribute'])
                continue
            if isinstance(statement, ast.Try):
                translated = translate_exceptions(self, statement, env, target, initializing, _data_shapes)
                if translated is None:
                    self.issue('decorator_statement_unsupported', ref, statement)
                    return returns + [_data()], True
                values, falls = translated
                returns.extend(values)
                if not falls:
                    return returns, False
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
                initial_state = dict(self.state)
                continuing_docs = []
                continuing_states = []
                for branch, selected in branches:
                    local = dict(env)
                    self.documentation = initial_doc
                    self.state = dict(initial_state)
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
                        continuing_states.append(dict(self.state))
                self.documentation = (continuing_docs[0] if continuing_docs and all(
                    value == continuing_docs[0] for value in continuing_docs) else initial_doc)
                self.state = {name: _join_values([state.get(name, _data()) for state in continuing_states])
                              for name in set().union(*(state.keys() for state in continuing_states))}
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

    ## Analyze one source function body with recursion and path limits.
    ## 在递归与路径预算约束下分析一个源码函数体。
    #
    #  @param self Decorator proof state tracking active functions.
    #  @param target Selected source function pair.
    #  @param env Parameter bindings at function entry.
    #  @param initializing Whether the function constructs receiver state.
    #  @return Return abstract values and normal-fallthrough status.
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

    ## Build the final source-bound effect fact for a decorator expression.
    ## 为装饰器表达式构建最终源码绑定效果事实。
    #
    #  @param self Decorator proof state and collected evidence.
    #  @param expression Decorator expression at the source site.
    #  @param multiple Whether more than one decoration is being summarized.
    #  @return Structured decorator effect fact.
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
                    item['file_path'] for item in evidence} | self.dependency_paths)
                    if path in self.analyzer.hashes},
                'assumptions': ['source_snapshot_bindings_hold', 'builtin_function_attribute_semantics',
                                'no_external_monkeypatch_or_import_hook'] + _unique(self.extra_assumptions)}
