## @package pcresolve._constructor_retention
#  Partial fresh-receiver write proofs, separate from execution/completion facts.

import ast
from dataclasses import asdict

from .program_facts import SourceSpan
from .scope_facts import function_scope_facts, statement_scope_facts


class _OpenReceiver(Exception):
    pass


## Describe root initializer stores retained on normal construction return.
#  @param analyzer Fixed source generation and bounded source lookup.
#  @param hierarchy Source MRO already checked by the constructor binding.
#  @param target Selected initializer definition pair.
#  @param binding Source class invocation binding, never a runtime observation.
#  @return Store witnesses, or none for open protocols, effects or budgets.
def retained_stores(analyzer, hierarchy, target, binding):
    ref, initializer = target
    if (binding['status'] != 'source_bound' or binding['phase'] != '__init__'
            or not hierarchy or len(hierarchy) > 64):
        return []
    forbidden = {'__setattr__', '__delattr__', '__getattribute__', '__getattr__',
                 '__slots__', '__dict__', '__class__'}
    namespace = set()
    captures = set()
    for _, cls in hierarchy:
        namespace.update(statement_scope_facts(cls.body).bound)
        for method in cls.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            parameters = method.args.posonlyargs + method.args.args
            if not parameters:
                continue
            receiver = parameters[0].arg
            for node in ast.walk(method):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Attribute)
                        and isinstance(node.targets[0].value, ast.Name)
                        and node.targets[0].value.id == receiver
                        and any(isinstance(child, ast.Name) and child.id == receiver
                                and isinstance(child.ctx, ast.Load)
                                for child in ast.walk(node.value))):
                    captures.add(node.targets[0].attr)
    if forbidden & namespace:
        return []
    identities = {owner for owner, _ in hierarchy}
    mutations, truncated = analyzer._class_binding_writes(include_escapes=True)
    if truncated:
        return []
    for written, _, reason, owner, node in mutations:
        if written not in identities:
            continue
        # A verified builtin super(Class, self) does not expose Class to user code.
        definitions = analyzer._definition_index.find(owner.module, owner.qualname)
        if (reason == 'visible_class_escape' and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == 'super'
                and len(definitions) == 1
                and analyzer._builtin_name_status(owner, definitions[0][1], 'super')
                == 'confirmed_builtin'):
            continue
        return []

    remaining = [10000]
    checked = {}
    writes = []
    calls = set()

    def charge(node):
        remaining[0] -= 1
        if remaining[0] < 0:
            raise _OpenReceiver()

    def method_target(name, after=None):
        start = after is None
        for owner, cls in hierarchy:
            if not start:
                start = owner == after
                continue
            if name not in statement_scope_facts(cls.body).bound:
                continue
            matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
            if (len(matches) != 1 or not isinstance(matches[0][1], ast.FunctionDef)
                    or matches[0][1].decorator_list):
                raise _OpenReceiver()
            return matches[0]
        raise _OpenReceiver()

    def inspect(definition, active=()):
        owner, method = definition
        if owner in active or len(active) >= 32:
            raise _OpenReceiver()
        if owner in checked:
            return
        checked[owner] = method
        parameters = method.args.posonlyargs + method.args.args
        if not parameters:
            raise _OpenReceiver()
        receiver = parameters[0].arg

        def receiver_read(node):
            return any(isinstance(child, ast.Name) and child.id == receiver
                       and isinstance(child.ctx, ast.Load) for child in ast.walk(node))

        def captured_read(node):
            return any(isinstance(child, ast.Attribute) and child.attr in captures
                       and isinstance(child.value, ast.Name) and child.value.id == receiver
                       for child in ast.walk(node))

        def visit(node, parent=None, captured_store=False):
            charge(node)
            if (isinstance(node, ast.Return) and method.name == '__init__'
                    and node.value is not None and not (
                        isinstance(node.value, ast.Constant) and node.value.value is None)):
                raise _OpenReceiver()
            if isinstance(node, ast.Raise) and owner != ref:
                # The consumer selects root guards but does not execute these
                # receiver-only callees. Do not use a vacuous normal-return proof.
                raise _OpenReceiver()
            if isinstance(node, (ast.Global, ast.Nonlocal, ast.Await, ast.Yield, ast.YieldFrom,
                                 ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
                                 ast.Try, ast.NamedExpr, ast.ClassDef)):
                raise _OpenReceiver()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if receiver_read(node) and not (isinstance(node, ast.Lambda) and captured_store):
                    raise _OpenReceiver()
                defaults = node.args.defaults + [v for v in node.args.kw_defaults if v is not None]
                for value in defaults:
                    visit(value)
                return
            if isinstance(node, ast.Assign):
                own_store = (len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
                             and isinstance(node.targets[0].value, ast.Name)
                             and node.targets[0].value.id == receiver)
                visit(node.value, node, own_store)
                for destination in node.targets:
                    visit(destination, node)
                return
            if isinstance(node, ast.Call):
                selected = None
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == receiver:
                        selected = method_target(node.func.attr)
                elif (isinstance(node.func, ast.Attribute)
                      and isinstance(node.func.value, ast.Call)
                      and isinstance(node.func.value.func, ast.Name)
                      and node.func.value.func.id == 'super'):
                    invocation = node.func.value
                    if (analyzer._builtin_name_status(owner, method, 'super') != 'confirmed_builtin'
                            or invocation.keywords or len(invocation.args) not in (0, 2)):
                        raise _OpenReceiver()
                    enclosing = next((item for item, _ in hierarchy
                                      if item.module == owner.module
                                      and item.qualname == owner.qualname.rpartition('.')[0]), None)
                    if enclosing is None:
                        raise _OpenReceiver()
                    if invocation.args:
                        first, second = invocation.args
                        head = ast.unparse(first).partition('.')[0]
                        if (not isinstance(first, (ast.Name, ast.Attribute))
                                or head in function_scope_facts(method).bound
                                or not analyzer._stable_import_name(owner.module + '.' + head)):
                            raise _OpenReceiver()
                        selected_class = analyzer._resolve_class(owner, ast.unparse(first))
                        if (not selected_class or selected_class[0] != enclosing
                                or not isinstance(second, ast.Name) or second.id != receiver):
                            raise _OpenReceiver()
                    selected = method_target(node.func.attr, after=enclosing)
                if selected is None:
                    if isinstance(node.func, ast.Name) and node.func.id in (
                            'exec', 'eval', 'globals', 'locals', 'vars', '__import__'):
                        raise _OpenReceiver()
                    visit(node.func, node)
                else:
                    calls.add(selected[0].qualname.rsplit('.', 1)[-1])
                    inspect(selected, active + (owner,))
                for argument in node.args + [keyword.value for keyword in node.keywords]:
                    if captured_read(argument):
                        raise _OpenReceiver()
                    visit(argument, node)
                return
            if isinstance(node, ast.Attribute):
                if node.attr in forbidden:
                    raise _OpenReceiver()
                if (isinstance(node.ctx, ast.Load) and node.attr in captures
                        and isinstance(node.value, ast.Name) and node.value.id == receiver):
                    raise _OpenReceiver()
                if (isinstance(node.ctx, ast.Load) and node.attr in namespace
                        and isinstance(node.value, ast.Name) and node.value.id == receiver):
                    # An arbitrary class member read may invoke a descriptor or
                    # expose a bound method. Direct checked calls are handled above.
                    raise _OpenReceiver()
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    if not isinstance(node.value, ast.Name) or node.value.id != receiver:
                        if receiver_read(node):
                            raise _OpenReceiver()
                    else:
                        writes.append((owner, node.attr, node, parent))
                if isinstance(node.value, ast.Name) and node.value.id == receiver:
                    return
            if isinstance(node, ast.Name) and node.id == receiver:
                raise _OpenReceiver()
            for child in ast.iter_child_nodes(node):
                visit(child, node)

        for statement in method.body:
            visit(statement)

    try:
        inspect(target)
    except (RecursionError, _OpenReceiver):
        return []
    if any(attribute in calls for _, attribute, _, _ in writes):
        return []
    paths = {owner.file_path for owner in checked} | set(binding['source_hashes'])
    result = []
    for owner, attribute, destination, statement in writes:
        if (owner != ref or attribute in namespace or attribute.startswith('__')
                or not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(destination.ctx, ast.Store)
                or sum(name == attribute for _, name, _, _ in writes) != 1):
            continue
        result.append({'kind': 'retained_instance_attribute_store', 'status': 'source_bound',
            'basis': 'source_snapshot', 'function': asdict(ref),
            'receiver_class': binding['receiver_class'],
            'receiver': initializer.args.posonlyargs[0].arg if initializer.args.posonlyargs
                        else initializer.args.args[0].arg,
            'attribute': attribute, 'store_protocol': 'ordinary_instance_dict',
            'retention_scope': 'normal_constructor_return_after_store',
            'runtime_store_confirmed': False,
            'store_evidence': asdict(SourceSpan.from_ast(ref.file_path, statement)),
            'checked_methods': [asdict(item) for item in checked],
            'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)},
            'assumptions': list(binding['assumptions']) + ['no_external_frame_introspection']})
    return result
