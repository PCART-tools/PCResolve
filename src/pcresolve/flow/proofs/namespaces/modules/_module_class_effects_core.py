## @package pcresolve.flow.proofs.namespaces.modules._module_class_effects_core
#  Bounded effects of the first explicit source classmethod module call.
#  模块中首次显式源码类方法调用的有界效果。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.namespaces.modules._module_class_prefix import module_class_prefix
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Analyze a module class call under its independently established fresh prefix.
## 在独立证明的初始模块前缀下分析类方法调用。
#
#  @param analyzer Fixed source generation and existing effect budgets.
#  @param target Exact source root-class declaration.
#  @param call Actual standalone module-level classmethod call.
#  @param creation_calls Bounded class-creation effect evaluator.
#  @return Phase-specific effects or None; not a proof of later module state.
def module_class_effects(analyzer, target, call, creation_calls):
    prefix = module_class_prefix(analyzer, target, call)
    if prefix is None or not isinstance(call.func, ast.Attribute):
        return None
    owner, cls = target
    name = call.func.attr
    members = [node for node in cls.body if name in statement_scope_facts([node]).bound]
    if len(members) != 1 or not isinstance(members[0], ast.FunctionDef) or members[0].name != name:
        return None
    selected = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
    if (len(selected) != 1 or selected[0][1] is not members[0]
            or analyzer._descriptor_kind(selected[0]) != 'classmethod'):
        return None

    # The proof is limited to this call and its established module prefix.
    # 证明仅限于本次调用及其已确认的模块前缀。
    try:
        proof = creation_calls(analyzer, target, selected[0], ancestor_hooks=[], module_prefix=prefix)
    except _ClassEffectLimit:
        return None
    if proof is None:
        return None

    # Merge supporting premises without claiming the later module namespace.
    # 合并支持前提，不断言模块后续命名空间状态。
    attributes, evidence, calls, queries, metadata, signatures, class_queries = proof
    assumptions = set(prefix['assumptions'])
    assumptions.add('source_module_classmethod_effects')
    hashes = dict(prefix['source_hashes'])
    for record in metadata + signatures + class_queries:
        assumptions.update(record['assumptions'])
        hashes.update(record['source_hashes'])
    return {'kind': 'source_module_classmethod_effects', 'status': 'source_bound',
        'phase': 'module_initialization_call', 'receiver_class': asdict(owner),
        'target': asdict(selected[0][0]), 'module_prefix': prefix,
        'completion': 'normal_return_only', 'runtime_execution_confirmed': False,
        'post_module_namespace': 'unproved', 'attributes': attributes, 'evidence': evidence,
        'method_calls': calls, 'native_type_queries': queries, 'callable_metadata_queries': metadata,
        'signature_creations': signatures, 'class_metadata_queries': class_queries,
        'source_hashes': dict(sorted(hashes.items())), 'assumptions': sorted(assumptions)}
