## @package pcresolve.flow.proofs.classes._class_read_binding
#  Prove restricted class attribute reads.
#
#
#  Source invariants for class attributes which cannot invoke descriptors.
#  为不会触发描述符的类属性读取建立源码不变式。



import ast
import copy
from dataclasses import asdict, replace

from pcresolve.flow.proofs.classes._class_definition import _literal, namespace_issues
from pcresolve.flow.proofs.classes._class_name_binding import _global_calls, _readonly_call, _write_name
from pcresolve.flow.proofs.protocols.class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from pcresolve.facts.scope_facts import statement_scope_facts


## Apply Python private-name mangling for a class member.
## 按 Python 规则对类成员执行私有名称改写。
#
#  @param name Declared attribute or method name.
#  @param cls Class definition providing the mangling context.
#  @return Mangled storage name, or the original name when no mangling applies.
def _attribute(name, cls):
    owner = cls.name.lstrip('_')
    if name.startswith('__') and not name.endswith('__') and owner:
        return '_' + owner + name
    return name


## Prove absence or a builtin literal payload, without claiming presence or contents.
## 证明属性缺失或其值为内建字面量，但不声称属性存在或其内容已知。
#
#  @param summary Caller summary with an exact, uninvalidated source class argument.
#  @param identity Source class object selected for the helper.
#  @param definition Selected helper definition.
#  @param parameter Helper's bound ordinary class parameter.
#  @param call Actual helper call receiving this premise.
#  @param node Caller AST call, used to distinguish its explicitly inspected edge.
#  @param attribute Finite ordinary attribute name read by the helper.
#  @return Conditional source invariant with explicit issues and snapshot evidence.
def source_binding(summary, identity, definition, parameter, call, node, attribute):
    analyzer = summary.analyzer
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    if not hierarchy or len(hierarchy) > 64:
        return None
    ref, cls = hierarchy[0]
    issues, evidence = [], []

    ## Record a unique issue together with the supporting source location.
    ## 记录唯一的问题及其对应源码位置。
    #
    #  @param reason Machine-readable reason the invariant could not be proved.
    #  @param owner Class owning the source location.
    #  @param source AST node supporting the issue.
    #  @return None; the issue is appended only once.
    def issue(reason, owner=ref, source=cls):
        value = {'reason': reason, 'evidence': summary.evidence_at(owner, source)}
        if value not in issues:
            issues.append(value)

    if (not isinstance(attribute, str) or not attribute or len(attribute) > 2000
            or attribute == 'mro' or attribute.startswith('__') and attribute.endswith('__')):
        issue('class_read_protocol_attribute')
    if analyzer.index_boundaries:
        issue('class_read_source_scope_incomplete')
    inspected = 0
    structural = {'__class__', '__bases__'} | {_attribute(member.name, source) for _, source in hierarchy
        for member in source.body if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))}
    methods = structural - {'__class__', '__bases__'}
    checked_methods = set()

    # Audit every class in MRO order, retaining issues instead of guessing through open cases.
    # 按 MRO 顺序审计每个类；遇到开放情况时保留问题，不做猜测。
    for owner, source_class in hierarchy:
        if ('.' in owner.qualname or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
                or analyzer.definition_conditions.get(owner)):
            issue('class_read_source_binding_unconfirmed', owner, source_class)
        if source_class.keywords or source_class.decorator_list:
            issue('class_read_type_lookup_unconfirmed', owner, source_class)
        if owner != ref and '__init_subclass__' in statement_scope_facts(source_class.body).bound:
            issue('class_read_creation_hook', owner, source_class)
        evidence.append(summary.evidence_at(owner, source_class))
        for item in ast.walk(source_class):
            inspected += 1
            analyzer._class_effect_fact_steps -= 1
            if inspected > 2000 or analyzer._class_effect_fact_steps < 0:
                raise _ClassEffectLimit()
        bound = set()
        for member in source_class.body:
            names = {_attribute(name, source_class) for name in statement_scope_facts([member]).bound}
            if names & bound or names & methods and not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issue('class_read_namespace_rebinding', owner, member)
            bound.update(names)
            if attribute in names:
                if not (isinstance(member, (ast.Assign, ast.AnnAssign))
                        and (member.value is None or _literal(member.value))):
                    issue('class_read_namespace_value_unconfirmed', owner, member)
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            method = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)

            ## Charge work to the shared class-effect budget.
            ## 将工作量计入共享的类效果预算。
            #
            #  @param count Number of syntax nodes inspected for the method.
            #  @return None; the shared remaining budget is reduced in place.
            def charge(count):
                analyzer._class_effect_fact_steps -= count

            spelling = _attribute(member.name, source_class)
            if spelling not in checked_methods:
                checked_methods.add(spelling)
                parameters = member.args.posonlyargs + member.args.args

                # Induction over ordinary MRO method lookup: each selected body
                # preserves the invariant without exposing its receiver. Explicit
                # super/descriptor access is outside this closed call subset.
                # 对普通 MRO 方法查找逐层归纳：选中的方法体必须维持不变式且不暴露接收者。
                # 显式 super 或描述符访问不属于当前封闭调用子集。
                proof = class_attribute_writes(member, parameters[0].arg if parameters else '$receiver',
                    lambda name: analyzer._builtin_name_status(method, member, name) == 'confirmed_builtin',
                    lambda value: False, owner=source_class.name,
                    max_nodes=min(2000, analyzer._class_effect_fact_steps), charge=charge,
                    class_read=lambda name: name == attribute, class_calls=methods)
                if proof is None:
                    issue('class_read_method_effect_unconfirmed', method, member)

            # Inspect reflective writes and direct mutations that could change the queried payload.
            # 检查可能改变目标属性值的反射式写入和直接变更。
            parents = {child: parent for parent in ast.walk(member) for child in ast.iter_child_nodes(parent)}
            for item, parent in parents.items():
                if isinstance(item, ast.Attribute):
                    if item.attr in ('setattr', 'delattr', '__setattr__', '__delattr__', '__dict__'):
                        issue('class_read_reflective_write_unconfirmed', method, item)
                    if isinstance(item.ctx, (ast.Store, ast.Del)):
                        spelling = _attribute(item.attr, source_class)
                        if spelling in structural:
                            issue('class_read_structural_write', method, item)
                        elif spelling == attribute and not (isinstance(item.ctx, ast.Del)
                                or isinstance(parent, (ast.Assign, ast.AnnAssign))
                                and (parent.value is None or _literal(parent.value))):
                            issue('class_read_payload_write_unconfirmed', method, item)
                if isinstance(item, ast.Name) and item.id in ('setattr', 'delattr'):
                    if not (isinstance(parent, ast.Call) and parent.func is item):
                        issue('class_read_reflective_alias', method, item)
                if not (isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                        and item.func.id in ('setattr', 'delattr')):
                    continue
                name = (_write_name(item.args[1], member, item.args[0].id, None, item.lineno)
                        if len(item.args) >= 2 and isinstance(item.args[0], ast.Name) else None)
                if (name is None or name in structural or analyzer._builtin_name_status(
                        method, member, item.func.id) != 'confirmed_builtin'):
                    issue('class_read_dynamic_write_unconfirmed', method, item)
                elif name == attribute and (item.keywords or len(item.args) != (
                        3 if item.func.id == 'setattr' else 2) or item.func.id == 'setattr'
                        and not _literal(item.args[2])):
                    issue('class_read_payload_write_unconfirmed', method, item)
    for reason, owner, source in namespace_issues(analyzer, hierarchy):
        issue('class_read_' + reason, owner, source)
    writes, truncated = ([], False) if issues else analyzer._class_binding_writes(include_escapes=True)
    if truncated:
        raise _ClassEffectLimit()
    owners = {owner for owner, _ in hierarchy}

    # Allow only the active read call or a proven readonly call to observe the class.
    # 仅允许当前读取调用或已证明只读的调用观察该类。
    for written, name, reason, owner, source in writes:
        if written not in owners:
            continue
        if reason == 'visible_class_escape':
            current = ((owner.module, owner.qualname, owner.file_path)
                       == (summary.ref.module, summary.ref.qualname, summary.ref.file_path)
                       and summary.evidence_at(owner, source) == summary.evidence(node))
            if current or _readonly_call(analyzer, owner, source):
                continue
            issue('class_read_source_escape', owner, source)
        else:
            issue('class_read_visible_write', owner, source)
    for owner, source in (() if issues else _global_calls(analyzer)):
        for value in ast.walk(source):
            if isinstance(value, (ast.Name, ast.Attribute)):
                name = ast.unparse(value)
                match = analyzer._resolve_class(owner, name) or analyzer._class_symbol(owner.module + '.' + name)
                if match and match[0] in owners:
                    issue('class_read_global_activity', owner, source)
                    break
    return {'kind': 'class_attribute_read_invariant', 'status': 'unconfirmed' if issues else 'source_bound',
        'basis': 'source_snapshot', 'attribute': attribute, 'value_phase': 'call_entry',
        'state': 'absent_or_builtin_literal', 'runtime_value_confirmed': False,
        'receiver_class': copy.deepcopy(identity), 'target': asdict(definition[0]),
        'parameter': parameter, 'call_id': call.id, 'call_evidence': summary.evidence(node),
        'evidence': evidence, 'source_hashes': dict(sorted(analyzer.hashes.items())),
        'source_scope': 'analysis_source_snapshot', 'issues': issues,
        'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_attribute_reads',
            'source_snapshot_class_attribute_invariant', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_class_mutation']}
