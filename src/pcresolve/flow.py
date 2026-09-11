## @package pcresolve.flow
#  Experimental, explicit-boundary value-flow summaries for Python functions.

import ast
import builtins
import copy
import hashlib
import os
from dataclasses import dataclass, field, asdict

from .scanner import FileScanner


def _exception_class(name):
    value = getattr(builtins, name or '', None)
    return value if isinstance(value, type) and issubclass(value, BaseException) else None


def _may_raise(node):
    return any(isinstance(n, (ast.Call, ast.BinOp, ast.UnaryOp, ast.Attribute,
                              ast.Subscript, ast.Compare)) for n in ast.walk(node))


def _contains_yield(node):
    found = False

    def visit(item):
        nonlocal found
        if found:
            return
        if item is not node and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                   ast.ClassDef, ast.Lambda)):
            return
        if isinstance(item, (ast.Yield, ast.YieldFrom)):
            found = True
            return
        for child in ast.iter_child_nodes(item):
            visit(child)

    visit(node)
    return found


def _call_key(path, node):
    return '%s:%s:%s:%s:%s' % (path, node.lineno, node.col_offset,
                                node.end_lineno, node.end_col_offset)


def _call_span(node):
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


## A source function selector; definition location disambiguates duplicates.
@dataclass(frozen=True)
class FunctionRef:
    module: str = ''
    qualname: str = ''
    file_path: str = ''
    lineno: int = 0


## A syntactic call and its resolved definition, when available.
@dataclass
class FlowCall:
    id: str
    caller: FunctionRef
    callee_name: str
    lineno: int
    col_offset: int
    end_lineno: int = 0
    end_col_offset: int = 0
    target: object = None
    parameter_bindings: list = field(default_factory=list)
    parameter_flows: list = field(default_factory=list)
    return_flows: list = field(default_factory=list)
    argument_sources: list = field(default_factory=list)
    argument_flows: list = field(default_factory=list)
    capture_bindings: list = field(default_factory=list)
    return_dependencies: list = field(default_factory=list)
    receiver_sources: list = field(default_factory=list)
    analysis_status: str = 'analyzed'
    target_status: str = 'definition_unavailable'
    mutation_flows: list = field(default_factory=list)
    effects: list = field(default_factory=list)


## An immutable-by-convention analysis snapshot with JSON-safe views.
@dataclass
class FlowAnalysis:
    entry: FunctionRef
    inputs: dict
    functions: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    schema_version: str = 'flow-0.2'

    ## Find calls by caller and exact syntactic callee spelling.
    #  @param caller Optional function selector.
    #  @param callee_name Optional exact spelling.
    #  @return Matching calls in deterministic source order.
    def find_calls(self, caller=None, callee_name=None):
        return [c for c in self.calls
                if (caller is None or _matches(c.caller, caller))
                and (callee_name is None or c.callee_name == callee_name)]

    ## Return evidence for one exact call site.
    #  @param call_id Identifier returned by find_calls.
    #  @return JSON-safe call flow record.
    def describe_call_flow(self, call_id):
        for call in self.calls:
            if call.id == call_id:
                return asdict(call)
        raise KeyError(call_id)

    ## Serialize the snapshot without internal AST objects.
    #  @return Dictionary suitable for json.dumps.
    def to_dict(self):
        return asdict(self)

    ## Trace an entry parameter through explicitly expanded return summaries.
    #  @param parameter Entry parameter name.
    #  @return Proven return paths and boundaries; absence is not a no-flow proof.
    def trace_parameter(self, parameter):
        def function_key(ref):
            value = asdict(ref) if isinstance(ref, FunctionRef) else ref
            return (value['file_path'], value['qualname'], value['lineno'])

        functions = {function_key(f['function']): f for f in self.functions}
        calls = {c.id: c for c in self.calls}
        entry_key = function_key(self.entry)
        if parameter not in functions[entry_key]['parameters']:
            raise ValueError('Unknown entry parameter: ' + parameter)
        resolved = {key: [] for key in functions}
        status = 'bounded'
        limited = False

        def dependency_key(value):
            return repr({k: v for k, v in value.items()
                         if k not in ('evidence', 'conditions', 'call_context')})

        def compact(values):
            nonlocal limited
            unique = {}
            for value in values:
                key = dependency_key(value)
                if key not in unique:
                    if len(unique) >= 2048:
                        limited = True
                        break
                    unique[key] = value
            return list(unique.values())

        def sources(values, stack):
            found = []
            for value in values:
                if value['kind'] in ('parameter', 'capture'):
                    found.append(dict(value, call_context=[]))
                    continue
                call = calls.get(value['source'])
                if call is None or call.id in stack:
                    continue
                inner_values = (resolved.get(function_key(call.target), [])
                                if call.target is not None else call.return_dependencies)
                for inner in _select_flows(inner_values, value.get('projection', [])):
                    bindings = call.capture_bindings if inner['kind'] == 'capture' else call.argument_sources
                    for argument in bindings:
                        if argument.get('capture', argument.get('parameter')) != inner['source']:
                            continue
                        target_path = argument.get('target_path', [])
                        values = [dict(source, output_path=target_path + source.get('output_path', []))
                                  for source in argument['sources']] if target_path else argument['sources']
                        selected = _select_flows(values, inner.get('projection', []))
                        for outer in sources(selected, stack + (call.id,)):
                            path = value.get('output_path', []) + inner.get('output_path', []) + outer.get('output_path', [])
                            combined = dict(outer,
                                relation=_relation([v['relation'] for v in (value, inner, outer)]),
                                evidence=outer['evidence'] + inner['evidence'] + value['evidence'],
                                conditions=outer.get('conditions', []) + inner.get('conditions', []) + value.get('conditions', []),
                                call_context=outer['call_context'] + [call.id] + inner.get('call_context', []))
                            if path:
                                combined['output_path'] = path
                            else:
                                combined.pop('output_path', None)
                            found.append(combined)
            return compact(found)

        for iteration in range(32):
            updated = {key: compact(resolved[key] + sources(summary['returns'], ()))
                       for key, summary in functions.items()}
            if all({dependency_key(v) for v in updated[k]} ==
                   {dependency_key(v) for v in resolved[k]} for k in functions):
                resolved = updated
                status = 'bounded' if limited else 'converged'
                break
            resolved = updated
        paths = [v for v in resolved[entry_key] if v['source'] == parameter and v['kind'] == 'parameter']
        boundaries = copy.deepcopy(self.boundaries)
        if status != 'converged':
            boundaries.append({'reason': 'return_summary_limit', 'iterations': iteration + 1})
        return {'parameter': parameter, 'return_paths': paths,
                'status': 'flow_found' if paths else 'unknown',
                'summary_status': status, 'summary_iterations': iteration + 1,
                'boundaries': boundaries}



def _matches(actual, selector):
    return (actual.qualname == selector.qualname
            and (not selector.module or actual.module == selector.module)
            and (not selector.file_path or actual.file_path == os.path.abspath(selector.file_path))
            and (not selector.lineno or actual.lineno == selector.lineno))


def _scope_names(node):
    loaded, bound = set(), set()
    args = node.args
    bound.update(a.arg for a in args.posonlyargs + args.args + args.kwonlyargs)
    bound.update(a.arg for a in (args.vararg, args.kwarg) if a)
    def visit(item):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(item.name)
            return
        if isinstance(item, ast.Name):
            (loaded if isinstance(item.ctx, ast.Load) else bound).add(item.id)
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            bound.update(a.asname or a.name.split('.')[0] for a in item.names)
        for child in ast.iter_child_nodes(item):
            visit(child)
    body = [node.body] if isinstance(node, ast.Lambda) else node.body
    for statement in body:
        visit(statement)
    return loaded, bound


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _relation(relations):
    return 'derived' if 'derived' in relations else 'contained' if 'contained' in relations else 'direct'


def _select_flows(values, projection):
    if not projection:
        return values
    result = []
    for value in values:
        excluded = value.get('excluded_paths', [])
        if (projection and '*' not in projection
                and any(len(path) <= len(projection)
                        and path == projection[:len(path)] for path in excluded)):
            continue
        path = value.get('output_path', [])
        if path:
            if not all(a == b or a == '*' or b == '*' for a, b in zip(path, projection)):
                continue
            selected = dict(value, output_path=path[len(projection):])
            remaining_exclusions = [item[len(projection):] for item in excluded
                                    if len(item) > len(projection)
                                    and item[:len(projection)] == projection]
            if remaining_exclusions:
                selected['excluded_paths'] = remaining_exclusions
            else:
                selected.pop('excluded_paths', None)
            if len(projection) > len(path):
                selected['projection'] = value.get('projection', []) + projection[len(path):]
            result.append(selected)
        else:
            result.append(dict(value, relation='derived', projection=value.get('projection', []) + projection))
    return result


def _merge_env(environments):
    keys = set().union(*(e.keys() for e in environments))
    return {k: _unique([v for e in environments for v in e.get(k, [])]) for k in keys}


def _loop_key(value):
    return repr({k: v for k, v in value.items() if k not in ('evidence', 'conditions')})


def _loop_signature(env):
    return {k: frozenset(_loop_key(v) for v in values) for k, values in env.items()}


def _loop_env(env):
    # Keep one finite witness per abstract dependency. This is a may-flow
    # fixed point, not enumeration of all iteration counts or path conditions.
    result = {}
    for name, values in env.items():
        witnesses = {}
        for value in values:
            witnesses.setdefault(_loop_key(value), value)
        result[name] = list(witnesses.values())
    return result


## Analyze explicit Python source sets without executing analyzed code.
class FlowAnalyzer:
    ## Configure available sources; import roots do not enlarge the source set.
    #  @param source_files Explicit files, mutually exclusive with project_root.
    #  @param import_roots Roots used to derive module names.
    #  @param project_root Optional project directory scanned with FileScanner.
    #  @param return_summaries Opt-in exact callable summaries with provenance.
    #  @param parameter_shapes Opt-in trusted parameter shape contracts.
    def __init__(self, source_files=None, import_roots=None, project_root=None,
                 return_summaries=None, parameter_shapes=None):
        if (source_files is None) == (project_root is None):
            raise ValueError('Specify exactly one of source_files or project_root')
        self.files = set()
        self.return_summaries = copy.deepcopy(return_summaries or {})
        for contract in self.return_summaries.values():
            if not contract.get('provenance') or not isinstance(contract.get('parameters'), list):
                raise ValueError('Return summaries require parameters and provenance')
            for dependency in contract.get('returns', []):
                if (dependency.get('parameter') not in contract['parameters']
                        or dependency.get('relation') not in ('direct', 'derived', 'contained')):
                    raise ValueError('Invalid return dependency')
        self.parameter_shapes = copy.deepcopy(parameter_shapes or {})
        for callable_name, contract in self.parameter_shapes.items():
            parameters = contract.get('parameters') if isinstance(contract, dict) else None
            if (not isinstance(callable_name, str) or not callable_name
                    or not isinstance(contract, dict) or not contract.get('provenance')
                    or not isinstance(parameters, dict)
                    or any(not isinstance(name, str) or not name
                           or not isinstance(shape, str) or not shape
                           for name, shape in parameters.items())):
                raise ValueError('Parameter shape contracts require parameters and provenance')
        self.roots = [os.path.abspath(p) for p in (import_roots or ([project_root] if project_root else []))]
        self.add_files(FileScanner().scan(str(project_root)) if project_root else source_files)

    ## Add sources for the next analysis; existing snapshots remain unchanged.
    #  @param files Iterable of Python source paths.
    def add_files(self, files):
        self.files.update(os.path.abspath(p) for p in files if str(p).endswith(('.py', '.pyi')))

    def _index(self):
        self.definitions = []
        self.classes = []
        self.imports = {}
        self.module_bindings = {}
        self.texts = {}
        self.hashes = {}
        self.index_boundaries = []
        for path in sorted(self.files):
            try:
                with open(path, encoding='utf-8-sig') as stream:
                    source = stream.read()
                tree = ast.parse(source)
            except (OSError, UnicodeError, SyntaxError) as error:
                self.index_boundaries.append({'file_path': path, 'reason': 'source_unavailable', 'detail': str(error)})
                continue
            self.texts[path] = source
            self.hashes[path] = hashlib.sha256(source.encode('utf-8')).hexdigest()
            root = next((r for r in self.roots if os.path.commonpath([r, path]) == r), os.path.dirname(path))
            module = os.path.splitext(os.path.relpath(path, root))[0].replace(os.sep, '.')
            if module.endswith('.__init__'):
                module = module[:-9]
            aliases = {}
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        aliases[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                elif isinstance(node, ast.ImportFrom):
                    package = module if os.path.basename(path).startswith('__init__.') else module.rpartition('.')[0]
                    prefix = node.module or ''
                    if node.level:
                        parts = package.split('.') if package else []
                        prefix = '.'.join(parts[:len(parts) - node.level + 1] + ([prefix] if prefix else []))
                    for alias in node.names:
                        aliases[alias.asname or alias.name] = prefix + '.' + alias.name
            self.imports[module] = aliases
            self.module_bindings[module] = {
                n.id for statement in tree.body
                if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                for target in (statement.targets if isinstance(statement, ast.Assign) else [statement.target])
                for n in ast.walk(target) if isinstance(n, ast.Name)}
            def collect(body, prefix=''):
                for node in body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        name = prefix + node.name
                        if not isinstance(node, ast.ClassDef):
                            self.definitions.append((FunctionRef(module, name, path, node.lineno), node))
                        else:
                            self.classes.append((FunctionRef(module, name, path, node.lineno), node))
                        collect(node.body, name + '.')
                    else:
                        def collect_lambdas(item):
                            if isinstance(item, ast.Lambda):
                                name = prefix + '<lambda>@%s:%s' % (item.lineno, item.col_offset)
                                self.definitions.append((FunctionRef(module, name, path, item.lineno), item))
                                collect_lambdas(item.body)
                                return
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                return
                            for child in ast.iter_child_nodes(item):
                                collect_lambdas(child)
                        collect_lambdas(node)
            collect(tree.body)

    def _inherited_method(self, module, owner, method, seen=()):
        identity = (module, owner)
        if identity in seen:
            return None
        classes = [(r, n) for r, n in self.classes if r.module == module and r.qualname == owner]
        if len(classes) != 1:
            return None
        cls = classes[0][1]
        if cls.decorator_list or cls.keywords or len(cls.bases) != 1:
            return None
        if any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id == method
               for statement in cls.body if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               for n in ast.walk(statement)):
            return None
        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in
               (method, '__getattr__', '__getattribute__') for n in cls.body):
            return None
        name = ast.unparse(cls.bases[0])
        first, dot, rest = name.partition('.')
        if first in self.module_bindings.get(module, set()):
            return None
        alias = self.imports.get(module, {}).get(first)
        qualified = alias + dot + rest if alias else module + '.' + name
        bases = [(r, n) for r, n in self.classes if r.module + '.' + r.qualname == qualified]
        if len(bases) != 1 or bases[0][1].decorator_list or bases[0][1].keywords:
            return None
        ref, cls = bases[0]
        if any(isinstance(n, ast.FunctionDef) and n.name in ('__getattr__', '__getattribute__') for n in cls.body):
            return None
        matches = [d for d in self.definitions if d[0].module == ref.module and d[0].qualname == ref.qualname + '.' + method]
        if len(matches) == 1:
            return matches[0]
        return self._inherited_method(ref.module, ref.qualname, method, seen + (identity,))

    def _field_candidate(self, ref, field, method):
        owner = ref.qualname.rpartition('.')[0]
        classes = [(r, n) for r, n in self.classes if r.module == ref.module and r.qualname == owner]
        if len(classes) != 1 or classes[0][1].decorator_list:
            return None
        cls = classes[0][1]
        methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(n.name in ('__getattribute__', '__getattr__', field) for n in methods):
            return None
        writes = []
        for member in methods:
            for statement in ast.walk(member):
                if isinstance(statement, ast.Attribute) and statement.attr == field and isinstance(statement.ctx, (ast.Store, ast.Del)):
                    writes.append(statement)
        init = next((n for n in methods if n.name == '__init__' and not n.decorator_list), None)
        if len(writes) != 1 or init is None:
            return None
        assignment = next((n for n in init.body if isinstance(n, ast.Assign)
                           and len(n.targets) == 1 and n.targets[0] is writes[0]), None)
        args = init.args.posonlyargs + init.args.args
        if (assignment is None or not args or not isinstance(writes[0].value, ast.Name)
                or writes[0].value.id != args[0].arg or not isinstance(assignment.value, ast.Call)):
            return None
        name = ast.unparse(assignment.value.func)
        first, dot, rest = name.partition('.')
        if first in self.module_bindings.get(ref.module, set()) or first in _scope_names(init)[1]:
            return None
        alias = self.imports.get(ref.module, {}).get(first)
        qualified = alias + (dot + rest if dot else '') if alias else ref.module + '.' + name
        targets = [(r, n) for r, n in self.classes if r.module + '.' + r.qualname == qualified]
        if len(targets) != 1 or targets[0][1].decorator_list:
            return None
        target_class = targets[0]
        if any(isinstance(n, ast.FunctionDef) and n.name in ('__getattribute__', '__getattr__', '__new__') for n in target_class[1].body):
            return None
        target = [(r, n) for r, n in self.definitions
                  if r.module == target_class[0].module and r.qualname == target_class[0].qualname + '.' + method]
        return (target[0], assignment) if len(target) == 1 and not target[0][1].decorator_list else None

    def _descriptor_kind(self, target):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or not isinstance(decorators[0], ast.Name):
            return None
        name = decorators[0].id
        if name not in ('staticmethod', 'classmethod'):
            return None
        if (name in self.imports.get(ref.module, {})
                or name in self.module_bindings.get(ref.module, set())
                or any(candidate.module == ref.module and candidate.qualname == name
                       for candidate, _ in self.definitions)):
            return None
        owner = ref.qualname.rpartition('.')[0]
        cls = next((node for candidate, node in self.classes
                    if candidate.module == ref.module and candidate.qualname == owner), None)
        if cls is None:
            return None
        for statement in cls.body:
            if statement is node:
                break
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import,
                                      ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef)):
                names = {item.id for item in ast.walk(statement)
                         if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)}
                if name in names or getattr(statement, 'name', None) == name:
                    return None
        return name

    def _decorated_target(self, target):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or isinstance(decorators[0], ast.Call):
            return None
        decorator = self._resolve(ref, ast.unparse(decorators[0]))
        if decorator is None or getattr(decorator[1], 'decorator_list', []):
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
        matches = [candidate for candidate in self.definitions
                   if candidate[0].module == decorator[0].module
                   and candidate[0].qualname == qualname]
        if len(matches) != 1 or self._captures(*matches[0]):
            return None
        return matches[0]

    def _resolve(self, caller, name):
        # Nearest lexical definition wins before module imports. Class scopes
        # are deliberately excluded from implicit lexical method resolution.
        scope = caller.qualname
        function_scopes = {r.qualname for r, _ in self.definitions if r.module == caller.module}
        while scope:
            if scope in function_scopes:
                matches = [(r, n) for r, n in self.definitions
                           if r.module == caller.module and r.qualname == scope + '.' + name]
                if matches:
                    return matches[0] if len(matches) == 1 else None
            scope = scope.rpartition('.')[0]
        names = [caller.module + '.' + name]
        parent = caller.qualname.rpartition('.')[0]
        if parent:
            names.insert(0, caller.module + '.' + parent + '.' + name)
        alias, dot, rest = name.partition('.')
        imported = self.imports.get(caller.module, {}).get(alias)
        if imported:
            names = [imported + (dot + rest if dot else '')]
        for _ in range(20):
            matches = [(ref, node) for ref, node in self.definitions if ref.module + '.' + ref.qualname in names]
            if len(matches) == 1:
                return matches[0]
            expanded = []
            for name in names:
                mod, _, symbol = name.rpartition('.')
                value = self.imports.get(mod, {}).get(symbol)
                if value:
                    expanded.append(value)
            if not expanded:
                break
            names = expanded
        return None

    def _captures(self, ref, node):
        loaded, bound = _scope_names(node)
        declared_nonlocal = set()

        def collect_nonlocal(item):
            if item is not node and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                       ast.ClassDef, ast.Lambda)):
                return
            if isinstance(item, ast.Nonlocal):
                declared_nonlocal.update(item.names)
            for child in ast.iter_child_nodes(item):
                collect_nonlocal(child)

        collect_nonlocal(node)
        outer = set()
        parent = ref.qualname.rpartition('.')[0]
        while parent:
            definition = next((n for r, n in self.definitions
                               if r.module == ref.module and r.qualname == parent), None)
            if definition:
                outer.update(_scope_names(definition)[1])
            parent = parent.rpartition('.')[0]
        return sorted(((loaded | declared_nonlocal) - (bound - declared_nonlocal)) & outer)

    ## Analyze reachable summaries up to a bounded number of call edges.
    #  @param entry FunctionRef identifying the starting definition.
    #  @param max_depth Number of call-edge layers, at least one.
    #  @param max_functions Maximum distinct function summaries.
    #  @param max_call_contexts Maximum traversed call edges.
    #  @return FlowAnalysis snapshot; cutoffs are explicit boundaries.
    def analyze(self, entry, max_depth=1, max_functions=500, max_call_contexts=2000):
        if min(max_depth, max_functions, max_call_contexts) < 1:
            raise ValueError('Depth and budgets must be positive')
        self._index()
        matches = [(r, n) for r, n in self.definitions if _matches(r, entry)]
        if len(matches) != 1:
            raise ValueError('Entry must identify exactly one available definition')
        result = FlowAnalysis(matches[0][0], {'source_files': sorted(self.files), 'sha256': dict(self.hashes),
                              'import_roots': list(self.roots), 'max_depth': max_depth,
                              'return_summaries': copy.deepcopy(self.return_summaries),
                              'parameter_shapes': copy.deepcopy(self.parameter_shapes),
                              'coverage': 'explicit value dependencies and limited local container effects; no general heap or path feasibility proof'})
        result.boundaries.extend(self.index_boundaries)
        self._walk(result, matches[0], max_depth, (), max_functions, max_call_contexts)
        result.boundaries = _unique(result.boundaries)
        return result

    def _walk(self, result, definition, depth, ancestors, max_functions, max_calls):
        ref, node = definition
        if ref in ancestors:
            result.boundaries.append({'function': asdict(ref), 'reason': 'recursion'})
            return
        existing = any(f['function'] == asdict(ref) for f in result.functions)
        if existing:
            calls = [c for c in result.calls if c.caller == ref]
        else:
            if len(result.functions) >= max_functions or len(result.calls) >= max_calls:
                result.boundaries.append({'function': asdict(ref), 'reason': 'budget_exceeded'})
                return
            summary = _Summary(self, result, ref, node, max_calls - len(result.calls))
            summary.run()
            calls = summary.calls
        for call in calls:
            if call.target is None:
                if call.target_status not in ('python_protocol', 'local_container_protocol'):
                    result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                              'reason': call.target_status})
            elif depth > 1:
                result.boundaries = [b for b in result.boundaries if not (b.get('call_id') == call.id and b['reason'] == 'depth_limit')]
                target = next(d for d in self.definitions if d[0] == call.target)
                self._walk(result, target, depth - 1, ancestors + (ref,), max_functions, max_calls)
            else:
                result.boundaries.append({'call_id': call.id, 'reason': 'depth_limit'})

    ## Expand the selected call target, retaining existing function summaries.
    #  @param result Previous snapshot from this source set.
    #  @param call_id Exact call-site identifier.
    #  @param additional_depth Layers below the selected target.
    #  @return New snapshot, leaving result unchanged.
    def expand(self, result, call_id, additional_depth=1):
        if additional_depth < 1:
            raise ValueError('additional_depth must be positive')
        self._index()
        if (self.hashes != result.inputs['sha256'] or sorted(self.files) != result.inputs['source_files']
                or self.return_summaries != result.inputs.get('return_summaries', {})
                or self.parameter_shapes != result.inputs.get('parameter_shapes', {})):
            raise ValueError('Sources changed; call analyze again before expand')
        call = next(c for c in result.calls if c.id == call_id)
        updated = copy.deepcopy(result)
        if call.target is not None:
            updated.boundaries = [b for b in updated.boundaries if not (b.get('call_id') == call_id and b['reason'] == 'depth_limit')]
            self._walk(updated, next(d for d in self.definitions if d[0] == call.target), additional_depth, (call.caller,), 500, 2000)
        updated.boundaries = _unique(updated.boundaries)
        return updated


class _Summary:
    def __init__(self, analyzer, result, ref, node, remaining):
        self.analyzer, self.result, self.ref, self.node = analyzer, result, ref, node
        self.calls = []
        self.returns = []
        self.conditions = []
        self.remaining = remaining
        self.evaluated_calls = set()
        self.loops = []
        self.yields = []
        self.source_lines = [line.encode('utf-8') for line in
                             self.analyzer.texts[ref.file_path].split('\n')]
        self.evidence_cache = {}

    def evidence(self, node):
        return self.evidence_at(self.ref, node)

    def evidence_at(self, ref, node):
        key = (ref.file_path, node.lineno, node.col_offset,
               node.end_lineno, node.end_col_offset)
        if key in self.evidence_cache:
            return self.evidence_cache[key]
        _, first, start, last, end = key
        source_lines = (self.source_lines if ref.file_path == self.ref.file_path else
                        [line.encode('utf-8') for line in
                         self.analyzer.texts[ref.file_path].split('\n')])
        if first == last:
            snippet = source_lines[first - 1][start:end]
        else:
            snippet = b'\n'.join([source_lines[first - 1][start:]] +
                                  source_lines[first:last - 1] +
                                  [source_lines[last - 1][:end]])
        value = {'file_path': ref.file_path, 'lineno': node.lineno,
                'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
                'end_col_offset': node.end_col_offset,
                'source_text': snippet.decode('utf-8')}
        self.evidence_cache[key] = value
        return value

    def marked(self, values, node, relation=None):
        result = [dict(v, relation=relation or v['relation'], evidence=v['evidence'] + [self.evidence(node)],
                       conditions=v.get('conditions', []) + list(self.conditions)) for v in values]
        if relation and relation != 'direct':
            for value in result:
                value.pop('python_shape', None)
        return result

    def callable_value(self, target, node, defaults=None):
        return {'kind': 'callable', 'source': target.qualname, 'module': target.module,
                'defaults': defaults or {}, 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}

    def bind_call_arguments(self, node, params, positional, call_id):
        records = []
        position = 0
        uncertain_position = False

        def positional_record(argument, slot, expanded=False):
            nonlocal position
            parameter = None
            target_path = []
            if not uncertain_position and position < len(positional):
                parameter = positional[position].arg
            elif params.vararg and (not uncertain_position or position >= len(positional)):
                parameter = params.vararg.arg
                target_path = [position - len(positional)] if not uncertain_position else ['*']
            status = 'exact' if parameter else 'unresolved'
            records.append({'argument': slot, 'node': argument, 'parameter': parameter,
                            'target_path': target_path, 'status': status,
                            'binding_kind': 'starred' if expanded else 'explicit'})
            position += 1

        for source_position, argument in enumerate(node.args):
            if isinstance(argument, ast.Starred):
                if isinstance(argument.value, (ast.Tuple, ast.List)):
                    for star_index, element in enumerate(argument.value.elts):
                        positional_record(element, {'position': position,
                            'expanded_from': source_position, 'star_index': star_index}, True)
                else:
                    parameter = (params.vararg.arg if params.vararg and position >= len(positional)
                                 else None)
                    records.append({'argument': {'position': source_position, 'starred': True},
                        'node': argument.value, 'parameter': parameter,
                        'target_path': ['*'] if parameter else [],
                        'status': 'exact' if parameter else 'unresolved',
                        'binding_kind': 'dynamic_starred'})
                    uncertain_position = True
                    self.result.boundaries.append({'call_id': call_id,
                                                   'reason': 'dynamic_argument_expansion'})
                continue
            positional_record(argument, {'position': position})

        keyword_arguments = []
        for keyword in node.keywords:
            if (keyword.arg is None and isinstance(keyword.value, ast.Dict)
                    and all(isinstance(key, ast.Constant) and isinstance(key.value, str)
                            for key in keyword.value.keys)
                    and len({key.value for key in keyword.value.keys}) == len(keyword.value.keys)):
                keyword_arguments.extend((key.value, value, True)
                                         for key, value in zip(keyword.value.keys, keyword.value.values))
            else:
                keyword_arguments.append((keyword.arg, keyword.value, False))
        allowed = {argument.arg for argument in params.args if argument in positional}
        allowed.update(argument.arg for argument in params.kwonlyargs)
        for key, argument, expanded in keyword_arguments:
            if key is None:
                parameter = params.kwarg.arg if params.kwarg and not allowed else None
                target_path = ['*'] if parameter else []
                self.result.boundaries.append({'call_id': call_id,
                                               'reason': 'dynamic_argument_expansion'})
            else:
                parameter = key if key in allowed else (params.kwarg.arg if params.kwarg else None)
                target_path = [key] if params.kwarg and parameter == params.kwarg.arg else []
            records.append({'argument': {'keyword': key}, 'node': argument,
                'parameter': parameter, 'target_path': target_path,
                'status': 'exact' if parameter else 'unresolved',
                'binding_kind': 'expanded_keyword' if expanded else 'explicit'})
        if any(record['status'] == 'unresolved'
               and record['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
               for record in records):
            self.result.boundaries.append({'call_id': call_id,
                                           'reason': 'invalid_argument_binding'})
        return records

    def expression(self, node, env):
        if node is None:
            return []
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            target = self.analyzer._resolve(self.ref, node.id)
            if target:
                return [self.callable_value(target[0], node)]
            imported = self.analyzer.imports.get(self.ref.module, {}).get(node.id)
            if imported:
                return [{'kind': 'import', 'source': imported, 'relation': 'direct',
                         'evidence': [self.evidence(node)],
                         'conditions': list(self.conditions)}]
            return []
        if isinstance(node, ast.Constant):
            return []
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            values = self.expression(node.value, env)
            if isinstance(node, ast.YieldFrom):
                values = self.project(values, '*', env)
            values = self.materialize(values, env)
            self.yields.extend(self.marked([
                dict(value, output_path=['*'] + value.get('output_path', []))
                for value in values], node, 'contained'))
            return []
        if isinstance(node, ast.Lambda):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):],
                                node.args.defaults))
            defaults += [(argument, default) for argument, default in
                         zip(node.args.kwonlyargs, node.args.kw_defaults) if default is not None]
            values = {argument.arg: self.expression(default, env)
                      for argument, default in defaults}
            target = FunctionRef(self.ref.module,
                self.ref.qualname + '.<lambda>@%s:%s' % (node.lineno, node.col_offset),
                self.ref.file_path, node.lineno)
            return [self.callable_value(target, node, values)]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            key = '$heap:%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
            items = []
            keys = []
            elements = list(zip(node.keys, node.values)) if isinstance(node, ast.Dict) else list(enumerate(node.elts))
            for index, element in elements:
                if isinstance(node, ast.Dict):
                    if index is None:
                        mapping = self.expression(element, env)
                        copied = False
                        for reference in mapping:
                            if (reference.get('kind') == 'container'
                                    and reference.get('container_shape') == 'dict'):
                                items.extend(copy.deepcopy(env.get(reference['source'], [])))
                                keys.extend(copy.deepcopy(env.get(reference['source'] + '$keys', [])))
                                copied = True
                        if not copied:
                            values = self.marked(self.materialize(mapping, env), element, 'contained')
                            items.extend(dict(v, output_path=['*'] + v.get('output_path', []))
                                         for v in values)
                            keys.append({'kind': 'key', 'source': '*', 'key': '*'})
                        continue
                    slot = index.value if isinstance(index, ast.Constant) and isinstance(index.value, (str, int)) else '*'
                    key_values = self.marked(self.materialize(self.expression(index, env), env),
                                             index, 'contained')
                else:
                    slot = index if not isinstance(node, ast.Set) else '*'
                keys.append({'kind': 'key', 'source': repr(slot), 'key': slot})
                if isinstance(node, ast.Dict) and slot != '*':
                    updated = []
                    for value in items:
                        path = value.get('output_path', [None])
                        if path[0] == slot:
                            continue
                        if path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[slot]]))
                        updated.append(value)
                    items = updated
                    for marker in keys[:-1]:
                        if marker['key'] == '*':
                            marker.setdefault('excluded_keys', []).append(slot)
                if isinstance(node, ast.Dict):
                    items.extend(dict(v, output_path=[slot] + v.get('output_path', []),
                                      container_role='key') for v in key_values)
                values = self.expression(element, env)
                items.extend(dict(v, output_path=[slot] + v.get('output_path', [])) for v in values)
            env[key] = items
            env[key + '$keys'] = keys
            return [{'kind': 'container', 'source': key, 'container_shape': type(node).__name__.lower(),
                     'relation': 'direct', 'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
        if isinstance(node, ast.Subscript):
            values = self.expression(node.value, env)
            self.expression(node.slice, env)
            if isinstance(node.slice, (ast.Slice, ast.UnaryOp)):
                selected = []
                for value in values:
                    keys = env.get(value['source'] + '$keys', [])
                    slots = [k['key'] for k in keys]
                    if value.get('container_shape') not in ('list', 'tuple') or slots != list(range(len(slots))):
                        selected.extend(self.project([value], '*', env))
                        continue
                    try:
                        if isinstance(node.slice, ast.Slice):
                            bounds = [ast.literal_eval(n) if n is not None else None
                                      for n in (node.slice.lower, node.slice.upper, node.slice.step)]
                            indices = list(range(len(slots)))[slice(*bounds)]
                            for position, index in enumerate(indices):
                                selected.extend(dict(v, output_path=[position] + v.get('output_path', []))
                                                for v in self.project([value], index, env))
                        else:
                            index = ast.literal_eval(node.slice)
                            index = list(range(len(slots)))[index]
                            selected.extend(self.project([value], index, env))
                    except IndexError:
                        pass
                    except (ValueError, TypeError):
                        selected.extend(self.project([value], '*', env))
                return self.marked(selected, node)
            index = node.slice.value if isinstance(node.slice, ast.Constant) else '*'
            return self.marked(self.project(values, index, env), node)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)) and not any(g.is_async for g in node.generators):
            local = copy.deepcopy(env)
            for generator in node.generators:
                iterable = self.expression(generator.iter, local)
                if iterable and all(v['kind'] == 'container' and
                                    local.get(v['source'] + '$keys') == [] for v in iterable):
                    return []
                values = self.project(iterable, '*', local)
                self.assign_target(generator.target, values, local, generator.target)
                for condition in generator.ifs:
                    self.expression(condition, local)
                    if isinstance(condition, ast.Constant) and not condition.value:
                        return []
                    self.refine_guard(condition, local)
            elements = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            values = [v for element in elements for v in self.materialize(self.expression(element, local), local)]
            for key in set(env) | set(local):
                if key.startswith('$heap:'):
                    env[key] = _unique(env.get(key, []) + local.get(key, []))
            return self.marked([dict(v, output_path=['*'] + v.get('output_path', [])) for v in values], node, 'contained')
        if isinstance(node, ast.IfExp):
            self.expression(node.test, env)
            before = list(self.conditions)
            positive, negative = copy.deepcopy(env), copy.deepcopy(env)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            self.refine_guard(node.test, positive)
            left = self.marked(self.expression(node.body, positive), node.body)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            right = self.marked(self.expression(node.orelse, negative), node.orelse)
            env.clear()
            env.update(_merge_env([positive, negative]))
            self.conditions = before
            return left + right
        if isinstance(node, ast.BoolOp):
            current = copy.deepcopy(env)
            before = list(self.conditions)
            values = []
            exits = []
            for operand in node.values:
                values.extend(self.marked(self.materialize(self.expression(operand, current), current), operand))
                exits.append(copy.deepcopy(current))
                self.conditions = self.conditions + [{'test': self.evidence(operand), 'branch': isinstance(node.op, ast.And)}]
                if isinstance(node.op, ast.And):
                    self.refine_guard(operand, current)
            env.clear()
            env.update(_merge_env(exits))
            self.conditions = before
            return values
        if isinstance(node, ast.Call):
            location = _call_span(node)
            if location not in self.evaluated_calls and self.remaining <= 0:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'budget_exceeded', 'evidence': self.evidence(node)})
                return []
            if location not in self.evaluated_calls:
                self.remaining -= 1
                self.evaluated_calls.add(location)
            name = ast.unparse(node.func)
            binding = env.get(name.split('.')[0])
            target = self.analyzer._resolve(self.ref, name) if binding is None else None
            canonical = self.ref.module + '.' + name
            receiver_values = (self.expression(node.func.value, env)
                                if isinstance(node.func, ast.Attribute) else [])
            receiver_sources = self.materialize(receiver_values, env)
            bound_receiver = False
            dispatch_kind = None
            field_evidence = None
            owner = self.ref.qualname.rpartition('.')[0]
            function_names = {r.qualname for r, _ in self.analyzer.definitions if r.module == self.ref.module}
            if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and owner and owner not in function_names
                    and (self.node.args.posonlyargs or self.node.args.args)
                    and receiver_sources and all(v['kind'] == 'parameter' and v['relation'] == 'direct'
                        and v['source'] == (self.node.args.posonlyargs + self.node.args.args)[0].arg
                        for v in receiver_sources)):
                matches = [d for d in self.analyzer.definitions if d[0].module == self.ref.module
                           and d[0].qualname == owner + '.' + node.func.attr]
                if not matches:
                    inherited = self.analyzer._inherited_method(self.ref.module, owner, node.func.attr)
                    matches = [inherited] if inherited else []
                if len(matches) == 1 and not getattr(self.node, 'decorator_list', []):
                    target = matches[0]
                    bound_receiver = True
                    dispatch_kind = 'instance_method'
            if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name)
                    and not getattr(self.node, 'decorator_list', [])):
                args = self.node.args.posonlyargs + self.node.args.args
                bases = env.get(node.func.value.value.id, [])
                if args and bases and all(v['kind'] == 'parameter' and v['source'] == args[0].arg
                                         and v['relation'] == 'direct' for v in bases):
                    candidate = self.analyzer._field_candidate(self.ref, node.func.value.attr, node.func.attr)
                    if candidate:
                        target, field_evidence = candidate
                        bound_receiver = True
                        dispatch_kind = 'field_method'
            is_zero_super = (isinstance(node.func, ast.Attribute)
                             and isinstance(node.func.value, ast.Call)
                             and isinstance(node.func.value.func, ast.Name)
                             and node.func.value.func.id == 'super'
                             and not node.func.value.args and not node.func.value.keywords)
            if is_zero_super and owner and not getattr(self.node, 'decorator_list', []):
                inherited = self.analyzer._inherited_method(
                    self.ref.module, owner, node.func.attr)
                args = self.node.args.posonlyargs + self.node.args.args
                if inherited and args:
                    target = inherited
                    bound_receiver = True
                    dispatch_kind = 'super_method'
                    receiver_values = env.get(args[0].arg, [])
                    receiver_sources = self.materialize(receiver_values, env)
            if binding and all(v['kind'] == 'import' for v in binding):
                imported = {v['source'] for v in binding}
                if len(imported) == 1:
                    canonical = next(iter(imported)) + ('.' + name.split('.', 1)[1] if '.' in name else '')
                    matches = [d for d in self.analyzer.definitions
                               if d[0].module + '.' + d[0].qualname == canonical]
                    target = matches[0] if len(matches) == 1 else None
            elif binding is None:
                alias, dot, rest = name.partition('.')
                imported = self.analyzer.imports.get(self.ref.module, {}).get(alias)
                if imported:
                    canonical = imported + (dot + rest if dot else '')
            if binding and all(v['kind'] == 'callable' for v in binding):
                targets = {(v.get('module', self.ref.module), v['source']) for v in binding}
                if len(targets) == 1:
                    module, qualname = next(iter(targets))
                    target = next((d for d in self.analyzer.definitions
                                   if d[0].module == module and d[0].qualname == qualname), None)
            descriptor_kind = self.analyzer._descriptor_kind(target) if target else None
            if target and getattr(target[1], 'decorator_list', []) and descriptor_kind is None:
                replacement = self.analyzer._decorated_target(target)
                if replacement:
                    target = replacement
                    dispatch_kind = 'decorator_replacement'
                else:
                    target = None
            elif descriptor_kind == 'staticmethod':
                dispatch_kind = 'staticmethod'
            elif descriptor_kind == 'classmethod':
                bound_receiver = True
                dispatch_kind = 'classmethod'
                receiver_values = []
                receiver_sources = []
            call_id = _call_key(self.ref.file_path, node)
            call = FlowCall(call_id, self.ref, name, node.lineno, node.col_offset,
                            node.end_lineno, node.end_col_offset, target[0] if target else None)
            call.receiver_sources = receiver_sources
            call.target_status = (dispatch_kind if target and dispatch_kind else
                                  'lexical_method_candidate' if target and bound_receiver else
                                  'resolved' if target else 'receiver_unresolved' if isinstance(node.func, ast.Attribute)
                                  else 'builtin_boundary' if binding is None and hasattr(builtins, name)
                                  else 'definition_unavailable')
            if field_evidence:
                call.target_status = 'constructor_field_candidate'
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                    'reason': 'constructor_field_assumption', 'evidence': self.evidence(field_evidence)})
            string_arity = {'split': (0, 2), 'rsplit': (0, 2),
                            'strip': (0, 1), 'lstrip': (0, 1), 'rstrip': (0, 1),
                            'startswith': (1, 3), 'endswith': (1, 3),
                            'partition': (1, 1), 'rpartition': (1, 1)}
            method = node.func.attr if isinstance(node.func, ast.Attribute) else ''
            limits = string_arity.get(method)
            string_protocol = (target is None and isinstance(node.func, ast.Attribute)
                               and isinstance(node.func.value, ast.Name)
                               and limits is not None and limits[0] <= len(node.args) <= limits[1]
                               and not node.keywords
                               and not any(isinstance(argument, ast.Starred)
                                           for argument in node.args)
                               and receiver_sources
                               and all(v.get('python_shape') == 'str'
                                       for v in receiver_sources))
            if string_protocol:
                call.target_status = 'python_protocol'
                call.argument_sources.append({'argument': {'receiver': True}, 'parameter': '$receiver',
                                              'sources': receiver_sources})
                if method in ('partition', 'rpartition'):
                    call.return_dependencies = [
                        {'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                         'output_path': [index],
                         'evidence': [{'provenance':
                            'Guarded or trusted str partition result dependency'}],
                         'conditions': list(self.conditions)} for index in range(3)]
                else:
                    call.return_dependencies = [{
                        'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                        'evidence': [{'provenance':
                            'Guarded str receiver dependency; builtin method implementation assumed'}],
                        'conditions': list(self.conditions)}]
                    self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                                   'reason': 'string_subclass_override_possible'})
                if method in ('partition', 'rpartition'):
                    self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                                   'reason': 'string_subclass_override_possible'})
            literal_join = (target is None and isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)
                            and node.func.attr == 'join' and len(node.args) == 1 and not node.keywords
                            and not isinstance(node.args[0], ast.Starred))
            if target and bound_receiver and dispatch_kind in ('instance_method', 'field_method'):
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                               'reason': 'dynamic_method_override_possible'})
            capture_values = {}
            if target:
                for capture in self.analyzer._captures(*target):
                    capture_values[capture] = copy.deepcopy(env.get(capture, []))
                    call.capture_bindings.append({'capture': capture,
                        'sources': capture_values[capture]})
            params = target[1].args if target else None
            contract = self.analyzer.return_summaries.get(canonical) if target is None else None
            if (contract is None and target is None and binding is None
                    and name in ('str', 'repr', 'bool', 'len', 'list', 'tuple', 'set')
                    and canonical == self.ref.module + '.' + name
                    and len(node.args) == 1 and not node.keywords
                    and not isinstance(node.args[0], ast.Starred)):
                contract = {'parameters': ['object'], 'returns': [
                    {'parameter': 'object', 'relation': 'derived'}],
                    'provenance': 'Python builtin result dependency (not owner preservation)'}
                call.target_status = 'python_protocol'
            if (contract is None and target is None and binding is None and name == 'next'
                    and canonical == self.ref.module + '.next'
                    and len(node.args) == 1 and not node.keywords
                    and not isinstance(node.args[0], ast.Starred)):
                contract = {'parameters': ['iterator'], 'returns': [
                    {'parameter': 'iterator', 'projection': ['*'], 'relation': 'direct'}],
                    'provenance': 'Python next returns an element produced by its iterator'}
                call.target_status = 'python_protocol'
            if contract and (binding is None or all(v['kind'] == 'import' for v in binding)):
                params = ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in contract['parameters']],
                                       vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
                call.return_dependencies = [
                    {'kind': 'parameter', 'source': d['parameter'], 'relation': d['relation'],
                     'projection': d.get('projection', []),
                     'evidence': [{'provenance': contract['provenance'], 'callable': canonical}], 'conditions': []}
                    for d in contract.get('returns', [])]
            positional = params.posonlyargs + params.args if params else []
            if bound_receiver and target and positional:
                call.argument_sources.append({'argument': {'receiver': True}, 'parameter': positional[0].arg,
                                              'sources': receiver_sources})
                positional = positional[1:]
            records = self.bind_call_arguments(node, params, positional, call_id) if params else [
                {'argument': {'position': i}, 'node': arg.value if isinstance(arg, ast.Starred) else arg,
                 'parameter': None, 'target_path': [], 'status': 'unresolved',
                 'binding_kind': 'dynamic_starred' if isinstance(arg, ast.Starred) else 'explicit'}
                for i, arg in enumerate(node.args)] + [
                {'argument': {'keyword': kw.arg}, 'node': kw.value, 'parameter': None,
                 'target_path': [], 'status': 'unresolved', 'binding_kind': 'explicit'}
                for kw in node.keywords]
            invalid_binding = bool(params) and any(
                record['status'] == 'unresolved'
                and record['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
                for record in records)
            actual_values = {}
            for record in records:
                slot, arg = record['argument'], record['node']
                parameter, target_path = record['parameter'], record['target_path']
                binding_record = {'argument': slot, 'parameter': parameter,
                                  'status': record['status']}
                if target_path:
                    binding_record['target_path'] = target_path
                if record['binding_kind'] != 'explicit':
                    binding_record['binding_kind'] = record['binding_kind']
                call.parameter_bindings.append(binding_record)
                raw_values = self.expression(arg, env)
                actual_values[parameter] = _unique(actual_values.get(parameter, []) + raw_values)
                values = self.marked(self.materialize(raw_values, env), arg)
                argument_record = {'argument': slot, 'parameter': parameter, 'sources': values}
                if target_path:
                    argument_record['target_path'] = target_path
                call.argument_sources.append(argument_record)
                for value in values:
                    call.argument_flows.append(dict(value, target_parameter=parameter,
                                                    target_path=target_path, argument=slot,
                                                    status='flow_found'))
                    if value['kind'] == 'parameter':
                        call.parameter_flows.append(dict(value, source_parameter=value['source'],
                                                         target_parameter=parameter,
                                                         target_path=target_path,
                                                         argument=slot, status='flow_found'))
            if literal_join:
                call.target_status = 'python_protocol'
                call.argument_sources[0]['parameter'] = 'iterable'
                call.parameter_bindings[0].update(parameter='iterable', status='exact')
                for value in call.argument_flows + call.parameter_flows:
                    value['target_parameter'] = 'iterable'
                call.return_dependencies = [{'kind': 'parameter', 'source': 'iterable', 'projection': ['*'],
                    'relation': 'derived', 'evidence': [{'provenance': 'Python str.join iterable elements'}],
                    'conditions': list(self.conditions)}]
            if params:
                supplied = {b['parameter'] for b in call.parameter_bindings if b['status'] == 'exact'}
                defaults = list(zip(positional[len(positional) - len(params.defaults):], params.defaults))
                defaults += [(a, d) for a, d in zip(params.kwonlyargs, params.kw_defaults) if d is not None]
                for param, default in defaults:
                    unknown_keywords = any(keyword.arg is None and not isinstance(keyword.value, ast.Dict)
                                           for keyword in node.keywords)
                    unknown_positions = any(isinstance(argument, ast.Starred)
                                            and not isinstance(argument.value, (ast.Tuple, ast.List))
                                            for argument in node.args)
                    possibly_expanded = unknown_keywords or (unknown_positions and param in positional)
                    if param.arg not in supplied and not possibly_expanded:
                        call.parameter_bindings.append({'argument': None, 'parameter': param.arg,
                                                        'binding_kind': 'default', 'status': 'exact',
                                                        'source_text': ast.unparse(default)})
                        if binding and all(v['kind'] == 'callable' for v in binding):
                            call.argument_sources.append({'argument': None, 'parameter': param.arg,
                                'sources': _unique([v for b in binding for v in b.get('defaults', {}).get(param.arg, [])])})
            if target and not invalid_binding:
                self.apply_effects(target, actual_values, capture_values, call, env, node)
            container_result = self.container_call(node, receiver_values, call, env)
            self.calls.append(call)
            if invalid_binding:
                return []
            if container_result is not None:
                return container_result
            return [{'kind': 'call_result', 'source': call_id, 'relation': 'direct',
                     'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_expression', 'evidence': self.evidence(node)})
            return []
        values = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                values.extend(self.materialize(self.expression(child, env), env))
        relation = 'contained' if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) else 'derived'
        return self.marked(values, node, relation)

    def materialize(self, values, env, visited=()):
        result = []
        for value in values:
            if value['kind'] != 'container':
                result.append(value)
                continue
            if value['source'] in visited:
                continue
            for item in self.materialize(env.get(value['source'], []), env, visited + (value['source'],)):
                prefix = value.get('output_path', [])
                materialized = dict(item, relation='contained',
                    output_path=prefix + item.get('output_path', []),
                    evidence=item['evidence'] + value['evidence'])
                if item.get('excluded_paths'):
                    materialized['excluded_paths'] = [prefix + path
                                                      for path in item['excluded_paths']]
                result.append(materialized)
        return result

    def project(self, values, index, env):
        result = []
        for value in values:
            if value['kind'] == 'container':
                content = [item for item in env.get(value['source'], [])
                           if item.get('container_role') != 'key']
                result.extend(_select_flows(content, [index]))
            else:
                result.extend(_select_flows([value], [index]))
        return result

    def container_call(self, node, receiver, call, env):
        if not isinstance(node.func, ast.Attribute) or not receiver or not all(v['kind'] == 'container' for v in receiver):
            return None
        shapes = {v['container_shape'] for v in receiver}
        method = node.func.attr
        valid = ((method == 'append' and shapes == {'list'} and len(node.args) == 1)
                 or (method == 'clear' and shapes <= {'list', 'set', 'dict'} and not node.args)
                 or (method == 'get' and shapes == {'dict'} and len(node.args) in (1, 2))
                 or (method == 'pop' and shapes == {'list'} and len(node.args) in (0, 1)))
        if not valid or node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
            self.result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                           'reason': 'container_effect_unknown'})
            return None
        call.target_status = 'local_container_protocol'
        parameters = (('key', 'default') if method == 'get' else
                      ('index',) if method == 'pop' else ('object',))
        for index, argument in enumerate(call.argument_sources):
            argument['parameter'] = parameters[index]
            call.parameter_bindings[index].update(parameter=parameters[index], status='exact')
        for flow in call.argument_flows + call.parameter_flows:
            slot = flow['argument']
            if 'position' in slot:
                flow['target_parameter'] = parameters[slot['position']]
        if method == 'get':
            index = node.args[0].value if isinstance(node.args[0], ast.Constant) else '*'
            known = all(any(k['key'] == index for k in env.get(v['source'] + '$keys', []))
                        and not any(k['key'] == '*' and index not in k.get('excluded_keys', [])
                                    for k in env.get(v['source'] + '$keys', []))
                        for v in receiver) and index != '*'
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': self.materialize(receiver, env)})
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if len(node.args) == 2 and not known:
                call.return_dependencies.append({'kind': 'parameter', 'source': 'default',
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)})
            return None  # Preserve the call-result endpoint as well as its dependencies.
        if method == 'pop':
            requested = -1
            if node.args:
                try:
                    requested = ast.literal_eval(node.args[0])
                except (ValueError, TypeError):
                    requested = '*'
                if not isinstance(requested, int):
                    requested = '*'
            index = requested
            valid_index = True
            if requested != '*' and len({value['source'] for value in receiver}) == 1:
                reference = receiver[0]
                keys = [key['key'] for key in env.get(reference['source'] + '$keys', [])]
                if keys == list(range(len(keys))):
                    try:
                        index = list(range(len(keys)))[requested]
                    except IndexError:
                        valid_index = False
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': copy.deepcopy(self.materialize(receiver, env))})
            if not valid_index:
                return []
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if index != '*' and len({v['source'] for v in receiver}) == 1:
                for ref in receiver:
                    keys = [key['key'] for key in env.get(ref['source'] + '$keys', [])]
                    remaining = []
                    for value in env.get(ref['source'], []):
                        path = value.get('output_path', [])
                        if path and path[0] == index:
                            continue
                        if path and isinstance(path[0], int) and path[0] > index:
                            value = dict(value, output_path=[path[0] - 1] + path[1:])
                        remaining.append(value)
                    env[ref['source']] = remaining
                    env[ref['source'] + '$keys'] = [
                        {'kind': 'key', 'source': repr(position), 'key': position}
                        for position in range(len(keys) - 1)]
            return None
        for ref in receiver:
            if method == 'clear':
                if len({v['source'] for v in receiver}) == 1:
                    env[ref['source']] = []
                    env[ref['source'] + '$keys'] = [{'kind': 'key', 'source': '<cleared>', 'key': '*'}]
            else:
                values = self.marked(call.argument_sources[0]['sources'], node)
                inserted = [dict(v, output_path=['*'] + v.get('output_path', [])) for v in values]
                env[ref['source']] = _loop_env({'items': env.get(ref['source'], []) + inserted})['items']
                env[ref['source'] + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(v, target_container=ref['source']) for v in inserted)
        return None  # Preserve the mutator's call-result endpoint (the runtime value is None).

    def apply_effects(self, definition, actuals, captures, call, env, node):
        # Apply only unconditional, statically bound writes. Unsupported body
        # statements leave the caller environment unchanged.
        target_ref, target = definition
        if not isinstance(target, ast.FunctionDef) or _contains_yield(target):
            return
        body = [s for s in target.body if not (isinstance(s, ast.Expr)
                and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
        nonlocal_names = {name for statement in body if isinstance(statement, ast.Nonlocal)
                          for name in statement.names}
        operations = []
        for statement in body:
            if isinstance(statement, ast.Nonlocal):
                continue
            if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Attribute)
                    and isinstance(statement.value.func.value, ast.Name)
                    and not statement.value.keywords):
                effect = statement.value
                receiver_name = effect.func.value.id
                if (effect.func.attr == 'append' and len(effect.args) == 1
                        and isinstance(effect.args[0], ast.Name)):
                    operations.append(('append', receiver_name, effect.args[0].id, statement))
                    continue
                if effect.func.attr == 'clear' and not effect.args:
                    operations.append(('clear', receiver_name, None, statement))
                    continue
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id in nonlocal_names
                    and isinstance(statement.value, ast.Name)):
                operations.append(('nonlocal', statement.targets[0].id,
                                   statement.value.id, statement))
                continue
            return
        values_by_name = dict(captures)
        values_by_name.update(actuals)
        for kind, target_name, source_name, statement in operations:
            if kind == 'nonlocal':
                values = values_by_name.get(source_name, [])
                env[target_name] = self.marked(values, node)
                call.effects.append({'kind': 'nonlocal_write', 'target': target_name,
                                     'source': source_name, 'status': 'exact',
                                     'evidence': [self.evidence_at(target_ref, statement)]})
                call.mutation_flows.extend(dict(value, target_binding=target_name,
                                                effect_summary='nonlocal_write')
                                           for value in self.materialize(values, env))
                continue
            receivers = values_by_name.get(target_name, [])
            expected_shape = 'list' if kind == 'append' else None
            if (not receivers or not all(value.get('kind') == 'container'
                    and (expected_shape is None or value.get('container_shape') == expected_shape)
                    for value in receivers)
                    or len({value['source'] for value in receivers}) != 1):
                continue
            if kind == 'clear':
                for reference in receivers:
                    env[reference['source']] = []
                    env[reference['source'] + '$keys'] = [
                        {'kind': 'key', 'source': '<cleared>', 'key': '*'}]
                call.effects.append({'kind': 'container_clear', 'target': target_name,
                                     'status': 'exact',
                                     'evidence': [self.evidence_at(target_ref, statement)]})
                continue
            values = values_by_name.get(source_name, [])
            for reference in receivers:
                inserted = [dict(value, output_path=['*'] + value.get('output_path', []))
                            for value in self.marked(values, node)]
                env[reference['source']] = _loop_env({
                    'items': env.get(reference['source'], []) + inserted})['items']
                env[reference['source'] + '$keys'] = [
                    {'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(value, target_container=reference['source'],
                    effect_summary='unconditional_append')
                    for value in self.materialize(inserted, env))
            call.effects.append({'kind': 'container_append', 'target': target_name,
                                 'source': source_name, 'status': 'exact',
                                 'evidence': [self.evidence_at(target_ref, statement)]})

    def block(self, statements, env):
        # Exit tuples carry pending returns through finally without committing
        # them to the function summary prematurely.
        active = [env]
        exits = []
        for node in statements:
            if not active:
                break
            current = _merge_env(active)
            outcomes = self.statement(node, current)
            active = [e for kind, e, _, _ in outcomes if kind == 'normal']
            exits.extend(o for o in outcomes if o[0] != 'normal')
        exits.extend(('normal', e, [], None) for e in active)
        return exits

    def statement(self, node, env):
        normal = lambda e: [('normal', e, [], None)]
        exceptional = []
        # A possible exception uses the environment BEFORE evaluation. Simple
        # name/constant assignments cannot import a later definition into it.
        expressions = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Expr)):
            expressions = [node.value]
        elif isinstance(node, ast.If):
            expressions = [node.test]
        if any(_may_raise(e) for e in expressions if e is not None):
            exceptional = [('raise', copy.deepcopy(env), [], None)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults))
            defaults += [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]
            values = {a.arg: self.expression(d, env) for a, d in defaults}
            target = FunctionRef(self.ref.module, self.ref.qualname + '.' + node.name,
                                 self.ref.file_path, node.lineno)
            env[node.name] = [self.callable_value(target, node, values)]
            return normal(env)
        if isinstance(node, ast.ClassDef):
            env[node.name] = []
            return normal(env)
        if isinstance(node, ast.If):
            self.expression(node.test, env)
            before = list(self.conditions)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            positive = copy.deepcopy(env)
            self.refine_guard(node.test, positive)
            left = self.block(node.body, positive)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            right = self.block(node.orelse, copy.deepcopy(env))
            self.conditions = before
            return exceptional + left + right
        if isinstance(node, ast.Try):
            return self.try_statement(node, env)
        if isinstance(node, (ast.For, ast.While)):
            before = copy.deepcopy(env)
            head = copy.deepcopy(env)
            exits = []
            if isinstance(node, ast.For):
                iterable = self.marked(self.project(self.expression(node.iter, env), '*', env), node.iter, 'derived')
            converged = False
            for iteration in range(16):
                body_env = copy.deepcopy(head)
                if isinstance(node, ast.For):
                    self.assign_target(node.target, iterable, body_env, node)
                else:
                    self.expression(node.test, body_env)
                outcomes = self.block(node.body, body_env)
                exits.extend(o for o in outcomes if o[0] not in ('normal', 'continue'))
                continuing = [before] + [e for k, e, _, _ in outcomes if k in ('normal', 'continue')]
                updated = _loop_env(_merge_env(continuing))
                if _loop_signature(updated) == _loop_signature(head):
                    head = updated
                    converged = True
                    break
                head = updated
            else:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'loop_iteration_limit',
                                               'evidence': self.evidence(node)})
            self.loops.append({'lineno': node.lineno, 'col_offset': node.col_offset,
                               'iterations': iteration + 1,
                               'status': 'converged' if converged else 'bounded',
                               'semantics': 'may-flow; one witness per dependency'})
            completed = self.block(node.orelse, head)
            completed += [('normal', e, [], None) for k, e, _, _ in exits if k == 'break']
            completed += [o for o in exits if o[0] != 'break']
            return completed
        if isinstance(node, (ast.Break, ast.Continue)):
            return [('break' if isinstance(node, ast.Break) else 'continue', env, [], None)]
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], (ast.Tuple, ast.List))
                    and isinstance(node.value, (ast.Tuple, ast.List))
                    and len(node.targets[0].elts) == len(node.value.elts)
                    and not any(isinstance(n, ast.Starred) for n in node.targets[0].elts + node.value.elts)):
                elements = [self.expression(v, env) for v in node.value.elts]
                for target, values in zip(node.targets[0].elts, elements):
                    self.assign_target(target, values, env, node)
                return exceptional + normal(env)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            values = self.expression(node.value, env)
            if isinstance(node, ast.AugAssign):
                values = self.marked(self.expression(node.target, env) + values, node, 'derived')
            for target in targets:
                self.assign_target(target, values, env, node)
            return exceptional + normal(env)
        if isinstance(node, ast.Return):
            return exceptional + [('return', env, self.marked(self.expression(node.value, env), node), None)]
        if isinstance(node, ast.Expr):
            self.expression(node.value, env)
            return exceptional + normal(env)
        if isinstance(node, ast.Raise):
            self.expression(node.exc, env)
            expression = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            exception = expression.id if isinstance(expression, ast.Name) else None
            return [('raise', env, [], exception)]
        if isinstance(node, ast.Import):
            for alias in node.names:
                env[alias.asname or alias.name.split('.')[0]] = [{
                    'kind': 'import',
                    'source': alias.name if alias.asname else alias.name.split('.')[0],
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.ImportFrom):
            if node.level:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'relative_local_import', 'evidence': self.evidence(node)})
            for alias in node.names:
                env[alias.asname or alias.name] = ([{'kind': 'import',
                    'source': (node.module or '') + '.' + alias.name,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
                                                  if not node.level else [])
            return normal(env)
        if isinstance(node, ast.Pass):
            return normal(env)
        self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_statement', 'evidence': self.evidence(node)})
        return [('unknown', env, [], None)]

    def assign_target(self, target, values, env, node):
        if isinstance(target, ast.Name):
            env[target.id] = self.marked(values, node)
        elif isinstance(target, (ast.Tuple, ast.List)) and not any(isinstance(t, ast.Starred) for t in target.elts):
            for index, element in enumerate(target.elts):
                projected = self.project(values, index, env)
                self.assign_target(element, projected, env, node)
        elif isinstance(target, ast.Subscript):
            receiver = self.expression(target.value, env)
            if receiver and all(v['kind'] == 'container' and v['container_shape'] == 'dict' for v in receiver):
                index = target.slice.value if isinstance(target.slice, ast.Constant) else '*'
                self.expression(target.slice, env)
                for ref in receiver:
                    previous = env.get(ref['source'], [])
                    if index != '*' and len({v['source'] for v in receiver}) == 1:
                        updated = []
                        for value in previous:
                            path = value.get('output_path', [None])
                            if path[0] == index:
                                continue
                            if path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[index]]))
                            updated.append(value)
                        previous = updated
                    inserted = [dict(v, output_path=[index] + v.get('output_path', []))
                                for v in self.marked(self.materialize(values, env), node)]
                    env[ref['source']] = _loop_env({'items': previous + inserted})['items']
                    keys = env.get(ref['source'] + '$keys', [])
                    for marker in keys:
                        if marker['key'] == '*' and index != '*':
                            marker.setdefault('excluded_keys', []).append(index)
                    env[ref['source'] + '$keys'] = _unique(keys +
                        [{'kind': 'key', 'source': repr(index), 'key': index}])
            else:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_assignment', 'evidence': self.evidence(node)})
        else:
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_assignment', 'evidence': self.evidence(node)})

    def refine_guard(self, test, env):
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            for operand in test.values:
                self.refine_guard(operand, env)
        if (isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == 'isinstance' and len(test.args) == 2 and not test.keywords
                and isinstance(test.args[0], ast.Name) and isinstance(test.args[1], ast.Name)
                and test.args[1].id == 'str'
                and all(name not in env and name not in self.analyzer.imports.get(self.ref.module, {})
                        and name not in self.analyzer.module_bindings.get(self.ref.module, set())
                        and self.analyzer._resolve(self.ref, name) is None for name in ('str', 'isinstance'))):
            name = test.args[0].id
            env[name] = [dict(v, python_shape='str',
                              conditions=v.get('conditions', []) + list(self.conditions))
                         for v in env.get(name, [])]

    def try_statement(self, node, env):
        outcomes = self.block(node.body, copy.deepcopy(env))
        completed = []
        # Merge exception prefixes by known exception spelling. This bounds
        # repeated handler analysis and preserves definitions at raise sites.
        raised = {}
        for kind, state, values, exception in outcomes:
            if kind == 'normal':
                completed.extend(self.block(node.orelse, state))
            elif kind == 'raise':
                raised.setdefault(exception, []).append(state)
            else:
                completed.append((kind, state, values, exception))
        for exception, states in raised.items():
            state = _merge_env(states)
            caught = False
            for handler in node.handlers:
                names = ([n.id for n in handler.type.elts if isinstance(n, ast.Name)]
                         if isinstance(handler.type, ast.Tuple)
                         else [handler.type.id] if isinstance(handler.type, ast.Name) else [])
                exact = handler.type is None
                raised_class = _exception_class(exception)
                handler_classes = [_exception_class(n) for n in names]
                # Unknown/custom inheritance cannot safely exclude a handler.
                if raised_class and handler_classes and all(handler_classes):
                    if not any(issubclass(raised_class, cls) for cls in handler_classes):
                        continue
                    exact = True
                before = list(self.conditions)
                self.conditions = before + [{'handler': self.evidence(handler), 'exception': exception or 'unknown'}]
                handled = copy.deepcopy(state)
                if handler.name:
                    handled[handler.name] = []
                handler_exits = self.block(handler.body, handled)
                for item in handler_exits:
                    if handler.name:
                        item[1].pop(handler.name, None)
                completed.extend(handler_exits)
                self.conditions = before
                if exact:
                    caught = True
                    break
            if not caught:
                completed.append(('raise', state, [], exception))
        if not node.finalbody:
            return completed
        finalized = []
        for kind, state, values, exception in completed:
            for final_kind, final_env, final_values, final_exc in self.block(node.finalbody, copy.deepcopy(state)):
                if final_kind == 'normal':
                    finalized.append((kind, final_env, values, exception))
                else:
                    finalized.append((final_kind, final_env, final_values, final_exc))
        return finalized

    def run(self):
        args = self.node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [a for a in (args.vararg, args.kwarg) if a]
        env = {a.arg: [{'kind': 'parameter', 'source': a.arg, 'relation': 'direct',
                        'evidence': [self.evidence(a)], 'conditions': []}] for a in parameters}
        shape_contract = self.analyzer.parameter_shapes.get(
            self.ref.module + '.' + self.ref.qualname, {})
        shapes = shape_contract.get('parameters', {})
        for name, shape in shapes.items():
            if name in env:
                env[name] = [dict(value, python_shape=shape,
                                  shape_provenance=shape_contract['provenance'])
                             for value in env[name]]
        for local in _scope_names(self.node)[1]:
            env.setdefault(local, [])
        for capture in self.analyzer._captures(self.ref, self.node):
            env[capture] = [{'kind': 'capture', 'source': capture, 'relation': 'direct',
                             'evidence': [], 'conditions': []}]
        outcomes = ([('return', env,
                      self.marked(self.expression(self.node.body, env), self.node.body), None)]
                    if isinstance(self.node, ast.Lambda) else self.block(self.node.body, env))
        generator = _contains_yield(self.node)
        for kind, state, values, _ in outcomes:
            if kind == 'return' and not generator:
                self.returns.extend(self.materialize(values, state))
        if generator:
            self.returns.extend(self.yields)
        self.returns = _unique(self.returns)
        merged = {}
        for call in self.calls:
            if call.id not in merged:
                merged[call.id] = call
            else:
                previous = merged[call.id]
                if previous.target != call.target:
                    previous.target = None
                for attribute in ('parameter_bindings', 'parameter_flows', 'argument_sources', 'argument_flows',
                                  'capture_bindings', 'receiver_sources', 'mutation_flows',
                                  'return_dependencies', 'effects'):
                    setattr(previous, attribute, _unique(getattr(previous, attribute) + getattr(call, attribute)))
        self.calls = list(merged.values())
        def collect(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call):
                call_id = _call_key(self.ref.file_path, node)
                if call_id not in merged and self.remaining > 0:
                    self.remaining -= 1
                    call = FlowCall(call_id, self.ref, ast.unparse(node.func), node.lineno, node.col_offset,
                                    node.end_lineno, node.end_col_offset,
                                    analysis_status='not_analyzed', target_status='flow_not_analyzed')
                    self.calls.append(call)
                    merged[call_id] = call
            for child in ast.iter_child_nodes(node):
                collect(child)
        body = [self.node.body] if isinstance(self.node, ast.Lambda) else self.node.body
        for statement in body:
            collect(statement)
        self.calls.sort(key=lambda c: (c.lineno, c.col_offset))
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'parameter_shapes': copy.deepcopy(shapes),
                                      'generator': generator,
                                      'loops': self.loops,
                                      'returns': self.returns})
        self.result.calls.extend(self.calls)
