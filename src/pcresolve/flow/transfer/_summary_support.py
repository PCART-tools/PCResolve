## @package pcresolve.flow.transfer.summary
#  Experimental, explicit-boundary value-flow summaries for Python functions.
#  针对 Python 函数的实验性数据流摘要，显式保留分析边界。

import ast
import builtins
import copy
import os
from dataclasses import asdict, replace
from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches
from pcresolve.flow.index.generation import same_generation
from pcresolve.flow.transfer.environment import (
    merge_environments as _merge_env, merge_result_sources as _merge_result_sources,
)
from pcresolve.runtime.limits import AnalysisBudget
from pcresolve.flow.proofs.protocols import syntax_facts

from pcresolve.frontend.scanner import FileScanner
from pcresolve.facts.program_facts import SourceSpan, FunctionSignature, bind_ast_call
from pcresolve.frontend.source_snapshot import (SourceStore, ModuleIndex, FLOW_SOURCE, FLOW_MODULES,
                              module_name_for_path)
from pcresolve.facts.call_resolution import DefinitionRecord, DefinitionIndex, CallContext
from pcresolve.facts.scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)
from pcresolve.facts.return_resolution import (CallBinding, ReturnCall,
                                resolve_return_dependencies,
                                select_dependencies)
from pcresolve.facts.effect_facts import (container_method_effect, contains_yield,
                           function_effects, FunctionEffect, finite_key_delete_sites)
from pcresolve.facts.import_facts import import_facts, resolve_relative_module
from pcresolve.facts.star_imports import static_star_imports
from pcresolve.flow.proofs.callables.decorators._decorator_effects import _DecoratorEffects
from pcresolve.flow.proofs.callables._function_factory import factory_wrapper
from pcresolve.flow.proofs.namespaces.metadata._metadata_queries import metadata_query
from pcresolve.flow.proofs.namespaces.metadata._metadata_observer import observer_effects
from pcresolve.flow.proofs.namespaces.source._source_dependencies import publish as publish_source_dependencies
from pcresolve.flow.proofs.namespaces.source._source_dependencies import validate as validate_source_dependencies
from pcresolve.flow.proofs.callables._callable_instance_binding import source_binding
from pcresolve.flow.proofs.callables._constructor_binding import source_binding as constructor_source_binding
from pcresolve.flow.proofs.callables._constructor_entry import binding as constructor_entry_binding
from pcresolve.flow.proofs.callables._fresh_receiver import (method_binding as fresh_method_binding,
                              super_method_binding as fresh_super_method_binding,
                              incoming_origin as fresh_incoming_origin)
from pcresolve.flow.proofs.callables._fresh_receiver import recover_lookup_receiver as fresh_lookup_receiver
from pcresolve.flow.proofs.callables._fresh_member_checks import fresh_checks as fresh_mapping_member_checks
from pcresolve.flow.proofs.protocols._contextmanager_instance_effects import (
    temporary_receiver_attributes as bounded_temporary_receiver_attributes)
from pcresolve.flow.proofs.callables._constructor_entry import source_member as constructor_source_member
from pcresolve.flow.proofs.callables._constructor_entry import _definition_issues as constructor_definition_issues
from pcresolve.flow.proofs.classes._class_definition import _source_callable_object_identity
from pcresolve.flow.proofs.containers.mapping_remainders import mapping_remainder, _ProofLimit
from pcresolve.flow.proofs.protocols.class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from pcresolve.flow.proofs.classes._class_name_binding import source_binding as source_class_name_binding
from pcresolve.flow.proofs.classes._class_name_binding import _write_name as class_write_name
from pcresolve.flow.proofs.classes._class_read_binding import source_binding as source_class_read_binding
from pcresolve.flow.proofs.callables.dispatch.finite_dispatch import generated_dict, DispatchLimit
from pcresolve.flow.proofs.callables.dispatch.entry_alias import reference as source_entry_alias
from pcresolve.flow.proofs.callables.dispatch.conditional_constructor import signature_reference as conditional_constructor_signature
from pcresolve.flow.proofs.callables.dispatch.conditional_constructor import supports_entry as conditional_constructor_entry
from pcresolve.flow.proofs.callables.dispatch.keyword_validation import checks as keyword_validation_checks
from pcresolve.flow.proofs.containers.mapping_attribute_transfer import transfers as mapping_attribute_transfers
from pcresolve.flow.proofs.containers.mapping_key_access import footprints as mapping_key_access_footprints
from pcresolve.flow.proofs.containers.mapping_return_transfer import transfers as mapping_return_transfers
from pcresolve.flow.proofs.protocols.capture_rejection_guard import checks as capture_rejection_checks
from pcresolve.flow.proofs.containers.container_predicates import checks as container_predicate_checks
from pcresolve.flow.proofs.protocols._cached_imports import cached_import
from pcresolve.flow.proofs.classes._class_decoration import constructor_decorations, member_preservation
from pcresolve.flow.proofs.classes._class_metadata_read import native_function_scalar
from pcresolve.flow.proofs.classes._class_creation import creation_effects
from pcresolve.flow.proofs.classes._class_type_tests import native_class_operand
from pcresolve.flow.proofs.callables.decorators._fresh_decoration import fresh_decoration
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified as namespace_unmodified


_CLASS_BINDING_NODE_LIMIT = 1000000
_CLASS_BINDING_IRRELEVANT_LEAVES = (
    ast.Constant, ast.expr_context, ast.operator, ast.unaryop, ast.boolop, ast.cmpop)
_DECORATOR_EFFECT_NODE_LIMIT = 2000
_CONTEXT_PROTOCOL_NODE_LIMIT = 2000
_CONTEXT_EXIT_PATH_LIMIT = 32
_BUILTIN_SCOPE = replace(FLOW_SCOPE, descend_lambdas=False,
                        include_comprehension_targets=False,
                        include_except_targets=True, import_from_root=False)


## Look up a builtin exception class by name.
## 按名称查找内置异常类。
#
#  @param name Candidate builtin name.
#  @return Exception class or None when unavailable.
def _exception_class(name):
    value = getattr(builtins, name or '', None)
    return value if isinstance(value, type) and issubclass(value, BaseException) else None


## Conservatively identify syntax that may raise during evaluation.
## 保守识别求值时可能抛出异常的语法。
#
#  @param node Source AST node.
#  @return True when a modeled potentially raising expression occurs.
def _may_raise(node):
    return any(isinstance(n, (ast.Call, ast.BinOp, ast.UnaryOp, ast.Attribute,
                              ast.Subscript, ast.Compare)) for n in ast.walk(node))


## Find root names of attribute or subscript writes in the current scope.
## 查找当前作用域内属性或下标写入的根名称。
#
#  @param node Source AST node.
#  @return Set of root names, excluding nested definitions.
def _attribute_write_roots(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                         ast.Lambda)):
        return set()
    roots = set()
    if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
            node.ctx, (ast.Store, ast.Del)):
        root = node.value
        while isinstance(root, (ast.Attribute, ast.Subscript)):
            root = root.value
        if isinstance(root, ast.Name):
            roots.add(root.id)
    for child in ast.iter_child_nodes(node):
        roots.update(_attribute_write_roots(child))
    return roots


## Build a snapshot-local call identifier, including any implicit suffix.
## 构建快照内调用标识，包括可选的隐式调用后缀。
#
#  @param path Source file path.
#  @param node Call or implicit protocol AST node.
#  @return Call identifier string.
def _call_key(path, node):
    key = SourceSpan.from_ast(path, node).key
    return key + getattr(node, '_flow_implicit_suffix', '')


## Read call coordinates and any implicit protocol suffix.
## 读取调用坐标及可选的隐式协议后缀。
#
#  @param node Call or implicit protocol AST node.
#  @return Coordinate tuple with suffix.
def _call_span(node):
    return SourceSpan.from_ast('', node).coordinates + (getattr(node, '_flow_implicit_suffix', ''),)


## Deduplicate values while retaining their first occurrence order.
## 去重并保留值首次出现的顺序。
#
#  @param values Iterable of comparable values.
#  @return List of unique values in input order.
def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


## Build an environment key for invalidated source-class identity.
## 为已失效的源码类身份构建环境键。
#
#  @param identity Class identity dictionary.
#  @return Internal class-origin invalidation key.
def _class_origin_key(identity):
    return '$class_origin_invalid:%s' % repr(tuple(identity.get(key)
        for key in ('module', 'qualname', 'file_path', 'lineno')))


## Build an environment key for one source class identity.
## 为源码类标识构建环境键。
#
#  @param identity Class identity dictionary.
#  @return Internal class-lookup key.
def _class_lookup_key(identity):
    return '$class_lookup_state:%s' % repr(tuple(identity.get(key)
        for key in ('module', 'qualname', 'file_path', 'lineno')))


## Build a dependency identity without explanatory path records.
## 构建不包含解释路径记录的依赖标识。
#
#  @param value Dependency record.
#  @return Representation used for loop convergence.
def _loop_key(value):
    return repr({k: v for k, v in value.items() if k not in ('evidence', 'conditions')})


## Build a loop convergence signature for each environment binding.
## 为每个环境绑定构建循环收敛签名。
#
#  @param env Abstract environment.
#  @return Mapping from names to dependency-key sets.
def _loop_signature(env):
    return {k: frozenset(_loop_key(v) for v in values) for k, values in env.items()}


## Retain one witness per dependency for a finite may-flow fixed point.
## 为有限的可能数据流不动点保留每个依赖的一条证据。
#
#  @param env Abstract environment.
#  @return Environment with duplicate dependency witnesses removed.
def _loop_env(env):
    # Keep one finite witness per abstract dependency. This is a may-flow
    # fixed point, not enumeration of all iteration counts or path conditions.
    # 这是可能流的不动点，不枚举所有迭代次数或路径条件。
    result = {}
    for name, values in env.items():
        witnesses = {}
        for value in values:
            witnesses.setdefault(_loop_key(value), value)
        result[name] = list(witnesses.values())
    return result


## Analyze explicit Python source sets without executing analyzed code.
## 分析显式选定的 Python 源码集合，不执行被分析代码。


__all__ = [name for name in globals() if not name.startswith('__')]
