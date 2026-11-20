## @package pcresolve.flow.analyzer
#  Experimental, explicit-boundary value-flow summaries for Python functions.
#
#
#  Configures source selection and proof queries, and composes indexing and
#  per-run analysis components without executing the selected source.
#  配置源码选择与证明查询，组合索引和单次分析组件，不执行所选源码。



import ast
import builtins
import copy
import os
from dataclasses import asdict, replace
from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches
from pcresolve.flow.index.generation import same_generation
from pcresolve.flow.transfer.summary import _Summary
from pcresolve.flow.transfer.call_expression import CallExpressionMixin
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
from pcresolve.flow.index.source import SourceIndexMixin
from pcresolve.flow.index.definitions import ClassFactsMixin
from pcresolve.flow.analysis.proof_context import ProofContextMixin
from pcresolve.flow.runtime.analysis_run import FlowRunMixin
## Compose indexing, proof and per-run components for explicit source analysis.
## 为显式源码分析组合索引、证明与单次运行组件。
class FlowAnalyzer(SourceIndexMixin, ClassFactsMixin, ProofContextMixin, FlowRunMixin):
    ## Configure available sources; import roots do not enlarge the source set.
    ## 配置可用源码；导入根目录不会扩大源码集合。
    #
    #  @param source_files Explicit files, mutually exclusive with project_root.
    #  @param import_roots Roots used to derive module names.
    #  @param project_root Optional project directory scanned with FileScanner.
    #  @param return_summaries Opt-in exact callable summaries with provenance.
    #  @param parameter_shapes Opt-in trusted parameter shape contracts.
    #  @param analysis_limits Optional cooperative resource limits for each analyze().
    #  @param support_source_protocols Opt in to separately versioned dependency protocol proofs.
    #  @param source_store Optional run-local SourceStore; reads still refresh content.
    #  @return None
    def __init__(self, source_files=None, import_roots=None, project_root=None,
                 return_summaries=None, parameter_shapes=None, analysis_limits=None,
                 support_source_protocols=False, source_store=None):
        if type(support_source_protocols) is not bool:
            raise ValueError('support_source_protocols must be bool')
        self.support_source_protocols = support_source_protocols
        self.analysis_limits = analysis_limits
        self._analysis_budget = None
        if (source_files is None) == (project_root is None):
            raise ValueError('Specify exactly one of source_files or project_root')
        self.files = set()
        if source_store is not None and not isinstance(source_store, SourceStore):
            raise TypeError('source_store must be a SourceStore')
        self._source_store = source_store if source_store is not None else SourceStore()
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
    ## 为下次分析添加源码；已有快照保持不变。
    #
    #  @param files Iterable of Python source paths.
    #  @return None
    def add_files(self, files):
        self.files.update(os.path.abspath(p) for p in files if str(p).endswith(('.py', '.pyi')))

    ## Read bounded literal, protocol and context-manager facts for one exact caller call
    ## 读取精确调用点的有界字面量、协议和上下文管理器事实。
    #
    #  @param callsite Exact caller source span.
    #  @return Versioned caller-input fact; no caller expression is executed.
    def caller_inputs(self, callsite):
        if not isinstance(callsite, SourceSpan):
            raise TypeError('callsite must be a SourceSpan')
        from pcresolve.flow.proofs.protocols._caller_inputs import literal_inputs
        fact = literal_inputs(callsite, store=self._source_store, import_roots=self.roots)
        return dict(fact, schema_version='caller-inputs-0.1')

    ## Build a fresh-decoration fact in the active flow execution context.
    ## 在当前数据流执行上下文中构造新鲜装饰证明事实。
    #
    #  @param ref Exact source definition reference.
    #  @param node Decorator expression represented as a function definition.
    #  @param limit Maximum proof work allowed for this query.
    #  @return Fresh-decoration evidence or None when the proof is incomplete.
    def _fresh_decoration_fact(self, ref, node, limit
                               ):
        summary = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
        return fresh_decoration(self, (ref, node), summary.evidence_at, limit)

    ## Resolve source-class creation effects through the analyzer's proof registry.
    ## 通过分析器证明注册表解析源码类创建效果。
    #
    #  @param target Exact source class identity and syntax node.
    #  @return Bounded class-creation evidence or None when unresolved.
    def _class_creation_effects(self, target):
        return creation_effects(self, target)

    ## Report whether one source class member has a stable class binding
    ## 报告源码类成员的类绑定是否稳定。
    #
    #  @param module Source module containing the class.
    #  @param qualname Fully qualified source class name.
    #  @param member Class member whose binding is queried.
    #  @param file_path Exact source file for this class identity.
    #  @return Versioned binding fact, or None when identity or analysis is incomplete.
    def source_class_member_binding(self, module, qualname, member, file_path):
        if not all(isinstance(value, str) and value for value in
                   (module, qualname, member, file_path)):
            raise ValueError('Class identity and member must be non-empty strings')
        probe = type(self)(source_files=set(self.files) | {os.path.abspath(file_path)},
                           import_roots=self.roots,
                           support_source_protocols=self.support_source_protocols)
        probe._index(preserve_source_facts=True)
        normalized = os.path.normcase(os.path.abspath(file_path))
        classes = [(ref, node) for ref, node in probe._definition_index.find(
            module, qualname, kind='class')
            if os.path.normcase(os.path.abspath(ref.file_path)) == normalized]
        if len(classes) != 1:
            return None
        class_ref, class_node = classes[0]
        member_nodes = []
        for statement in class_node.body:
            if (isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.ClassDef))
                    and statement.name == member):
                member_nodes.append(statement)
            elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = (statement.targets if isinstance(statement, ast.Assign)
                           else [statement.target])
                if any(isinstance(target, ast.Name) and target.id == member
                       for target in targets):
                    member_nodes.append(statement)
        if len(member_nodes) != 1:
            return None
        member_node = member_nodes[0]
        member_value = (member_node.value if isinstance(member_node, (ast.Assign, ast.AnnAssign))
                        else None)
        writes, truncated = probe._class_binding_writes()
        if truncated:
            return None
        changed = any(owner == class_ref and name in (member, '*')
                      for owner, name, _, _, _ in writes)
        path = os.path.abspath(class_ref.file_path)
        digest = probe.hashes.get(path)
        if not isinstance(digest, str):
            return None
        return {
            'schema_version': 'source-class-member-binding-0.1',
            'kind': 'source_class_member_binding',
            'status': 'may_be_rebound' if changed else 'stable',
            'basis': 'source_snapshot',
            'class': {'module': class_ref.module, 'qualname': class_ref.qualname,
                      'file_path': path, 'lineno': class_ref.lineno},
            'member': member,
            'member_kind': ('assignment' if isinstance(member_node, (ast.Assign, ast.AnnAssign))
                            else 'definition'),
            'member_expression': ast.unparse(member_value) if member_value is not None else None,
            'member_span': {'lineno': member_nodes[0].lineno,
                            'col_offset': member_nodes[0].col_offset,
                            'end_lineno': member_nodes[0].end_lineno,
                            'end_col_offset': member_nodes[0].end_col_offset},
            'source_hashes': {path: digest},
            'assumptions': ['source_snapshot_bindings_hold',
                            'no_external_monkeypatch_or_import_hook'],
        }

    ## Prove a source method returns a fallback after a selected exception
    ## 证明源码方法在指定异常后返回回退值。
    #
    #  @param module Source module containing the class.
    #  @param qualname Fully qualified source class name.
    #  @param member Method whose exception branch is queried.
    #  @param file_path Exact source file for this class identity.
    #  @param exception Exception name handled by the method.
    #  @return Versioned source behavior fact, or None when the shape is unsupported.
    def source_method_exception_fallback(self, module, qualname, member, file_path,
                                        exception='RuntimeError'):
        if not all(isinstance(value, str) and value for value in
                   (module, qualname, member, file_path, exception)):
            raise ValueError('Class, method, path and exception identities must be non-empty')
        probe = type(self)(source_files=set(self.files) | {os.path.abspath(file_path)},
                           import_roots=self.roots,
                           support_source_protocols=self.support_source_protocols)
        probe._index(preserve_source_facts=True)
        normalized = os.path.normcase(os.path.abspath(file_path))
        classes = [(ref, node) for ref, node in probe._definition_index.find(
            module, qualname, kind='class')
            if os.path.normcase(os.path.abspath(ref.file_path)) == normalized]
        if len(classes) != 1:
            return None
        class_ref, class_node = classes[0]
        methods = [node for node in class_node.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == member]
        if len(methods) != 1 or methods[0].decorator_list:
            return None
        method = methods[0]
        tries = [node for node in method.body if isinstance(node, ast.Try)]
        if len(tries) != 1 or tries[0].orelse or tries[0].finalbody:
            return None
        instance_name = (method.args.posonlyargs + method.args.args)[1].arg \
            if len(method.args.posonlyargs + method.args.args) > 1 else None
        before_try = method.body[:method.body.index(tries[0])]

        ## Check that early paths return only the descriptor or its class value.
        ## 检查提前返回路径仅返回描述符或其类值。
        #
        #  @param statements Early branch statements.
        #  @return True when the supported block always returns an allowed value.
        def only_safe_returns(statements):
            falls_through = True
            for statement in statements:
                if isinstance(statement, ast.Return):
                    value = statement.value
                    if (isinstance(value, ast.Name) and value.id == 'self'
                            or isinstance(value, ast.Attribute)
                            and isinstance(value.value, ast.Name)
                            and value.value.id == 'self' and value.attr == 'class_value'):
                        falls_through = False
                        continue
                    return False
                if isinstance(statement, ast.If):
                    if (not isinstance(statement.test, ast.Compare)
                            or any(not isinstance(child, (ast.Name, ast.Attribute, ast.Constant,
                                                          ast.Compare, ast.Load, ast.Is, ast.IsNot))
                                   for child in ast.walk(statement.test))
                            or not only_safe_returns(statement.body)
                            or statement.orelse and not only_safe_returns(statement.orelse)):
                        return False
                    body_falls = _safe_return_block_falls_through(statement.body)
                    else_falls = (_safe_return_block_falls_through(statement.orelse)
                                  if statement.orelse else True)
                    falls_through = body_falls or else_falls
                    continue
                return False
            return bool(statements) and not falls_through

        ## Check whether a supported return block can fall through.
        ## 检查受支持的返回语句块是否可能继续执行。
        #
        #  @param statements Branch statements.
        #  @return True when a path can reach the following statement.
        def _safe_return_block_falls_through(statements):
            falls_through = True
            for statement in statements:
                if isinstance(statement, ast.Return):
                    falls_through = False
                elif isinstance(statement, ast.If):
                    body_falls = _safe_return_block_falls_through(statement.body)
                    else_falls = (_safe_return_block_falls_through(statement.orelse)
                                  if statement.orelse else True)
                    falls_through = body_falls or else_falls
                else:
                    return True
            return falls_through

        first_lookup = tries[0].body[0] if len(tries[0].body) == 1 else None
        lookup_call = (first_lookup.value if isinstance(first_lookup, ast.Expr)
                       else first_lookup.value if isinstance(first_lookup, ast.Assign)
                       and len(first_lookup.targets) == 1
                       and isinstance(first_lookup.targets[0], ast.Name) else None)
        lookup_instance = (lookup_call.func.value if isinstance(lookup_call, ast.Call)
                           and isinstance(lookup_call.func, ast.Attribute) else None)
        if (instance_name is None or len(before_try) > 1
                or before_try and not isinstance(before_try[0], ast.If)
                or before_try and before_try[0].orelse
                or before_try and not isinstance(before_try[0].test, ast.Compare)
                or before_try and not isinstance(before_try[0].test.left, ast.Name)
                or before_try and before_try[0].test.left.id != instance_name
                or before_try and len(before_try[0].test.ops) != 1
                or before_try and not isinstance(before_try[0].test.ops[0], ast.Is)
                or before_try and len(before_try[0].test.comparators) != 1
                or before_try and not isinstance(before_try[0].test.comparators[0], ast.Constant)
                or before_try and before_try[0].test.comparators[0].value is not None
                or before_try and not only_safe_returns(before_try[0].body)
                or not isinstance(lookup_call, ast.Call)
                or not isinstance(lookup_instance, ast.Name)
                or lookup_instance.id != instance_name):
            return None
        handler_matches = [handler for handler in tries[0].handlers
                           if isinstance(handler.type, ast.Name)
                           and handler.type.id == exception]
        if (len(tries[0].handlers) != 1 or len(handler_matches) != 1
                or len(handler_matches[0].body) not in (2, 4)
                or not isinstance(handler_matches[0].body[0], ast.If)
                or handler_matches[0].body[0].orelse
                or not isinstance(handler_matches[0].body[0].test, ast.Compare)
                or not isinstance(handler_matches[0].body[0].test.left, ast.Attribute)
                or handler_matches[0].body[0].test.left.attr != 'fallback'
                or not isinstance(handler_matches[0].body[0].test.left.value, ast.Name)
                or handler_matches[0].body[0].test.left.value.id != 'self'
                or len(handler_matches[0].body[0].test.ops) != 1
                or not isinstance(handler_matches[0].body[0].test.ops[0], ast.Is)
                or len(handler_matches[0].body[0].test.comparators) != 1
                or not isinstance(handler_matches[0].body[0].test.comparators[0], ast.Constant)
                or handler_matches[0].body[0].test.comparators[0].value is not None
                or len(handler_matches[0].body[0].body) != 1
                or not isinstance(handler_matches[0].body[0].body[0], ast.Raise)):
            return None
        handler = handler_matches[0]
        returns = [node for node in handler.body if isinstance(node, ast.Return)]
        fallback_mode = 'direct_call'
        value = returns[0].value if len(returns) == 1 else None
        direct = (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                  and isinstance(value.func.value, ast.Name)
                  and value.func.value.id == 'self' and value.func.attr == 'fallback'
                  and len(value.args) == 1 and not value.keywords)
        if not direct:
            fallback_mode = 'bound_method'
            if len(handler.body) != 4:
                return None
            assignment, attribute_branch, returned = handler.body[1:]
            if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
                    or not isinstance(assignment.targets[0], ast.Name)
                    or not isinstance(assignment.value, ast.Call)
                    or not isinstance(assignment.value.func, ast.Attribute)
                    or assignment.value.func.attr != '__get__'
                    or not isinstance(assignment.value.func.value, ast.Attribute)
                    or assignment.value.func.value.attr != 'fallback'
                    or not isinstance(assignment.value.func.value.value, ast.Name)
                    or assignment.value.func.value.value.id != 'self'
                    or len(assignment.value.args) != 2
                    or not isinstance(assignment.value.args[0], ast.Name)
                    or assignment.value.args[0].id != instance_name
                    or not isinstance(assignment.value.args[1], ast.Name)
                    or assignment.value.args[1].id != 'owner'
                    or assignment.value.keywords
                    or not isinstance(attribute_branch, ast.If)
                    or not isinstance(attribute_branch.test, ast.Attribute)
                    or attribute_branch.test.attr != 'is_attr'
                    or not isinstance(attribute_branch.test.value, ast.Name)
                    or attribute_branch.test.value.id != 'self'
                    or len(attribute_branch.body) != 1
                    or not isinstance(attribute_branch.body[0], ast.Return)
                    or not isinstance(attribute_branch.body[0].value, ast.Call)
                    or not isinstance(attribute_branch.body[0].value.func, ast.Name)
                    or attribute_branch.body[0].value.func.id != assignment.targets[0].id
                    or attribute_branch.body[0].value.args or attribute_branch.orelse
                    or not isinstance(returned, ast.Return)
                    or not isinstance(returned.value, ast.Name)
                    or returned.value.id != assignment.targets[0].id):
                return None
            value = assignment.value
            returns = [attribute_branch.body[0], returned]
        path = os.path.abspath(class_ref.file_path)
        digest = probe.hashes.get(path)
        if not isinstance(digest, str):
            return None
        return {
            'schema_version': 'source-method-exception-fallback-0.1',
            'kind': 'source_method_exception_fallback',
            'status': 'source_bound', 'basis': 'source_snapshot',
            'class': {'module': class_ref.module, 'qualname': class_ref.qualname,
                      'file_path': path, 'lineno': class_ref.lineno},
            'member': member, 'exception': exception,
            'receiver_parameter': instance_name,
            'protected_call': ast.dump(lookup_call, include_attributes=False),
            'protected_span': {'lineno': lookup_call.lineno,
                               'col_offset': lookup_call.col_offset,
                               'end_lineno': lookup_call.end_lineno,
                               'end_col_offset': lookup_call.end_col_offset},
            'lookup_member': lookup_call.func.attr,
            'fallback_expression': ast.dump(value, include_attributes=False),
            'fallback_mode': fallback_mode,
            'source_span': {'lineno': returns[0].lineno,
                            'col_offset': returns[0].col_offset,
                            'end_lineno': returns[0].end_lineno,
                            'end_col_offset': returns[0].end_col_offset},
            'source_hashes': {path: digest},
            'assumptions': ['source_snapshot_bindings_hold',
                            'no_external_monkeypatch_or_import_hook'],
        }

    ## Resolve a supported source protocol used by one exact function call
    ## 解析精确函数调用使用的受支持源码协议。
    #
    #  @param caller Function containing the call.
    #  @param callsite Exact source span of the call expression.
    #  @param protocol Supported source protocol query.
    #  @return Versioned protocol fact or None when the query is unproven.
    def source_call_protocol(self, caller, callsite, protocol='iterability'):
        if not isinstance(caller, FunctionRef):
            raise TypeError('caller must be a FunctionRef')
        if not isinstance(callsite, SourceSpan):
            raise TypeError('callsite must be a SourceSpan')
        if protocol != 'iterability':
            raise ValueError('Unsupported source call protocol')
        validate_source_dependencies(getattr(self, '_supporting_source_hashes', {}))
        self._index(preserve_source_facts=True)
        validate_source_dependencies(self._supporting_source_hashes)
        # Require both the caller identity and full call span to match uniquely.
        # 要求调用方标识和完整调用位置唯一匹配。
        definitions = [(ref, node) for ref, node in self.definitions
                       if _matches(ref, caller)
                       and os.path.normcase(os.path.abspath(ref.file_path))
                       == os.path.normcase(os.path.abspath(callsite.file_path))]
        calls = [(ref, definition, node) for ref, definition in definitions
                 for node in ast.walk(definition) if isinstance(node, ast.Call)
                 and (node.lineno, node.col_offset, getattr(node, 'end_lineno', None),
                      getattr(node, 'end_col_offset', None)) == callsite.coordinates]
        if len(calls) != 1:
            return None
        ref, definition, node = calls[0]
        from pcresolve.flow.proofs.protocols._native_class_protocol import iterability_query
        fact = iterability_query(self, (ref, definition), node.func)
        if fact is None:
            validate_source_dependencies(self._supporting_source_hashes)
            return None
        target, proof = fact
        validate_source_dependencies(self._supporting_source_hashes)
        return {
            'schema_version': 'source-call-protocol-0.1',
            'status': 'source_bound',
            'protocol': 'iterability',
            'caller': {'module': ref.module, 'qualname': ref.qualname,
                       'file_path': ref.file_path, 'lineno': ref.lineno},
            'callsite': {'file_path': callsite.file_path,
                         'lineno': callsite.lineno, 'col_offset': callsite.col_offset,
                         'end_lineno': callsite.end_lineno,
                         'end_col_offset': callsite.end_col_offset},
            'call_syntax': ast.dump(node, include_attributes=False),
            'target': target,
            'fact': proof,
            'assumptions': sorted(proof.get('assumptions', ())),
        }
