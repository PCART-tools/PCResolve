## @package pcresolve.flow.transfer.summary_call_evidence
#  Record call evidence and boundaries for flow summaries.
#
#
#  Provides call-site evidence, callable facts and boundary records on the current summary.
#  为当前摘要记录调用点证据、可调用对象事实和分析边界。



import ast
from dataclasses import asdict
from pcresolve.flow.transfer._summary_support import _unique
from pcresolve.flow.transfer.call_binding_state import CallBindingMixin
from pcresolve.flow.transfer.source_evidence import SourceEvidenceMixin


## Record call-site evidence and analysis boundaries on flow summaries.
## 在流摘要中记录调用点证据和分析边界。
class CallEvidenceMixin(CallBindingMixin, SourceEvidenceMixin):
    ## Build constructor call evidence for a module-level callable assignment.
    ## 为模块级可调用赋值构造其构造调用证据。
    #
    #  @param facts Collected module callable facts with reference and arguments.
    #  @param node Source call node that produced the assignment.
    #  @return Evidence with qualified name, constructor arguments and assignment.
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

    ## Annotate values with a relation, the node's evidence and conditions.
    ## 为值补充关系、节点证据和当前条件。
    #
    #  @param values Value facts to annotate.
    #  @param node Source node whose evidence is appended.
    #  @param relation Optional relation replacing the value's own relation.
    #  @return Annotated copies; non-direct relations drop shape hints.
    def marked(self, values, node, relation=None):
        result = [dict(v, relation=relation or v['relation'], evidence=v['evidence'] + [self.evidence(node)],
                       conditions=v.get('conditions', []) + list(self.conditions)) for v in values]
        if relation and relation != 'direct':
            for value in result:
                value.pop('python_shape', None)
                value.pop('container_object', None)
        return result

    ## Collect the parameter and capture roots reached by the given values.
    ## 收集给定值可达的参数根与捕获根。
    #
    #  @param values Value facts whose dependencies are inspected.
    #  @param env Environment used to materialize values and call results.
    #  @return Parameter and capture roots plus an unknown-source flag.
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

    ## Append a boundary record with the scope affected by the given values.
    ## 追加边界记录，并标注给定值受影响的范围。
    #
    #  @param reason Stable boundary reason stored in the summary.
    #  @param node Source node that triggered the boundary.
    #  @param env Environment used to resolve affected values.
    #  @param values Value facts describing the affected scope.
    #  @param fields Extra boundary fields merged into the record.
    #  @return None
    def add_boundary(self, reason, node, env, values=(), **fields):
        roots, unknown = self.affected_values(values, env)
        record = {'function': asdict(self.ref), 'reason': reason,
                  'evidence': self.evidence(node),
                  'affected_scope': 'unknown' if unknown else
                                    'known' if roots else 'none',
                  'affected_values': roots}
        record.update(fields)
        self.result.boundaries.append(record)

    ## Build a callable value fact for a resolved source function.
    ## 为已解析的源码函数构造可调用值事实。
    #
    #  @param target Function reference stored as the value source.
    #  @param node Source node providing the callable evidence.
    #  @param defaults Optional default value facts keyed by parameter name.
    #  @return Callable value fact with identity, defaults and conditions.
    def callable_value(self, target, node, defaults=None):
        return {'kind': 'callable', 'source': target.qualname, 'module': target.module,
                'defaults': defaults or {}, 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}
