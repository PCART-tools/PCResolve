## @package pcresolve._source_bindings
#  Conditional declaration references, separate from callable/body preservation.

import ast
import copy

from ._export_lists import ExportListResolver, _OpenExports, implicit_submodule
from .import_facts import import_facts, resolve_relative_module
from .scope_facts import statement_scope_facts
from .source_snapshot import FLOW_SOURCE


## Select a source function declaration along bounded module-binding paths.
#  No target module is imported. Decorators and execution fields need other proofs.
class SourceBindingResolver(ExportListResolver):
    def _span(self, module, node):
        return {'file_path': self.documents[module].file_path,
                **{field: getattr(node, field) for field in
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')}}

    def _guard(self, module, name):
        document = self.source(module)
        parents, aliases = {}, {}
        for node in ast.walk(document.tree):
            self.charge()
            for child in ast.iter_child_nodes(node):
                parents[child] = node
            for fact in import_facts(node):
                if fact.kind == 'import':
                    qualified = fact.name if fact.asname else fact.python_binding
                elif not fact.wildcard:
                    base = resolve_relative_module(module, document.file_path.endswith('__init__.py'),
                                                   fact.module, fact.level)
                    qualified = base + '.' + fact.name
                else:
                    child = implicit_submodule(module, document.file_path.endswith('__init__.py'), fact)
                    if child is not None:
                        aliases.setdefault(child.rpartition('.')[2], set()).add(child)
                    continue
                aliases.setdefault(fact.python_binding, set()).add(qualified)

        def finite_global_write(node):
            """Ignore a finite globals() write only when it cannot touch name."""
            if ('globals' in statement_scope_facts(document.tree.body).bound
                    or not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load)):
                return False
            call = parents.get(node)
            target = parents.get(call)
            assignment = parents.get(target)
            if (not isinstance(call, ast.Call) or call.func is not node or call.args or call.keywords
                    or not isinstance(target, ast.Subscript) or target.value is not call
                    or not isinstance(target.ctx, ast.Store)
                    or not isinstance(assignment, (ast.Assign, ast.AnnAssign))
                    or isinstance(assignment, ast.Assign)
                    and (len(assignment.targets) != 1 or assignment.targets[0] is not target)
                    or isinstance(assignment, ast.AnnAssign) and assignment.target is not target):
                return False
            key = target.slice
            if not isinstance(key, ast.Name):
                return False
            current = assignment
            loop = None
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    return False
                if isinstance(current, (ast.For, ast.AsyncFor)):
                    loop = current
                    break
            if (loop is None or not isinstance(loop.target, ast.Name)
                    or loop.target.id != key.id or not isinstance(loop.iter, (ast.List, ast.Tuple))
                    or not loop.iter.elts or len(loop.iter.elts) > 64
                    or any(not isinstance(item, ast.Constant) or type(item.value) is not str
                           for item in loop.iter.elts)):
                return False
            keys = {item.value for item in loop.iter.elts}
            if name in keys:
                return False
            # The loop target is the only permitted write to the key variable;
            # otherwise the finite literal set would not bound the subscript.
            for statement in loop.body:
                for candidate in ast.walk(statement):
                    if (isinstance(candidate, ast.Name) and candidate.id == key.id
                            and isinstance(candidate.ctx, (ast.Store, ast.Del))):
                        return False
            return True

        def canonical(node):
            parts = []
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            return ({'.'.join([head, *reversed(parts)])
                     for head in aliases.get(node.id, ())}
                    if isinstance(node, ast.Name) else set())

        for node in ast.walk(document.tree):
            self.charge()
            if isinstance(node, ast.Global) and {name, '__getattr__'} & set(node.names):
                raise _OpenExports('source_binding_runtime_global_write', module, node)
            if (isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name)
                    and node.target.id in (name, '__getattr__')):
                raise _OpenExports('source_binding_expression_rebinding', module, node)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                imported = canonical(node)
                if imported & {'sys.modules', 'sys.meta_path', 'sys.path_hooks',
                               'importlib.import_module',
                               'builtins.globals', 'builtins.locals', 'builtins.vars',
                               'builtins.exec', 'builtins.eval', 'builtins.__import__'}:
                    raise _OpenExports('source_binding_namespace_capability', module, node)
                if node.id in ('exec', 'eval', 'locals', 'vars', '__import__', '__builtins__'):
                    raise _OpenExports('source_binding_dynamic_namespace', module, node)
                if node.id == 'globals':
                    call = parents.get(node)
                    attribute = parents.get(call)
                    use = parents.get(attribute)
                    if not (isinstance(call, ast.Call) and call.func is node
                            and not call.args and not call.keywords
                            and isinstance(attribute, ast.Attribute) and attribute.value is call
                            and attribute.attr in ('keys', 'values', 'items')
                            and isinstance(use, ast.Call) and use.func is attribute
                            and not use.args and not use.keywords):
                        if not finite_global_write(node):
                            raise _OpenExports('source_binding_namespace_escape', module, node)
            if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
                parent = parents.get(node)
                if module in canonical(node) and not (
                        isinstance(parent, ast.Attribute) and parent.value is node):
                    raise _OpenExports('source_binding_own_module_escape', module, node)
            if isinstance(node, ast.Attribute):
                if node.attr in ('__dict__', '__globals__', '__import__', 'import_module',
                                 'meta_path', 'path_hooks'):
                    raise _OpenExports('source_binding_reflective_namespace', module, node)
                if (node.attr == 'modules' and isinstance(node.value, ast.Name)
                        and 'sys' in aliases.get(node.value.id, ())):
                    raise _OpenExports('source_binding_module_registry', module, node)
                if isinstance(node.ctx, (ast.Store, ast.Del)) and (
                        node.attr == '__class__' or module in canonical(node.value)):
                    raise _OpenExports('source_binding_module_layout_or_attribute', module, node)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'getattr' and len(node.args) >= 2
                    and 'sys' in canonical(node.args[0])):
                raise _OpenExports('source_binding_module_registry', module, node)

    def _exports(self, module):
        if module in self.export_cache:
            return self.export_cache[module]
        available = max(1, self.remaining)
        reader = ExportListResolver(self.roots, max_nodes=available,
            max_modules=self.max_modules, max_depth=self.max_depth,
            max_names=self.max_names, budget=self.budget)
        fact = reader.resolve(module, validate_module_inputs=True)
        self.remaining -= available - reader.remaining
        if self.remaining < 0:
            raise _OpenExports('export_list_budget', module)
        if reader.last_boundary in ('export_list_budget', 'export_module_budget'):
            raise _OpenExports(reader.last_boundary, module)
        # A failed list proof is an unknown star, not proof of no binding.
        if fact is not None:
            for key, document in reader.documents.items():
                if key in self.documents and self.documents[key].sha256 != document.sha256:
                    raise _OpenExports('source_binding_snapshot_changed', key)
                if key not in self.documents:
                    if len(self.documents) >= self.max_modules:
                        raise _OpenExports('export_module_budget')
                    self.documents[key] = document
            self.export_facts.append(fact)
        self.export_cache[module] = fact
        return fact

    def _touches(self, statement, name):
        if {name, '__getattr__'} & statement_scope_facts([statement]).bound:
            return True
        return any(isinstance(node, ast.ImportFrom) and any(
            fact.wildcard for fact in import_facts(node)) for node in ast.walk(statement))

    def _select(self, module, name):
        key = (module, name)
        if key in self.selected:
            return copy.deepcopy(self.selected[key])
        if key in self.selecting or len(self.selecting) >= self.max_depth:
            raise _OpenExports('source_binding_cycle_or_depth', module)
        self.selecting.add(key)
        document = self.source(module)
        self._guard(module, name)

        def imported(states, statement, base, imported_name, wildcard):
            try:
                children = self._select(base, imported_name)
            except _OpenExports as error:
                if str(error) in ('export_list_budget', 'export_module_budget',
                                  'source_binding_snapshot_changed'):
                    raise
                children = [{'value': False, 'fallback': True, 'conditions': [], 'imports': []}]
            result = []
            for state in states:
                for child in children:
                    if child['value'] is None and not child['fallback'] and wildcard:
                        # __all__ demands the missing attribute; this import
                        # cannot complete normally on that source path.
                        continue
                    result.append({**state,
                        'value': child['value'] if child['value'] is not None else False,
                        'conditions': state['conditions'] + child['conditions'],
                        'imports': state['imports'] + child['imports'] + [{
                            'module': module, 'imported_module': base,
                            'binding_name': name,
                            'imported_name': imported_name, 'wildcard': wildcard,
                            'completion': 'normal_import_return_only',
                            'evidence': self._span(module, statement)}]})
            return result

        def evaluate(body, states):
            for statement in body:
                self.charge()
                if not states:
                    break
                if isinstance(statement, ast.Raise):
                    return []
                if isinstance(statement, ast.If) and self._touches(statement, name):
                    branches = []
                    for label, suite in (('if', statement.body), ('else', statement.orelse)):
                        conditioned = [{**state, 'conditions': state['conditions'] + [{
                            'branch': label, 'evidence': self._span(module, statement.test)}]}
                            for state in states]
                        branches.extend(evaluate(suite, conditioned))
                    states = branches
                elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if statement.name == name:
                        value = (module, name, document.file_path, statement.lineno)
                        states = [{**state, 'value': value} for state in states]
                    if statement.name == '__getattr__':
                        states = [{**state, 'fallback': True} for state in states]
                elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                    for fact in import_facts(statement):
                        if fact.kind == 'import':
                            if fact.python_binding == name:
                                states = [{**state, 'value': False} for state in states]
                            if fact.python_binding == '__getattr__':
                                states = [{**state, 'fallback': True} for state in states]
                            continue
                        base = resolve_relative_module(module,
                            document.file_path.endswith('__init__.py'), fact.module, fact.level)
                        if fact.wildcard:
                            exports = self._exports(base)
                            if exports is None:
                                states = [{**state, 'value': False, 'fallback': True}
                                          for state in states]
                                continue
                            if '__getattr__' in exports['values']:
                                states = [{**state, 'fallback': True} for state in states]
                            if name not in exports['values']:
                                continue
                        elif fact.python_binding != name:
                            if fact.python_binding == '__getattr__':
                                states = [{**state, 'fallback': True} for state in states]
                            continue
                        states = imported(states, statement, base,
                                          name if fact.wildcard else fact.name, fact.wildcard)
                elif isinstance(statement, ast.Delete):
                    deleted = {node.id for node in statement.targets if isinstance(node, ast.Name)}
                    states = [{**state, 'value': None if name in deleted else state['value'],
                               'fallback': False if '__getattr__' in deleted else state['fallback']}
                              for state in states]
                elif self._touches(statement, name):
                    bound = statement_scope_facts([statement]).bound
                    # Loops, handlers, pattern binding and arbitrary assignments
                    # cannot inherit a source declaration from their input.
                    states = [{**state, 'value': False,
                               'fallback': state['fallback'] or '__getattr__' in bound}
                              for state in states]
                if len(states) > 64:
                    raise _OpenExports('source_binding_path_budget', module, statement)
            return states

        result = evaluate(document.tree.body,
                          [{'value': None, 'fallback': False, 'conditions': [], 'imports': []}])
        self.selecting.remove(key)
        self.selected[key] = copy.deepcopy(result)
        return result

    ## Capture a unique declaration selected on all successful bounded lookups.
    #  @param module Explicit source module name under the configured import roots.
    #  @param name Single module attribute to trace, not a dotted runtime expression.
    #  @return Source reference or None; callable identity/body preservation are unproved.
    def resolve(self, module, name):
        self.remaining = self.max_nodes
        self.documents, self.selected, self.selecting = {}, {}, set()
        self.export_cache, self.export_facts = {}, []
        self.last_boundary = self.last_evidence = None
        try:
            if not isinstance(name, str) or not name.isidentifier():
                raise _OpenExports('invalid_source_binding_name', module)
            states = self._select(module, name)
            if any(state['value'] is False or state['value'] is None and state['fallback']
                   for state in states):
                raise _OpenExports('source_binding_open_lookup_path', module)
            values = {state['value'] for state in states if state['value'] is not None}
            if len(values) != 1:
                raise _OpenExports('source_binding_missing_or_competing_declaration', module)
            target_module, target_name, path, lineno = next(iter(values))
            hashes = {document.file_path: document.sha256 for document in self.documents.values()}
            captured = self.store.snapshot(hashes, FLOW_SOURCE, self.budget)
            if any(captured.documents[path].sha256 != digest for path, digest in hashes.items()):
                raise _OpenExports('source_binding_snapshot_changed', module)
        except _OpenExports as error:
            self.last_boundary, self.last_evidence = str(error), error.details
            return None
        paths = [{key: value for key, value in state.items() if key != 'value'}
                 for state in states if state['value'] is not None]
        assumptions = {'source_snapshot_bindings_hold', 'standard_source_import_protocol',
            'standard_module_attribute_lookup', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_module_mutation'}
        for fact in self.export_facts:
            assumptions.update(fact['assumptions'])
        return {'kind': 'source_module_binding_reference',
            'status': 'unique_declaration_when_lookup_succeeds',
            'basis': 'source_snapshot', 'requested': {'module': module, 'name': name},
            'target': {'module': target_module, 'qualname': target_name,
                       'file_path': path, 'lineno': lineno},
            'completion': 'normal_module_return_and_attribute_lookup_only',
            'may_be_unbound': any(state['value'] is None for state in states),
            'runtime_target_confirmed': False, 'callable_identity_proven': False,
            'body_binding_proven': False, 'paths': paths,
            'export_constructions': copy.deepcopy(self.export_facts),
            'source_hashes': hashes,
            'assumptions': sorted(assumptions)}
