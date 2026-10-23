## @package pcresolve._metadata_observer
#  Bounded effects of a private source receiver observing one native class.

import ast
import copy
from dataclasses import asdict, dataclass, field

from ._class_type_tests import native_class_operand
from ._native_class_protocol import iterability_query
from ._metadata_entry import entry as _entry
from ._metadata_creation import regex_pattern, string_set
from ._metadata_namespace import builtin_namespace, namespace
from ._metadata_queries import _Query, _Value, _scalar, _span, _OpenQuery, metadata_query
from .class_attribute_effects import _ClassEffectLimit
from .program_facts import FunctionSignature, bind_ast_call
from .scope_facts import statement_scope_facts


@dataclass(frozen=True)
class _Observed(_Value):
    origin: str = ''
    prefixes: tuple = ()
    heap: int = 0
    name_evidence: tuple = ()


@dataclass
class _Frame:
    env: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
    heap: dict = field(default_factory=dict)
    control: str = 'normal'
    result: object = None


def _string(origin='', prefixes=(), name_evidence=()):
    return _Observed('scalar', frozenset({'str'}), origin=origin, prefixes=tuple(prefixes),
                     name_evidence=tuple(name_evidence))


def _data(value):
    return value.kind in ('scalar', 'list', 'dict', 'set', 'tuple')


def _literal(value):
    return (value is None or type(value) is bool
            or type(value) is int and value.bit_length() <= 64
            or type(value) is str and len(value) <= 2000)


def _arguments(selected, call, values, receiver=False):
    function = selected[1]
    args = function.args
    parameters = args.posonlyargs + args.args
    if (not isinstance(function, ast.FunctionDef) or args.vararg or args.kwarg
            or receiver and not parameters):
        raise _OpenQuery()
    signature = FunctionSignature.from_ast(args, parameters[1:] if receiver else parameters)
    records, reasons = bind_ast_call(call, signature)
    if (reasons or len(records) != len(values)
            or any(record['status'] != 'exact' or record['destination_kind'] != 'parameter'
                   for record in records)):
        raise _OpenQuery()
    incoming = {}
    # Defaults execute when the source function is created, even if a caller
    # supplies that parameter. Never hide an unsupported declaration input.
    for name, default in signature.defaults:
        if not isinstance(default, ast.Constant) or not _literal(default.value):
            raise _OpenQuery()
        incoming[name] = _scalar({type(default.value).__name__}, default.value, True)
    incoming.update((record['parameter'], value) for record, value in zip(records, values))
    return incoming


class _Observer(_Query):
    def __init__(self, analyzer, owner):
        self.owner, self.cls = owner
        super().__init__(analyzer, owner)
        self.remaining = 20000
        self.stack, self.loop_heaps = [], set()
        self.member_prefixes, self.required_protocols = set(), set()
        self.cached, self.iterability, self.method_calls = False, [], []
        self.cache_queries, self.type_tests = [], []
        self.member_lookups = []
        self.native_data_members = {}
        self.mro_queries = []
        self.next_heap = 0
        self.names = statement_scope_facts(self.cls.body).bound

    def container(self, frame, kind, values=()):
        if any(not _data(value) for value in values):
            raise _OpenQuery()
        self.next_heap += 1
        frame.heap[self.next_heap] = {'kind': kind, 'values': list(values)}
        return _Observed(kind, heap=self.next_heap)

    def element(self, frame, value):
        if value.kind == 'mro_sequence':
            return _Observed('ancestor_class')
        if value.kind not in ('list', 'set'):
            raise _OpenQuery()
        values = frame.heap[value.heap]['values']
        return self.elements(frame, values)

    def elements(self, frame, values, depth=0):
        self.charge()
        if depth > 16:
            raise _OpenQuery()
        if not values:
            return _string()
        if all(item.kind == 'tuple' for item in values):
            rows = [frame.heap[item.heap]['values'] for item in values]
            if len(rows[0]) > 64 or any(len(row) != len(rows[0]) for row in rows):
                raise _OpenQuery()
            return self.container(frame, 'tuple',
                [self.elements(frame, [row[index] for row in rows], depth + 1)
                 for index in range(len(rows[0]))])
        if all(item.kind == 'scalar' and item.shapes == {'str'} for item in values):
            origins = {getattr(item, 'origin', '') for item in values}
            prefixes = set.intersection(*(set(getattr(item, 'prefixes', ())) for item in values))
            origin = next(iter(origins)) if len(origins) == 1 else ''
            evidence = []
            if origin:
                for item in values:
                    for step in getattr(item, 'name_evidence', ()):
                        if step not in evidence:
                            evidence.append(step)
                            self.charge()
            return _string(origin, sorted(prefixes), evidence)
        if all(item.kind == 'scalar' and item.shapes and item.shapes <= {'str', 'NoneType'}
               for item in values):
            return _scalar(set().union(*(item.shapes for item in values)))
        raise _OpenQuery()

    def bind_target(self, target, value, frame, depth=0):
        self.charge()
        if depth > 16:
            raise _OpenQuery()
        if isinstance(target, ast.Name):
            frame.env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)) and value.kind == 'tuple':
            values = frame.heap[value.heap]['values']
            if len(target.elts) != len(values):
                raise _OpenQuery()
            for part, element in zip(target.elts, values):
                self.bind_target(part, element, frame, depth + 1)
        else:
            raise _OpenQuery()

    def name_step(self, operation, node, **details):
        return {'operation': operation, 'evidence': _span(self.target[0], node), **details}

    def restored_name(self, prefix, suffix, node):
        if prefix and getattr(suffix, 'origin', '') == 'input_class_suffix:' + prefix:
            evidence = suffix.name_evidence + (self.name_step('restore_prefix', node, prefix=prefix),)
            return _string('input_class_names', (prefix,), evidence)
        return _string()

    def data_member(self, name):
        if name not in self.native_data_members:
            shadowed = set()
            for statement in self.cls.body:
                bound = statement_scope_facts([statement]).bound
                if name in bound:
                    if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                            or not isinstance(statement.targets[0], ast.Name)
                            or statement.targets[0].id != name):
                        raise _OpenQuery()
                    if isinstance(statement.value, ast.Set):
                        for item in statement.value.elts:
                            self.charge()
                    proof = (string_set(self.analyzer, self.owner, statement.value)
                             or regex_pattern(self.analyzer, self.owner, statement.value, shadowed))
                    if proof is None:
                        raise _OpenQuery()
                    self.native_data_members[name] = {'attribute': name, 'creation': proof,
                        'runtime_value_confirmed': False}
                    break
                shadowed.update(bound)
            else:
                raise _OpenQuery()
        kind = self.native_data_members[name]['creation']['result_kind']
        return _Value('native_string_set' if kind == 'native_string_set' else 'pattern')

    def comprehension(self, node, frame):
        if len(node.generators) != 1 or node.generators[0].is_async:
            raise _OpenQuery()
        generator = node.generators[0]
        local = copy.deepcopy(frame)
        iterator = generator.iter
        if (isinstance(iterator, ast.Call) and isinstance(iterator.func, ast.Name)
                and iterator.func.id == 'zip' and not iterator.keywords and len(iterator.args) == 2
                and self.analyzer._builtin_name_status(self.target[0], self.target[1], 'zip')
                    == 'confirmed_builtin'):
            sequences = [self.expression(argument, local) for argument in iterator.args]
            if any(value.kind != 'list' or any(item.kind != 'scalar' or not item.shapes
                       or not item.shapes <= {'str', 'NoneType'}
                       for item in local.heap[value.heap]['values']) for value in sequences):
                raise _OpenQuery()
            rows = [] if any(not local.heap[value.heap]['values'] for value in sequences) else [
                self.container(local, 'tuple', [self.element(local, value) for value in sequences])]
            iterable = self.container(local, 'list', rows)
        else:
            iterable = self.expression(iterator, local)
        empty = iterable.kind in ('list', 'set') and not local.heap[iterable.heap]['values']
        value = None
        if not empty:
            self.bind_target(generator.target, self.element(local, iterable), local)
            prior = set(self.loop_heaps)
            self.loop_heaps.add(iterable.heap)
            try:
                for test in generator.ifs:
                    self.expression(test, local)
                    local.env = self.refined(test, local.env, True)
                value = self.expression(node.elt, local)
            finally:
                self.loop_heaps = prior
        # This bounded form reads a private sequence. Discarding mutations of
        # the receiver or an existing container would hide later effects.
        if local.fields != frame.fields or any(local.heap.get(key) != value
                                               for key, value in frame.heap.items()):
            raise _OpenQuery()
        # Newly allocated private row objects remain reachable from the result.
        # Existing heaps have already been checked for discarded mutations.
        frame.heap.update((key, value) for key, value in local.heap.items() if key not in frame.heap)
        return self.container(frame, 'list', [] if empty else [value])

    def expression(self, node, frame):
        self.charge()
        if isinstance(node, ast.Attribute):
            base = self.expression(node.value, frame)
            if base.kind == 'class' and node.attr == '__mro__':
                self.mro_queries.append({'caller': asdict(self.target[0]),
                    'evidence': _span(self.target[0], node), 'runtime_lookup_confirmed': False})
                return _Observed('mro_sequence')
            if base.kind == 'receiver' and node.attr in frame.fields:
                return frame.fields[node.attr]
            if base.kind == 'receiver' and node.attr in self.names:
                return self.data_member(node.attr)
            if base.kind == 'match' and node.attr == 'group':
                raise _OpenQuery()
            if base.kind == 'signature' and node.attr == 'parameters':
                return _Value('parameters')
            if base.kind == 'callable' and node.attr == '__code__':
                self.required_protocols.add('native_python_code_metadata_without_user_callbacks')
                return _Value('code')
            if base.kind == 'callable' and node.attr in ('__doc__', '__module__', '__qualname__'):
                self.required_protocols.add('native_python_function_name_and_doc_metadata_without_callbacks')
                return _scalar({'str', 'NoneType'}) if node.attr == '__doc__' else _string()
            if base.kind == 'code' and node.attr == 'co_varnames':
                return _Value('varnames')
            raise _OpenQuery()
        if isinstance(node, ast.JoinedStr):
            values = []
            for part in node.values:
                if isinstance(part, ast.Constant) and type(part.value) is str:
                    values.append(_scalar({'str'}, part.value, True))
                elif isinstance(part, ast.FormattedValue) and part.conversion == -1 and part.format_spec is None:
                    value = self.expression(part.value, frame)
                    if value.kind != 'scalar' or value.shapes != {'str'}:
                        raise _OpenQuery()
                    values.append(value)
                else:
                    raise _OpenQuery()
            if len(values) == 2 and values[0].known:
                return self.restored_name(values[0].literal, values[1], node)
            return _string()
        if isinstance(node, (ast.List, ast.Set, ast.Dict)):
            if isinstance(node, ast.Dict):
                if node.keys:
                    raise _OpenQuery()
                return self.container(frame, 'dict')
            values = []
            for item in node.elts:
                if isinstance(item, ast.Starred) and isinstance(node, ast.List):
                    expanded = self.expression(item.value, frame)
                    if expanded.kind != 'list':
                        raise _OpenQuery()
                    values.extend(frame.heap[expanded.heap]['values'])
                else:
                    values.append(self.expression(item, frame))
            return self.container(frame, type(node).__name__.lower(), values)
        if isinstance(node, ast.Tuple) and all(isinstance(item, ast.Constant)
                and type(item.value) is str for item in node.elts):
            return _Value('prefixes', literal=tuple(item.value for item in node.elts), known=True)
        if isinstance(node, ast.Tuple):
            return self.container(frame, 'tuple', [self.expression(item, frame) for item in node.elts])
        if isinstance(node, ast.BinOp):
            left, right = self.expression(node.left, frame), self.expression(node.right, frame)
            left_string = left.kind == 'scalar' and left.shapes == {'str'}
            right_string = right.kind == 'scalar' and right.shapes == {'str'}
            if isinstance(node.op, ast.Add) and left_string and right_string:
                if left.known and type(left.literal) is str:
                    return self.restored_name(left.literal, right, node)
                return _string()
            if isinstance(node.op, ast.Mult) and (
                    left_string and right.kind == 'scalar' and right.shapes == {'int'}
                    or right_string and left.kind == 'scalar' and left.shapes == {'int'}):
                return _string()
            if isinstance(node.op, ast.Mod) and left_string and (
                    _data(right) or right.kind == 'prefixes'):
                if (left.known and type(left.literal) is str and left.literal.endswith('%s')
                        and '%' not in left.literal[:-2] and right_string):
                    return self.restored_name(left.literal[:-2], right, node)
                # Native containers are private and contain only native data.
                # Formatting can fail; only its normal return is summarized.
                return _string()
            raise _OpenQuery()
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            base = self.expression(node.value, frame)
            if base.kind != 'scalar' or not base.shapes or not base.shapes <= {'str', 'NoneType'}:
                raise _OpenQuery()
            for part in (node.slice.lower, node.slice.upper, node.slice.step):
                if part is not None and (not isinstance(part, ast.Constant)
                        or type(part.value) is not int or part is node.slice.step and part.value == 0):
                    raise _OpenQuery()
            if (getattr(base, 'origin', '') == 'input_class_names' and len(base.prefixes) == 1
                    and isinstance(node.slice.lower, ast.Constant)
                    and type(node.slice.lower.value) is int
                    and node.slice.lower.value == len(base.prefixes[0])
                    and node.slice.upper is None and (node.slice.step is None
                        or isinstance(node.slice.step, ast.Constant)
                        and type(node.slice.step.value) is int and node.slice.step.value == 1)):
                prefix = base.prefixes[0]
                evidence = base.name_evidence + (self.name_step('remove_prefix', node, prefix=prefix),)
                return _string('input_class_suffix:' + prefix, name_evidence=evidence)
            return _string()
        if isinstance(node, ast.Subscript):
            base = self.expression(node.value, frame)
            if (base.kind == 'varnames' and isinstance(node.slice, ast.Constant)
                    and type(node.slice.value) is int):
                return _string()
            raise _OpenQuery()
        if isinstance(node, ast.ListComp):
            return self.comprehension(node, frame)
        if isinstance(node, ast.BoolOp):
            local = copy.deepcopy(frame)
            for child in node.values:
                value = self.expression(child, local)
                value = self.truth(value)
                if value.kind != 'scalar':
                    raise _OpenQuery()
                if value.known and bool(value.literal) == isinstance(node.op, ast.Or):
                    break
                local.env = self.refined(child, local.env, isinstance(node.op, ast.And))
            return _scalar({'bool'})
        if isinstance(node, ast.Call):
            test = self.type_test(node, frame)
            if test is not None:
                return test
            value = self.call(node, frame)
            if value is not None:
                return value
        # Scalar metadata operations share the same primitive implementation.
        # Its recursive calls are routed through the current private frame.
        return self.scalar_expression(node, frame)

    def scalar_expression(self, node, frame):
        if node is None:
            return _scalar({'NoneType'}, None, True)
        if isinstance(node, ast.Name) and node.id in frame.env:
            return frame.env[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool, float, type(None)):
            return _scalar({type(node.value).__name__}, node.value, True)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = self.expression(node.operand, frame)
            if _data(value):
                return (_scalar({'bool'}, not bool(value.literal), True)
                        if value.known else _scalar({'bool'}))
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = self.expression(node.left, frame), self.expression(node.comparators[0], frame)
            if (left.kind == 'scalar' and left.shapes == {'str'}
                    and right.kind == 'native_string_set' and isinstance(node.ops[0], (ast.In, ast.NotIn))):
                return _scalar({'bool'})
            if (left.kind == 'match' and right.known and right.literal is None
                    and isinstance(node.ops[0], (ast.Is, ast.IsNot))):
                return _scalar({'bool'})
            if left.kind == right.kind == 'scalar':
                if isinstance(node.ops[0], (ast.Is, ast.IsNot)) and right.known and right.literal is None:
                    if left.known or 'NoneType' not in left.shapes:
                        result = (left.known and left.literal is None) == isinstance(node.ops[0], ast.Is)
                        return _scalar({'bool'}, result, True)
                return _scalar({'bool'})
        raise _OpenQuery()

    def truth(self, value):
        if value.kind in ('match', 'optional_callable'):
            return _scalar({'bool'})
        if value.kind == 'callable':
            return _scalar({'bool'}, True, True)
        return value

    def refined(self, test, env, selected):
        if isinstance(test, ast.Name) and env.get(test.id, _Value('unknown')).kind == 'optional_callable':
            env = dict(env)
            env[test.id] = _Value('callable') if selected else _scalar({'NoneType'}, None, True)
            return env
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return self.refined(test.operand, env, not selected)
        if isinstance(test, ast.BoolOp) and (isinstance(test.op, ast.And) == selected):
            for child in test.values:
                env = self.refined(child, env, selected)
            return env
        if (selected and isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                and test.func.attr == 'startswith' and isinstance(test.func.value, ast.Name)
                and len(test.args) == 1 and not test.keywords):
            try:
                prefixes = ast.literal_eval(test.args[0])
            except (ValueError, TypeError):
                raise _OpenQuery()
            prefixes = (prefixes,) if type(prefixes) is str else prefixes
            if not isinstance(prefixes, tuple) or not prefixes or any(type(p) is not str or not p for p in prefixes):
                raise _OpenQuery()
            name = test.func.value.id
            value = env.get(name)
            if value is None or value.kind != 'scalar' or value.shapes != {'str'}:
                raise _OpenQuery()
            env = dict(env)
            env[name] = _string(getattr(value, 'origin', ''), prefixes,
                                getattr(value, 'name_evidence', ()))
        result = super().refine(test, env, selected)
        if result is None:
            raise _OpenQuery()
        return result

    def call(self, node, frame):
        ref, function = self.target
        if (any(keyword.arg is None for keyword in node.keywords)
                or any(isinstance(arg, ast.Starred) for arg in node.args)):
            raise _OpenQuery()
        if node.keywords:
            if not isinstance(node.func, ast.Attribute):
                raise _OpenQuery()
            receiver = self.expression(node.func.value, frame)
            if receiver.kind != 'receiver':
                raise _OpenQuery()
            values = [self.expression(arg, frame) for arg in node.args]
            values.extend(self.expression(keyword.value, frame) for keyword in node.keywords)
            return self.method(node.func.attr, values, frame, node)
        if isinstance(node.func, ast.Name):
            name = node.func.id
            builtin = self.analyzer._builtin_name_status(ref, function, name) == 'confirmed_builtin'
            if (builtin and name == 'max' and len(node.args) == 1
                    and isinstance(node.args[0], ast.GeneratorExp)):
                sequence = self.comprehension(node.args[0], frame)
                if any(value.kind != 'scalar' or value.shapes != {'int'}
                       for value in frame.heap[sequence.heap]['values']):
                    raise _OpenQuery()
                # Empty input raises; summarize only native normal returns.
                return _scalar({'int'})
            values = [self.expression(arg, frame) for arg in node.args]
            if builtin and name == 'isinstance' and len(values) == 2:
                raise _OpenQuery()
            if builtin and name == 'dir' and len(values) == 1 and values[0].kind == 'class':
                return self.container(frame, 'list', [_string('input_class_names',
                    name_evidence=(self.name_step('directory', node),))])
            if (builtin and name in ('getattr', 'hasattr') and len(values) in (
                    (2, 3) if name == 'getattr' else (2,)) and values[0].kind in ('class', 'ancestor_class')):
                member = values[1]
                if (member.kind != 'scalar' or member.shapes != {'str'}
                        or getattr(member, 'origin', '') != 'input_class_names'
                        or not getattr(member, 'prefixes', ())):
                    raise _OpenQuery()
                if len(values) == 3 and not _data(values[2]):
                    raise _OpenQuery()
                ancestor = values[0].kind == 'ancestor_class'
                if ancestor and len(values) == 3 and not (values[2].known and values[2].literal is None):
                    raise _OpenQuery()
                self.member_prefixes.update(member.prefixes)
                lookup = {'caller': asdict(ref), 'operation': name,
                    'call_evidence': _span(ref, node), 'name_source': 'input_class_directory',
                    'member_prefixes': list(member.prefixes), 'name_evidence': list(member.name_evidence),
                    'runtime_lookup_confirmed': False}
                if ancestor:
                    lookup.update(receiver_scope='input_class_mro', presence='unresolved')
                self.member_lookups.append(lookup)
                if name == 'hasattr':
                    if ancestor:
                        return _scalar({'bool'})
                    lookup['result'] = True
                    return _scalar({'bool'}, True, True)
                return _Value('optional_callable' if ancestor and len(values) == 3 else 'callable')
            if builtin and name == 'callable' and len(values) == 1 and values[0].kind == 'callable':
                return _scalar({'bool'}, True, True)
            if builtin and name == 'set' and not values:
                return self.container(frame, 'set')
            if (builtin and name == 'sorted' and len(values) == 1
                    and values[0].kind in ('list', 'set', 'collection_choices')):
                items = frame.heap[values[0].heap]['values']
                if values[0].kind == 'collection_choices':
                    items = [item for choice in items for item in frame.heap[choice.heap]['values']]
                if all(item.kind == 'scalar' and item.shapes == {'str'} for item in items):
                    return self.container(frame, 'list', items)
            if builtin and name == 'len' and len(values) == 1:
                if (values[0].kind == 'parameters' or values[0].kind == 'scalar'
                        and values[0].shapes and values[0].shapes <= {'str', 'NoneType'}):
                    return _scalar({'int'})
            if len(values) == 1 and values[0].kind == 'class':
                proof = iterability_query(self.analyzer, self.target, node.func)
                if proof is not None:
                    canonical, source = proof
                    self.iterability.append({'caller': asdict(ref), 'callee': canonical,
                        'call_evidence': _span(ref, node), 'source_protocol': source})
                    return _scalar({'bool'}, source['result'], True)
        if isinstance(node.func, ast.Attribute):
            # Global stdlib calls are resolved before receiver attributes.
            from ._function_factory import _canonical
            canonical = _canonical(self.analyzer, ref, function, node.func)
            if canonical and len(node.args) == 1 and not node.keywords:
                protocol = iterability_query(self.analyzer, self.target, node.func)
                if protocol is not None:
                    canonical, source = protocol
                    argument = self.expression(node.args[0], frame)
                    if argument.kind != 'class' or source.get(
                            'precondition', {}).get('exact_metaclass') != 'type':
                        raise _OpenQuery()
                    self.iterability.append({'caller': asdict(ref), 'callee': canonical,
                        'call_evidence': _span(ref, node), 'source_protocol': source})
                    return _scalar({'bool'}, source['result'], True)
            if canonical in ('inspect.signature', 'inspect.getdoc'):
                values = [self.expression(arg, frame) for arg in node.args]
                if len(values) != 1 or values[0].kind != 'callable':
                    raise _OpenQuery()
                operation = canonical.rsplit('.', 1)[1]
                self.inspect_names.add(operation)
                self.required_protocols.add('native_signature_resolution_without_user_callbacks'
                    if operation == 'signature' else 'native_documentation_resolution_without_user_callbacks')
                return _Value('signature') if operation == 'signature' else _scalar({'str', 'NoneType'})
            if canonical == 're.search':
                values = [self.expression(arg, frame) for arg in node.args]
                if (len(values) != 2 or values[0].kind != 'scalar' or values[0].shapes != {'str'}
                        or values[1].kind != 'scalar' or not values[1].shapes <= {'str', 'NoneType'}):
                    raise _OpenQuery()
                if namespace(self.analyzer, 're', ('search',)) is None:
                    raise _OpenQuery()
                return _Value('match')
            if canonical == 're.sub':
                values = [self.expression(arg, frame) for arg in node.args]
                if (len(values) != 3 or any(value.kind != 'scalar' or not value.shapes
                                          or not value.shapes <= {'str', 'NoneType'} for value in values)
                        or namespace(self.analyzer, 're', ('sub',)) is None):
                    raise _OpenQuery()
                return _string()
            root = node.func
            while isinstance(root, ast.Attribute):
                root = root.value
            if canonical and isinstance(root, ast.Name) and len(node.args) == 1:
                argument = self.expression(node.args[0], frame)
                if argument.kind == 'class':
                    proof = iterability_query(self.analyzer, self.target, node.func)
                    if proof is not None:
                        qualified, source = proof
                        self.iterability.append({'caller': asdict(ref), 'callee': qualified,
                            'call_evidence': _span(ref, node), 'source_protocol': source})
                        return _scalar({'bool'}, source['result'], True)
            receiver = self.expression(node.func.value, frame)
            name = node.func.attr
            if (receiver.kind == 'scalar' and receiver.shapes == {'str'}
                    and name == 'join' and len(node.args) == 1):
                argument = node.args[0]
                sequence = (self.comprehension(argument, frame) if isinstance(argument, ast.GeneratorExp)
                            else self.expression(argument, frame))
                if (sequence.kind != 'list' or any(value.kind != 'scalar' or value.shapes != {'str'}
                        for value in frame.heap[sequence.heap]['values'])):
                    raise _OpenQuery()
                return _string()
            values = [self.expression(arg, frame) for arg in node.args]
            if receiver.kind == 'receiver':
                return self.method(name, values, frame, node)
            if (receiver.kind == 'scalar' and receiver.shapes
                    and receiver.shapes <= {'str', 'NoneType'} and name == 'ljust' and len(values) == 1
                    and values[0].kind == 'scalar' and values[0].shapes == {'int'}):
                return _string()
            if receiver.kind == 'scalar' and receiver.shapes == {'str'}:
                if name == 'startswith' and len(values) == 1:
                    if values[0].kind == 'prefixes' or values[0].kind == 'scalar' and values[0].shapes == {'str'}:
                        return _scalar({'bool'})
                if name == 'format' and all(value.kind == 'scalar' for value in values):
                    return _string()
                if (name == 'replace' and len(values) == 2
                        and all(value.kind == 'scalar' and value.shapes == {'str'} for value in values)):
                    return _string()
            if receiver.kind == 'match' and name == 'group' and len(values) == 1:
                if values[0].kind == 'scalar' and values[0].shapes <= {'str', 'int'}:
                    return _scalar({'str', 'NoneType'})
            if (receiver.kind == 'pattern' and name == 'search' and len(values) == 1
                    and values[0].kind == 'scalar' and values[0].shapes == {'str'}):
                return _Value('match')
            if receiver.kind in ('list', 'set', 'dict'):
                if receiver.kind == 'dict' and name == 'get' and len(values) == 2:
                    if values[0].kind != 'scalar' or values[0].shapes != {'str'}:
                        raise _OpenQuery()
                    choices = frame.heap[receiver.heap]['values'] + [values[1]]
                    if any(value.kind not in ('list', 'set') for value in choices):
                        raise _OpenQuery()
                    # Keep live alternative references; copying their elements
                    # now would lose a later mutation through another alias.
                    return self.container(frame, 'collection_choices', choices)
                if receiver.heap in self.loop_heaps:
                    raise _OpenQuery()
                if name in ('append', 'add') and len(values) == 1 and _data(values[0]):
                    if (receiver.kind, name) not in (('list', 'append'), ('set', 'add')):
                        raise _OpenQuery()
                    frame.heap[receiver.heap]['values'].append(values[0])
                    return _scalar({'NoneType'}, None, True)
                if receiver.kind == 'dict' and name == 'setdefault' and len(values) == 2:
                    if values[0].kind != 'scalar' or values[0].shapes != {'str'} or values[1].kind != 'set':
                        raise _OpenQuery()
                    frame.heap[receiver.heap]['values'].append(values[1])
                    return values[1]
        raise _OpenQuery()

    def type_test(self, node, frame):
        if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                or node.func.id != 'isinstance' or len(node.args) != 2 or node.keywords):
            return None
        value = self.expression(node.args[0], frame)
        if value.kind != 'class' or not native_class_operand(self.analyzer, self.target[0], node, {}):
            return None
        operand = node.args[1]
        if isinstance(operand, ast.Name) and operand.id in ('type', 'object') and (
                self.analyzer._builtin_name_status(self.target[0], self.target[1], operand.id)
                == 'confirmed_builtin'):
            result = True
        elif isinstance(operand, (ast.Name, ast.Attribute)) and self.analyzer._resolve_class(
                self.target[0], ast.unparse(operand)) is not None:
            result = False
        else:
            raise _OpenQuery()
        self.type_tests.append({'caller': asdict(self.target[0]), 'call_evidence': _span(self.target[0], node),
                                'result': result})
        return _scalar({'bool'}, result, True)

    def method(self, name, values, frame, call):
        matches = self.analyzer._definition_index.find(self.owner.module, self.owner.qualname + '.' + name)
        if len(matches) != 1:
            raise _OpenQuery()
        selected = matches[0]
        parameters = selected[1].args.posonlyargs + selected[1].args.args
        query = metadata_query(self.analyzer, selected) if selected[1].decorator_list else None
        self.method_calls.append({'caller': asdict(self.target[0]), 'target': asdict(selected[0]),
                                  'call_evidence': _span(self.target[0], call)})
        if query is not None:
            _arguments(selected, call, values)
            if len(values) != 1 or values[0].kind != 'callable':
                raise _OpenQuery()
            self.cached |= query['input_effects']['native_cache_retention']
            self.required_protocols.update(query['input_preconditions']['protocols'])
            self.cache_queries.append(query)
            return _scalar(query['result_shapes'])
        if selected[1].decorator_list or not parameters:
            raise _OpenQuery()
        incoming = _arguments(selected, call, values, receiver=True)
        result = self.run(selected, frame, {parameters[0].arg: _Value('receiver'), **incoming})
        if any(path.fields != result[0].fields for path in result[1:]):
            raise _OpenQuery()
        merged = {}
        for path in result:
            for key, container in path.heap.items():
                saved = merged.setdefault(key, {'kind': container['kind'], 'values': []})
                if saved['kind'] != container['kind']:
                    raise _OpenQuery()
                saved['values'].extend(value for value in container['values'] if value not in saved['values'])
        frame.fields, frame.heap = result[0].fields, merged
        returns = [path.result for path in result]
        if all(value == returns[0] for value in returns):
            return returns[0]
        if all(value.kind == 'scalar' for value in returns):
            return _scalar(set().union(*(value.shapes for value in returns)))
        raise _OpenQuery()

    def block(self, body, frames, depth=0):
        if depth > 48 or len(frames) > 64:
            raise _OpenQuery()
        for node in body:
            pending = []
            for frame in frames:
                if frame.control != 'normal':
                    pending.append(frame)
                    continue
                self.charge()
                if isinstance(node, ast.Expr):
                    if not isinstance(node.value, ast.Constant):
                        self.expression(node.value, frame)
                elif isinstance(node, ast.Pass):
                    pass
                elif isinstance(node, ast.Assign):
                    value = self.expression(node.value, frame)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            frame.env[target.id] = value
                        elif (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                                and frame.env.get(target.value.id, _Value('unknown')).kind == 'receiver'
                                and not self.loop_heaps and target.attr not in self.names
                                and not target.attr.startswith('__') and (_data(value) or value.kind == 'class')):
                            frame.fields[target.attr] = value
                        else:
                            raise _OpenQuery()
                elif isinstance(node, ast.Return):
                    frame.result = self.expression(node.value, frame)
                    frame.control = 'return'
                elif isinstance(node, (ast.Continue, ast.Break)):
                    if not self.loop_heaps:
                        raise _OpenQuery()
                    frame.control = 'continue' if isinstance(node, ast.Continue) else 'break'
                elif isinstance(node, ast.If):
                    test = self.type_test(node.test, frame) or self.expression(node.test, frame)
                    test = self.truth(test)
                    if not _data(test):
                        raise _OpenQuery()
                    choices = [bool(test.literal)] if test.known else [True, False]
                    for chosen in choices:
                        local = copy.deepcopy(frame)
                        local.env = self.refined(node.test, local.env, chosen)
                        branch = node.body if chosen else node.orelse
                        pending.extend(self.block(branch, [local], depth + 1))
                    continue
                elif isinstance(node, ast.For):
                    if not isinstance(node.target, ast.Name):
                        raise _OpenQuery()
                    assigned = statement_scope_facts(node.body).bound - {node.target.id}
                    if assigned & frame.env.keys():
                        raise _OpenQuery()
                    iterable = self.expression(node.iter, frame)
                    element = self.element(frame, iterable)
                    zero, once = copy.deepcopy(frame), copy.deepcopy(frame)
                    once.env[node.target.id] = element
                    prior = set(self.loop_heaps)
                    self.loop_heaps.add(iterable.heap)
                    try:
                        branches = self.block(node.body, [once], depth + 1)
                    finally:
                        self.loop_heaps = prior
                    # Exhaustion executes else; break exits this loop only.
                    # Keep both zero and symbolic iteration paths, including
                    # all effects from the body before selecting its exit.
                    exhausted = [zero]
                    for branch in branches:
                        if branch.control == 'break':
                            branch.control = 'normal'
                            pending.append(branch)
                        elif branch.control in ('normal', 'continue'):
                            branch.control = 'normal'
                            exhausted.append(branch)
                        else:
                            pending.append(branch)
                    pending.extend(self.block(node.orelse, exhausted, depth + 1))
                    continue
                else:
                    raise _OpenQuery()
                pending.append(frame)
            frames = pending
        return frames

    def run(self, selected, frame, env):
        if selected[0] in self.stack or len(self.stack) >= 16:
            raise _OpenQuery()
        previous = self.target
        self.target = selected
        self.stack.append(selected[0])
        local = _Frame(dict(env), copy.deepcopy(frame.fields), copy.deepcopy(frame.heap))
        try:
            result = self.block(selected[1].body, [local])
            for path in result:
                if path.control == 'normal':
                    path.result = _scalar({'NoneType'}, None, True)
                elif path.control != 'return':
                    raise _OpenQuery()
            return result
        finally:
            self.stack.pop()
            self.target = previous


## Describe a whole private observer query under native class-metadata protocols.
#  @param analyzer Fixed source snapshot and explicit support dependency registry.
#  @param owner Exact source observer class; input class is a separate obligation.
#  @param name Selected instance method, without library-specific naming rules.
#  @param positional_literals Exact native literal arguments at the proposed query.
#  @param keyword_literals Exact native literal keyword arguments at that query.
#  @return Conditional source effects, or None for open state, callbacks or budgets.
def observer_query(analyzer, owner, name, *, positional_literals=(), keyword_literals=None):
    if keyword_literals is None:
        keyword_literals = {}
    if (not isinstance(positional_literals, (tuple, list)) or len(positional_literals) > 64
            or not isinstance(keyword_literals, dict) or len(keyword_literals) > 64
            or any(not _literal(value) for value in positional_literals)
            or any(type(key) is not str or not key.isidentifier() or not _literal(value)
                   for key, value in keyword_literals.items())):
        return None
    key = (owner[0], name,
           tuple((type(value).__name__, value) for value in positional_literals),
           tuple((name, type(value).__name__, value) for name, value in sorted(keyword_literals.items())))
    cache = analyzer._metadata_observer_cache
    if key not in cache:
        cache[key] = None
        cache[key] = _observer_query(analyzer, owner, name, positional_literals, keyword_literals)
    return copy.deepcopy(cache[key])


## Publish conditional observer facts for explicit source metadata iteration.
#  @param analyzer Fixed source/index generation and caller query budget.
#  @param target Exact selected source method; existing flow boundaries stay intact.
#  @return Optional templates without inferring any actual entry receiver state.
def observer_effects(analyzer, target):
    ref, function = target
    if not isinstance(function, ast.FunctionDef) or function.decorator_list:
        return []
    parameters = function.args.posonlyargs + function.args.args
    if len(parameters) != 1:
        return []
    owner_name = ref.qualname.rpartition('.')[0]
    if not owner_name:
        return []
    candidate = False
    for index, node in enumerate(ast.walk(function)):
        if index > 2000:
            return []
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dir'
                and len(node.args) == 1 and isinstance(node.args[0], ast.Attribute)
                and isinstance(node.args[0].value, ast.Name)
                and node.args[0].value.id == parameters[0].arg):
            candidate = True
    if not candidate:
        return []
    owners = analyzer._definition_index.find(ref.module, owner_name, kind='class')
    if len(owners) != 1 or function not in owners[0][1].body:
        return []
    fact = observer_query(analyzer, owners[0], function.name)
    return [fact] if fact is not None else []


def _observer_query(analyzer, owner, name, positional_literals, keyword_literals):
    ref, cls = owner
    forbidden = {'__new__', '__del__', '__getattribute__', '__getattr__', '__setattr__',
                 '__delattr__', '__slots__', '__dict__', '__class__'}
    if forbidden & statement_scope_facts(cls.body).bound:
        return None
    init = analyzer._definition_index.find(ref.module, ref.qualname + '.__init__')
    target = analyzer._definition_index.find(ref.module, ref.qualname + '.' + name)
    if len(init) != 1 or len(target) != 1:
        return None
    binding = _entry(analyzer, target[0], declaration_only=True)
    if binding is None:
        return None
    params = init[0][1].args.posonlyargs + init[0][1].args.args
    if (len(params) != 2 or init[0][1].decorator_list or init[0][1].args.defaults
            or init[0][1].args.vararg or init[0][1].args.kwarg or init[0][1].args.kwonlyargs):
        return None
    proof = _Observer(analyzer, owner)
    try:
        if not builtin_namespace(analyzer, ref)[0]:
            return None
        paths = proof.run(init[0], _Frame(), {params[0].arg: _Value('receiver'), params[1].arg: _Value('class')})
        invocation = ast.Call(func=ast.Name(id=name, ctx=ast.Load()),
            args=[ast.Constant(value=value) for value in positional_literals],
            keywords=[ast.keyword(arg=key, value=ast.Constant(value=value))
                      for key, value in sorted(keyword_literals.items())])
        values = [_scalar({type(value).__name__}, value, True)
                  for value in list(positional_literals) + [value for _, value in sorted(keyword_literals.items())]]
        incoming = _arguments(target[0], invocation, values, receiver=True)
        explicit = {record['parameter'] for record in bind_ast_call(invocation,
            FunctionSignature.from_ast(target[0][1].args,
                (target[0][1].args.posonlyargs + target[0][1].args.args)[1:]))[0]}
        defaults = {key: value.literal for key, value in incoming.items() if key not in explicit}
        outputs = []
        fields = set()
        for path in paths:
            if path.result.kind != 'scalar' or path.result.shapes != {'NoneType'}:
                return None
            fields.update(key for key, value in path.fields.items() if value.kind == 'class')
            parameters = target[0][1].args.posonlyargs + target[0][1].args.args
            if not parameters or target[0][1].decorator_list:
                return None
            outputs.extend(proof.run(target[0], path, {parameters[0].arg: _Value('receiver'), **incoming}))
        for path in outputs:
            fields.update(key for key, value in path.fields.items() if value.kind == 'class')
        if namespace(analyzer, 'inspect', proof.inspect_names) is None:
            return None
        kinds = {path.result.kind for path in outputs}
        if kinds == {'list'}:
            if any(any(value.kind != 'scalar' or value.shapes != {'str'}
                       for value in path.heap[path.result.heap]['values']) for path in outputs):
                return None
            shape = 'native_string_list'
        elif kinds == {'dict'}:
            if any(any(value.kind != 'set' or any(element.kind != 'scalar' or element.shapes != {'str'}
                       for element in path.heap[value.heap]['values'])
                       for value in path.heap[path.result.heap]['values']) for path in outputs):
                return None
            shape = 'native_string_set_mapping'
        else:
            return None
    except (_OpenQuery, _ClassEffectLimit):
        return None
    hashes = {**analyzer.hashes, **analyzer._supporting_source_hashes}
    assumptions = set(binding['assumptions']) | {'source_snapshot_bindings_hold',
        'source_private_metadata_observer', 'standard_library_callable_metadata_protocols',
        'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
        'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_module_mutation',
        'no_unmodeled_indirect_function_mutation'}
    for query in proof.iterability:
        assumptions.update(query['source_protocol']['assumptions'])
    for query in proof.cache_queries:
        assumptions.update(query['assumptions'])
    for member in proof.native_data_members.values():
        assumptions.update(member['creation']['assumptions'])
    return {'kind': 'source_private_class_metadata_observer', 'status': 'requires_native_class_metadata',
        'owner_class': asdict(ref), 'target': asdict(target[0][0]), 'owner_binding': binding,
        'constructor_evidence': _span(*init[0]), 'method_evidence': _span(*target[0]),
        'completion': 'normal_return_only', 'runtime_execution_confirmed': False,
        'receiver_lifetime': 'single_private_query',
        'input_preconditions': {'exact_metaclass': 'type', 'member_prefixes': sorted(proof.member_prefixes),
            **({'ancestry': 'native_type_mro_with_unchanged_member_namespaces',
                'ancestor_matching_members': 'native_python_functions_or_methods_or_absent'}
               if proof.mro_queries else {}),
            'member_namespace': 'unchanged_during_query',
            'observer_members': 'source_declarations_hold',
            'observer_data_members': 'source_creation_values_preserved',
            'matching_members': 'native_python_functions_or_methods',
            'metadata_results': {'signature': 'native_inspect_signature',
                                 'documentation': 'native_builtin_str_or_none',
                                 'directory': 'native_builtin_string_names',
                                 **({'code': 'native_code_with_native_string_varnames'}
                                    if 'native_python_code_metadata_without_user_callbacks'
                                    in proof.required_protocols else {})},
            'native_function_metadata_protocols': sorted(proof.required_protocols)},
        'input_effects': {'source_writes': [], 'source_exposures': [],
            'private_receiver_fields': sorted(fields), 'native_cache_retention': proof.cached},
        'result_shape': shape,
        'query_arguments': {'binding': 'exact_source_signature',
            'positional': list(positional_literals), 'keywords': dict(keyword_literals), 'defaults': defaults},
        'native_iterability_queries': proof.iterability,
        'native_type_tests': proof.type_tests, 'method_calls': proof.method_calls,
        'native_member_lookups': proof.member_lookups,
        'native_mro_queries': proof.mro_queries,
        'native_data_members': list(proof.native_data_members.values()),
        'callable_metadata_queries': proof.cache_queries,
        'source_hashes': dict(sorted(hashes.items())), 'assumptions': sorted(assumptions)}
