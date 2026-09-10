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


## An immutable-by-convention analysis snapshot with JSON-safe views.
@dataclass
class FlowAnalysis:
    entry: FunctionRef
    inputs: dict
    functions: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    schema_version: str = 'flow-0.1'

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
        def sources(ref, values, stack):
            found = []
            for value in values:
                if value['kind'] in ('parameter', 'capture'):
                    found.append(dict(value, call_context=[]))
                    continue
                call = next((c for c in self.calls if c.id == value['source']), None)
                if call is None or call.id in stack:
                    continue
                summary = next((f for f in self.functions if call.target is not None
                                and f['function'] == asdict(call.target)), None)
                if summary is None and call.return_dependencies:
                    summary = {'returns': call.return_dependencies}
                if summary is None:
                    continue
                for inner in sources(call.target, summary['returns'], stack + (call.id,)):
                    bindings = (call.capture_bindings if inner['kind'] == 'capture'
                                else call.argument_sources)
                    for argument in bindings:
                        if argument.get('capture', argument.get('parameter')) != inner['source']:
                            continue
                        for outer in sources(ref, argument['sources'], stack + (call.id,)):
                            found.append(dict(outer,
                                relation=_relation([v['relation'] for v in (value, inner, outer)]),
                                evidence=outer['evidence'] + inner['evidence'] + value['evidence'],
                                conditions=outer.get('conditions', []) + inner.get('conditions', []) + value.get('conditions', []),
                                call_context=outer['call_context'] + [call.id] + inner['call_context']))
            return found
        summary = next(f for f in self.functions if f['function'] == asdict(self.entry))
        if parameter not in summary['parameters']:
            raise ValueError('Unknown entry parameter: ' + parameter)
        paths = [v for v in sources(self.entry, summary['returns'], ()) if v['source'] == parameter]
        return {'parameter': parameter, 'return_paths': paths,
                'status': 'flow_found' if paths else 'unknown',
                'boundaries': copy.deepcopy(self.boundaries)}


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
    for statement in node.body:
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
    def __init__(self, source_files=None, import_roots=None, project_root=None, return_summaries=None):
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
        self.roots = [os.path.abspath(p) for p in (import_roots or ([project_root] if project_root else []))]
        self.add_files(FileScanner().scan(str(project_root)) if project_root else source_files)

    ## Add sources for the next analysis; existing snapshots remain unchanged.
    #  @param files Iterable of Python source paths.
    def add_files(self, files):
        self.files.update(os.path.abspath(p) for p in files if str(p).endswith(('.py', '.pyi')))

    def _index(self):
        self.definitions = []
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
                        collect(node.body, name + '.')
            collect(tree.body)

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
        outer = set()
        parent = ref.qualname.rpartition('.')[0]
        while parent:
            definition = next((n for r, n in self.definitions
                               if r.module == ref.module and r.qualname == parent), None)
            if definition:
                outer.update(_scope_names(definition)[1])
            parent = parent.rpartition('.')[0]
        return sorted((loaded - bound) & outer)

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
                              'coverage': 'explicit value dependencies; no heap effects or path feasibility proof'})
        result.boundaries.extend(self.index_boundaries)
        self._walk(result, matches[0], max_depth, (), max_functions, max_call_contexts)
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
                or self.return_summaries != result.inputs.get('return_summaries', {})):
            raise ValueError('Sources changed; call analyze again before expand')
        call = next(c for c in result.calls if c.id == call_id)
        updated = copy.deepcopy(result)
        if call.target is not None:
            updated.boundaries = [b for b in updated.boundaries if not (b.get('call_id') == call_id and b['reason'] == 'depth_limit')]
            self._walk(updated, next(d for d in self.definitions if d[0] == call.target), additional_depth, (call.caller,), 500, 2000)
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
        self.source_lines = [line.encode('utf-8') for line in
                             self.analyzer.texts[ref.file_path].split('\n')]
        self.evidence_cache = {}

    def evidence(self, node):
        key = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
        if key in self.evidence_cache:
            return self.evidence_cache[key]
        first, start, last, end = key
        if first == last:
            snippet = self.source_lines[first - 1][start:end]
        else:
            snippet = b'\n'.join([self.source_lines[first - 1][start:]] +
                                  self.source_lines[first:last - 1] +
                                  [self.source_lines[last - 1][:end]])
        value = {'file_path': self.ref.file_path, 'lineno': node.lineno,
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

    def expression(self, node, env):
        if node is None:
            return []
        if isinstance(node, ast.Name):
            return [v for v in env.get(node.id, []) if v['kind'] not in ('callable', 'import')]
        if isinstance(node, ast.Constant):
            return []
        if isinstance(node, ast.IfExp):
            self.expression(node.test, env)
            before = list(self.conditions)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            left = self.marked(self.expression(node.body, env), node.body)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            right = self.marked(self.expression(node.orelse, env), node.orelse)
            self.conditions = before
            return left + right
        if isinstance(node, ast.Call):
            location = (node.lineno, node.col_offset)
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
            receiver_sources = (self.expression(node.func.value, env)
                                if isinstance(node.func, ast.Attribute) else [])
            bound_receiver = False
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
                if len(matches) == 1 and not self.node.decorator_list:
                    target = matches[0]
                    bound_receiver = True
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
                targets = {v['source'] for v in binding}
                if len(targets) == 1:
                    target = next((d for d in self.analyzer.definitions
                                   if d[0].module == self.ref.module and d[0].qualname in targets), None)
            if target and target[1].decorator_list:
                target = None
            call_id = '%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
            call = FlowCall(call_id, self.ref, name, node.lineno, node.col_offset, target[0] if target else None)
            call.receiver_sources = receiver_sources
            call.target_status = ('lexical_method_candidate' if target and bound_receiver else
                                  'resolved' if target else 'receiver_unresolved' if isinstance(node.func, ast.Attribute)
                                  else 'builtin_boundary' if binding is None and hasattr(builtins, name)
                                  else 'definition_unavailable')
            if (target is None and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.attr in ('split', 'rsplit', 'strip', 'lstrip', 'rstrip', 'startswith', 'endswith')
                    and receiver_sources and all(v.get('python_shape') == 'str' for v in receiver_sources)):
                call.target_status = 'python_protocol'
                call.argument_sources.append({'argument': {'receiver': True}, 'parameter': '$receiver',
                                              'sources': receiver_sources})
                call.return_dependencies = [{'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                    'evidence': [{'provenance': 'Guarded str receiver dependency; builtin method implementation assumed'}],
                    'conditions': list(self.conditions)}]
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                               'reason': 'string_subclass_override_possible'})
            if target and bound_receiver:
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                               'reason': 'dynamic_method_override_possible'})
            if target:
                for capture in self.analyzer._captures(*target):
                    call.capture_bindings.append({'capture': capture,
                        'sources': copy.deepcopy(env.get(capture, []))})
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
            if contract and (binding is None or all(v['kind'] == 'import' for v in binding)):
                params = ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in contract['parameters']],
                                       vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
                call.return_dependencies = [
                    {'kind': 'parameter', 'source': d['parameter'], 'relation': d['relation'],
                     'evidence': [{'provenance': contract['provenance'], 'callable': canonical}], 'conditions': []}
                    for d in contract.get('returns', [])]
            positional = params.posonlyargs + params.args if params else []
            if bound_receiver and target and positional:
                call.argument_sources.append({'argument': {'receiver': True}, 'parameter': positional[0].arg,
                                              'sources': receiver_sources})
                positional = positional[1:]
            arguments = [({'position': i}, arg) for i, arg in enumerate(node.args)]
            arguments += [({'keyword': kw.arg}, kw.value) for kw in node.keywords]
            expanded = False
            for slot, arg in arguments:
                if isinstance(arg, ast.Starred) or slot.get('keyword', '') is None:
                    expanded = True
                    self.result.boundaries.append({'call_id': call_id, 'reason': 'dynamic_argument_expansion'})
                parameter = None
                if params and not expanded:
                    if 'position' in slot:
                        i = slot['position']
                        parameter = positional[i].arg if i < len(positional) else (params.vararg.arg if params.vararg else None)
                    else:
                        key = slot['keyword']
                        allowed = [a.arg for a in params.args + params.kwonlyargs]
                        parameter = key if key in allowed else (params.kwarg.arg if params.kwarg else None)
                call.parameter_bindings.append({'argument': slot, 'parameter': parameter,
                                                'status': 'exact' if parameter else 'unresolved'})
                values = self.marked(self.expression(arg, env), arg)
                call.argument_sources.append({'argument': slot, 'parameter': parameter, 'sources': values})
                for value in values:
                    call.argument_flows.append(dict(value, target_parameter=parameter,
                                                    argument=slot, status='flow_found'))
                    if value['kind'] == 'parameter':
                        call.parameter_flows.append(dict(value, source_parameter=value['source'],
                                                         target_parameter=parameter, argument=slot, status='flow_found'))
            if params:
                supplied = {b['parameter'] for b in call.parameter_bindings}
                defaults = list(zip(positional[len(positional) - len(params.defaults):], params.defaults))
                defaults += [(a, d) for a, d in zip(params.kwonlyargs, params.kw_defaults) if d is not None]
                for param, default in defaults:
                    if param.arg not in supplied and not expanded:
                        call.parameter_bindings.append({'argument': None, 'parameter': param.arg,
                                                        'binding_kind': 'default', 'status': 'exact',
                                                        'source_text': ast.unparse(default)})
                        if binding and all(v['kind'] == 'callable' for v in binding):
                            call.argument_sources.append({'argument': None, 'parameter': param.arg,
                                'sources': _unique([v for b in binding for v in b.get('defaults', {}).get(param.arg, [])])})
            self.calls.append(call)
            return [{'kind': 'call_result', 'source': call_id, 'relation': 'direct',
                     'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_expression', 'evidence': self.evidence(node)})
            return []
        values = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                values.extend(self.expression(child, env))
        relation = 'contained' if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) else 'derived'
        return self.marked(values, node, relation)

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
            env[node.name] = [{'kind': 'callable', 'source': self.ref.qualname + '.' + node.name, 'defaults': values}]
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
                iterable = self.marked(self.expression(node.iter, env), node.iter, 'derived')
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
            values = self.expression(node.value, env)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
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
                env[alias.asname or alias.name.split('.')[0]] = [{'kind': 'import', 'source': alias.name if alias.asname else alias.name.split('.')[0]}]
            return normal(env)
        if isinstance(node, ast.ImportFrom):
            if node.level:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'relative_local_import', 'evidence': self.evidence(node)})
            for alias in node.names:
                env[alias.asname or alias.name] = ([{'kind': 'import', 'source': (node.module or '') + '.' + alias.name}]
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
                projected = [dict(v, relation='derived', projection=v.get('projection', []) + [index]) for v in values]
                self.assign_target(element, projected, env, node)
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
        for local in _scope_names(self.node)[1]:
            env.setdefault(local, [])
        for capture in self.analyzer._captures(self.ref, self.node):
            env[capture] = [{'kind': 'capture', 'source': capture, 'relation': 'direct',
                             'evidence': [], 'conditions': []}]
        for kind, _, values, _ in self.block(self.node.body, env):
            if kind == 'return':
                self.returns.extend(values)
        self.returns = _unique(self.returns)
        merged = {}
        for call in self.calls:
            if call.id not in merged:
                merged[call.id] = call
            else:
                previous = merged[call.id]
                if previous.target != call.target:
                    previous.target = None
                for attribute in ('parameter_bindings', 'parameter_flows', 'argument_sources', 'argument_flows', 'capture_bindings', 'receiver_sources'):
                    setattr(previous, attribute, _unique(getattr(previous, attribute) + getattr(call, attribute)))
        self.calls = list(merged.values())
        def collect(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call):
                call_id = '%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
                if call_id not in merged and self.remaining > 0:
                    self.remaining -= 1
                    call = FlowCall(call_id, self.ref, ast.unparse(node.func), node.lineno, node.col_offset,
                                    analysis_status='not_analyzed', target_status='flow_not_analyzed')
                    self.calls.append(call)
                    merged[call_id] = call
            for child in ast.iter_child_nodes(node):
                collect(child)
        for statement in self.node.body:
            collect(statement)
        self.calls.sort(key=lambda c: (c.lineno, c.col_offset))
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'loops': self.loops,
                                      'returns': self.returns})
        self.result.calls.extend(self.calls)
