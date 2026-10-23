## @package pcresolve._export_lists
#  Finite export-list construction facts, not final module namespace bindings.

import ast
from dataclasses import dataclass
from pathlib import Path

from .import_facts import import_facts, resolve_relative_module
from .scope_facts import statement_scope_facts
from .source_snapshot import FLOW_SOURCE, SourceStore


class _OpenExports(ValueError):
    def __init__(self, reason, module='', node=None):
        super().__init__(reason)
        self.details = {'reason': reason, 'module': module,
                        'lineno': getattr(node, 'lineno', None)}


@dataclass(frozen=True)
class _Values:
    kind: str
    names: tuple
    borrowed: bool = False


## Identify a direct child whose loading can bind an attribute of its parent.
#  This syntax fact is not evidence that the resulting module binding survives.
def implicit_submodule(owner, is_package, fact):
    if not is_package or fact.kind != 'from' or not fact.wildcard:
        return None
    target = resolve_relative_module(owner, True, fact.module, fact.level)
    return target if target.rpartition('.')[0] == owner else None


## Read literal export-list computations from explicit filesystem import roots.
#  Each resolve() captures fresh source versions. It never imports target code.
class ExportListResolver:
    ## Configure source lookup and finite construction limits.
    #  @param import_roots Explicit source roots; ambiguous files are not selected.
    #  @param max_nodes Maximum charged source/evaluation nodes per resolve().
    #  @param max_modules Maximum source modules read for this construction.
    #  @param max_depth Maximum recursive imported-export depth.
    #  @param max_names Maximum number of names in any intermediate value.
    #  @param budget Optional cooperative analysis budget.
    def __init__(self, import_roots, max_nodes=1000000, max_modules=64,
                 max_depth=32, max_names=10000, budget=None):
        if any(type(value) is not int or value <= 0
               for value in (max_nodes, max_modules, max_depth, max_names)):
            raise ValueError('Export-list limits must be positive integers')
        self.roots = tuple(dict.fromkeys(Path(root).resolve() for root in import_roots))
        self.max_nodes, self.max_modules = max_nodes, max_modules
        self.max_depth, self.max_names, self.budget = max_depth, max_names, budget
        self.store = SourceStore()
        self.last_boundary = None

    def charge(self):
        self.remaining -= 1
        if self.budget is not None:
            self.budget.checkpoint()
        if self.remaining < 0:
            raise _OpenExports('export_list_budget')

    def source(self, module):
        if module in self.documents:
            return self.documents[module]
        if len(self.documents) >= self.max_modules:
            raise _OpenExports('export_module_budget')
        if not module or not all(part.isidentifier() for part in module.split('.')):
            raise _OpenExports('invalid_export_module')
        paths = set()
        for root in self.roots:
            stem = root.joinpath(*module.split('.'))
            for candidate in (stem.with_suffix('.py'), stem / '__init__.py'):
                path = candidate.resolve()
                if path.is_file() and (path == root or root in path.parents):
                    paths.add(path)
        if len(paths) != 1:
            raise _OpenExports('export_source_missing_or_ambiguous')
        path = str(next(iter(paths)))
        document = self.store.snapshot([path], FLOW_SOURCE, self.budget).documents[path]
        if document.tree is None:
            raise _OpenExports('export_source_unavailable')
        self.documents[module] = document
        for _ in ast.walk(document.tree):
            self.charge()
        return document

    def qualify(self, node, aliases, bindings, globals_written, owner):
        parts = []
        while isinstance(node, ast.Attribute):
            if len(parts) >= self.max_depth:
                raise _OpenExports('export_attribute_depth')
            parts.append(node.attr)
            node = node.value
        if (not isinstance(node, ast.Name) or node.id in globals_written
                or len(bindings.get(node.id, ())) != 1 or node.id not in aliases):
            raise _OpenExports('export_import_binding_unproven')
        qualified = '.'.join([aliases[node.id], *reversed(parts)])
        statement = bindings[node.id][0]
        self.module_bindings.append({'module': owner, 'local_name': node.id,
            'target_module': qualified, 'status': 'required',
            'import_evidence': {'file_path': self.documents[owner].file_path,
                'lineno': statement.lineno, 'col_offset': statement.col_offset,
                'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset}})
        return qualified

    def bounded(self, kind, values, borrowed=False):
        if len(values) > self.max_names or any(type(name) is not str or not name.isidentifier()
                                              for name in values):
            raise _OpenExports('export_names_unproven_or_exhausted')
        return _Values(kind, tuple(values), borrowed)

    def exports(self, module):
        if module in self.results:
            return self.results[module]
        if module in self.active or len(self.active) >= self.max_depth:
            raise _OpenExports('export_dependency_cycle_or_depth')
        self.active.add(module)
        document = self.source(module)
        aliases, bindings, globals_written, implicit = {}, {}, set(), {}
        for statement in document.tree.body:
            for name in statement_scope_facts([statement]).bound:
                bindings.setdefault(name, []).append(statement)
            for fact in import_facts(statement):
                if fact.kind == 'import':
                    aliases[fact.python_binding] = fact.name if fact.asname else fact.python_binding
                elif not fact.wildcard:
                    base = resolve_relative_module(module, document.file_path.endswith('__init__.py'),
                                                   fact.module, fact.level)
                    aliases[fact.python_binding] = base + '.' + fact.name
                else:
                    child = implicit_submodule(module, document.file_path.endswith('__init__.py'), fact)
                    if child is not None:
                        name = child.rpartition('.')[2]
                        implicit.setdefault(name, []).append((child, statement))
            for node in ast.walk(statement):
                if isinstance(node, ast.Global):
                    globals_written.update(node.names)
        for name, candidates in implicit.items():
            if name not in bindings:
                aliases[name] = candidates[0][0]
                bindings[name] = [statement for _, statement in candidates]
        if '__all__' in globals_written:
            raise _OpenExports('runtime_export_rebinding')
        current, allowed = None, set()

        def evaluate(node):
            self.charge()
            if isinstance(node, (ast.List, ast.Tuple)) and all(
                    isinstance(item, ast.Constant) and type(item.value) is str for item in node.elts):
                return self.bounded('list' if isinstance(node, ast.List) else 'tuple',
                                    [item.value for item in node.elts])
            if isinstance(node, ast.Name) and node.id == '__all__' and current is not None:
                return current
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left, right = evaluate(node.left), evaluate(node.right)
                if left.kind != right.kind:
                    raise _OpenExports('export_sequence_type_mismatch')
                return self.bounded(left.kind, left.names + right.names)
            if isinstance(node, ast.Attribute) and node.attr == '__all__':
                imported = self.qualify(node.value, aliases, bindings, globals_written, module)
                value = self.exports(imported)
                return _Values(value.kind, value.names, value.kind == 'list')
            raise _OpenExports('export_value_unmodeled')

        for statement in document.tree.body:
            self.charge()
            selected = False
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == '__all__'):
                current, selected = evaluate(statement.value), True
            elif (isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name)
                  and statement.target.id == '__all__' and isinstance(statement.op, ast.Add)):
                if current is None or current.borrowed:
                    raise _OpenExports('export_mutable_alias_or_missing_input')
                added = evaluate(statement.value)
                if current.kind == 'tuple' and added.kind != 'tuple':
                    raise _OpenExports('export_sequence_type_mismatch')
                current, selected = self.bounded(current.kind, current.names + added.names), True
            elif (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                  and isinstance(statement.value.func, ast.Attribute)
                  and isinstance(statement.value.func.value, ast.Name)
                  and statement.value.func.value.id == '__all__'):
                call = statement.value
                if (current is None or current.kind != 'list' or current.borrowed
                        or call.keywords or len(call.args) != 1):
                    raise _OpenExports('export_list_method_unproven')
                name, argument = call.func.attr, call.args[0]
                if name == 'extend':
                    current = self.bounded('list', current.names + evaluate(argument).names)
                elif name in ('append', 'remove') and isinstance(argument, ast.Constant) and type(
                        argument.value) is str:
                    values = list(current.names)
                    if name == 'append':
                        values.append(argument.value)
                    elif argument.value in values:
                        values.remove(argument.value)
                    else:
                        raise _OpenExports('export_remove_missing_name')
                    current = self.bounded('list', values)
                else:
                    raise _OpenExports('export_list_method_unmodeled')
                selected = True
            if selected:
                allowed.update(ast.walk(statement))
                self.evidence.append({'module': module, 'file_path': document.file_path,
                    'lineno': statement.lineno, 'col_offset': statement.col_offset,
                    'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset})
        if current is None:
            raise _OpenExports('export_declaration_missing')
        for node in ast.walk(document.tree):
            self.charge()
            if node in allowed:
                continue
            imported_exports = False
            if isinstance(node, ast.Attribute) and node.attr == '__all__':
                head = node.value
                while isinstance(head, ast.Attribute):
                    head = head.value
                imported_exports = (not isinstance(node.ctx, ast.Load)
                                    or isinstance(head, ast.Name) and head.id in aliases)
            if (isinstance(node, ast.Name) and node.id == '__all__'
                    or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == '__all__'
                    or imported_exports):
                raise _OpenExports('export_use_outside_construction', module, node)
        self.active.remove(module)
        self.results[module] = current
        return current

    def implicit_input(self, owner, statement, imported):
        document = self.documents[owner]
        target = implicit_submodule(owner, document.file_path.endswith('__init__.py'), imported)
        if target is None:
            raise _OpenExports('export_implicit_parent_binding_unproven', owner, statement)
        bound = statement_scope_facts(document.tree.body).bound
        children = {implicit_submodule(owner, True, fact)
                    for item in document.tree.body for fact in import_facts(item)} - {None}
        children = {child for child in children if child.rpartition('.')[2] not in bound}
        names = {child.rpartition('.')[2] for child in children}
        import_state = {'__path__', '__spec__', '__loader__', '__package__', '__name__',
                        '__class__', '__dict__', '__getattribute__', '__getattr__'}
        capabilities = {'__path__', '__spec__', '__loader__', '__dict__'}
        # Loading a child only creates this attribute on a fresh load. Cached
        # imports cannot repair a deleted/replaced parent attribute. Reject all
        # visible competing bindings, including names injected by other stars.
        for item in document.tree.body:
            self.charge()
            if (names | import_state) & statement_scope_facts([item]).bound:
                raise _OpenExports('export_implicit_parent_name_may_be_rebound', owner, item)
            for fact in import_facts(item):
                if fact.wildcard:
                    base = resolve_relative_module(owner, True, fact.module, fact.level)
                    if (names | import_state) & set(self.exports(base).names):
                        raise _OpenExports('export_implicit_parent_star_may_shadow_module', owner, item)
        # Audit the complete captured construction input set once per parent.
        # A child may directly modify or expose its parent during its import.
        key = owner, tuple(sorted(self.documents))
        if key not in self.implicit_guards:
            for module, captured in list(self.documents.items()):
                aliases, parents = {}, {}
                for node in ast.walk(captured.tree):
                    self.charge()
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
                    for fact in import_facts(node):
                        if fact.kind == 'import':
                            canonical = fact.name if fact.asname else fact.python_binding
                        elif not fact.wildcard:
                            prefix = resolve_relative_module(module,
                                captured.file_path.endswith('__init__.py'), fact.module, fact.level)
                            canonical = prefix + '.' + fact.name
                        else:
                            continue
                        aliases.setdefault(fact.python_binding, set()).add(canonical)

                def references(node):
                    parts = []
                    while isinstance(node, ast.Attribute):
                        parts.append(node.attr)
                        node = node.value
                    return ({'.'.join([head, *reversed(parts)])
                             for head in aliases.get(node.id, ())}
                            if isinstance(node, ast.Name) else set())

                for node in ast.walk(captured.tree):
                    self.charge()
                    if (module == owner and isinstance(node, ast.Global)
                            and (names | import_state) & set(node.names)
                            or isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                            and node.id in ('exec', 'eval', '__import__', '__builtins__')
                            or module == owner and isinstance(node, ast.Name)
                            and isinstance(node.ctx, ast.Load)
                            and node.id in capabilities | {'globals', 'locals', 'vars'}
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and references(node) & {'sys.modules', 'importlib.import_module',
                                'builtins.exec', 'builtins.eval', 'builtins.__import__'}
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and references(node) & {owner + '.' + name for name in capabilities}):
                        raise _OpenExports('export_implicit_parent_namespace_capability', module, node)
                    if (isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                            and owner in references(node.value)):
                        raise _OpenExports('export_implicit_parent_attribute_write', module, node)
                    if (isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load)
                            and owner in references(node)):
                        parent = parents.get(node)
                        if not isinstance(parent, ast.Attribute) or parent.value is not node:
                            raise _OpenExports('export_implicit_parent_namespace_escape', module, node)
            self.implicit_guards.add(key)
        return target

    def module_input(self, requirement):
        owner = requirement['module']
        document = self.documents[owner]
        evidence = requirement['import_evidence']
        matching = [node for node in document.tree.body
            if all(getattr(node, field, None) == evidence[field]
                   for field in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'))]
        if len(matching) != 1:
            raise _OpenExports('export_import_site_unproven', owner)
        statement = matching[0]
        facts = [fact for fact in import_facts(statement)
                 if fact.python_binding == requirement['local_name']
                 or (implicit_submodule(owner, document.file_path.endswith('__init__.py'), fact)
                     or '').rpartition('.')[2] == requirement['local_name']]
        if len(facts) != 1:
            raise _OpenExports('export_import_name_unproven', owner, statement)
        imported = facts[0]
        target = requirement['target_module']
        if imported.kind == 'import' and '.' not in imported.name:
            expected = imported.name
        elif imported.kind == 'from' and imported.wildcard:
            expected = self.implicit_input(owner, statement, imported)
        elif imported.kind == 'from' and not imported.wildcard:
            base = resolve_relative_module(owner, document.file_path.endswith('__init__.py'),
                                           imported.module, imported.level)
            if base != owner or not document.file_path.endswith('__init__.py'):
                raise _OpenExports('export_parent_namespace_unproven', owner, statement)
            # A from-package import consults existing attributes before loading
            # a submodule. A matching filename alone cannot bypass that lookup.
            aliases = {}
            for root in document.tree.body:
                for item in ast.walk(root):
                    for fact in import_facts(item):
                        if fact.kind == 'import':
                            canonical = fact.name if fact.asname else fact.python_binding
                        elif not fact.wildcard:
                            prefix = resolve_relative_module(owner, True, fact.module, fact.level)
                            canonical = prefix + '.' + fact.name
                        else:
                            continue
                        aliases.setdefault(fact.python_binding, set()).add(canonical)

            def namespace_names(node):
                parts = []
                while isinstance(node, ast.Attribute):
                    parts.append(node.attr)
                    node = node.value
                if not isinstance(node, ast.Name):
                    return set()
                return {'.'.join([head, *reversed(parts)]) for head in aliases.get(node.id, ())}

            for prior in document.tree.body:
                self.charge()
                if prior is statement:
                    break
                bound = statement_scope_facts([prior]).bound
                if imported.name in bound or '__getattr__' in bound:
                    raise _OpenExports('export_parent_attribute_may_shadow_module', owner, prior)
                for node in ast.walk(prior):
                    self.charge()
                    if (isinstance(node, ast.Global)
                            and {imported.name, '__getattr__'} & set(node.names)
                            or isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                            and node.id in ('exec', 'eval', 'globals', 'locals', 'vars', '__import__')
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and isinstance(node.ctx, ast.Load) and owner in namespace_names(node)
                            or isinstance(node, ast.Call)
                            and 'importlib.import_module' in namespace_names(node.func)
                            or isinstance(node, ast.Attribute) and node.attr == 'modules'
                            and 'sys' in namespace_names(node.value)):
                        raise _OpenExports('export_parent_namespace_write_or_escape', owner, node)
                for fact in import_facts(prior):
                    if not fact.wildcard:
                        continue
                    module = resolve_relative_module(owner, True, fact.module, fact.level)
                    exported = self.exports(module)
                    if imported.name in exported.names or '__getattr__' in exported.names:
                        raise _OpenExports('export_parent_star_may_shadow_module', owner, prior)
            expected = base + '.' + imported.name
        else:
            raise _OpenExports('export_module_import_protocol_unmodeled', owner, statement)
        if target != expected:
            raise _OpenExports('export_module_attribute_chain_unproven', owner, statement)
        target_source = self.source(target)
        sys_names = {fact.python_binding for node in ast.walk(target_source.tree)
                     for fact in import_facts(node)
                     if fact.kind == 'import' and fact.name == 'sys'}

        def system_module(node):
            return (isinstance(node, ast.Name) and node.id in sys_names
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == '__import__' and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'sys')

        def module_table(node):
            return (isinstance(node, ast.Attribute) and node.attr == 'modules'
                    and system_module(node.value)
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'getattr' and len(node.args) >= 2
                    and system_module(node.args[0]) and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == 'modules')

        for node in ast.walk(target_source.tree):
            self.charge()
            if (isinstance(node, ast.Attribute) and node.attr == '__class__'
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    or isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and module_table(node)
                    or isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and module_table(node.value)
                    or isinstance(node, (ast.Assign, ast.AnnAssign)) and module_table(node.value)
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and module_table(node.func.value) and node.func.attr in (
                        'update', 'clear', 'pop', 'setdefault', '__setitem__', '__delitem__')
                    or isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
                    and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
                    in ('setattr', 'delattr', '__setattr__', '__delattr__')
                    and any(isinstance(arg, ast.Constant) and arg.value == '__class__'
                            for arg in node.args)):
                raise _OpenExports('export_imported_module_layout_or_registry_write', target, node)
        proof = {'kind': 'source_export_module_input', 'status': 'source_bound',
            'owner_module': owner, 'local_name': requirement['local_name'],
            'target_module': target, 'target_file_path': target_source.file_path,
            'import_evidence': dict(evidence),
            'completion': 'normal_import_return_only', 'runtime_module_confirmed': False,
            'assumptions': ['standard_source_import_protocol', 'standard_module_attribute_lookup',
                'no_unmodeled_indirect_module_mutation', 'no_external_monkeypatch_or_import_hook']}
        if imported.wildcard:
            proof['binding_protocol'] = 'implicit_parent_submodule_attribute'
        return proof

    ## Capture one finite export-list construction and its supporting source versions.
    #  @param module Qualified source module name.
    #  @param validate_module_inputs Require independently checked module import inputs.
    #  @return Construction fact or None; final callable namespace is never proved here.
    def resolve(self, module, validate_module_inputs=False):
        self.remaining = self.max_nodes
        self.documents, self.results, self.active, self.evidence = {}, {}, set(), []
        self.module_bindings = []
        self.implicit_guards = set()
        self.last_boundary = None
        self.last_evidence = None
        try:
            value = self.exports(module)
            module_inputs = []
            if validate_module_inputs:
                index = 0
                while index < len(self.module_bindings):
                    self.charge()
                    module_inputs.append(self.module_input(self.module_bindings[index]))
                    index += 1
        except _OpenExports as error:
            self.last_boundary = str(error)
            self.last_evidence = error.details
            return None
        assumptions = {'source_snapshot_bindings_hold', 'native_list_tuple_export_construction',
            'imported_export_list_module_bindings_hold', 'standard_module_attribute_lookup',
            'no_unmodeled_indirect_export_list_mutation', 'no_external_monkeypatch_or_import_hook'}
        for proof in module_inputs:
            assumptions.update(proof['assumptions'])
        return {'kind': 'source_export_list_construction', 'module': module,
            'status': 'construction_proven', 'scope': 'finite_source_export_list_construction',
            'completion': 'normal_construction_only', 'container_kind': value.kind,
            'values': list(value.names), 'borrowed_list': value.borrowed,
            'namespace_binding_proven': False, 'runtime_exports_confirmed': False,
            'required_module_bindings': list(self.module_bindings),
            'module_inputs_proven': bool(validate_module_inputs),
            'module_input_bindings': module_inputs,
            'construction_evidence': list(self.evidence),
            'source_hashes': {document.file_path: document.sha256
                              for document in self.documents.values()},
            'assumptions': sorted(assumptions)}
