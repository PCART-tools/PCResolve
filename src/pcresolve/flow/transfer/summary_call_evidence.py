## @package pcresolve.flow.transfer.summary_call_evidence
## @brief Call Evidence operations for query-local flow summaries.

import ast
from dataclasses import asdict
from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.flow.transfer._summary_support import _unique


class CallEvidenceMixin:
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

    def module_callable_evidence(self, facts, node):
        ref = facts['module_ref']
        arguments = []
        for record in facts['arguments']:
            expression = record['node']
            source = {'kind': 'expression', 'text': ast.unparse(expression)}
            assignments = []
            if isinstance(expression, ast.Constant):
                source = {'kind': 'literal', 'value': expression.value}
            elif isinstance(expression, ast.Name):
                imported = self.analyzer.imports.get(ref.module, {}).get(expression.id)
                if expression.id in self.analyzer.module_bindings.get(ref.module, set()):
                    source = {'kind': 'module_symbol',
                              'qualified_name': ref.module + '.' + expression.id}
                    for statement in facts['source_body']:
                        if statement.lineno > facts['assignment'].lineno or not isinstance(
                                statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                            continue
                        targets = (statement.targets if isinstance(statement, ast.Assign)
                                   else [statement.target])
                        for target in targets:
                            root = target
                            while isinstance(root, (ast.Subscript, ast.Attribute)):
                                root = root.value
                            if isinstance(root, ast.Name) and root.id == expression.id:
                                assignments.append(self.evidence_at(ref, statement))
                                break
                elif imported:
                    source = {'kind': 'import', 'qualified_name': imported}
                else:
                    source = {'kind': 'unresolved', 'name': expression.id}
            arguments.append({
                'argument': record['argument'], 'parameter': record['parameter'],
                'source': source, 'expression': ast.unparse(expression),
                'evidence': self.evidence_at(ref, expression),
                'source_assignments': assignments})
        return {'qualified_name': facts['qualified_name'],
                'instance_type': asdict(facts['class_ref']),
                'assignment': self.evidence_at(ref, facts['assignment']),
                'constructor': self.evidence_at(ref, facts['constructor']),
                'constructor_arguments': arguments,
                'call': self.evidence(node)}

    def marked(self, values, node, relation=None):
        result = [dict(v, relation=relation or v['relation'], evidence=v['evidence'] + [self.evidence(node)],
                       conditions=v.get('conditions', []) + list(self.conditions)) for v in values]
        if relation and relation != 'direct':
            for value in result:
                value.pop('python_shape', None)
                value.pop('container_object', None)
        return result

    def affected_values(self, values, env):
        roots = []
        unknown = False
        pending = list(self.materialize(values, env))
        expanded_calls = set()
        while pending:
            value = pending.pop(0)
            if (value.get('container_object')
                    and self.container_values([value])[0]['kind'] == 'container'):
                continue  # Its element roots have already been materialized.
            if value.get('kind') == 'call_result':
                source = value.get('source')
                call = next((item for item in self.calls
                             if item.id == source), None)
                if call is not None and source not in expanded_calls:
                    expanded_calls.add(source)
                    if call.result_sources:
                        pending.extend(self.materialize(call.result_sources, env))
                    else:
                        # An opaque callee can return a value from any input it
                        # receives, but cannot read an unpassed local parameter.
                        # Include lexical captures for locally defined callees.
                        # 不透明调用可能返回其接收的实参或词法捕获，但不能读取未传入的局部参数。
                        pending.extend(value for argument in call.argument_sources
                                       for value in argument.get('sources', []))
                        pending.extend(call.receiver_sources)
                        pending.extend(value for capture in call.capture_bindings
                                       for value in capture.get('sources', []))
                    continue
            if value.get('kind') in ('parameter', 'capture'):
                root = {'kind': value['kind'], 'name': value['source'],
                        'element_path': value.get(
                            'output_path', value.get('projection', []))}
                if root not in roots:
                    roots.append(root)
            elif value.get('kind') not in ('import', 'key', 'callable'):
                unknown = True
        return roots, unknown

    def add_boundary(self, reason, node, env, values=(), **fields):
        roots, unknown = self.affected_values(values, env)
        record = {'function': asdict(self.ref), 'reason': reason,
                  'evidence': self.evidence(node),
                  'affected_scope': 'unknown' if unknown else
                                    'known' if roots else 'none',
                  'affected_values': roots}
        record.update(fields)
        self.result.boundaries.append(record)

    def callable_value(self, target, node, defaults=None):
        return {'kind': 'callable', 'source': target.qualname, 'module': target.module,
                'defaults': defaults or {}, 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}

    def bind_call_arguments(self, node, params, positional, call):
        records, reasons = bind_ast_call(node, FunctionSignature.from_ast(params, positional))
        self.result.boundaries.extend({'call_id': call.id, 'reason': reason} for reason in reasons)
        for record in records:
            if record['status'] == 'missing':
                call.binding_issues.append({
                    'kind': 'missing_required', 'parameter': record['parameter']})
            elif record['status'] == 'duplicate':
                call.binding_issues.append({
                    'kind': 'duplicate_binding', 'parameter': record['parameter'],
                    'argument': record['argument'],
                    'conflicts_with': record.get('conflicts_with')})
            elif (record['status'] == 'unresolved'
                  and record['binding_kind'] not in (
                      'dynamic_starred', 'dynamic_keyword')):
                call.binding_issues.append({
                    'kind': 'unresolved_argument', 'argument': record['argument']})
        if 'dynamic_argument_expansion' in reasons:
            call.binding_issues.append({'kind': 'dynamic_expansion'})
        call.binding_issues = _unique(call.binding_issues)
        call.binding_status = ('invalid' if any(
            issue['kind'] in ('missing_required', 'duplicate_binding', 'unresolved_argument')
            for issue in call.binding_issues) else
            'uncertain' if call.binding_issues else 'complete')
        return records
