## @package pcresolve._function_observation
#  Source guards for local object isolation during fresh function decoration.

import ast
import copy
import re
from dataclasses import asdict

from .effect_facts import contains_yield
from .import_facts import import_facts, resolve_relative_module

# Complete Matplotlib's fixed API source snapshot; the previous node cap was
# below the size of that snapshot and turned a whole-source observer check into
# an unconditional unknown for otherwise bounded source wrappers.
_LIMIT = 10_000_000
_PRIVATE = {'f_locals', 'f_trace', 'gi_frame', 'cr_frame', 'ag_frame', 'tb_frame',
            '__traceback__', '__globals__', 'get_objects', 'get_referrers', 'settrace', 'setprofile'}
_FACTORIES = {'_getframe', '_current_frames', 'currentframe', 'walk_stack'}
_OTHER = {'inspect.stack', 'inspect.getouterframes', 'inspect.getinnerframes',
          'inspect.getargvalues', 'traceback.walk_tb'}
_EXECUTION = {'__code__', '__defaults__', '__kwdefaults__', '__closure__', 'cell_contents'}
_FRAME_FIELDS = {'f_back', 'f_globals', 'f_code', 'f_lineno', 'f_lasti'}


def _ambient_namespaces(analyzer, module, path, nodes, parents, scopes):
    aliases, initializers = {}, []
    callable_names = {ref.qualname.rsplit('.', 1)[-1] for ref, _ in analyzer.definitions}
    callable_names.update(('isinstance', 'type', 'super', 'object', 'getattr', 'setattr'))
    for node in nodes:
        for fact in import_facts(node):
            imported = (fact.name if fact.kind == 'import' else resolve_relative_module(
                module, path.endswith('__init__.py'), fact.module, fact.level) + '.' + fact.name)
            if fact.kind == 'import' and not fact.asname:
                imported = imported.partition('.')[0]
            aliases.setdefault(fact.python_binding, set()).add(imported)
    for node in nodes:
        if isinstance(node, ast.Global) and callable_names.intersection(node.names):
            return None
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if node.attr in _EXECUTION:
                return None
            if isinstance(node.value, (ast.Name, ast.Attribute)):
                head, dot, rest = ast.unparse(node.value).partition('.')
                for value in aliases.get(head, ()):
                    owner = value + (dot + rest if dot else '')
                    if owner not in set(analyzer.module_bodies) | {'builtins', 'sys', 'inspect', 'traceback'}:
                        continue
                    bindings = analyzer.import_binding_facts.get(owner, ())
                    if (owner not in analyzer.module_bodies or node.attr.startswith('__')
                            or node.attr in ('isinstance', 'type', 'super', 'object', 'getattr', 'setattr')
                            or any(table.get(node.attr) for table in bindings)
                            or analyzer._definition_index.find_qualified([owner + '.' + node.attr])
                            or analyzer._definition_index.find_qualified(
                                [owner + '.' + node.attr], kind='class')):
                        return None
                    initializers.append({'module': module, 'file_path': path,
                        'phase': 'module_initialization' if scopes[node] is None else 'new_export_only',
                        'lineno': node.lineno, 'col_offset': node.col_offset,
                        'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset})
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            if (name in ('setattr', 'delattr', '__setattr__', '__delattr__')
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value in _EXECUTION):
                return None
        if not (isinstance(node, ast.Name) and node.id == 'globals'):
            continue
        call = parents.get(node)
        if not (isinstance(call, ast.Call) and call.func is node and not call.args and not call.keywords):
            return None
        use = parents.get(call)
        if isinstance(use, ast.Subscript) and isinstance(use.ctx, ast.Load):
            if isinstance(use.slice, ast.Constant) and use.slice.value == '__builtins__':
                return None
            continue
        read = parents.get(use)
        if (isinstance(use, ast.Attribute) and isinstance(read, ast.Call)
                and read.func is use and not read.keywords):
            if use.attr == 'items' and not read.args:
                continue
            if (use.attr == 'get' and len(read.args) in (1, 2)
                    and isinstance(read.args[0], ast.Constant)
                    and type(read.args[0].value) is str
                    and read.args[0].value != '__builtins__'):
                continue
            if (use.attr == 'update' and scopes[node] is None
                    and isinstance(parents.get(read), ast.Expr)):
                initializers.append({'module': module, 'file_path': path,
                    'phase': 'module_initialization', 'lineno': read.lineno,
                    'col_offset': read.col_offset, 'end_lineno': read.end_lineno,
                    'end_col_offset': read.end_col_offset})
                continue
        return None
    return initializers


def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
            'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}


## Guard source-visible access to frame locals and global GC object discovery.
#  @param analyzer Fixed source snapshot; no target library code is imported.
#  @param modules Optional source modules whose reachable call path is being checked.
#  @return Observer premises for the selected source scope, or None for an open capability.
def nonobserving_source(analyzer, modules=None):
    selected = tuple(sorted(set(modules))) if modules is not None else None
    cache_key = (selected, tuple(sorted(analyzer.hashes.items())))
    cache = getattr(analyzer, '_fresh_function_observer_cache', {})
    if cache_key in cache:
        return copy.deepcopy(cache[cache_key])
    if selected is None:
        cached = analyzer._fresh_function_observer_premise
    else:
        cached = False
    if cached is not False:
        return copy.deepcopy(cached)
    if selected is None:
        analyzer._fresh_function_observer_premise = None
    if analyzer.index_boundaries:
        cache[cache_key] = None
        analyzer._fresh_function_observer_cache = cache
        return None
    definitions = {node: ref for ref, node in analyzer.definitions}
    records, initializers, count = [], [], 0
    for module, bodies in analyzer.module_bodies.items():
        if selected is not None and module not in selected:
            continue
        for path, body in bodies:
            nodes, parents, scopes = [], {}, {}
            pending = [(node, None) for node in reversed(body)]
            while pending:
                node, scope = pending.pop()
                count += 1
                if count > _LIMIT:
                    return None
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                nodes.append(node)
                scopes[node] = scope
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    scope = node
                for child in reversed(list(ast.iter_child_nodes(node))):
                    parents[child] = node
                    pending.append((child, scope))
            namespace = _ambient_namespaces(analyzer, module, path, nodes, parents, scopes)
            if namespace is None:
                return None
            initializers.extend(namespace)

            def canonical(expression, scope):
                if not isinstance(expression, (ast.Name, ast.Attribute)):
                    return ''
                head, dot, rest = ast.unparse(expression).partition('.')
                imported = analyzer.imports.get(module, {}).get(head, '')
                if (not imported or scope is not None and head in analyzer._scope_facts(scope).bound
                        or imported.partition('.')[0] in analyzer.module_bodies
                        or not analyzer._stable_import_name(module + '.' + head)):
                    return ''
                return imported + (dot + rest if dot else '')

            roots, checked_metadata = [], set()
            for node in nodes:
                scope = scopes[node]
                resolved = canonical(node, scope)
                if (isinstance(node, ast.ImportFrom) and scope is not None
                        and any(alias.name in _PRIVATE | _FACTORIES for alias in node.names)):
                    return None
                spelling = (node.attr if isinstance(node, ast.Attribute) else
                            node.id if isinstance(node, ast.Name) else
                            node.value if isinstance(node, ast.Constant)
                            and type(node.value) is str else None)
                if resolved in {'sys.settrace', 'sys.setprofile', 'gc.get_objects', 'gc.get_referrers'}:
                    return None
                if resolved in {'sys._getframe', 'sys._current_frames', 'inspect.currentframe',
                                'traceback.walk_stack'}:
                    spelling = resolved.rpartition('.')[2]
                if spelling in _PRIVATE:
                    return None
                if (isinstance(node, ast.Constant) and type(node.value) is str
                        and set(re.findall(r'[A-Za-z_]\w*', node.value)) & (_PRIVATE | _FACTORIES)):
                    return None
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in ('exec', 'eval')):
                    # Implicit locals can expose a protected decoration frame.
                    # An explicitly supplied namespace remains subject to the
                    # no-indirect/no-external observation premises; it is not a
                    # claim that an empty __builtins__ mapping is a sandbox.
                    namespace = node.args[1] if len(node.args) == 2 else None
                    if (node.func.id != 'eval' or node.keywords or not isinstance(namespace, ast.Dict)
                            or not any(isinstance(key, ast.Constant) and key.value == '__builtins__'
                                       and isinstance(value, ast.Dict) and not value.keys
                                       for key, value in zip(namespace.keys, namespace.values))):
                        return None
                if (isinstance(node, (ast.Name, ast.Attribute)) and canonical(node, scope) in _OTHER
                        or isinstance(node, ast.Call) and canonical(node.func, scope) in _OTHER):
                    return None
                if spelling not in _FACTORIES:
                    continue
                call = parents.get(node)
                ref = definitions.get(scope)
                if (not isinstance(call, ast.Call) or call.func is not node or call.keywords
                        or ref is None or not isinstance(scope, ast.FunctionDef)
                        or contains_yield(scope)):
                    return None
                selected = canonical(node, scope)
                if selected == 'traceback.walk_stack':
                    if not (len(call.args) == 1 and isinstance(call.args[0], ast.Constant)
                            and call.args[0].value is None):
                        return None
                elif call.args:
                    return None
                destination = parents.get(call)
                if selected == 'sys._getframe' and isinstance(destination, ast.Assign):
                    if len(destination.targets) != 1 or not isinstance(destination.targets[0], ast.Name):
                        return None
                    variable = destination.targets[0]
                elif (selected == 'sys._current_frames' and isinstance(destination, ast.Attribute)
                        and destination.attr == 'values'):
                    values = parents.get(destination)
                    loop = parents.get(values)
                    if (not isinstance(values, ast.Call) or values.func is not destination
                            or values.args or values.keywords or not isinstance(loop, ast.For)
                            or loop.iter is not values or not isinstance(loop.target, ast.Name)):
                        return None
                    variable, destination = loop.target, loop
                elif selected == 'traceback.walk_stack':
                    if (not isinstance(destination, ast.For) or destination.iter is not call
                            or not isinstance(destination.target, ast.Tuple)
                            or len(destination.target.elts) != 2
                            or any(not isinstance(item, ast.Name) for item in destination.target.elts)
                            or destination.target.elts[0].id == destination.target.elts[1].id):
                        return None
                    variable = destination.target.elts[0]
                else:
                    return None
                facts = analyzer._scope_facts(scope)
                if variable.id in facts.globals | facts.nonlocals:
                    return None
                roots.append((ref, scope, call, variable.id, destination))

            for ref, scope, call, name, origin in roots:
                class IgnoreNameStores(ast.NodeTransformer):
                    def visit_Name(self, node):
                        return (ast.copy_location(ast.Name(id='$frame_store', ctx=ast.Store()), node)
                                if node.id == name and isinstance(node.ctx, ast.Store) else node)

                probe = IgnoreNameStores().visit(copy.deepcopy(scope))
                if (name in analyzer._scope_facts(probe).bound
                        or any(type(node).__name__.startswith('Match')
                               or isinstance(node, ast.ExceptHandler) and node.name == name
                               for node in ast.walk(scope))):
                    return None
                fields = set()
                for node in nodes:
                    if not isinstance(node, ast.Name) or node.id != name:
                        continue
                    # A same-spelled name in an unrelated scope does not refer
                    # to this local frame. A nested closure does expose it.
                    containing = scopes[node]
                    if containing is not scope:
                        current = containing
                        while current is not None and current is not scope:
                            current = scopes.get(current)
                        if current is scope:
                            return None
                        continue
                    ancestor = parents.get(node)
                    while ancestor is not None and ancestor is not scope:
                        if isinstance(ancestor, ast.ClassDef):
                            return None
                        ancestor = parents.get(ancestor)
                    parent = parents.get(node)
                    if isinstance(node.ctx, ast.Store):
                        assignment = parent
                        if (assignment is origin or isinstance(origin, ast.For)
                                and isinstance(origin.target, ast.Tuple)
                                and assignment is origin.target and node is origin.target.elts[0]):
                            continue
                        if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
                                or assignment.targets[0] is not node
                                or not isinstance(assignment.value, ast.Attribute)
                                or assignment.value.attr != 'f_back'
                                or not isinstance(assignment.value.value, ast.Name)
                                or assignment.value.value.id != name):
                            return None
                        continue
                    if not isinstance(node.ctx, ast.Load):
                        return None
                    if isinstance(parent, (ast.If, ast.While)) and parent.test is node:
                        continue
                    if (isinstance(parent, ast.Compare) and parent.left is node
                            and len(parent.ops) == 1 and isinstance(parent.ops[0], (ast.Is, ast.IsNot))
                            and isinstance(parent.comparators[0], ast.Constant)
                            and parent.comparators[0].value is None):
                        continue
                    if (not isinstance(parent, ast.Attribute) or parent.value is not node
                            or not isinstance(parent.ctx, ast.Load)):
                        return None
                    fields.add(parent.attr)
                    if parent.attr == 'f_back':
                        assignment = parents.get(parent)
                        if (not isinstance(assignment, ast.Assign)
                                or len(assignment.targets) != 1
                                or not isinstance(assignment.targets[0], ast.Name)
                                or assignment.targets[0].id != name):
                            return None
                    elif parent.attr == 'f_globals':
                        getter = parents.get(parent)
                        read = parents.get(getter)
                        if (not isinstance(getter, ast.Attribute) or getter.attr != 'get'
                                or not isinstance(read, ast.Call) or read.func is not getter
                                or read.keywords or len(read.args) not in (1, 2)
                                or not isinstance(read.args[0], ast.Constant)
                                or read.args[0].value != '__name__'
                                or len(read.args) == 2 and not (isinstance(read.args[1], ast.Constant)
                                    and type(read.args[1].value) is str)):
                            return None
                    elif parent.attr not in ('f_code', 'f_lineno', 'f_lasti'):
                        return None
                    checked_metadata.add(parent)
                records.append({'kind': 'source_frame_metadata_use', 'status': 'source_bound',
                    'function': asdict(ref), 'scope': 'native_frame_metadata_only',
                    'factory': canonical(call.func, scope), 'variable': name,
                    'fields': sorted(fields), 'evidence': _span(ref, call),
                    'global_keys': ['__name__'] if 'f_globals' in fields else [],
                    'runtime_observation_confirmed': False})
            if any(isinstance(node, ast.Attribute) and node.attr in _FRAME_FIELDS
                   and node not in checked_metadata for node in nodes):
                return None
    result = {'source_hashes': dict(sorted(analyzer.hashes.items())), 'frame_metadata': records,
        'namespace_guard': {'scope': 'bounded_source_callable_namespaces',
            'module_initializers': initializers, 'runtime_reflective_writes': [],
            'execution_field_writes': []},
        'assumptions': ['source_snapshot_bindings_hold', 'standard_sys_frame_metadata_protocol',
            'source_frame_metadata_non_escape', 'no_unmodeled_indirect_frame_or_gc_observation',
            'no_external_frame_or_gc_observation', 'no_external_monkeypatch_or_import_hook',
            'source_module_initialization_completed_before_query',
            'no_unmodeled_indirect_module_mutation', 'no_unmodeled_indirect_function_mutation']}
    if any(record['factory'] == 'traceback.walk_stack' for record in records):
        result['assumptions'].append('standard_traceback_frame_iteration_protocol')
    if selected is None:
        analyzer._fresh_function_observer_premise = result
    cache[cache_key] = result
    analyzer._fresh_function_observer_cache = cache
    return copy.deepcopy(result)
