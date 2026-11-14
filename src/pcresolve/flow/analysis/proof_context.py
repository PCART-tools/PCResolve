## @package pcresolve.flow.analysis.proof_context
#  Bounded source proof preparation and semantic queries.
#  有界源码证明准备和语义查询。

import ast

import copy

from dataclasses import asdict, replace

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches

from pcresolve.flow.transfer.summary import _Summary

from pcresolve.facts.program_facts import SourceSpan, FunctionSignature, bind_ast_call

from pcresolve.facts.scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)

from pcresolve.facts.effect_facts import (container_method_effect, contains_yield,
                           function_effects, FunctionEffect, finite_key_delete_sites)

from pcresolve.facts.import_facts import import_facts, resolve_relative_module

from pcresolve.flow.proofs.callables.decorators._decorator_effects import _DecoratorEffects

from pcresolve.flow.proofs.callables._constructor_entry import _definition_issues as constructor_definition_issues

from pcresolve.flow.proofs.classes._class_definition import _source_callable_object_identity

from pcresolve.flow.proofs.protocols.class_attribute_effects import class_attribute_writes, _ClassEffectLimit

from pcresolve.flow.proofs.classes._class_decoration import constructor_decorations, member_preservation

from pcresolve.flow.proofs.classes._class_creation import creation_effects

from pcresolve.flow.proofs.callables.decorators._fresh_decoration import fresh_decoration



_CLASS_BINDING_NODE_LIMIT = 1000000

_DECORATOR_EFFECT_NODE_LIMIT = 2000

_CONTEXT_PROTOCOL_NODE_LIMIT = 2000



## Find root names of attribute or subscript writes in the current scope.
## 查找当前作用域内属性或下标写入的根名称。
#
#  @param node Source AST node.
#  @return Set of root names, excluding nested definitions.
def _attribute_write_roots(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                         ast.Lambda)):
        return set()
    roots = set()
    if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
            node.ctx, (ast.Store, ast.Del)):
        root = node.value
        while isinstance(root, (ast.Attribute, ast.Subscript)):
            root = root.value
        if isinstance(root, ast.Name):
            roots.add(root.id)
    for child in ast.iter_child_nodes(node):
        roots.update(_attribute_write_roots(child))
    return roots



## Deduplicate values while retaining their first occurrence order.
## 去重并保留值首次出现的顺序。
#
#  @param values Iterable of comparable values.
#  @return List of unique values in input order.
def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

## Prepare bounded proof evidence used by value-flow transfer.
## 准备数据流传播使用的有界证明证据。
class ProofContextMixin:

    ## Resolve a single stable source decorator definition.
    ## 解析单个稳定的源码装饰器定义。
    #
    #  @param target Decorated source identity and AST pair.
    #  @param kind Definition category to resolve.
    #  @return Decorator definition or None when ambiguous or unsupported.
    def _decorator_definition(self, target, kind='function'):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or not isinstance(
                decorators[0], (ast.Name, ast.Attribute)):
            return None
        name = ast.unparse(decorators[0])
        first, dot, rest = name.partition('.')
        owner = ref.qualname.rpartition('.')[0]
        if owner:
            ancestors = owner.split('.')
            if any(self._definition_index.find(ref.module, '.'.join(
                    ancestors[:length])) for length in range(1, len(ancestors))):
                return None
            enclosing = self._definition_index.find(ref.module, owner, kind='class')
            if len(enclosing) != 1:
                return None
            preceding = []
            for statement in enclosing[0][1].body:
                if statement is node:
                    break
                preceding.append(statement)
            if first in statement_scope_facts(preceding).bound:
                return None
        imported = self.imports.get(ref.module, {}).get(first)
        qualified = imported + (dot + rest if dot else '') if imported else ref.module + '.' + name
        if not self._stable_import_name(ref.module + '.' + first):
            return None
        decorator = self._definition_index.resolve_qualified([qualified], self.imports,
            kind=kind, qualified_guard=self._stable_import_name)
        if decorator is None or getattr(decorator[1], 'decorator_list', []):
            return None
        return decorator

    ## Prove that every normal decorator return preserves its input identity.
    ## 证明装饰器每条正常返回路径均保留输入身份。
    #
    #  @param target Decorated source definition.
    #  @return Source proof facts, or None outside the bounded supported shape.
    def _identity_decorator(self, target):
        decorator = self._decorator_definition(target)
        if decorator is None or not isinstance(decorator[1], ast.FunctionDef):
            return None
        ref, node = decorator
        arguments = node.args
        positional = arguments.posonlyargs + arguments.args
        if (len(positional) != 1 or arguments.vararg or arguments.kwonlyargs
                or arguments.kwarg or arguments.defaults):
            return None
        parameter = positional[0].arg
        body = node.body
        if (not body or not isinstance(body[-1], ast.Return)
                or parameter in statement_scope_facts(body).bound):
            return None
        nodes = list(ast.walk(node))
        if len(nodes) > 256:
            return None
        allowed = (ast.If, ast.Assign, ast.AnnAssign, ast.AugAssign,
                   ast.Expr, ast.Return, ast.Raise, ast.Pass)
        returns = []
        for child in nodes[1:]:
            if (isinstance(child, ast.stmt) and not isinstance(child, allowed)
                    or isinstance(child, (ast.Lambda, ast.Yield, ast.YieldFrom,
                                          ast.Await, ast.ListComp, ast.SetComp,
                                          ast.DictComp, ast.GeneratorExp))):
                return None
            if isinstance(child, ast.Return):
                if not isinstance(child.value, ast.Name) or child.value.id != parameter:
                    return None
                returns.append(child)
            if (isinstance(child, (ast.Assign, ast.AnnAssign))
                    and isinstance(child.value, ast.Name)
                    and child.value.id == parameter):
                return None
            if isinstance(child, (ast.Attribute, ast.Subscript)) and isinstance(
                    child.ctx, (ast.Store, ast.Del)):
                root = child.value
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    root = root.value
                if isinstance(root, ast.Name) and root.id == parameter:
                    return None
        return {'decorator': ref, 'definition': node,
                'parameter': parameter, 'returns': returns,
                'effects_unmodeled': any(isinstance(child, ast.Call) or
                    isinstance(child, (ast.Attribute, ast.Subscript)) and
                    isinstance(child.ctx, ast.Store) for child in nodes)}

    ## Describe one bounded decoration on the exact original source definition.
    ## 描述精确原始源码定义上的有界装饰效果。
    #
    #  @param target FunctionRef and source definition.
    #  @return JSON-safe function-level effect facts, separate from identity proof.
    def _decoration_facts(self, target):
        ref, node = target
        original = [item for item in self._definition_index.find(ref.module, ref.qualname) if item[0] == ref]
        if len(original) == 1:
            node = original[0][1]
            target = ref, node
        if ref not in self._decoration_fact_cache:
            decorators = getattr(node, 'decorator_list', [])
            if not decorators:
                self._decoration_fact_cache[ref] = []
                return []
            summary = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
            self._decoration_fact_cache[ref] = [
                _DecoratorEffects(self, target, summary.evidence_at, _DECORATOR_EFFECT_NODE_LIMIT).fact(
                    expression, multiple=len(decorators) != 1)
                for expression in decorators]
            if (len(decorators) == 1 and isinstance(decorators[0], ast.Attribute)
                    and isinstance(decorators[0].value, ast.Name)):
                owner_name, _, method_name = ref.qualname.rpartition('.')
                owners = (self._definition_index.find(ref.module, owner_name, kind='class')
                          if owner_name else [(ref, node)])
                if len(owners) == 1 and self._stable_import_name(ref.module + '.' + ref.qualname):
                    assumptions, paths = set(), {ref.file_path}
                    stable = True
                    if owner_name:
                        writes, truncated = self._class_binding_writes()
                        stable = not truncated and not any(
                            owner == owners[0][0] and name in (method_name, '*', '__class__', '__bases__')
                            for owner, name, _, _, _ in writes)
                    if (stable and _source_callable_object_identity(
                            self, owners[0][0], node, paths, assumptions)
                            == 'source_callable_object_identity_decorator'
                            and all(path in self.hashes for path in paths)):
                        module = self.imports.get(ref.module, {}).get(decorators[0].value.id)
                        decorator_files = {path for path, _ in self.module_bodies.get(module, [])}
                        paths.update(decorator_files)
                        if not decorator_files or any(path not in self.hashes for path in paths):
                            return copy.deepcopy(self._decoration_fact_cache[ref])
                        assumptions.add('module_initialization_completed_before_query')
                        self._decoration_fact_cache[ref][0]['callable_object_identity_proof'] = {
                            'kind': 'source_callable_object_identity', 'status': 'source_bound',
                            'basis': 'source_snapshot', 'completion': 'normal_return',
                            'runtime_target_confirmed': False, 'function': asdict(ref),
                            'expression': summary.evidence_at(ref, decorators[0]),
                            'returned_object': 'original_function',
                            'mutated_function_attributes': ['__doc__'],
                            'decorator_source_files': sorted(decorator_files),
                            'source_hashes': {path: self.hashes[path] for path in sorted(paths)},
                            'assumptions': sorted(assumptions)}
        return copy.deepcopy(self._decoration_fact_cache[ref])

    ## Refine an identity-preserving decoration using a fresh-function proof.
    ## 使用新建函数证明细化保留身份的装饰事实。
    #
    #  @param target Function identity and source definition.
    #  @return Copied list of refined facts, possibly empty.
    def _fresh_decoration_facts(self, target):
        ref, node = target
        if ref not in self._fresh_decoration_fact_cache:
            self._fresh_decoration_fact_cache[ref] = []
            ordinary = self._decoration_facts(target)
            if (len(ordinary) == 1 and ordinary[0]['identity_status'] == 'preserved'
                    and ordinary[0]['body_binding_status'] == 'unknown'):
                summary = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
                fact = fresh_decoration(self, target, summary.evidence_at, _DECORATOR_EFFECT_NODE_LIMIT)
                if fact is not None:
                    self._fresh_decoration_fact_cache[ref] = [fact]
        return copy.deepcopy(self._fresh_decoration_fact_cache[ref])

    ## Select ordinary or refined decoration facts for binding analysis.
    ## 为绑定分析选择普通或细化后的装饰事实。
    #
    #  @param target Function identity and source definition.
    #  @return Decoration fact list.
    def _binding_decoration_facts(self, target):
        facts = self._decoration_facts(target)
        if len(facts) == 1 and facts[0]['body_binding_status'] != 'preserved':
            return self._fresh_decoration_facts(target) or facts
        return facts

    ## Resolve a simple noncapturing wrapper returned by a source decorator.
    ## 解析源码装饰器返回的简单无捕获包装函数。
    #
    #  @param target Decorated source identity and AST pair.
    #  @return Wrapper definition or None when the shape is unsupported.
    def _decorated_target(self, target):
        decorator = self._decorator_definition(target)
        if decorator is None or not isinstance(decorator[1], ast.FunctionDef):
            return None
        arguments = decorator[1].args
        positional = arguments.posonlyargs + arguments.args
        if (len(positional) != 1 or arguments.vararg or arguments.kwonlyargs
                or arguments.kwarg or arguments.defaults):
            return None
        body = [statement for statement in decorator[1].body
                if not (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))]
        if (len(body) != 2 or not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef))
                or body[0].decorator_list or not isinstance(body[1], ast.Return)
                or not isinstance(body[1].value, ast.Name)
                or body[1].value.id != body[0].name):
            return None
        qualname = decorator[0].qualname + '.' + body[0].name
        matches = self._definition_index.find(decorator[0].module, qualname)
        if len(matches) != 1 or self._captures(*matches[0]):
            return None
        return matches[0]

    ## Resolve a callable name using the caller's lexical and import context.
    ## 使用调用方的词法和导入上下文解析可调用名称。
    #
    #  @param caller Caller function identity.
    #  @param name Syntactic callable name.
    #  @return Unique source definition or None.
    def _resolve(self, caller, name):
        return self._definition_index.resolve_name(
            caller.module, caller.qualname, name, self.imports)

    ## Check a qualified source binding for a unique stable declaration chain.
    ## 检查限定源码绑定是否具有唯一稳定的声明链。
    #
    #  @param qualified Qualified name to inspect.
    #  @return True only when every component has one supported binding.
    def _stable_import_name(self, qualified):
        module, _, name = qualified.rpartition('.')
        while module and module not in self.import_binding_facts:
            module, _, prefix = module.rpartition('.')
            name = prefix + '.' + name
        sources = self.import_binding_facts.get(module, [])
        if len(sources) != 1:
            return False
        bindings_by_name = sources[0]
        parts = name.split('.')
        for index, part in enumerate(parts):
            bindings = bindings_by_name.get(part, [])
            if len(bindings) != 1 or not isinstance(bindings[0], (
                    ast.Import, ast.ImportFrom, ast.FunctionDef,
                    ast.AsyncFunctionDef, ast.ClassDef)):
                return False
            if index == len(parts) - 1:
                return True
            if not isinstance(bindings[0], ast.ClassDef):
                return False
            bindings_by_name = {}
            for statement in bindings[0].body:
                for member in (statement_scope_facts([statement]).bound
                               | _attribute_write_roots(statement)):
                    bindings_by_name.setdefault(member, []).append(statement)
        return False

    ## Resolve a qualified source target through stable import bindings.
    ## 通过稳定导入绑定解析限定源码目标。
    #
    #  @param qualified Qualified target name.
    #  @return Unique source definition or None.
    def _resolve_import_binding(self, qualified):
        return self._definition_index.resolve_qualified(
            [qualified], self.imports, qualified_guard=self._stable_import_name)

    ## Find global declarations that can rebind a module-level definition.
    ## 查找可能重新绑定模块级定义的 global 声明。
    #
    #  @param ref Source definition identity.
    #  @return Matching declaration nodes.
    def _module_global_declarations(self, ref):
        definitions = self.import_binding_facts.get(ref.module, [])
        name = ref.qualname.partition('.')[0]
        return ([statement for statement in definitions[0].get(name, [])
                 if isinstance(statement, ast.Global)] if len(definitions) == 1 else [])

    ## Collect source evidence for possible module-global rebindings.
    ## 收集模块全局名称可能被重新绑定的源码证据。
    #
    #  @return Ordered rebinding fact records.
    def _module_global_rebindings(self):
        result = []
        for module, bodies in sorted(self.module_bodies.items()):
            for (path, _), bindings in zip(bodies, self.import_binding_facts.get(module, [])):
                for name, statements in sorted(bindings.items()):
                    if self._analysis_budget is not None:
                        self._analysis_budget.checkpoint()
                    declarations = [statement for statement in statements if isinstance(statement, ast.Global)]
                    if declarations:
                        result.append({'kind': 'module_global_rebinding', 'status': 'may_write',
                            'basis': 'source_snapshot', 'module': module, 'name': name,
                            'declarations': [{'file_path': path, 'lineno': statement.lineno,
                                'col_offset': statement.col_offset, 'end_lineno': statement.end_lineno,
                                'end_col_offset': statement.end_col_offset} for statement in declarations],
                            'source_hash': self.hashes[path]})
        return result

    ## Resolve a class name in a caller's lexical and import context.
    ## 在调用方词法和导入上下文中解析类名。
    #
    #  @param caller Caller function identity.
    #  @param name Syntactic class name.
    #  @return Unique source class or None.
    def _resolve_class(self, caller, name):
        return self._definition_index.resolve_name(
            caller.module, caller.qualname, name, self.imports, kind='class')

    ## Resolve a class through stable imports and bounded assignment aliases.
    ## 通过稳定导入和有界赋值别名解析类。
    #
    #  @param qualified Qualified class name.
    #  @param seen Previously visited names.
    #  @return Unique source class or None for cycles or uncertainty.
    def _class_symbol(self, qualified, seen=()):
        if qualified in seen or len(seen) >= 20:
            return None
        target = self._definition_index.resolve_qualified(
            [qualified], self.imports, kind='class',
            qualified_guard=self._stable_import_name)
        if target is not None:
            return target
        module, _, name = qualified.rpartition('.')
        bodies = self.module_bodies.get(module, [])
        bindings = self.import_binding_facts.get(module, [])
        if len(bodies) != 1 or len(bindings) != 1:
            return None
        statements = bindings[0].get(name, [])
        if len(statements) != 1 or statements[0] not in bodies[0][1]:
            return None
        statement = statements[0]
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)) or not isinstance(
                statement.value, (ast.Name, ast.Attribute)):
            return None
        expression = ast.unparse(statement.value)
        first, dot, rest = expression.partition('.')
        imported = self.imports.get(module, {}).get(first)
        if imported and not self._stable_import_name(module + '.' + first):
            return None
        next_name = (imported + (dot + rest if dot else '') if imported
                     else module + '.' + expression)
        return self._class_symbol(next_name, seen + (qualified,))

    ## Check whether source class construction follows the modeled ordinary path.
    ## 检查源码类构造是否遵循已建模的普通路径。
    #
    #  @param class_ref Source class identity.
    #  @param allow_bounded_decorations Permit independently proved decorations.
    #  @return True only when the ordinary construction premises hold.
    def _ordinary_construction(self, class_ref, allow_bounded_decorations=False):
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if hierarchy is None:
            return False
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in ('__new__', '__class__', '__bases__', '*')
                and any(written == owner for owner, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return False
        # Ancestor decoration has already happened when a new subclass hook
        # observes its inherited namespace. Establish that completed prefix
        # before asking for the current class's creation effects.
        if allow_bounded_decorations and any(
                constructor_decorations(self, parent) is None
                for parent in reversed(hierarchy[1:])):
            return False
        if creation_effects(self, hierarchy[0]) is None:
            return False
        return all((constructor_decorations(self, (owner, cls)) is not None
                    if allow_bounded_decorations else not cls.decorator_list)
            and not cls.keywords and not any(
            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name == '__new__' or
            '__new__' in statement_scope_facts([member]).bound
            for member in cls.body) for owner, cls in hierarchy)

    ## Check source premises for explicit object.__new__ allocation.
    ## 检查显式 object.__new__ 分配的源码前提。
    #
    #  @param class_ref Source class identity.
    #  @return True only when the modeled ordinary layout is established.
    def _explicit_object_allocation(self, class_ref):
        # Explicit object.__new__ bypasses the selected class's __new__ and
        # __init__. Its source class/MRO must still identify an ordinary object
        # layout, and class-definition evaluation must preserve that identity.
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if not hierarchy or len(hierarchy) > 64:
            return False
        if any(cls.keywords or cls.decorator_list or self.definition_conditions.get(owner)
                or owner != class_ref and '__init_subclass__' in statement_scope_facts(cls.body).bound
                for owner, cls in hierarchy):
            return False
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in ('__class__', '__bases__', '*')
                and any(written == owner for owner, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return False
        try:
            return not constructor_definition_issues(self, hierarchy)
        except _ClassEffectLimit:
            return False

    ## Summarize enter returns symbolically, never caching a caller object identity.
    ## 符号化概括 enter 返回值，不缓存调用方对象身份。
    #
    #  @param definition Exact source protocol method.
    #  @param receiver_class Source instance class used for the type lookup.
    #  @return Bounded normal-return paths, completion and unresolved proof issues.
    def _context_enter_returns(self, definition, receiver_class):
        ref, node = definition
        key = ref, receiver_class
        if key in self._context_enter_stack:
            return {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_recursion']}
        if key in self._context_enter_cache:
            return copy.deepcopy(self._context_enter_cache[key])
        steps = 0
        for _ in ast.walk(node):
            steps += 1
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint()
            if steps > _CONTEXT_PROTOCOL_NODE_LIMIT:
                break
        if (len(self._context_enter_stack) >= 8 or self._fact_functions <= 0
                or steps > min(self._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT)):
            return {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_budget']}
        self._fact_functions -= 1
        self._fact_calls -= steps
        positional = node.args.posonlyargs + node.args.args
        incoming = {positional[0].arg: [{'instance_type': asdict(receiver_class)}]} if positional else {}
        scratch = FlowAnalysis(ref, {})
        self._context_enter_stack.append(key)
        try:
            summary = _Summary(self, scratch, ref, node, self._fact_calls, incoming=incoming)
            summary.run()
            supported_constructors = set()
            issues = []
            for call in summary.calls:
                constructor = (call.result_sources and all(value.get('instance_type')
                    for value in call.result_sources) and call.target_status in (
                        'constructor', 'constructor_unavailable'))
                if constructor and call.target is not None:
                    target = self._definition_index.find(call.target.module, call.target.qualname)
                    constructor = len(target) == 1 and function_effects(target[0][1]) == ()
                elif constructor:
                    constructor = all(not any('__init__' in statement_scope_facts([member]).bound
                        for member in cls.body) for value in call.result_sources
                        for _, cls in self._class_mro(value['instance_type']['module'],
                            value['instance_type']['qualname']) or ())
                if constructor:
                    supported_constructors.add(call.id)
                if not constructor:
                    issues.append('context_enter_call_unmodeled')
            issues.extend(item['reason'] for item in scratch.boundaries if not (
                item.get('call_id') in supported_constructors
                and item['reason'] == 'module_callable_instance_unresolved'
                and item.get('cause') == 'constructor_unavailable'))
            if any(isinstance(statement, (ast.If, ast.Try, ast.For, ast.While))
                   for statement in node.body):
                issues.append('context_enter_control_effects_unmodeled')
            effects_known = not issues and (function_effects(node) == ()
                or bool(supported_constructors) and len(supported_constructors) == len(summary.calls))
            completion = ('no_normal_return' if summary.exit_kinds
                and summary.exit_kinds <= {'raise'} else 'normal_possible')
            if summary.incomplete_return:
                issues.append('context_enter_return_unresolved')
            fact = {'paths': copy.deepcopy(summary.normal_returns), 'completion': completion,
                    'parameter': positional[0].arg if positional else None, 'issues': _unique(issues),
                    'effects_status': 'source_modeled' if effects_known else 'unmodeled',
                    'exceptions': _unique(exception for kind, _, _, exception in summary.outcomes
                                          if kind == 'raise')}
            self._context_enter_cache[key] = fact
            return copy.deepcopy(fact)
        finally:
            self._context_enter_stack.pop()

    ## Prove a single-inheritance source chain ending at the unshadowed builtin dict.
    ## 证明单继承源码链最终指向未被遮蔽的内置 dict。
    #
    #  @param class_ref Source class identity; no whole-object builtin shape is inferred.
    #  @param seen Class identities already visited on this path.
    #  @return Source hierarchy, or None for incomplete or customized construction.
    def _dict_subclass_hierarchy(self, class_ref, seen=()):
        identity = (class_ref.module, class_ref.qualname)
        if identity in seen or len(seen) >= 20:
            return None
        matches = self._definition_index.find(*identity, kind='class')
        if len(matches) != 1 or self._class_symbol('.'.join(identity)) != matches[0]:
            return None
        ref, cls = matches[0]
        if cls.decorator_list or cls.keywords or len(cls.bases) != 1:
            return None
        base = cls.bases[0]
        if isinstance(base, ast.Name) and base.id == 'dict':
            if (base.id in self.imports.get(ref.module, {})
                    or base.id in self.module_bindings.get(ref.module, set())
                    or self._definition_index.find(ref.module, base.id)
                    or self._definition_index.find(ref.module, base.id, kind='class')):
                return None
            outer = ref.qualname.rpartition('.')[0]
            scopes = self._definition_index.find(ref.module, outer)
            if any(base.id in self._scope_facts(node).bound for _, node in scopes):
                return None
            return (matches[0],)
        if not isinstance(base, (ast.Name, ast.Attribute)):
            return None
        first = ast.unparse(base).partition('.')[0]
        if not self._stable_import_name(ref.module + '.' + first):
            return None
        inherited = self._resolve_class(ref, ast.unparse(base))
        if inherited is None:
            return None
        hierarchy = self._dict_subclass_hierarchy(inherited[0], seen + (identity,))
        return (matches[0],) + hierarchy if hierarchy else None

    ## Describe a builtin method's source binding without treating a subclass as dict.
    ## 描述内置方法的源码绑定，不将子类直接视为 dict。
    #
    #  @param class_ref Source receiver class.
    #  @param method Exact attribute being looked up.
    #  @return Proof, an explicit scan-budget issue, or None for uncertain lookup/writes.
    def _dict_method_binding(self, class_ref, method):
        if method not in ('setdefault', '__getitem__'):
            return None
        hierarchy = self._dict_subclass_hierarchy(class_ref)
        if hierarchy is None:
            return None
        blocked = {method, '__getattribute__', '__getattr__', '__setattr__',
                   '__delattr__', '__new__', '__init_subclass__'}
        remaining = _CLASS_BINDING_NODE_LIMIT
        for ref, cls in hierarchy:
            if any(blocked.intersection(statement_scope_facts([member]).bound)
                   for member in cls.body):
                return None
            for node in ast.walk(cls):
                remaining -= 1
                if remaining < 0:
                    return {'status': 'unconfirmed', 'reason': 'class_binding_budget'}
                if isinstance(node, ast.Attribute) and (node.attr == '__dict__' or
                        isinstance(node.ctx, (ast.Store, ast.Del)) and node.attr in blocked | {'__class__'}):
                    return None
                if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                    if name in ('setattr', 'delattr', 'vars', 'exec', 'eval', '__setattr__', '__delattr__'):
                        return None
        writes, truncated = self._class_binding_writes(include_escapes=True)
        identities = {(ref.module, ref.qualname) for ref, _ in hierarchy}
        if truncated:
            return {'status': 'unconfirmed', 'reason': 'class_binding_budget'}
        if any((ref.module, ref.qualname) in identities for ref, _, _, _, _ in writes):
            return None
        return {'kind': 'builtin_method_binding', 'builtin': 'dict.' + method,
                'receiver_class': asdict(class_ref), 'status': 'source_bound',
                'basis': 'source_snapshot', 'runtime_target_confirmed': False,
                'assumptions': ['source_snapshot_bindings_hold',
                                'source_class_receiver_without_instance_shadowing',
                                'no_external_monkeypatch_or_import_hook'],
                'hierarchy': hierarchy}

    ## Summarize supported function effects under recursion and work limits.
    ## 在递归和工作量限制下概括受支持的函数效果。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Pair of complete effects or None, and an unresolved reason.
    def _function_effects(self, definition):
        ref, node = definition
        key = (ref, repr(getattr(node, '_flow_conditions', [])))
        if key in self._function_effect_cache:
            return self._function_effect_cache[key]
        if key in self._function_effect_stack:
            return None, 'recursive_helper_effects'
        if len(self._function_effect_stack) >= 16:
            return None, 'mapping_effect_budget'

        # Cache complete outcomes and explicit cutoff reasons for this query.
        # 缓存本次查询中的完整结果及明确的截断原因。
        steps = len(getattr(node, 'body', ())) if isinstance(node, ast.FunctionDef) else 1
        if getattr(node, '_flow_branch_budget', None) is not None:
            result = None, 'literal_branch_budget'
        elif self._effect_fact_functions <= 0 or steps > self._effect_fact_steps:
            result = None, 'mapping_effect_budget'
        else:
            self._effect_fact_functions -= 1
            self._effect_fact_steps -= steps
            self._function_effect_stack.add(key)
            try:
                effects = function_effects(node, lambda statement, aliases:
                    self._nested_mapping_effects(definition, statement, aliases))
                result = effects, self._nested_effect_failures.get(ref, 'unsupported_helper_body')
            finally:
                self._function_effect_stack.remove(key)
        self._function_effect_cache[key] = result
        return result

    ## Compose complete same-module mapping effects from a direct helper call.
    ## 组合直接调用同模块辅助函数所产生的完整映射效果。
    #
    #  @param definition Calling source definition.
    #  @param statement Expression call whose result is unused.
    #  @param aliases Calling ordinary-name bindings, with parameter identity.
    #  @return Remapped complete effects or None for an unproved call.
    def _nested_mapping_effects(self, definition, statement, aliases):
        ref, node = definition
        call = statement.value
        if (not isinstance(call.func, ast.Name)
                or call.func.id in self._scope_facts(node).bound):
            return None
        target = self._resolve(ref, call.func.id)
        if (target is None or target[0].module != ref.module
                or not self._stable_import_name(ref.module + '.' + call.func.id)
                or not isinstance(target[1], ast.FunctionDef) or target[1].decorator_list
                or self._captures(*target)):
            return None
        records, issues = bind_ast_call(call, FunctionSignature.from_ast(target[1].args))
        if issues or any(record['status'] != 'exact' or record.get('target_path')
                         or not isinstance(record['node'], ast.Name)
                         or record['node'].id not in aliases for record in records):
            return None
        incoming = {record['parameter']: aliases[record['node'].id] for record in records}
        effects, cause = self._function_effects(target)
        if effects is None and cause in ('mapping_effect_budget', 'recursive_helper_effects'):
            self._nested_effect_failures[ref] = cause
        if effects is None or any(effect.kind not in (
                'mapping_pop', 'mapping_delete', 'mapping_delete_keys', 'container_clear')
                or effect.target not in incoming
                or effect.source is not None and effect.source not in incoming for effect in effects):
            return None
        return tuple(replace(effect, target=incoming[effect.target],
            source=incoming.get(effect.source), statement=statement,
            sequence_loop=statement if effect.sequence_loop is not None else None)
            for effect in effects)

    ## Summarize supported returns that preserve an argument object identity.
    ## 概括受支持的、保留实参对象身份的返回。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Pair of optional return fact and unresolved reason.
    def _object_returns(self, definition):
        ref, node = definition
        if getattr(node, '_flow_branch_budget', None) is not None:
            return None, 'literal_branch_budget'
        key = (ref, repr(getattr(node, '_flow_conditions', [])))
        if key in self._object_return_cache:
            return self._object_return_cache[key]
        if self._object_fact_functions <= 0:
            return None, 'container_return_budget'
        self._object_fact_functions -= 1
        fact, cause = None, 'unsupported_return_object'
        owner = ref.qualname.rpartition('.')[0]
        if (not isinstance(node, ast.FunctionDef) or contains_yield(node)
                or node.decorator_list
                or self._definition_index.find(ref.module, owner, kind='class')
                or (not owner and not self._stable_import_name(
                    ref.module + '.' + ref.qualname))):
            cause = 'dynamic_return_callable'
        else:
            ordinary = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            aliases = {argument.arg: argument.arg for argument in ordinary}
            evidence = []
            modeled_effects = None
            for statement in node.body:
                if self._object_fact_steps <= 0:
                    cause = 'container_return_budget'
                    break
                self._object_fact_steps -= 1
                if isinstance(statement, ast.Pass) or (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str)):
                    continue
                if (isinstance(statement, (ast.Assign, ast.AnnAssign))
                        and isinstance(statement.value, ast.Name)):
                    targets = (statement.targets if isinstance(statement, ast.Assign)
                               else [statement.target])
                    if all(isinstance(target, ast.Name) for target in targets):
                        parameter = aliases.get(statement.value.id)
                        for target in targets:
                            if parameter is None:
                                aliases.pop(target.id, None)
                            else:
                                aliases[target.id] = parameter
                        evidence.append(statement)
                        continue
                if isinstance(statement, (ast.Expr, ast.Delete, ast.For)):
                    effects, effect_cause = self._function_effects(definition)
                    if (effects is not None
                            and all(effect.kind in ('mapping_pop', 'mapping_delete',
                                                    'mapping_delete_keys', 'container_clear') for effect in effects)
                            and any(effect.statement is statement or effect.sequence_loop is statement
                                    for effect in effects)):
                        modeled_effects = effects
                        evidence.append(statement)
                        continue
                    if effect_cause == 'mapping_effect_budget':
                        cause = 'container_return_budget'
                        break
                if isinstance(statement, ast.Return):
                    if isinstance(statement.value, ast.Name):
                        parameter = aliases.get(statement.value.id)
                        if parameter is not None:
                            fact = {'parameter': parameter, 'identity': 'argument_alias',
                                    'evidence': evidence + [statement]}
                            if modeled_effects:
                                fact['effects'] = modeled_effects
                            cause = None
                        elif node.args.kwarg and statement.value.id == node.args.kwarg.arg:
                            cause = 'fresh_variadic_capture'
                        elif node.args.vararg and statement.value.id == node.args.vararg.arg:
                            cause = 'fresh_variadic_capture'
                    break
                cause = 'unmodeled_helper_effects'
                break
        if fact and getattr(node, '_flow_conditions', None):
            fact['conditions'] = copy.deepcopy(node._flow_conditions)
        self._object_return_cache[key] = (fact, cause)
        return fact, cause

    ## Specialize bounded literal branches for one incoming call context.
    ## 为单个传入调用上下文特化有界字面量分支。
    #
    #  @param definition Source function identity and AST pair.
    #  @param incoming Incoming argument facts keyed by parameter.
    #  @return Original or condition-annotated function definition pair.
    def _selected_definition(self, definition, incoming):
        ref, node = definition
        if not isinstance(node, ast.FunctionDef) or contains_yield(node):
            return definition
        literals = {name: values[0]['literal'] for name, values in incoming.items()
                    if len(values) == 1 and values[0].get('literal')}
        evidence = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
        conditions = []
        branch_budget = None
        pending, body = list(node.body), []
        while pending:
            statement = pending.pop(0)
            test = statement.test if isinstance(statement, ast.If) else None
            operand = test.operand if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) else test
            literal = literals.get(operand.id) if isinstance(operand, ast.Name) else None
            if test is not None and literal is not None and len(conditions) >= 8:
                branch_budget = test
            if test is not None and literal is not None and len(conditions) < 8:
                branch = bool(literal['value'])
                if isinstance(test, ast.UnaryOp):
                    branch = not branch
                conditions.append({'test': evidence.evidence(test), 'branch': branch,
                    'binding': {'parameter': operand.id, 'literal': copy.deepcopy(literal),
                        'evidence': copy.deepcopy(incoming.get(operand.id, []))}})
                pending = list(statement.body if branch else statement.orelse) + pending
                continue
            body.append(statement)
            if isinstance(statement, (ast.Return, ast.Raise)):
                break
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)):
                fact = evidence.literal_fact(statement.value, {})
                if isinstance(statement.value, ast.Name):
                    fact = literals.get(statement.value.id)
                if fact is not None:
                    literals[statement.targets[0].id] = fact
                else:
                    literals.pop(statement.targets[0].id, None)
                if any(isinstance(child, ast.Call) for child in ast.walk(statement.value)):
                    literals.clear()
            elif not (isinstance(statement, ast.Pass) or isinstance(statement, ast.Expr)
                      and isinstance(statement.value, ast.Constant)):
                literals.clear()
        if not conditions:
            return definition
        selected = copy.copy(node)
        selected.body = body
        selected._flow_conditions = conditions
        selected._flow_branch_budget = branch_budget
        return ref, selected

    ## Describe a supported guarded argument-alias return path.
    ## 描述受支持的、受守卫约束的实参别名返回路径。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Partial-path return facts, possibly empty.
    def _guarded_object_returns(self, definition):
        ref, node = definition
        body = [statement for statement in getattr(node, 'body', [])
                if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))] if isinstance(node, ast.FunctionDef) else []
        if (not isinstance(node, ast.FunctionDef) or contains_yield(node)
                or node.decorator_list or not body
                or not isinstance(body[0], ast.If)):
            return []
        branch = body[0]
        operand = (branch.test.operand if isinstance(branch.test, ast.UnaryOp)
                   and isinstance(branch.test.op, ast.Not) else branch.test)
        if not isinstance(operand, ast.Name):
            return []
        if len(branch.body) != 1 or not isinstance(branch.body[0], ast.Return):
            return []
        value = branch.body[0].value
        ordinary = {argument.arg for argument in node.args.posonlyargs
                    + node.args.args + node.args.kwonlyargs}
        if not isinstance(value, ast.Name) or value.id not in ordinary:
            return []
        evidence = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
        return [{'parameter': value.id, 'identity': 'argument_alias',
            'conditions': [{'test': evidence.evidence(branch.test), 'branch': True}],
            'completion': 'normal_return', 'completeness': 'partial_paths',
            'requires_literal_guard': operand.id,
            'content_status': 'unchanged_on_this_path',
            'evidence': [evidence.evidence(branch.body[0])]}]

    ## Determine a classmethod or allocator receiver class when uniquely supported.
    ## 在证据唯一时确定类方法或分配器的接收者类。
    #
    #  @param definition Source function identity and AST pair.
    #  @param call Optional call containing receiver argument sources.
    #  @return Source class identity or None when uncertain.
    def _receiver_class(self, definition, call=None):
        ref, node = definition
        positional = node.args.posonlyargs + node.args.args
        if not positional or not (self._descriptor_kind(definition) == 'classmethod'
                                  or getattr(node, 'name', None) == '__new__'):
            return None
        if call is not None:
            values = [value for item in call.argument_sources
                      if item.get('parameter') == positional[0].arg
                      for value in item.get('sources', [])]
            types = [value.get('class_type') for value in values]
            if (values and all(types) and len(_unique(types)) == 1
                    and all(value.get('relation') == 'direct'
                            and not value.get('projection')
                            and not value.get('output_path')
                            and not value.get('value_incomplete') for value in values)):
                return FunctionRef(**types[0])
            return None
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        return classes[0][0] if len(classes) == 1 else None

    ## Summarize source-class return candidates under a bounded context.
    ## 在有界上下文中概括源码类返回候选。
    #
    #  @param definition Source function identity and AST pair.
    #  @param receiver_class Optional source receiver class.
    #  @param incoming Optional incoming parameter facts.
    #  @return Candidate records and an optional recursion or budget reason.
    def _class_returns(self, definition, receiver_class, incoming=None):
        ref, node = definition
        incoming = {parameter: [{'class_lookup_mutations': copy.deepcopy(
            value['class_lookup_mutations'])} for value in values
            if value.get('class_lookup_mutations')]
            for parameter, values in (incoming or {}).items()}
        incoming = {parameter: values for parameter, values in incoming.items() if values}
        key = (ref, receiver_class, repr(getattr(node, '_flow_conditions', [])), repr(incoming))
        if key in self._class_return_cache:
            return self._class_return_cache[key]
        if key in self._class_return_stack:
            return [], 'class_return_recursion'
        if (len(self._class_return_stack) >= 8 or self._fact_functions <= 0
                or self._fact_calls <= 0):
            return [], 'class_return_budget'
        if isinstance(node, ast.AsyncFunctionDef) or contains_yield(node):
            return [], None
        if self._descriptor_kind(definition) == 'classmethod' and receiver_class is None:
            return [], None
        if ('.' not in ref.qualname and not self._stable_import_name(
                ref.module + '.' + ref.qualname)):
            return [], None
        if (getattr(node, 'decorator_list', []) and self._descriptor_kind(definition) is None
                and self._identity_decorator(definition) is None):
            return [], None
        self._fact_functions -= 1
        self._class_return_stack.append(key)
        scratch = FlowAnalysis(ref, {})
        summary = _Summary(self, scratch, ref, node, self._fact_calls,
                           receiver_class, incoming)
        try:
            summary.run()
            values = []
            complete = bool(summary.normal_returns) and not summary.incomplete_return
            for returned in summary.normal_returns:
                known = summary.class_values(returned)
                if not known:
                    complete = False
                values.extend(known)
            values = _unique(values) if complete else _unique([
                dict(value, value_incomplete=True) for value in summary.returns
                if value.get('kind') == 'class' and value.get('class_type')
                and value.get('attribute_provenance')
                and value.get('relation') == 'direct' and not value.get('projection')
                and not value.get('output_path')])
            cause = next((item['reason'] for item in scratch.boundaries
                          if item['reason'] in ('class_return_recursion',
                                                'class_return_budget', 'budget_exceeded')), None)
            if values and not complete and cause is None:
                cause = 'class_attribute_state_unknown'
            self._class_return_cache[key] = (values, cause)
            return values, cause
        finally:
            self._class_return_stack.pop()

    ## Find a source __call__ candidate for one imported module-level instance.
    ## 为导入的模块级实例查找源码 __call__ 候选。
    #
    #  @param caller Function containing the invocation.
    #  @param name Syntactic callee spelling.
    #  @param binding Current lexical binding of the callee's first name.
    #  @return (target, constructor facts, unresolved cause), conservatively.
    def _module_callable_instance(self, caller, name, binding):
        first, dot, rest = name.partition('.')
        if binding is not None and not (
                binding and all(item.get('kind') == 'import' for item in binding)):
            return None, None, None
        if binding and any(value.get('import_modified')
                           or value.get('import_incomplete')
                           or value.get('conditions') for value in binding):
            return None, None, None
        if first in self.module_bindings.get(caller.module, set()) and dot:
            return None, None, None
        imports = self.imports.get(caller.module, {})
        imported = imports.get(first)
        if imported:
            if binding and {item['source'] for item in binding} != {imported}:
                return None, None, None
            qualified = imported + (dot + rest if dot else '')
        elif not dot:
            qualified = caller.module + '.' + first
        else:
            return None, None, None
        module, _, variable = qualified.rpartition('.')
        sources = self.module_bodies.get(module, [])
        if not sources:
            return None, None, None
        if len(sources) != 1:
            return None, None, 'ambiguous_module'
        path, body = sources[0]

        ## Find the root name of an attribute or subscript target.
        ## 查找属性或下标目标的根名称。
        #
        #  @param node Target AST node.
        #  @return Root name or None when unavailable.
        def root_name(node):
            while isinstance(node, (ast.Attribute, ast.Subscript)):
                node = node.value
            return node.id if isinstance(node, ast.Name) else ''

        ## Traverse statements without entering deferred callable bodies.
        ## 遍历语句，不进入延迟执行的可调用体。
        #
        #  @param nodes Statement sequence.
        #  @return Iterator of inspected statements.
        def statements(nodes):
            for statement in nodes:
                yield statement
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.ClassDef)):
                    continue
                children = [child for child in ast.iter_child_nodes(statement)
                            if isinstance(child, ast.stmt)]
                yield from statements(children)

        bindings = []
        dynamic_write = False
        method_write = False
        for statement in statements(body):
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign,
                                      ast.Delete)):
                targets = (statement.targets if isinstance(statement, (ast.Assign, ast.Delete))
                           else [statement.target])
                for target in targets:
                    if root_name(target) != variable:
                        continue
                    if isinstance(target, ast.Name) and isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        bindings.append(statement)
                    else:
                        dynamic_write = True
                        if (isinstance(target, ast.Attribute)
                                and target.attr == '__call__'):
                            method_write = True
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef)) and statement.name == variable:
                bindings.append(statement)
            elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                if any(fact.python_binding == variable for fact in import_facts(statement)):
                    bindings.append(statement)
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                function = statement.value.func
                if isinstance(function, ast.Name) and function.id in (
                        'globals', 'exec', 'eval', 'setattr', 'delattr'):
                    dynamic_write = True
        if any(any(isinstance(node, ast.Global) and variable in node.names
                   for node in ast.walk(statement))
               for statement in body
               if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))):
            dynamic_write = True
        if len(bindings) != 1:
            return None, None, 'multiple_bindings' if bindings else None
        if method_write:
            return None, None, 'dynamic_method_write'
        if dynamic_write:
            return None, None, 'dynamic_binding_write'
        assignment = bindings[0]
        if assignment not in body:
            return None, None, 'conditional_binding'
        value = (assignment.value if isinstance(assignment, (ast.Assign, ast.AnnAssign))
                 else None)
        if not isinstance(value, ast.Call):
            return None, None, 'constructor_unavailable'
        constructor_name = ast.unparse(value.func)
        if constructor_name.partition('.')[0] in self.module_bindings.get(module, set()):
            return None, None, 'constructor_unavailable'
        module_ref = FunctionRef(module, '', path)
        constructed = self._resolve_class(module_ref, constructor_name)
        if constructed is None:
            return None, None, 'constructor_unavailable'
        class_ref, cls = constructed
        if cls.decorator_list or cls.keywords:
            return None, None, 'dynamic_class'
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if hierarchy is None or any(base.decorator_list for _, base in hierarchy):
            return None, None, 'dynamic_class'
        if any(isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
               and member.name == '__new__'
               for _, base in hierarchy for member in base.body):
            return None, None, 'dynamic_constructor'
        methods = [member for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))]
        init = [member for member in methods if member.name == '__init__']
        if len(init) != 1 or init[0].decorator_list:
            return None, None, 'dynamic_constructor'
        calls = self._definition_index.find(
            class_ref.module, class_ref.qualname + '.__call__')
        if not calls:
            inherited = self._inherited_method(
                class_ref.module, class_ref.qualname, '__call__')
            calls = [inherited] if inherited else []
        if len(calls) != 1 or calls[0][1].decorator_list:
            return None, None, 'dynamic_method_write'
        if any(isinstance(member, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                       and node.id == '__call__' for node in ast.walk(member))
               for member in cls.body):
            return None, None, 'dynamic_method_write'
        class_name = constructor_name.partition('.')[0]
        for statement in statements(body):
            if not isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign,
                                          ast.Delete)):
                continue
            targets = (statement.targets if isinstance(statement, (ast.Assign, ast.Delete))
                       else [statement.target])
            for target in targets:
                if (root_name(target) in (class_name, variable)
                        and isinstance(target, ast.Attribute)
                        and target.attr == '__call__'):
                    return None, None, 'dynamic_method_write'
        selected = init[0].args.posonlyargs + init[0].args.args
        records, reasons = bind_ast_call(
            value, FunctionSignature.from_ast(init[0].args, selected[1:]))
        if reasons or any(record['status'] != 'exact' for record in records):
            return None, None, 'constructor_binding_uncertain'
        return calls[0], {
            'qualified_name': qualified, 'module_ref': module_ref,
            'assignment': assignment, 'constructor': value,
            'class_ref': class_ref, 'arguments': records,
            'source_body': body}, None
