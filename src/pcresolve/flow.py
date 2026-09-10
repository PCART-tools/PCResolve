## @package pcresolve.flow
#  Experimental, explicit-boundary value-flow summaries for Python functions.

import ast
import copy
import hashlib
import os
from dataclasses import dataclass, field, asdict

from .scanner import FileScanner


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
                if value['kind'] == 'parameter':
                    found.append(dict(value, call_context=[]))
                    continue
                call = next((c for c in self.calls if c.id == value['source']), None)
                if call is None or call.id in stack or call.target is None:
                    continue
                summary = next((f for f in self.functions if f['function'] == asdict(call.target)), None)
                if summary is None:
                    continue
                for inner in sources(call.target, summary['returns'], stack + (call.id,)):
                    for argument in call.argument_sources:
                        if argument['parameter'] != inner['source']:
                            continue
                        for outer in sources(ref, argument['sources'], stack + (call.id,)):
                            found.append(dict(outer,
                                relation='direct' if all(v['relation'] == 'direct' for v in (value, inner, outer)) else 'derived',
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


## Analyze explicit Python source sets without executing analyzed code.
class FlowAnalyzer:
    ## Configure available sources; import roots do not enlarge the source set.
    #  @param source_files Explicit files, mutually exclusive with project_root.
    #  @param import_roots Roots used to derive module names.
    #  @param project_root Optional project directory scanned with FileScanner.
    def __init__(self, source_files=None, import_roots=None, project_root=None):
        if (source_files is None) == (project_root is None):
            raise ValueError('Specify exactly one of source_files or project_root')
        self.files = set()
        self.roots = [os.path.abspath(p) for p in (import_roots or ([project_root] if project_root else []))]
        self.add_files(FileScanner().scan(str(project_root)) if project_root else source_files)

    ## Add sources for the next analysis; existing snapshots remain unchanged.
    #  @param files Iterable of Python source paths.
    def add_files(self, files):
        self.files.update(os.path.abspath(p) for p in files if str(p).endswith(('.py', '.pyi')))

    def _index(self):
        self.definitions = []
        self.imports = {}
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
            def collect(body, prefix=''):
                for node in body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        name = prefix + node.name
                        if not isinstance(node, ast.ClassDef):
                            self.definitions.append((FunctionRef(module, name, path, node.lineno), node))
                        collect(node.body, name + '.')
            collect(tree.body)

    def _resolve(self, caller, name):
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
                result.boundaries.append({'call_id': call.id, 'reason': 'definition_unavailable'})
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
        if self.hashes != result.inputs['sha256'] or sorted(self.files) != result.inputs['source_files']:
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

    def evidence(self, node):
        return {'file_path': self.ref.file_path, 'lineno': node.lineno,
                'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
                'end_col_offset': node.end_col_offset,
                'source_text': ast.get_source_segment(self.analyzer.texts[self.ref.file_path], node)}

    def marked(self, values, node, relation=None):
        return [dict(v, relation=relation or v['relation'], evidence=v['evidence'] + [self.evidence(node)],
                     conditions=v.get('conditions', []) + list(self.conditions)) for v in values]

    def expression(self, node, env):
        if node is None:
            return []
        if isinstance(node, ast.Name):
            return env.get(node.id, [])
        if isinstance(node, ast.Constant):
            return []
        if isinstance(node, ast.Call):
            if self.remaining <= 0:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'budget_exceeded', 'evidence': self.evidence(node)})
                return []
            self.remaining -= 1
            name = ast.unparse(node.func)
            target = self.analyzer._resolve(self.ref, name) if name.split('.')[0] not in env else None
            if target and target[1].decorator_list:
                target = None
            call_id = '%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
            call = FlowCall(call_id, self.ref, name, node.lineno, node.col_offset, target[0] if target else None)
            params = target[1].args if target else None
            positional = params.posonlyargs + params.args if params else []
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
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.If):
                self.expression(node.test, env)
                before = list(self.conditions)
                self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
                left = self.block(node.body, copy.deepcopy(env))
                self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
                right = self.block(node.orelse, copy.deepcopy(env))
                self.conditions = before
                if left is None and right is None:
                    return None
                if left is None or right is None:
                    env = right if left is None else left
                else:
                    env = {k: left.get(k, []) + right.get(k, []) for k in left.keys() | right.keys()}
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                values = self.expression(node.value, env)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if isinstance(node, ast.AugAssign):
                    values = self.marked(self.expression(node.target, env) + values, node, 'derived')
                for target in targets:
                    if isinstance(target, ast.Name):
                        env[target.id] = self.marked(values, node)
                    else:
                        self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_assignment', 'evidence': self.evidence(node)})
            elif isinstance(node, ast.Return):
                self.returns.extend(self.marked(self.expression(node.value, env), node))
                return None
            elif isinstance(node, ast.Expr):
                self.expression(node.value, env)
            elif isinstance(node, ast.Raise):
                self.expression(node.exc, env)
                return None
            elif not isinstance(node, (ast.Pass, ast.Import, ast.ImportFrom)):
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_statement', 'evidence': self.evidence(node)})
                # Stop rather than claim flows through unmodeled control flow.
                return None
        return env

    def run(self):
        args = self.node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [a for a in (args.vararg, args.kwarg) if a]
        env = {a.arg: [{'kind': 'parameter', 'source': a.arg, 'relation': 'direct',
                        'evidence': [self.evidence(a)], 'conditions': []}] for a in parameters}
        self.block(self.node.body, env)
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'returns': self.returns})
        self.result.calls.extend(self.calls)
