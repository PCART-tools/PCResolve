## @package pcresolve.flow.proofs.callables._constructor_entry
#  Describe source constructor entry bindings.
#
#
#  Source class query bindings, separate from actual call-site evidence.
#  描述源码类查询绑定，并与真实调用点证据分离。



import ast
from dataclasses import asdict

from pcresolve.facts.effect_facts import contains_yield
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.flow.proofs.classes._class_definition import (namespace_issues, _source_function_decoration,
                                _source_callable_object_identity,
                                source_identity_factory_wrapper_chain)
from pcresolve.flow.proofs.callables._function_factory import factory_wrapper
from pcresolve.flow.proofs.callables._constructor_retention import retained_stores
from pcresolve.flow.proofs.classes._class_decoration import constructor_decorations
from pcresolve.flow.proofs.classes._class_creation import creation_effects
from pcresolve.flow.proofs.callables._fresh_receiver import allocation_origin


## Recognize a narrow imported typing.overload declaration.
## 识别有限形式的已导入 typing.overload 声明。
#
#  @param analyzer Analyzer containing import and source binding facts.
#  @param owner Class reference containing the declaration.
#  @param cls Class AST whose preceding bindings are inspected.
#  @param member Candidate overload declaration.
#  @return True only when the overload marker and declaration remain unambiguous.
def _overload_declaration(analyzer, owner, cls, member):
    if (not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], (ast.Name, ast.Attribute))):
        return False
    name = ast.unparse(member.decorator_list[0])
    head, dot, rest = name.partition('.')
    imported = analyzer.imports.get(owner.module, {}).get(head, '')
    if (imported + (dot + rest if dot else '') != 'typing.overload'
            or 'typing' in analyzer.module_bodies
            or not analyzer._stable_import_name(owner.module + '.' + head)):
        return False
    for previous in cls.body:
        if previous is member:
            break
        if head in statement_scope_facts([previous]).bound:
            return False
    parameters = member.args.posonlyargs + member.args.args + member.args.kwonlyargs
    parameters += [arg for arg in (member.args.vararg, member.args.kwarg) if arg is not None]
    annotations = [arg.annotation for arg in parameters] + [member.returns]
    defaults = member.args.defaults + [d for d in member.args.kw_defaults if d is not None]
    return (all(value is None or isinstance(value, (ast.Name, ast.Constant))
                for value in annotations)
            and all(isinstance(value, ast.Constant) for value in defaults))


## Collect class-definition issues across the selected constructor hierarchy.
## 收集选定构造器继承层级中的类定义问题。
#
#  @param analyzer Analyzer providing namespace and declaration checks.
#  @param hierarchy Ordered class references and definitions to inspect.
#  @param dependencies Optional set collecting supporting source paths.
#  @param assumptions Optional set collecting discharged source premises.
#  @return Namespace issues as source-located records.
def _definition_issues(analyzer, hierarchy, dependencies=None, assumptions=None):
    return namespace_issues(analyzer, hierarchy,
        declaration=lambda owner, cls, member: _overload_declaration(analyzer, owner, cls, member),
        dependencies=dependencies, assumptions=assumptions if assumptions is not None else set())


## Select a direct member or one final implementation after proven typing stubs.
## 在已证明的 typing 存根之后选择直接成员或唯一最终实现。
#
#  @param analyzer Source generation and import bindings.
#  @param owner Class reference owning the member.
#  @param cls Class definition whose direct statements determine binding order.
#  @param name Member name, without inherited fallback.
#  @return Exact function pair, or None for ambiguous/assigned/effectful members.
def source_member(analyzer, owner, cls, name):
    members = [member for member in cls.body if name in statement_scope_facts([member]).bound]
    implementations = [member for member in members
                       if not _overload_declaration(analyzer, owner, cls, member)]
    if (not members or len(implementations) != 1 or members[-1] is not implementations[0]
            or not isinstance(implementations[0], (ast.FunctionDef, ast.AsyncFunctionDef))
            or implementations[0].name != name):
        return None
    matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
    return next((item for item in matches if item[1] is implementations[0]), None)


## Describe the first supported invocation of a queried source class.
## 描述被查询源码类的首个受支持调用。
#
#  @param analyzer Fixed source generation and bounded lookup machinery.
#  @param class_target Exact source class reference and definition.
#  @param target Selected allocator or ordinary initializer definition.
#  @return Source-only entry binding; no fabricated call site or initialized state.
def binding(analyzer, class_target, target):
    class_ref, cls = class_target
    ref, method = target
    phase = method.name
    issues = []

    ## Record a unique constructor-entry issue with optional source evidence.
    ## 记录构造入口中的唯一问题，并可附带源码证据。
    #
    #  @param reason Machine-readable reason the entry premise failed.
    #  @param owner Optional class owning the evidence node.
    #  @param source Optional AST node supporting the issue.
    #  @return None; the issue is appended only once.
    def issue(reason, owner=None, source=None):
        item = {'reason': reason}
        if source is not None:
            item['evidence'] = {'file_path': owner.file_path,
                'lineno': source.lineno, 'col_offset': source.col_offset,
                'end_lineno': source.end_lineno, 'end_col_offset': source.end_col_offset}
        if item not in issues:
            issues.append(item)

    hierarchy = analyzer._class_mro(class_ref.module, class_ref.qualname)
    if not hierarchy or len(hierarchy) > 64:
        issue('constructor_mro_unconfirmed')
    checked = (hierarchy or [])[:64]
    definition_paths = set()
    definition_assumptions = set()

    # Check class declarations and bounded MRO before interpreting constructor binding.
    # 解释构造器绑定前，先检查类声明和有界 MRO。
    try:
        for reason, owner, source in _definition_issues(
                analyzer, checked, definition_paths, definition_assumptions):
            issue('constructor_' + reason, owner, source)
    except _ClassEffectLimit:
        issue('constructor_class_definition_budget')
    if not analyzer._stable_import_name(class_ref.module + '.' + class_ref.qualname):
        issue('constructor_class_origin_unconfirmed')
    decorations = []
    for owner, base in checked:
        facts = constructor_decorations(analyzer, (owner, base))
        if base.keywords or facts is None or analyzer.definition_conditions.get(owner):
            issue('constructor_class_lookup_customization')
        for fact in facts or []:
            decorations.append(fact)
            definition_paths.update(fact['source_hashes'])
            definition_assumptions.update(fact['assumptions'])
    hooks = creation_effects(analyzer, class_target) if checked else None
    if hooks is None:
        issue('constructor_class_creation_hook')
    for fact in hooks or []:
        definition_paths.update(fact['source_hashes'])
        definition_assumptions.update(fact['assumptions'])
    parameters = method.args.posonlyargs + method.args.args
    if not parameters:
        issue('implicit_receiver_parameter_missing')
    if not isinstance(method, ast.FunctionDef) or contains_yield(method):
        issue('constructor_entry_deferred')
    constructor_wrapper_forwarding = None

    # Establish descriptor and identity preservation for the selected phase.
    # 为选定构造阶段建立描述符与身份保持证明。
    if phase == '__new__':
        if method.decorator_list and analyzer._descriptor_kind(target) != 'staticmethod':
            issue('constructor_new_descriptor_unconfirmed')
    elif phase == '__init__':
        identity_preserved = _source_callable_object_identity(
            analyzer, class_ref, method, definition_paths, definition_assumptions)
        preserved = (not method.decorator_list or identity_preserved
            or _source_function_decoration(
                analyzer, target, definition_paths, definition_assumptions))
        wrapper_forwarding = None
        if not preserved and len(method.decorator_list) == 1:
            wrapper = factory_wrapper(analyzer, target)
            forwarding = wrapper.get('forwarding') if wrapper else None
            if (forwarding is not None
                    and forwarding.get('forwarded_function') == asdict(ref)
                    and forwarding.get('argument_scope') == 'same_args_and_kwargs'
                    and forwarding.get('normal_return_paths') ==
                    'all_explicit_returns_forward_original_args_kwargs'):
                preserved = True
                wrapper_forwarding = wrapper
                definition_paths.update(wrapper.get('source_hashes', {}))
                definition_assumptions.update(wrapper.get('assumptions', ()))
        elif not preserved and len(method.decorator_list) == 2:
            wrapper = source_identity_factory_wrapper_chain(
                analyzer, class_ref, target, definition_paths, definition_assumptions)
            forwarding = wrapper.get('forwarding') if wrapper else None
            if (forwarding is not None
                    and forwarding.get('forwarded_function') == asdict(ref)
                    and forwarding.get('argument_scope') == 'same_args_and_kwargs'
                    and forwarding.get('normal_return_paths') ==
                    'all_explicit_returns_forward_original_args_kwargs'):
                preserved = True
                wrapper_forwarding = wrapper
        if wrapper_forwarding is not None:
            constructor_wrapper_forwarding = wrapper_forwarding
        if not preserved or not analyzer._ordinary_construction(
                class_ref, allow_bounded_decorations=True):
            issue('constructor_initialization_unconfirmed')
    else:
        issue('constructor_phase_unconfirmed')
    writes, truncated = analyzer._class_binding_writes()
    if truncated:
        issue('constructor_binding_budget')
    affected = {'__new__', '__class__', '__bases__', '*', phase}
    if any(attribute in affected and any(written == owner for owner, _ in checked)
           for written, attribute, _, _, _ in writes):
        issue('constructor_binding_write')
    paths = {owner.file_path for owner, _ in checked} | {ref.file_path} | definition_paths
    assumptions = ['source_snapshot_bindings_hold', 'builtin_type_call_and_new_binding',
                   'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']
    assumptions.extend(sorted(definition_assumptions))
    if len(analyzer._definition_index.find(ref.module, ref.qualname)) > 1:
        assumptions.append('stdlib_typing_overload_binding')
    # Keep runtime target selection and initialized instance state explicitly unconfirmed.
    # 明确保留运行时目标选择和实例初始化状态为未确认。
    result = {'query_kind': 'source_class_call',
        'status': 'unconfirmed' if issues else 'source_bound', 'basis': 'source_snapshot',
        'receiver_class': asdict(class_ref), 'target': asdict(ref), 'phase': phase,
        'hierarchy': [asdict(owner) for owner, _ in checked],
        'execution_scope': 'new_invocation_only' if phase == '__new__' else 'init_invocation_only',
        'body_execution': 'synchronous' if isinstance(method, ast.FunctionDef)
                          and not contains_yield(method) else 'deferred',
        'instance_state': 'unmodeled', 'runtime_target_confirmed': False,
        'implicit_binding': {'parameter': parameters[0].arg if parameters else None,
            'status': 'unconfirmed' if issues else 'static_bound',
            'value_kind': 'class' if phase == '__new__' else 'instance'},
        'definition_evidence': {'file_path': class_ref.file_path,
            'lineno': cls.lineno, 'col_offset': cls.col_offset,
            'end_lineno': cls.end_lineno, 'end_col_offset': cls.end_col_offset},
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)
                          if path in analyzer.hashes},
        'assumptions': assumptions,
        'issues': issues}
    if decorations:
        result['class_decorations'] = decorations
    if constructor_wrapper_forwarding is not None:
        result['constructor_wrapper_forwarding'] = constructor_wrapper_forwarding
    if hooks:
        result['class_creation_hooks'] = hooks
    result['retained_instance_attribute_stores'] = retained_stores(analyzer, checked, target, result)
    fresh = allocation_origin(analyzer, checked, target, result)
    if fresh is not None:
        result['fresh_receiver_origin'] = fresh
    return result
