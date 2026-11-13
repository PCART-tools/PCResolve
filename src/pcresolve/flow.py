## @package pcresolve.flow
#  Experimental, explicit-boundary value-flow summaries for Python functions.
#  针对 Python 函数的实验性数据流摘要，显式保留分析边界。

import ast
import builtins
import copy
import os
from dataclasses import dataclass, field, asdict, replace
from .analysis_limits import AnalysisBudget
from . import syntax_facts

from .scanner import FileScanner
from .program_facts import SourceSpan, FunctionSignature, bind_ast_call
from .source_snapshot import (SourceStore, ModuleIndex, FLOW_SOURCE, FLOW_MODULES,
                              module_name_for_path)
from .call_resolution import DefinitionRecord, DefinitionIndex, CallContext
from .scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)
from .return_resolution import (CallBinding, ReturnCall,
                                resolve_return_dependencies,
                                select_dependencies)
from .effect_facts import (container_method_effect, contains_yield,
                           function_effects, FunctionEffect, finite_key_delete_sites)
from .import_facts import import_facts, resolve_relative_module
from .star_imports import static_star_imports
from ._decorator_effects import _DecoratorEffects
from ._function_factory import factory_wrapper
from ._metadata_queries import metadata_query
from ._metadata_observer import observer_effects
from ._source_dependencies import publish as publish_source_dependencies
from ._source_dependencies import validate as validate_source_dependencies
from ._callable_instance_binding import source_binding
from ._constructor_binding import source_binding as constructor_source_binding
from ._constructor_entry import binding as constructor_entry_binding
from ._fresh_receiver import (method_binding as fresh_method_binding,
                              super_method_binding as fresh_super_method_binding,
                              incoming_origin as fresh_incoming_origin)
from ._fresh_receiver import recover_lookup_receiver as fresh_lookup_receiver
from ._fresh_member_checks import fresh_checks as fresh_mapping_member_checks
from ._contextmanager_instance_effects import (
    temporary_receiver_attributes as bounded_temporary_receiver_attributes)
from ._constructor_entry import source_member as constructor_source_member
from ._constructor_entry import _definition_issues as constructor_definition_issues
from ._class_definition import _source_callable_object_identity
from .mapping_remainders import mapping_remainder, _ProofLimit
from .class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from ._class_name_binding import source_binding as source_class_name_binding
from ._class_name_binding import _write_name as class_write_name
from ._class_read_binding import source_binding as source_class_read_binding
from .finite_dispatch import generated_dict, DispatchLimit
from .entry_alias import reference as source_entry_alias
from .conditional_constructor import signature_reference as conditional_constructor_signature
from .conditional_constructor import supports_entry as conditional_constructor_entry
from .keyword_validation import checks as keyword_validation_checks
from .mapping_attribute_transfer import transfers as mapping_attribute_transfers
from .mapping_key_access import footprints as mapping_key_access_footprints
from .mapping_return_transfer import transfers as mapping_return_transfers
from .capture_rejection_guard import checks as capture_rejection_checks
from .container_predicates import checks as container_predicate_checks
from ._cached_imports import cached_import
from ._class_decoration import constructor_decorations, member_preservation
from ._class_metadata_read import native_function_scalar
from ._class_creation import creation_effects
from ._class_type_tests import native_class_operand
from ._fresh_decoration import fresh_decoration
from ._runtime_namespace import unmodified as namespace_unmodified


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


## A source function selector; definition location disambiguates duplicates.
## 源码函数选择器；定义位置用于区分重复名称。
@dataclass(frozen=True)
class FunctionRef:
    module: str = ''
    qualname: str = ''
    file_path: str = ''
    lineno: int = 0


## A source call or identified implicit protocol call, with source candidates.
## 带有源码候选项的调用或已识别隐式协议调用。
@dataclass
class FlowCall:
    id: str
    caller: FunctionRef
    callee_name: str
    lineno: int
    col_offset: int
    end_lineno: int = 0
    end_col_offset: int = 0
    target: object = None
    target_candidates: list = field(default_factory=list)
    parameter_bindings: list = field(default_factory=list)
    parameter_flows: list = field(default_factory=list)
    return_flows: list = field(default_factory=list)
    argument_sources: list = field(default_factory=list)
    argument_flows: list = field(default_factory=list)
    capture_bindings: list = field(default_factory=list)
    return_dependencies: list = field(default_factory=list)
    receiver_sources: list = field(default_factory=list)
    receiver_type_evidence: list = field(default_factory=list)
    callable_instance_evidence: dict = field(default_factory=dict)
    decorator_identity_evidence: list = field(default_factory=list)
    analysis_status: str = 'analyzed'
    target_status: str = 'definition_unavailable'
    mutation_flows: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    result_sources: list = field(default_factory=list)
    binding_status: str = 'unavailable'
    binding_issues: list = field(default_factory=list)
    callable_sources: list = field(default_factory=list)
    analysis_contexts: list = field(default_factory=list)
    conditional_returns: list = field(default_factory=list)
    class_method_bindings: list = field(default_factory=list)
    constructor_bindings: list = field(default_factory=list)
    instance_method_bindings: list = field(default_factory=list)
    implicit_protocol: dict = field(default_factory=dict)
    class_metadata_bindings: list = field(default_factory=list)
    class_read_bindings: list = field(default_factory=list)
    conditional_source_bindings: list = field(default_factory=list)
    candidate_paths: list = field(default_factory=list)
    conditions: list = field(default_factory=list)


## An immutable-by-convention analysis snapshot with JSON-safe views.
## 按约定不可变且提供 JSON 安全视图的分析快照。
@dataclass
class FlowAnalysis:
    entry: FunctionRef
    inputs: dict
    functions: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    schema_version: str = 'flow-0.2'

    ## Find calls by caller and exact syntactic callee spelling.
    ## 根据调用方和精确语法调用名查找调用。
    #
    #  @param caller Optional function selector.
    #  @param callee_name Optional exact spelling.
    #  @return Matching calls in deterministic source order.
    def find_calls(self, caller=None, callee_name=None):
        return [c for c in self.calls
                if (caller is None or _matches(c.caller, caller))
                and (callee_name is None or c.callee_name == callee_name)]

    ## Return evidence for one exact call site.
    ## 返回单个精确调用点的证据。
    #
    #  @param call_id Identifier returned by find_calls.
    #  @return JSON-safe call flow record.
    def describe_call_flow(self, call_id):
        for call in self.calls:
            if call.id == call_id:
                return asdict(call)
        raise KeyError(call_id)

    ## Serialize the snapshot without internal AST objects.
    ## 序列化快照，不包含内部 AST 对象。
    #
    #  @return Dictionary suitable for json.dumps.
    def to_dict(self):
        return asdict(self)

    ## Trace an entry parameter through explicitly expanded return summaries.
    ## 通过显式展开的返回摘要追踪入口参数。
    #
    #  @param parameter Entry parameter name.
    #  @return Proven return paths and boundaries; absence is not a no-flow proof.
    def trace_parameter(self, parameter):
        ## Derive a definition key that distinguishes file, name and line.
        ## 构建区分文件、名称和行号的定义键。
        #
        #  @param ref FunctionRef or serialized function identity.
        #  @return Definition key tuple.
        def function_key(ref):
            value = asdict(ref) if isinstance(ref, FunctionRef) else ref
            return (value['file_path'], value['qualname'], value['lineno'])

        functions = {function_key(f['function']): f for f in self.functions}
        entry_key = function_key(self.entry)
        if parameter not in functions[entry_key]['parameters']:
            raise ValueError('Unknown entry parameter: ' + parameter)
        calls = {}
        for call in self.calls:
            bindings = [
                CallBinding('capture', item.get('capture'),
                            tuple(value for value in item.get('sources', ())
                                  if not value.get('object_only')),
                            tuple(item.get('target_path', ())))
                for item in call.capture_bindings]
            bindings.extend(
                CallBinding('parameter', item.get('parameter'),
                            tuple(value for value in item.get('sources', ())
                                  if not value.get('object_only')),
                            tuple(item.get('target_path', ())))
                for item in call.argument_sources)
            calls[call.id] = ReturnCall(
                call.id, function_key(call.target) if call.target is not None else None,
                tuple(bindings), tuple(call.return_dependencies))
        # Compose supported return dependencies while preserving explicit boundaries.
        # 组合受支持的返回依赖，同时保留显式分析边界。
        resolution = resolve_return_dependencies(
            entry_key, parameter,
            {key: [value for value in summary['returns']
                   if not value.get('object_only')]
             for key, summary in functions.items()},
            calls)
        boundaries = copy.deepcopy(self.boundaries)
        if resolution.status != 'converged':
            boundaries.append({'reason': 'return_summary_limit',
                               'iterations': resolution.iterations})
        return {'parameter': parameter, 'return_paths': list(resolution.paths),
                'status': 'flow_found' if resolution.paths else 'unknown',
                'summary_status': resolution.status,
                'summary_iterations': resolution.iterations,
                'boundaries': boundaries}



## Match a function identity against optional selector components.
## 按选择器中提供的字段匹配函数标识。
#
#  @param actual Actual function identity.
#  @param selector Requested function selector.
#  @return True when all specified fields match.
def _matches(actual, selector):
    return (actual.qualname == selector.qualname
            and (not selector.module or actual.module == selector.module)
            and (not selector.file_path or actual.file_path == os.path.abspath(selector.file_path))
            and (not selector.lineno or actual.lineno == selector.lineno))


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


## Merge result alternatives while retaining incomplete container evidence.
## 合并结果候选，并保留不完整的容器证据。
#
#  @param left First branch sources.
#  @param right Second branch sources.
#  @return Deduplicated merged source records.
def _merge_result_sources(left, right):
    incomplete = any(not values or any(
        not value.get('container_object') or value.get('value_incomplete')
        for value in values) for values in (left, right))
    return _unique([dict(value, value_incomplete=True)
                    if incomplete and value.get('container_object') else value
                    for value in left + right])


## Merge branch environments without treating absent bindings as certain.
## 合并分支环境，不将缺失绑定视为确定事实。
#
#  @param environments Branch environment mappings.
#  @return Merged environment with uncertainty markers.
def _merge_env(environments):
    keys = set().union(*(e.keys() for e in environments))
    merged = {}
    for key in keys:
        values = _unique([value for env in environments for value in env.get(key, [])])
        if key.endswith('$keys'):
            values = [dict(value, presence_unconfirmed=True)
                      if not all(any(marker.get('key') == value.get('key')
                          and not marker.get('presence_unconfirmed')
                          for marker in env.get(key, [])) for env in environments)
                      else value for value in values]
        if any(not env.get(key) for env in environments):
            values = [dict(value, import_incomplete=True)
                      if value.get('kind') == 'import' else
                      dict(value, value_incomplete=True) if value.get('kind') in (
                          'class', 'call_result', 'container', 'callable')
                      or value.get('class_type') or value.get('callable_type') else value
                      for value in values]
        merged[key] = values
    return merged


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
class FlowAnalyzer:
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
        from ._caller_inputs import literal_inputs
        fact = literal_inputs(callsite, store=self._source_store, import_roots=self.roots)
        return dict(fact, schema_version='caller-inputs-0.1')

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
        from ._native_class_protocol import iterability_query
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
        }

    ## Build a source generation and reset per-query analysis state.
    ## 构建源码生成版本并重置每次查询的分析状态。
    #
    #  @param preserve_source_facts Reuse compatible facts from the same source generation.
    #  @return None
    def _index(self, preserve_source_facts=False):
        # Budgets, contracts and incoming contexts belong to one query even
        # when the source facts are unchanged.
        source_fact_cache_names = (
            '_scope_fact_cache', '_syntax_fact_cache', '_class_binding_write_cache',
            '_class_binding_escape_cache', '_class_decoration_cache',
            '_class_creation_cache', '_module_class_prefix_cache', '_native_class_protocol_cache',
            '_builtin_scope_cache', '_builtin_module_cache',
            '_decorator_import_namespace_cache', '_fresh_receiver_hook_premise',
            '_fresh_receiver_metadata_guard', '_fresh_function_observer_premise',
            '_contextmanager_namespace_premise', '_function_namespace_cache',
            '_function_factory_cache', '_signature_factory_namespace',
            '_metadata_stdlib_namespace',
            '_supporting_source_hashes',
            '_partial_class_namespace_premise', '_module_getattr_cache_premises',
            '_coroutine_namespace_premises', '_property_namespace_premises',
            '_decorator_literal_writes', '_class_type_test_namespace',
        )
        runtime_namespace_cache = getattr(self, '_runtime_namespace_cache', False)
        previous_runtime_namespace = (
            runtime_namespace_cache
            if self._analysis_budget is None and runtime_namespace_cache is not False
            else False)
        previous_source_facts = ({name: getattr(self, name) for name in source_fact_cache_names
                                  if hasattr(self, name)} if preserve_source_facts else {})
        self._scope_fact_cache = {}
        self._syntax_fact_cache = {}
        self._class_return_cache = {}
        self._class_return_stack = []
        self._context_summaries = {}
        self._context_call_count = 0
        self._object_return_cache = {}
        self._object_fact_functions = 500
        self._object_fact_steps = 2000
        self._function_effect_cache = {}
        self._function_effect_stack = set()
        self._nested_effect_failures = {}
        self._effect_fact_functions = 500
        self._effect_fact_steps = 2000
        self._class_effect_fact_steps = 2000
        self._fact_functions = 500
        self._fact_calls = 2000
        self._class_binding_write_cache = None
        self._class_binding_escape_cache = None
        self._callable_instance_binding_cache = {}
        self._capture_name_cache = {}
        self._decoration_fact_cache = {}
        self._fresh_decoration_fact_cache = {}
        self._class_decoration_cache = {}
        self._class_creation_cache = {}
        self._module_class_prefix_cache = {}
        self._metadata_query_cache = {}
        self._metadata_observer_cache = {}
        self._native_class_protocol_cache = {}
        self._class_type_test_namespace = None
        self._class_identity_cache = {}
        self._class_identity_steps = 20000
        self._class_identity_layout_guard = None
        self._class_identity_instance_guards = {}
        self._class_identity_guard_failures = {}
        self._decorator_import_namespace_cache = {}
        self._fresh_receiver_hook_premise = None
        self._fresh_receiver_metadata_guard = None
        self._fresh_function_observer_premise = False
        self._contextmanager_namespace_premise = None
        self._function_namespace_cache = {}
        self._function_factory_cache = {}
        self._signature_factory_namespace = None
        self._metadata_stdlib_namespace = {}
        self._runtime_namespace_cache = False
        self._supporting_source_hashes = {}
        self._partial_class_namespace_premise = None
        self._module_getattr_cache_premises = None
        self._builtin_scope_cache = {}
        self._builtin_module_cache = {}
        self._coroutine_namespace_premises = None
        self._property_namespace_premises = None
        self._decorator_literal_writes = None
        self._context_enter_cache = {}
        self._context_enter_stack = []
        self._context_exit_stack = []
        self._source_snapshot = (
            self._source_store.snapshot(sorted(self.files), FLOW_SOURCE, budget=self._analysis_budget)
            if self._analysis_budget is not None
            else self._source_store.snapshot(sorted(self.files), FLOW_SOURCE))
        previous = getattr(self, '_indexed_snapshot', None)
        if (previous is not None
                and previous.files == self._source_snapshot.files
                and previous.policy == self._source_snapshot.policy
                and self._indexed_roots == tuple(self.roots)
                and all(previous.documents[path] is self._source_snapshot.documents[path]
                        for path in previous.files)):
            for name, value in previous_source_facts.items():
                setattr(self, name, value)
            # Runtime namespace writes depend only on this immutable source
            # generation. Preserve both complete results and conservative
            # unknown results across unbudgeted queries; budgeted queries must
            # rebuild so their work limits remain authoritative.
            # 源码版本不变时可复用事实；有预算的查询仍须重新计量工作量。
            if self._analysis_budget is None:
                self._runtime_namespace_cache = previous_runtime_namespace
            return
        # Clear the reusable generation before construction so an interrupted
        # or failed build cannot expose partially rebuilt facts on the next query.
        # 构建前清空可复用版本，避免中断后暴露部分索引。
        self._indexed_snapshot = None
        self.definitions = []
        self.classes = []
        self.imports = {}
        self.module_bindings = {}
        self.module_bodies = {}
        self.import_binding_facts = {}
        self.texts = {}
        self.hashes = {}
        self.index_boundaries = []
        self.definition_conditions = {}
        # Preserve the prior behavior of deriving names only for parseable files.
        self._module_index = ModuleIndex.build(
            [path for path in sorted(self.files)
             if self._source_snapshot.documents[path].error is None], self.roots, FLOW_MODULES)
        next_file_indexes = {}
        for path in sorted(self.files):
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint(force=True)
            document = self._source_snapshot.documents[path]
            if document.error is not None:
                self.index_boundaries.append({
                    'file_path': path, 'reason': 'source_unavailable',
                    'detail': str(document.error),
                    'module': module_name_for_path(path, self.roots, FLOW_MODULES)})
                continue
            source, tree = document.text, document.tree
            self.texts[path] = source
            self.hashes[path] = document.sha256
            module = self._module_index.file_to_module[path]
            self.module_bodies.setdefault(module, []).append((path, tree.body))
            cached = getattr(self, '_file_indexes', {}).get(path)
            identity = (module, tuple(self.roots), self._source_snapshot.policy)
            if cached is None or cached[0] is not document or cached[1] != identity:
                facts = self._collect_file_index(path, document, module)
            else:
                facts = cached[2]
            next_file_indexes[path] = document, identity, facts
            bindings, aliases, bound, definitions, classes, conditions = facts
            self.import_binding_facts.setdefault(module, []).append(
                {name: list(nodes) for name, nodes in bindings})
            self.imports[module] = dict(aliases)
            self.module_bindings[module] = set(bound)
            self.definitions.extend(definitions)
            self.classes.extend(classes)
            self.definition_conditions.update(conditions)
        # Add statically supported wildcard bindings after collecting module bodies.
        # 收集模块体后，再加入静态支持的通配符导入绑定。
        star_facts = static_star_imports(self.module_bodies)
        for module, aliases in star_facts.aliases.items():
            self.imports[module].update(aliases)
            for name, statement in star_facts.bindings[module].items():
                self.import_binding_facts[module][0][name] = [statement]
        self._file_indexes = next_file_indexes
        self._definition_index = DefinitionIndex(
            [DefinitionRecord(ref.module, ref.qualname, (ref, node),
                              source_span=SourceSpan.from_ast(ref.file_path, node))
             for ref, node in self.definitions] +
            [DefinitionRecord(ref.module, ref.qualname, (ref, node), kind='class',
                              source_span=SourceSpan.from_ast(ref.file_path, node))
             for ref, node in self.classes])
        self._indexed_snapshot = self._source_snapshot
        self._indexed_roots = tuple(self.roots)

    ## Collect immutable file facts independently of query state.
    ## 独立于查询状态收集不可变文件事实。
    #
    #  @param path Source path.
    #  @param document Exact read-only source version.
    #  @param module Module identity under current import roots.
    #  @return Binding, import and definition facts in source order.
    def _collect_file_index(self, path, document, module):
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        tree = document.tree
        definitions, classes, definition_conditions = [], [], []
        bindings = {}
        for statement in tree.body:
            names = (list(fact.python_binding for fact in import_facts(statement))
                     if isinstance(statement, (ast.Import, ast.ImportFrom))
                     else statement_scope_facts([statement]).bound
                     | _attribute_write_roots(statement))
            for name in names:
                bindings.setdefault(name, []).append(statement)
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for scope in ast.walk(statement):
                    if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    facts = self._builtin_scope_facts(scope)
                    changed = facts.globals & facts.bound
                    if not changed:
                        continue
                    pending = list(scope.body)
                    while pending:
                        nested = pending.pop()
                        if isinstance(nested, ast.Global):
                            for name in changed & set(nested.names):
                                bindings.setdefault(name, []).append(nested)
                        elif not isinstance(nested, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                     ast.ClassDef, ast.Lambda)):
                            pending.extend(ast.iter_child_nodes(nested))
        aliases = {}
        for node in tree.body:
            for fact in import_facts(node):
                if fact.kind == 'import':
                    aliases[fact.python_binding] = (
                        fact.name if fact.asname else fact.python_binding)
                else:
                    prefix = (resolve_relative_module(
                        module,
                        os.path.basename(path).startswith('__init__.'),
                        fact.module, fact.level)
                        if fact.level else fact.module)
                    aliases[fact.python_binding] = prefix + '.' + fact.name
        module_bindings = {
            n.id for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (statement.targets if isinstance(statement, ast.Assign) else [statement.target])
            for n in ast.walk(target) if isinstance(n, ast.Name)}
        evidence_cache = {}
        source_lines = None

        ## Cache source-span evidence and optionally recover exact source text.
        ## 缓存源码位置证据，并按需恢复精确源码文本。
        #
        #  @param node AST node with source positions.
        #  @param text Whether to include the source snippet.
        #  @return Source evidence dictionary.
        def evidence(node, text=False):
            nonlocal source_lines
            key = id(node), text
            if key not in evidence_cache:
                value = asdict(SourceSpan.from_ast(path, node))
                if text:
                    if source_lines is None:
                        source_lines = [line.encode('utf-8') for line in document.text.split('\n')]
                    first, last = node.lineno, node.end_lineno
                    start, end = node.col_offset, node.end_col_offset
                    snippet = (source_lines[first - 1][start:end] if first == last else
                               b'\n'.join([source_lines[first - 1][start:]] +
                                          source_lines[first:last - 1] +
                                          [source_lines[last - 1][:end]]))
                    value['source_text'] = snippet.decode('utf-8')
                evidence_cache[key] = value
            return evidence_cache[key]

        ## Collect nested definitions and their syntactic conditions.
        ## 收集嵌套定义及其语法条件。
        #
        #  @param body Statement sequence.
        #  @param prefix Enclosing qualified-name prefix.
        #  @param conditions Enclosing syntactic conditions.
        #  @return None
        def collect(body, prefix='', conditions=()):
            for node in body:
                if self._analysis_budget is not None:
                    self._analysis_budget.checkpoint()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = prefix + node.name
                    ref = FunctionRef(module, name, path, node.lineno)
                    if conditions:
                        definition_conditions.append((ref, conditions))
                    if not isinstance(node, ast.ClassDef):
                        definitions.append((ref, node))
                    else:
                        classes.append((ref, node))
                    collect(node.body, name + '.', conditions)
                else:
                    ## Collect lambdas without crossing another statement boundary.
                    ## 收集 lambda，不跨越其他语句边界。
                    #
                    #  @param item AST node to inspect.
                    #  @param root Whether this is the starting statement.
                    #  @return None
                    def collect_lambdas(item, root=False):
                        if isinstance(item, ast.Lambda):
                            name = prefix + '<lambda>@%s:%s' % (item.lineno, item.col_offset)
                            ref = FunctionRef(module, name, path, item.lineno)
                            definitions.append((ref, item))
                            if conditions:
                                definition_conditions.append((ref, conditions))
                            collect_lambdas(item.body)
                            return
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            return
                        if not root and isinstance(item, (ast.stmt, ast.ExceptHandler)):
                            return
                        for child in ast.iter_child_nodes(item):
                            collect_lambdas(child)
                    collect_lambdas(node, root=True)
                    for field, value in ast.iter_fields(node):
                        if not isinstance(value, list):
                            continue
                        for child in value:
                            condition = ({'test': evidence(node.test, text=True), 'branch': field == 'body'}
                                if isinstance(node, ast.If) and field in ('body', 'orelse') else
                                {'definition_context': type(node).__name__, 'region': field,
                                 'evidence': evidence(node)})
                            if isinstance(child, ast.stmt):
                                collect([child], prefix, conditions + (condition,))
                            elif isinstance(child, ast.ExceptHandler):
                                collect(child.body, prefix, conditions + ({'handler': evidence(child)},))
        collect(tree.body)
        return (tuple((name, tuple(nodes)) for name, nodes in bindings.items()),
                tuple(aliases.items()), frozenset(module_bindings),
                tuple(definitions), tuple(classes), tuple(definition_conditions))

    ## Resolve exact source base classes without guessing dynamic bases.
    ## 解析精确源码基类，不猜测动态基类。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @return Tuple of base definitions or None when unresolved.
    def _base_classes(self, module, owner):
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        cls = classes[0][1]
        if cls.keywords:
            return None
        result = []
        for base in cls.bases:
            expression = base.value if isinstance(base, ast.Subscript) else base
            name = ast.unparse(expression)
            if (name == 'object' and 'object' not in self.imports.get(module, {})
                    and 'object' not in self.module_bindings.get(module, set())
                    and not self._definition_index.find(module, 'object')
                    and not self._definition_index.find(module, 'object', kind='class')):
                continue
            first, dot, rest = name.partition('.')
            if first in self.module_bindings.get(module, set()):
                return None
            alias = self.imports.get(module, {}).get(first)
            qualified = alias + dot + rest if alias else module + '.' + name
            matches = self._definition_index.find_qualified(
                [qualified], kind='class')
            if len(matches) != 1:
                return None
            result.append(matches[0])
        return tuple(result)

    ## Construct a source class MRO with cycle and ambiguity checks.
    ## 在循环和歧义检查下构造源码类 MRO。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @param seen Ancestor identities already visited.
    #  @return Ordered class definitions or None when unproven.
    def _class_mro(self, module, owner, seen=()):
        identity = (module, owner)
        if identity in seen:
            return None
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        bases = self._base_classes(module, owner)
        if bases is None:
            return None
        sequences = []
        for ref, _ in bases:
            inherited = self._class_mro(
                ref.module, ref.qualname, seen + (identity,))
            if inherited is None:
                return None
            sequences.append(list(inherited))
        sequences.append(list(bases))
        # Apply the C3 merge; incompatible base orders remain unresolved.
        # 执行 C3 合并；基类顺序不兼容时保持未解析。
        result = [classes[0]]
        while any(sequences):
            candidate = next((sequence[0] for sequence in sequences if sequence
                              and all(sequence[0] not in other[1:]
                                      for other in sequences)), None)
            if candidate is None:
                return None
            result.append(candidate)
            for sequence in sequences:
                if sequence and sequence[0] == candidate:
                    sequence.pop(0)
        return tuple(result)

    ## Find an inherited method only when source lookup remains unambiguous.
    ## 仅在源码查找无歧义时查找继承方法。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @param method Method name.
    #  @param seen Ancestor identities already visited.
    #  @param skip_current_members Whether to begin after the current class.
    #  @return Source definition or None when lookup is unproven.
    def _inherited_method(self, module, owner, method, seen=(),
                          skip_current_members=False):
        identity = (module, owner)
        if identity in seen:
            return None
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        cls = classes[0][1]
        if cls.keywords:
            return None
        if (not skip_current_members and any(
               isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id == method
               for statement in cls.body if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               for n in ast.walk(statement))):
            return None
        blocked_names = ('__getattr__', '__getattribute__') if skip_current_members else (
            method, '__getattr__', '__getattribute__')
        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in blocked_names for n in cls.body):
            return None
        bases = self._base_classes(module, owner)
        if bases is None:
            return None
        if bases:
            ref, _ = bases[0]
            matches = self._definition_index.find(
                ref.module, ref.qualname + '.' + method)
            if len(matches) == 1:
                return matches[0]
        mro = self._class_mro(module, owner)
        if mro is None:
            return None
        for ref, base in mro[1:]:
            matches = self._definition_index.find(
                ref.module, ref.qualname + '.' + method)
            if len(matches) == 1:
                return matches[0]
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name in ('__getattr__', '__getattribute__')
                   for n in base.body):
                return None
            if any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                   and n.id == method for statement in base.body
                   if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                   for n in ast.walk(statement)):
                return None
        return None

    ## Select the first modeled allocator or initializer in the source MRO.
    ## 从源码 MRO 中选择首个已建模的分配器或初始化器。
    #
    #  @param target_class Class reference and AST pair.
    #  @return Constructor source member or None when lookup is unproven.
    def _constructor_target(self, target_class):
        ref, _ = target_class
        hierarchy = self._class_mro(ref.module, ref.qualname)
        if not hierarchy or len(hierarchy) > 64:
            return None
        # type.__call__ invokes the MRO-selected allocator before deciding
        # whether initialization applies. A direct __init__ cannot override
        # an inherited __new__, and an unresolved allocator cannot license it.
        # 分配器先于初始化器选择；未解析的分配器不能证明初始化器被调用。
        for method in ('__new__', '__init__'):
            if method == '__init__' and not self._ordinary_construction(
                    ref, allow_bounded_decorations=True):
                return None
            for owner, cls in hierarchy:
                members = [member for member in cls.body
                           if method in statement_scope_facts([member]).bound]
                if members:
                    return constructor_source_member(self, owner, cls, method)
        return None

    ## Select an instance member through an unchanged source MRO.
    ## 通过未变更的源码 MRO 选择实例成员。
    #
    #  @param module Source receiver module.
    #  @param owner Actual receiver class, which may differ from the lexical owner.
    #  @param method Attribute being invoked.
    #  @return Unique source definition or None for unproven lookup/state.
    def _instance_method_candidate(self, module, owner, method):
        hierarchy = self._class_mro(module, owner)
        if not hierarchy or len(hierarchy) > 64:
            return None
        for _, cls in hierarchy:
            if (cls.keywords or any(name in
                    statement_scope_facts(cls.body).bound
                    for name in ('__getattribute__', '__getattr__'))):
                return None
        if member_preservation(self, hierarchy,
                {method, '__getattribute__', '__getattr__', '__class__', '__bases__', '*'}) is None:
            return None
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in (method, '*', '__class__', '__bases__')
                and any(written == ref for ref, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return None
        for ref, cls in hierarchy:
            if method in statement_scope_facts(cls.body).bound:
                return constructor_source_member(self, ref, cls, method)
        return None

    ## Find the innermost indexed class enclosing a source definition.
    ## 查找包围源码定义的最内层已索引类。
    #
    #  @param ref Source definition identity.
    #  @return Class name or empty string when no class is found.
    def _lexical_class_name(self, ref):
        parts = ref.qualname.split('.')[:-1]
        for length in range(len(parts), 0, -1):
            if self._definition_index.find(ref.module, '.'.join(parts[:length]), kind='class'):
                return parts[length - 1]
        return ''

    ## Reuse statement-ordered syntax only within this immutable source generation.
    ## 仅在当前不可变源码生成版本内复用按语句排序的语法事实。
    #
    #  @param body Ordered statements, never a synthetic or modified source body.
    #  @param limit Remaining caller-specific node allowance.
    #  @return Complete structure, or None to retain budgeted per-node traversal.
    def _syntax_facts(self, body, limit):
        if self._analysis_budget is not None:
            # Budgeted traversals must charge their own visits.
            # 有预算的遍历必须单独计量节点访问。
            return None
        key = tuple(body)
        facts = self._syntax_fact_cache.get(key)
        if facts is None:
            facts = syntax_facts.body_syntax(key, limit)
            self._syntax_fact_cache[key] = facts
        elif len(facts.nodes) > limit:
            raise syntax_facts.SyntaxLimit()
        return facts

    ## Read immutable lexical facts once per AST definition in this source generation.
    ## 在当前源码生成版本内，每个 AST 定义只读取一次不可变词法事实。
    #
    #  @param node Function or lambda definition.
    #  @return Flow-compatible lexical facts.
    def _scope_facts(self, node):
        facts = self._scope_fact_cache.get(node)
        if facts is None:
            facts = function_scope_facts(node, FLOW_SCOPE)
            self._scope_fact_cache[node] = facts
        return facts

    ## Collect bindings relevant to builtin lookup, including definition inputs.
    ## 收集与内置名称查找相关的绑定，包括定义时求值的输入。
    #
    #  @param body Statement sequence.
    #  @return Lexical facts augmented with definition-evaluation bindings.
    def _builtin_statement_facts(self, body):
        facts = statement_scope_facts(body, _BUILTIN_SCOPE)
        bound = set(facts.bound)

        ## Visit expressions evaluated while a definition is created.
        ## 访问创建定义时求值的表达式。
        #
        #  @param node Source AST node.
        #  @return None
        def evaluations(node):
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                expressions = list(node.args.defaults)
                expressions.extend(value for value in node.args.kw_defaults if value is not None)
                expressions.extend(getattr(node, 'decorator_list', []))
                arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                arguments += [value for value in (node.args.vararg, node.args.kwarg) if value is not None]
                expressions.extend(argument.annotation for argument in arguments if argument.annotation is not None)
                if getattr(node, 'returns', None) is not None:
                    expressions.append(node.returns)
            elif isinstance(node, ast.ClassDef):
                expressions = list(node.decorator_list) + list(node.bases)
                expressions.extend(keyword.value for keyword in node.keywords)
            else:
                for child in ast.iter_child_nodes(node):
                    evaluations(child)
                return
            # Definition evaluation belongs to this lexical body, not the new
            # function/class/lambda body. Keep the shared collectors unchanged.
            # 定义输入在外层词法体求值，不属于新定义的执行体。
            bound.update(statement_scope_facts(expressions, _BUILTIN_SCOPE).bound)
            for expression in expressions:
                evaluations(expression)

        for statement in body:
            evaluations(statement)
        return replace(facts, bound=frozenset(bound))

    ## Cache builtin-lookup bindings for a function, lambda or class body.
    ## 缓存函数、lambda 或类体的内置名称查找绑定。
    #
    #  @param node Source definition AST.
    #  @return Immutable lexical facts for builtin lookup.
    def _builtin_scope_facts(self, node):
        facts = self._builtin_scope_cache.get(node)
        if facts is None:
            body = [node.body] if isinstance(node, ast.Lambda) else node.body
            facts = self._builtin_statement_facts(body)
            # The statement collector already supplies this policy's body
            # facts and definition-evaluation bindings. Only root parameters
            # distinguish the function collector; do not walk its body twice.
            if not isinstance(node, ast.ClassDef) and _BUILTIN_SCOPE.include_parameters:
                args = node.args
                parameters = {arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs}
                parameters.update(arg.arg for arg in (args.vararg, args.kwarg) if arg)
                if _BUILTIN_SCOPE.exclude_outer_declarations:
                    parameters.difference_update(facts.globals | facts.nonlocals)
                facts = replace(facts, bound=facts.bound | parameters)
            self._builtin_scope_cache[node] = facts
        return facts

    ## Classify a bare builtin spelling under explicit lexical lookup rules.
    ## 按显式词法查找规则分类裸内置名称。
    #
    #  @param ref Source function identity.
    #  @param node Source function or lambda whose lexical names are checked.
    #  @param name Bare name, not an attribute or import alias.
    #  @param env Optional current bindings, including unknown/empty local bindings.
    #  @param definition_scope Check a definition's enclosing scope, not its future body locals.
    #  @return confirmed_builtin, source_binding, or unconfirmed; no runtime proof.
    def _builtin_name_status(self, ref, node, name, env=None, definition_scope=False):
        if not hasattr(builtins, name):
            return 'unconfirmed'
        if env is not None and name in env:
            return 'source_binding'
        facts = (statement_scope_facts([]) if definition_scope else self._builtin_scope_facts(node))
        if name in facts.bound:
            return 'source_binding'
        nonlocal_name = name in facts.nonlocals
        parent = ref.qualname.rpartition('.')[0]
        if name not in facts.globals:
            while parent:
                enclosing = self._definition_index.find(ref.module, parent)
                if len(enclosing) > 1:
                    return 'unconfirmed'
                if enclosing:
                    outer = self._builtin_scope_facts(enclosing[0][1])
                    if name in outer.globals:
                        break
                    if name in outer.bound - outer.nonlocals:
                        return 'source_binding'
                    nonlocal_name = nonlocal_name or name in outer.nonlocals
                elif not self._definition_index.find(ref.module, parent, kind='class'):
                    return 'unconfirmed'
                parent = parent.rpartition('.')[0]
        if nonlocal_name:
            return 'unconfirmed'

        # A module binding, incomplete index or possible namespace write blocks proof.
        # 模块绑定、索引不完整或可能的命名空间写入都会阻止证明。
        if ref.module not in self._builtin_module_cache:
            bodies = self.module_bodies.get(ref.module, [])
            names = set()
            uncertain = len(bodies) != 1 or any(
                item.get('module') == ref.module for item in self.index_boundaries)
            for _, body in bodies:
                names.update(self._builtin_statement_facts(body).bound)
                for statement in body:
                    for child in ast.walk(statement):
                        if self._analysis_budget is not None:
                            self._analysis_budget.checkpoint()
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            scope = self._builtin_scope_facts(child)
                            names.update(scope.globals & scope.bound)
            self._builtin_module_cache[ref.module] = names, uncertain
        names, uncertain = self._builtin_module_cache[ref.module]
        if name in names:
            return 'source_binding'
        if uncertain or '*' in names or '__builtins__' in names:
            return 'unconfirmed'
        if not namespace_unmodified(self, ref.module + '.' + name):
            return 'unconfirmed'
        return 'confirmed_builtin'

    ## Find a uniquely constructed field and its undecorated source method.
    ## 查找唯一构造的字段及其未装饰源码方法。
    #
    #  @param ref Accessing method identity.
    #  @param field Instance field name.
    #  @param method Requested method name.
    #  @return Target definition and assignment, or None when unproven.
    def _field_candidate(self, ref, field, method):
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        if len(classes) != 1 or classes[0][1].decorator_list:
            return None
        cls = classes[0][1]
        methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(n.name in ('__getattribute__', '__getattr__', field) for n in methods):
            return None
        writes = []
        for member in methods:
            for statement in ast.walk(member):
                if isinstance(statement, ast.Attribute) and statement.attr == field and isinstance(statement.ctx, (ast.Store, ast.Del)):
                    writes.append(statement)
        init = next((n for n in methods if n.name == '__init__' and not n.decorator_list), None)
        if len(writes) != 1 or init is None:
            return None
        assignment = next((n for n in init.body if isinstance(n, ast.Assign)
                           and len(n.targets) == 1 and n.targets[0] is writes[0]), None)
        args = init.args.posonlyargs + init.args.args
        if (assignment is None or not args or not isinstance(writes[0].value, ast.Name)
                or writes[0].value.id != args[0].arg or not isinstance(assignment.value, ast.Call)):
            return None
        name = ast.unparse(assignment.value.func)
        first, dot, rest = name.partition('.')
        if first in self.module_bindings.get(ref.module, set()) or first in self._scope_facts(init).bound:
            return None
        alias = self.imports.get(ref.module, {}).get(first)
        qualified = alias + (dot + rest if dot else '') if alias else ref.module + '.' + name
        targets = self._definition_index.find_qualified([qualified], kind='class')
        if len(targets) != 1 or targets[0][1].decorator_list:
            return None
        target_class = targets[0]
        if any(isinstance(n, ast.FunctionDef) and n.name in ('__getattribute__', '__getattr__', '__new__') for n in target_class[1].body):
            return None
        target = self._definition_index.find(
            target_class[0].module, target_class[0].qualname + '.' + method)
        return (target[0], assignment) if len(target) == 1 and not target[0][1].decorator_list else None

    ## Find constructor-backed field types shared by every normal return path.
    ## 查找所有正常返回路径共享的构造函数字段类型。
    #
    #  @param target Local method definition.
    #  @return Bounded field/type facts with assignment and return AST evidence.
    def _returned_field_instances(self, target):
        ref, accessor = target
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        if len(classes) != 1 or classes[0][1].decorator_list or accessor.decorator_list:
            return []
        cls = classes[0][1]
        owner_hierarchy = self._class_mro(ref.module, owner)
        if owner_hierarchy is None or any(
                base.decorator_list or any(
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name in ('__getattr__', '__getattribute__',
                                        '__setattr__', '__delattr__')
                    for member in base.body)
                for _, base in owner_hierarchy):
            return []
        params = accessor.args.posonlyargs + accessor.args.args
        if not params or accessor.args.vararg or accessor.args.kwarg:
            return []
        receiver = params[0].arg
        methods = [member for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name)
                       and isinstance(node.ctx, ast.Store)
                       and node.id == accessor.name
                       for node in ast.walk(statement))
               for statement in cls.body):
            return []

        ## Collect supported receiver-field returns and detect fallthrough paths.
        ## 收集受支持的接收者字段返回并检测可继续执行的路径。
        #
        #  @param statements Statement sequence to inspect.
        #  @return Return nodes and fallthrough flag, or None for unsupported syntax.
        def returns_from(statements):
            returns = []
            open_path = True
            for statement in statements:
                if not open_path:
                    break
                if isinstance(statement, ast.Return):
                    value = statement.value
                    if not (isinstance(value, ast.Attribute)
                            and isinstance(value.value, ast.Name)
                            and value.value.id == receiver):
                        return None
                    returns.append(statement)
                    open_path = False
                elif isinstance(statement, ast.If):
                    if not (isinstance(statement.test, ast.Constant)
                            or (isinstance(statement.test, ast.Name)
                                and statement.test.id != receiver)):
                        return None
                    left = returns_from(statement.body)
                    right = returns_from(statement.orelse)
                    if left is None or right is None:
                        return None
                    returns.extend(left[0] + right[0])
                    open_path = left[1] or right[1]
                elif isinstance(statement, ast.Pass) or (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str)):
                    continue
                else:
                    return None
            return returns, open_path

        paths = returns_from(accessor.body)
        if paths is None or paths[1] or not paths[0]:
            return []
        fields = {statement.value.attr for statement in paths[0]}
        if len(fields) != 1:
            return []
        field = next(iter(fields))
        if any(any(getattr(member, 'name', None) == field or
                   (isinstance(member, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    and any(isinstance(node, ast.Name)
                            and isinstance(node.ctx, ast.Store)
                            and node.id == field
                            for node in ast.walk(member)))
                   for member in base.body)
               for _, base in owner_hierarchy):
            return []
        writes = [node for member in methods for node in ast.walk(member)
                  if isinstance(node, ast.Attribute) and node.attr == field
                  and isinstance(node.ctx, (ast.Store, ast.Del))]
        initializers = [member for member in methods if member.name == '__init__']
        if (len(writes) != 1 or len(initializers) != 1
                or initializers[0].decorator_list):
            return []
        init = initializers[0]
        if any(isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                       and node.id == '__init__' for node in ast.walk(statement))
               for statement in cls.body):
            return []
        assignment = next((statement for statement in init.body
                           if isinstance(statement, ast.Assign)
                           and len(statement.targets) == 1
                           and statement.targets[0] is writes[0]
                           and isinstance(writes[0].value, ast.Name)
                           and writes[0].value.id == receiver), None)
        if assignment is None:
            return []
        if any(statement is not assignment and not isinstance(statement, ast.Pass)
               and not (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))
               for statement in init.body):
            return []
        if any((isinstance(node, ast.Attribute)
                and node.attr == '__dict__')
               or isinstance(node, ast.NamedExpr)
               or (isinstance(node, ast.Call)
                   and ((isinstance(node.func, ast.Name)
                         and node.func.id in ('setattr', 'delattr', 'vars'))
                        or (isinstance(node.func, ast.Attribute)
                            and node.func.attr in ('__setattr__', '__delattr__'))))
               for member in methods for node in ast.walk(member)
               if node is not assignment.value):
            return []

        ## Resolve every supported conditional constructor alternative.
        ## 解析所有受支持的条件构造器候选。
        #
        #  @param value Constructor expression.
        #  @return Class identities or None when an alternative is unproven.
        def constructors(value):
            if isinstance(value, ast.IfExp):
                if any(isinstance(node, (ast.Call, ast.NamedExpr))
                       for node in ast.walk(value.test)):
                    return None
                left, right = constructors(value.body), constructors(value.orelse)
                return left + right if left is not None and right is not None else None
            if not isinstance(value, ast.Call):
                return None
            name = ast.unparse(value.func)
            first = name.partition('.')[0]
            if (first in self.module_bindings.get(ref.module, set())
                    or first in self._scope_facts(init).bound):
                return None
            match = self._resolve_class(ref, name)
            if match is None or match[1].decorator_list or match[1].keywords:
                return None
            hierarchy = self._class_mro(match[0].module, match[0].qualname)
            if hierarchy is None or any(
                    base.decorator_list or any(
                        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and member.name in ('__new__', '__getattribute__',
                                            '__getattr__')
                        for member in base.body)
                    for _, base in hierarchy):
                return None
            return [match[0]]

        types = constructors(assignment.value)
        if not types:
            return []
        return [{'field': field, 'instance_type': asdict(class_ref),
                 'assignment_ref': ref, 'assignment_node': assignment,
                 'return_ref': ref, 'return_nodes': paths[0]}
                for class_ref in _unique(types)]

    ## Recognize an unshadowed builtin staticmethod or classmethod decorator.
    ## 识别未被遮蔽的内置 staticmethod 或 classmethod 装饰器。
    #
    #  @param target Function identity and AST pair.
    #  @return Descriptor name or None when not proven.
    def _descriptor_kind(self, target):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or not isinstance(decorators[0], ast.Name):
            return None
        name = decorators[0].id
        if name not in ('staticmethod', 'classmethod'):
            return None
        if (name in self.imports.get(ref.module, {})
                or name in self.module_bindings.get(ref.module, set())
                or self._definition_index.find(ref.module, name)
                or self._definition_index.find(ref.module, name, kind='class')):
            return None
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        cls = classes[0][1] if classes else None
        if cls is None:
            return None
        for statement in cls.body:
            if statement is node:
                break
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import,
                                      ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                names = {item.id for item in ast.walk(statement)
                         if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)}
                if name in names or getattr(statement, 'name', None) == name:
                    return None
        return name

    ## Scan bounded source for class-binding writes and optional escape evidence.
    ## 有界扫描源码中的类绑定写入及可选逃逸证据。
    #
    #  @param include_escapes Include possible class escapes in the scan.
    #  @param private_result Optional private-result projection callback.
    #  @return Pair of write records and truncation flag.
    def _class_binding_writes(self, include_escapes=False, private_result=None):
        cached = self._class_binding_escape_cache if include_escapes else self._class_binding_write_cache
        if cached is not None and private_result is None:
            return cached
        writes, remaining = [], [_CLASS_BINDING_NODE_LIMIT]
        closure_bindings = {}

        ## Find the unique source class owning a qualified method.
        ## 查找限定方法所属的唯一源码类。
        #
        #  @param qualified Qualified method name.
        #  @return Zero or one class identities.
        def method_owner(qualified):
            target = self._resolve_import_binding(qualified) if include_escapes else None
            owner = target[0].qualname.rpartition('.')[0] if target else ''
            classes = self._definition_index.find(target[0].module, owner, kind='class') if owner else []
            return [classes[0][0]] if len(classes) == 1 else []

        ## Resolve possible class identities from a bounded source expression.
        ## 从有界源码表达式解析可能的类标识。
        #
        #  @param expression Candidate expression.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @return Candidate class identities.
        def identity(expression, ref, aliases):
            if isinstance(expression, ast.IfExp):
                return _unique(identity(expression.body, ref, aliases)
                               + identity(expression.orelse, ref, aliases))
            if isinstance(expression, ast.Name) and expression.id in aliases:
                value = aliases[expression.id]
                return [value] if isinstance(value, FunctionRef) else value if isinstance(value, list) else []
            if not isinstance(expression, (ast.Name, ast.Attribute)):
                return []
            name = ast.unparse(expression)
            first, dot, rest = name.partition('.')
            if first in aliases:
                imported = aliases[first]
                if include_escapes and isinstance(imported, FunctionRef) and dot:
                    return method_owner(imported.module + '.' + imported.qualname + dot + rest)
                if isinstance(imported, str) and dot:
                    target = self._definition_index.resolve_qualified(
                        [imported + dot + rest], self.imports, kind='class')
                    return [target[0]] if target else method_owner(imported + dot + rest)
                return []
            target = self._resolve_class(ref, name)
            if target is None:
                target = self._class_symbol(ref.module + '.' + name)
            return [target[0]] if target else method_owner(ref.module + '.' + name)

        ## Find class identities potentially exposed by an expression.
        ## 查找表达式可能暴露的类标识。
        #
        #  @param expression Candidate expression.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @param held Captured class identities.
        #  @param result_only Restrict traversal to result projections.
        #  @param contained_only Treat candidates as contained exposures.
        #  @return Potentially exposed class identities.
        def exposed(expression, ref, aliases, held, result_only=False, contained_only=False):
            # Containment is an escape hazard, never an exact class identity.
            # 容器持有表示可能逃逸，不能据此断言精确类标识。
            found, pending = [], [(expression, aliases, held, result_only)]
            while pending:
                child, names, captures, projection = pending.pop()
                if child is None or isinstance(child, _CLASS_BINDING_IRRELEVANT_LEAVES):
                    continue
                remaining[0] -= 1
                if remaining[0] < 0:
                    break
                if child is None or projection and isinstance(child, ast.Call):
                    # Returning a call does not itself prove a returned class.
                    # Calls and their arguments are inspected separately below.
                    continue
                if (isinstance(child, ast.Attribute)
                        and native_function_scalar(self, child,
                            lambda value: identity(value, ref, names))):
                    # This scalar projection grants no class/method alias.
                    # Other escapes and every visible writer stay in the scan;
                    # consumers still require the complete closed-use invariant.
                    continue
                if (private_result is not None and isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Call)):
                    constructor = child.func.value
                    references = identity(constructor.func, ref, names)
                    if private_result(ref, child, references):
                        # Only the constructor's class identity is projected
                        # out. Input capabilities and both calls remain checked.
                        pending.extend((argument, names, captures, projection)
                                       for argument in constructor.args)
                        pending.extend((keyword.value, names, captures, projection)
                                       for keyword in constructor.keywords)
                        continue
                if isinstance(child, ast.Lambda):
                    defaults = child.args.defaults + [v for v in child.args.kw_defaults if v is not None]
                    pending.extend((value, names, captures, projection) for value in defaults)
                    bound = self._scope_facts(child).bound
                    local = dict(names)
                    local.update({name: None for name in bound})
                    retained = {name: refs for name, refs in captures.items() if name not in bound}
                    if ref not in closure_bindings:
                        enclosing = self._definition_index.find(ref.module, ref.qualname)
                        scope = self._scope_facts(enclosing[0][1]) if len(enclosing) == 1 else None
                        closure_bindings[ref] = ((scope.bound | scope.nonlocals) - scope.globals
                                                 if scope is not None else set())
                    for name in transitive_captured_names(child, set(names) | set(captures)):
                        remaining[0] -= 1
                        if remaining[0] < 0:
                            break
                        references = identity(ast.Name(id=name, ctx=ast.Load()), ref, names)
                        found.extend(captures.get(name, ()))
                        global_class = self._class_symbol(ref.module + '.' + name)
                        if (name in closure_bindings[ref] or global_class is None
                                or references != [global_class[0]]):
                            found.extend(references)
                    # A global name used as a future call's receiver is not
                    # stored in this function's closure. Actual arguments,
                    # returns and writes in that future body are scanned below.
                    pending.append((child.body, local, retained, True))
                    continue
                if isinstance(child, ast.Call) and native_class_operand(self, ref, child, names):
                    # The tested value still evaluates normally; nested calls
                    # can expose a class even though the native class operand
                    # itself does not pass to a user __instancecheck__ hook.
                    pending.append((child.args[0], names, captures, projection))
                    continue
                if isinstance(child, (ast.Name, ast.Attribute)):
                    if not contained_only:
                        found.extend(identity(child, ref, names))
                    if isinstance(child, ast.Name):
                        found.extend(captures.get(child.id, []))
                pending.extend((value, names, captures, projection) for value in ast.iter_child_nodes(child))
            return _unique(found)

        ## Record potential class escapes at a source node.
        ## 记录源码节点处可能发生的类逃逸。
        #
        #  @param references Class identities potentially exposed.
        #  @param ref Enclosing source identity.
        #  @param node Evidence AST node.
        #  @return None
        def escape(references, ref, node):
            writes.extend((class_ref, '*', 'visible_class_escape', ref, node)
                          for class_ref in references)

        ## Traverse one source node while tracking class aliases and captures.
        ## 遍历源码节点，同时跟踪类别名和捕获。
        #
        #  @param node AST node to inspect.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @param held Captured class identities.
        #  @return None
        def walk(node, ref, aliases, held):
            # These leaves cannot contain an import, class reference, closure or
            # effect. Inspect their parent operations, not repeated literal data.
            if isinstance(node, _CLASS_BINDING_IRRELEVANT_LEAVES):
                return
            remaining[0] -= 1
            if remaining[0] < 0:
                return
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                local = dict(aliases)
                bound = self._scope_facts(node).bound
                local.update({name: None for name in bound})
                retained = {name: refs for name, refs in held.items() if name not in bound}
                args = node.args
                for parameter in args.posonlyargs + args.args + args.kwonlyargs + [
                        arg for arg in (args.vararg, args.kwarg) if arg]:
                    local[parameter.arg] = None
                child_ref = FunctionRef(ref.module, (ref.qualname + '.' if ref.qualname else '')
                                        + getattr(node, 'name', '<lambda>'), ref.file_path)
                if isinstance(node, ast.Lambda):
                    for value in args.defaults + [v for v in args.kw_defaults if v is not None]:
                        walk(value, ref, aliases, held)
                    # Keep the enclosing source scope for builtin lookup;
                    # lambda parameters are masked in the scanner environment.
                    future = ast.copy_location(ast.Return(value=node.body), node.body)
                    walk(future, ref, local, retained)
                    return
                for statement in node.body if not isinstance(node, ast.Lambda) else []:
                    walk(statement, child_ref, local, retained)
                return
            if isinstance(node, ast.ClassDef):
                child_ref = FunctionRef(ref.module, (ref.qualname + '.' if ref.qualname else '')
                                        + node.name, ref.file_path)
                local = dict(aliases)
                retained = dict(held)
                for statement in node.body:
                    walk(statement, child_ref, local, retained)
                return
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for fact in import_facts(node):
                    qualified = (fact.name if fact.kind == 'import' else
                        (resolve_relative_module(ref.module,
                            os.path.basename(ref.file_path).startswith('__init__.'),
                            fact.module, fact.level)
                         if fact.level else fact.module) + '.' + fact.name)
                    target = self._class_symbol(qualified)
                    aliases[fact.python_binding] = target[0] if target else qualified
                    if include_escapes and target and ref.qualname:
                        held[fact.python_binding] = _unique(held.get(fact.python_binding, []) + [target[0]])
            if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
                owner = node.value
                attribute = node.attr if isinstance(node, ast.Attribute) else '*'
                if isinstance(owner, ast.Attribute) and owner.attr == '__dict__':
                    owner = owner.value
                target = identity(owner, ref, aliases)
                while not target and isinstance(owner, ast.Attribute):
                    attribute, owner = owner.attr, owner.value
                    target = identity(owner, ref, aliases)
                for class_ref in target:
                    writes.append((class_ref, attribute, 'visible_method_write', ref, node))
                if include_escapes:
                    escape([value for value in exposed(node.value, ref, aliases, held)
                            if value not in target], ref, node)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                function = ast.unparse(node.func)
                first, dot, rest = function.partition('.')
                imported = aliases.get(first)
                canonical = imported + dot + rest if isinstance(imported, str) else function
                if canonical in ('setattr', 'delattr', 'builtins.setattr', 'builtins.delattr') and node.args:
                    target = identity(node.args[0], ref, aliases)
                    if target:
                        attribute = (node.args[1].value if len(node.args) > 1
                            and isinstance(node.args[1], ast.Constant)
                            and isinstance(node.args[1].value, str) else '*')
                        writes.extend((class_ref, attribute, 'visible_dynamic_attribute_write', ref, node)
                                      for class_ref in target)
            if include_escapes:
                if isinstance(node, ast.Call):
                    escape(exposed(node.func, ref, aliases, held, contained_only=True), ref, node)
                    arguments = list(node.args) + [keyword.value for keyword in node.keywords]
                    if native_class_operand(self, ref, node, aliases):
                        arguments = arguments[:1]
                    for argument in arguments:
                        escape(exposed(argument, ref, aliases, held), ref, node)
                elif isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom)):
                    escape(exposed(node.value, ref, aliases, held, result_only=True), ref, node)
            for child in ast.iter_child_nodes(node):
                walk(child, ref, aliases, held)
            if isinstance(node, (ast.Assign, ast.AnnAssign)) or include_escapes and isinstance(
                    node, (ast.AugAssign, ast.NamedExpr)):
                target = identity(node.value, ref, aliases)
                contained = (exposed(node.value, ref, aliases, held, result_only=True)
                             if include_escapes else [])
                for destination in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(destination, ast.Name):
                        previous = aliases.get(destination.id)
                        previous = ([previous] if isinstance(previous, FunctionRef) else
                                    previous if isinstance(previous, list) else [])
                        aliases[destination.id] = _unique(previous + target)
                    if include_escapes:
                        if isinstance(destination, (ast.Attribute, ast.Subscript)):
                            escape(contained, ref, node)
                        else:
                            for child in ast.walk(destination):
                                if isinstance(child, ast.Name):
                                    held[child.id] = _unique(held.get(child.id, []) + contained)

        for module, bodies in self.module_bodies.items():
            for path, body in bodies:
                aliases, held = {}, {}
                for statement in body:
                    walk(statement, FunctionRef(module, '', path), aliases, held)
        result = writes, remaining[0] < 0
        if private_result is not None:
            return result
        if include_escapes:
            self._class_binding_escape_cache = result
        else:
            self._class_binding_write_cache = result
        return result

    ## Resolve a single stable source decorator definition.
    ## 解析单个稳定的源码装饰器定义。
    #
    #  @param target Decorated source identity and AST pair.
    #  @param kind Definition category to resolve.
    #  @return Decorator definition or None when ambiguous or unsupported.
    def _decorator_definition(self, target, kind='function'):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or not isinstance(
                decorators[0], (ast.Name, ast.Attribute)):
            return None
        name = ast.unparse(decorators[0])
        first, dot, rest = name.partition('.')
        owner = ref.qualname.rpartition('.')[0]
        if owner:
            ancestors = owner.split('.')
            if any(self._definition_index.find(ref.module, '.'.join(
                    ancestors[:length])) for length in range(1, len(ancestors))):
                return None
            enclosing = self._definition_index.find(ref.module, owner, kind='class')
            if len(enclosing) != 1:
                return None
            preceding = []
            for statement in enclosing[0][1].body:
                if statement is node:
                    break
                preceding.append(statement)
            if first in statement_scope_facts(preceding).bound:
                return None
        imported = self.imports.get(ref.module, {}).get(first)
        qualified = imported + (dot + rest if dot else '') if imported else ref.module + '.' + name
        if not self._stable_import_name(ref.module + '.' + first):
            return None
        decorator = self._definition_index.resolve_qualified([qualified], self.imports,
            kind=kind, qualified_guard=self._stable_import_name)
        if decorator is None or getattr(decorator[1], 'decorator_list', []):
            return None
        return decorator

    ## Prove that every normal decorator return preserves its input identity.
    ## 证明装饰器每条正常返回路径均保留输入身份。
    #
    #  @param target Decorated source definition.
    #  @return Source proof facts, or None outside the bounded supported shape.
    def _identity_decorator(self, target):
        decorator = self._decorator_definition(target)
        if decorator is None or not isinstance(decorator[1], ast.FunctionDef):
            return None
        ref, node = decorator
        arguments = node.args
        positional = arguments.posonlyargs + arguments.args
        if (len(positional) != 1 or arguments.vararg or arguments.kwonlyargs
                or arguments.kwarg or arguments.defaults):
            return None
        parameter = positional[0].arg
        body = node.body
        if (not body or not isinstance(body[-1], ast.Return)
                or parameter in statement_scope_facts(body).bound):
            return None
        nodes = list(ast.walk(node))
        if len(nodes) > 256:
            return None
        allowed = (ast.If, ast.Assign, ast.AnnAssign, ast.AugAssign,
                   ast.Expr, ast.Return, ast.Raise, ast.Pass)
        returns = []
        for child in nodes[1:]:
            if (isinstance(child, ast.stmt) and not isinstance(child, allowed)
                    or isinstance(child, (ast.Lambda, ast.Yield, ast.YieldFrom,
                                          ast.Await, ast.ListComp, ast.SetComp,
                                          ast.DictComp, ast.GeneratorExp))):
                return None
            if isinstance(child, ast.Return):
                if not isinstance(child.value, ast.Name) or child.value.id != parameter:
                    return None
                returns.append(child)
            if (isinstance(child, (ast.Assign, ast.AnnAssign))
                    and isinstance(child.value, ast.Name)
                    and child.value.id == parameter):
                return None
            if isinstance(child, (ast.Attribute, ast.Subscript)) and isinstance(
                    child.ctx, (ast.Store, ast.Del)):
                root = child.value
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    root = root.value
                if isinstance(root, ast.Name) and root.id == parameter:
                    return None
        return {'decorator': ref, 'definition': node,
                'parameter': parameter, 'returns': returns,
                'effects_unmodeled': any(isinstance(child, ast.Call) or
                    isinstance(child, (ast.Attribute, ast.Subscript)) and
                    isinstance(child.ctx, ast.Store) for child in nodes)}

    ## Describe one bounded decoration on the exact original source definition.
    ## 描述精确原始源码定义上的有界装饰效果。
    #
    #  @param target FunctionRef and source definition.
    #  @return JSON-safe function-level effect facts, separate from identity proof.
    def _decoration_facts(self, target):
        ref, node = target
        original = [item for item in self._definition_index.find(ref.module, ref.qualname) if item[0] == ref]
        if len(original) == 1:
            node = original[0][1]
            target = ref, node
        if ref not in self._decoration_fact_cache:
            decorators = getattr(node, 'decorator_list', [])
            if not decorators:
                self._decoration_fact_cache[ref] = []
                return []
            summary = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
            self._decoration_fact_cache[ref] = [
                _DecoratorEffects(self, target, summary.evidence_at, _DECORATOR_EFFECT_NODE_LIMIT).fact(
                    expression, multiple=len(decorators) != 1)
                for expression in decorators]
            if (len(decorators) == 1 and isinstance(decorators[0], ast.Attribute)
                    and isinstance(decorators[0].value, ast.Name)):
                owner_name, _, method_name = ref.qualname.rpartition('.')
                owners = (self._definition_index.find(ref.module, owner_name, kind='class')
                          if owner_name else [(ref, node)])
                if len(owners) == 1 and self._stable_import_name(ref.module + '.' + ref.qualname):
                    assumptions, paths = set(), {ref.file_path}
                    stable = True
                    if owner_name:
                        writes, truncated = self._class_binding_writes()
                        stable = not truncated and not any(
                            owner == owners[0][0] and name in (method_name, '*', '__class__', '__bases__')
                            for owner, name, _, _, _ in writes)
                    if (stable and _source_callable_object_identity(
                            self, owners[0][0], node, paths, assumptions)
                            == 'source_callable_object_identity_decorator'
                            and all(path in self.hashes for path in paths)):
                        module = self.imports.get(ref.module, {}).get(decorators[0].value.id)
                        decorator_files = {path for path, _ in self.module_bodies.get(module, [])}
                        paths.update(decorator_files)
                        if not decorator_files or any(path not in self.hashes for path in paths):
                            return copy.deepcopy(self._decoration_fact_cache[ref])
                        assumptions.add('module_initialization_completed_before_query')
                        self._decoration_fact_cache[ref][0]['callable_object_identity_proof'] = {
                            'kind': 'source_callable_object_identity', 'status': 'source_bound',
                            'basis': 'source_snapshot', 'completion': 'normal_return',
                            'runtime_target_confirmed': False, 'function': asdict(ref),
                            'expression': summary.evidence_at(ref, decorators[0]),
                            'returned_object': 'original_function',
                            'mutated_function_attributes': ['__doc__'],
                            'decorator_source_files': sorted(decorator_files),
                            'source_hashes': {path: self.hashes[path] for path in sorted(paths)},
                            'assumptions': sorted(assumptions)}
        return copy.deepcopy(self._decoration_fact_cache[ref])

    ## Refine an identity-preserving decoration using a fresh-function proof.
    ## 使用新建函数证明细化保留身份的装饰事实。
    #
    #  @param target Function identity and source definition.
    #  @return Copied list of refined facts, possibly empty.
    def _fresh_decoration_facts(self, target):
        ref, node = target
        if ref not in self._fresh_decoration_fact_cache:
            self._fresh_decoration_fact_cache[ref] = []
            ordinary = self._decoration_facts(target)
            if (len(ordinary) == 1 and ordinary[0]['identity_status'] == 'preserved'
                    and ordinary[0]['body_binding_status'] == 'unknown'):
                summary = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
                fact = fresh_decoration(self, target, summary.evidence_at, _DECORATOR_EFFECT_NODE_LIMIT)
                if fact is not None:
                    self._fresh_decoration_fact_cache[ref] = [fact]
        return copy.deepcopy(self._fresh_decoration_fact_cache[ref])

    ## Select ordinary or refined decoration facts for binding analysis.
    ## 为绑定分析选择普通或细化后的装饰事实。
    #
    #  @param target Function identity and source definition.
    #  @return Decoration fact list.
    def _binding_decoration_facts(self, target):
        facts = self._decoration_facts(target)
        if len(facts) == 1 and facts[0]['body_binding_status'] != 'preserved':
            return self._fresh_decoration_facts(target) or facts
        return facts

    ## Resolve a simple noncapturing wrapper returned by a source decorator.
    ## 解析源码装饰器返回的简单无捕获包装函数。
    #
    #  @param target Decorated source identity and AST pair.
    #  @return Wrapper definition or None when the shape is unsupported.
    def _decorated_target(self, target):
        decorator = self._decorator_definition(target)
        if decorator is None or not isinstance(decorator[1], ast.FunctionDef):
            return None
        arguments = decorator[1].args
        positional = arguments.posonlyargs + arguments.args
        if (len(positional) != 1 or arguments.vararg or arguments.kwonlyargs
                or arguments.kwarg or arguments.defaults):
            return None
        body = [statement for statement in decorator[1].body
                if not (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))]
        if (len(body) != 2 or not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef))
                or body[0].decorator_list or not isinstance(body[1], ast.Return)
                or not isinstance(body[1].value, ast.Name)
                or body[1].value.id != body[0].name):
            return None
        qualname = decorator[0].qualname + '.' + body[0].name
        matches = self._definition_index.find(decorator[0].module, qualname)
        if len(matches) != 1 or self._captures(*matches[0]):
            return None
        return matches[0]

    ## Resolve a callable name using the caller's lexical and import context.
    ## 使用调用方的词法和导入上下文解析可调用名称。
    #
    #  @param caller Caller function identity.
    #  @param name Syntactic callable name.
    #  @return Unique source definition or None.
    def _resolve(self, caller, name):
        return self._definition_index.resolve_name(
            caller.module, caller.qualname, name, self.imports)

    ## Check a qualified source binding for a unique stable declaration chain.
    ## 检查限定源码绑定是否具有唯一稳定的声明链。
    #
    #  @param qualified Qualified name to inspect.
    #  @return True only when every component has one supported binding.
    def _stable_import_name(self, qualified):
        module, _, name = qualified.rpartition('.')
        while module and module not in self.import_binding_facts:
            module, _, prefix = module.rpartition('.')
            name = prefix + '.' + name
        sources = self.import_binding_facts.get(module, [])
        if len(sources) != 1:
            return False
        bindings_by_name = sources[0]
        parts = name.split('.')
        for index, part in enumerate(parts):
            bindings = bindings_by_name.get(part, [])
            if len(bindings) != 1 or not isinstance(bindings[0], (
                    ast.Import, ast.ImportFrom, ast.FunctionDef,
                    ast.AsyncFunctionDef, ast.ClassDef)):
                return False
            if index == len(parts) - 1:
                return True
            if not isinstance(bindings[0], ast.ClassDef):
                return False
            bindings_by_name = {}
            for statement in bindings[0].body:
                for member in (statement_scope_facts([statement]).bound
                               | _attribute_write_roots(statement)):
                    bindings_by_name.setdefault(member, []).append(statement)
        return False

    ## Resolve a qualified source target through stable import bindings.
    ## 通过稳定导入绑定解析限定源码目标。
    #
    #  @param qualified Qualified target name.
    #  @return Unique source definition or None.
    def _resolve_import_binding(self, qualified):
        return self._definition_index.resolve_qualified(
            [qualified], self.imports, qualified_guard=self._stable_import_name)

    ## Find global declarations that can rebind a module-level definition.
    ## 查找可能重新绑定模块级定义的 global 声明。
    #
    #  @param ref Source definition identity.
    #  @return Matching declaration nodes.
    def _module_global_declarations(self, ref):
        definitions = self.import_binding_facts.get(ref.module, [])
        name = ref.qualname.partition('.')[0]
        return ([statement for statement in definitions[0].get(name, [])
                 if isinstance(statement, ast.Global)] if len(definitions) == 1 else [])

    ## Collect source evidence for possible module-global rebindings.
    ## 收集模块全局名称可能被重新绑定的源码证据。
    #
    #  @return Ordered rebinding fact records.
    def _module_global_rebindings(self):
        result = []
        for module, bodies in sorted(self.module_bodies.items()):
            for (path, _), bindings in zip(bodies, self.import_binding_facts.get(module, [])):
                for name, statements in sorted(bindings.items()):
                    if self._analysis_budget is not None:
                        self._analysis_budget.checkpoint()
                    declarations = [statement for statement in statements if isinstance(statement, ast.Global)]
                    if declarations:
                        result.append({'kind': 'module_global_rebinding', 'status': 'may_write',
                            'basis': 'source_snapshot', 'module': module, 'name': name,
                            'declarations': [{'file_path': path, 'lineno': statement.lineno,
                                'col_offset': statement.col_offset, 'end_lineno': statement.end_lineno,
                                'end_col_offset': statement.end_col_offset} for statement in declarations],
                            'source_hash': self.hashes[path]})
        return result

    ## Resolve a class name in a caller's lexical and import context.
    ## 在调用方词法和导入上下文中解析类名。
    #
    #  @param caller Caller function identity.
    #  @param name Syntactic class name.
    #  @return Unique source class or None.
    def _resolve_class(self, caller, name):
        return self._definition_index.resolve_name(
            caller.module, caller.qualname, name, self.imports, kind='class')

    ## Resolve a class through stable imports and bounded assignment aliases.
    ## 通过稳定导入和有界赋值别名解析类。
    #
    #  @param qualified Qualified class name.
    #  @param seen Previously visited names.
    #  @return Unique source class or None for cycles or uncertainty.
    def _class_symbol(self, qualified, seen=()):
        if qualified in seen or len(seen) >= 20:
            return None
        target = self._definition_index.resolve_qualified(
            [qualified], self.imports, kind='class',
            qualified_guard=self._stable_import_name)
        if target is not None:
            return target
        module, _, name = qualified.rpartition('.')
        bodies = self.module_bodies.get(module, [])
        bindings = self.import_binding_facts.get(module, [])
        if len(bodies) != 1 or len(bindings) != 1:
            return None
        statements = bindings[0].get(name, [])
        if len(statements) != 1 or statements[0] not in bodies[0][1]:
            return None
        statement = statements[0]
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)) or not isinstance(
                statement.value, (ast.Name, ast.Attribute)):
            return None
        expression = ast.unparse(statement.value)
        first, dot, rest = expression.partition('.')
        imported = self.imports.get(module, {}).get(first)
        if imported and not self._stable_import_name(module + '.' + first):
            return None
        next_name = (imported + (dot + rest if dot else '') if imported
                     else module + '.' + expression)
        return self._class_symbol(next_name, seen + (qualified,))

    ## Check whether source class construction follows the modeled ordinary path.
    ## 检查源码类构造是否遵循已建模的普通路径。
    #
    #  @param class_ref Source class identity.
    #  @param allow_bounded_decorations Permit independently proved decorations.
    #  @return True only when the ordinary construction premises hold.
    def _ordinary_construction(self, class_ref, allow_bounded_decorations=False):
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if hierarchy is None:
            return False
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in ('__new__', '__class__', '__bases__', '*')
                and any(written == owner for owner, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return False
        # Ancestor decoration has already happened when a new subclass hook
        # observes its inherited namespace. Establish that completed prefix
        # before asking for the current class's creation effects.
        if allow_bounded_decorations and any(
                constructor_decorations(self, parent) is None
                for parent in reversed(hierarchy[1:])):
            return False
        if creation_effects(self, hierarchy[0]) is None:
            return False
        return all((constructor_decorations(self, (owner, cls)) is not None
                    if allow_bounded_decorations else not cls.decorator_list)
            and not cls.keywords and not any(
            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name == '__new__' or
            '__new__' in statement_scope_facts([member]).bound
            for member in cls.body) for owner, cls in hierarchy)

    ## Check source premises for explicit object.__new__ allocation.
    ## 检查显式 object.__new__ 分配的源码前提。
    #
    #  @param class_ref Source class identity.
    #  @return True only when the modeled ordinary layout is established.
    def _explicit_object_allocation(self, class_ref):
        # Explicit object.__new__ bypasses the selected class's __new__ and
        # __init__. Its source class/MRO must still identify an ordinary object
        # layout, and class-definition evaluation must preserve that identity.
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if not hierarchy or len(hierarchy) > 64:
            return False
        if any(cls.keywords or cls.decorator_list or self.definition_conditions.get(owner)
                or owner != class_ref and '__init_subclass__' in statement_scope_facts(cls.body).bound
                for owner, cls in hierarchy):
            return False
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in ('__class__', '__bases__', '*')
                and any(written == owner for owner, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return False
        try:
            return not constructor_definition_issues(self, hierarchy)
        except _ClassEffectLimit:
            return False

    ## Summarize enter returns symbolically, never caching a caller object identity.
    ## 符号化概括 enter 返回值，不缓存调用方对象身份。
    #
    #  @param definition Exact source protocol method.
    #  @param receiver_class Source instance class used for the type lookup.
    #  @return Bounded normal-return paths, completion and unresolved proof issues.
    def _context_enter_returns(self, definition, receiver_class):
        ref, node = definition
        key = ref, receiver_class
        if key in self._context_enter_stack:
            return {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_recursion']}
        if key in self._context_enter_cache:
            return copy.deepcopy(self._context_enter_cache[key])
        steps = 0
        for _ in ast.walk(node):
            steps += 1
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint()
            if steps > _CONTEXT_PROTOCOL_NODE_LIMIT:
                break
        if (len(self._context_enter_stack) >= 8 or self._fact_functions <= 0
                or steps > min(self._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT)):
            return {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_budget']}
        self._fact_functions -= 1
        self._fact_calls -= steps
        positional = node.args.posonlyargs + node.args.args
        incoming = {positional[0].arg: [{'instance_type': asdict(receiver_class)}]} if positional else {}
        scratch = FlowAnalysis(ref, {})
        self._context_enter_stack.append(key)
        try:
            summary = _Summary(self, scratch, ref, node, self._fact_calls, incoming=incoming)
            summary.run()
            supported_constructors = set()
            issues = []
            for call in summary.calls:
                constructor = (call.result_sources and all(value.get('instance_type')
                    for value in call.result_sources) and call.target_status in (
                        'constructor', 'constructor_unavailable'))
                if constructor and call.target is not None:
                    target = self._definition_index.find(call.target.module, call.target.qualname)
                    constructor = len(target) == 1 and function_effects(target[0][1]) == ()
                elif constructor:
                    constructor = all(not any('__init__' in statement_scope_facts([member]).bound
                        for member in cls.body) for value in call.result_sources
                        for _, cls in self._class_mro(value['instance_type']['module'],
                            value['instance_type']['qualname']) or ())
                if constructor:
                    supported_constructors.add(call.id)
                if not constructor:
                    issues.append('context_enter_call_unmodeled')
            issues.extend(item['reason'] for item in scratch.boundaries if not (
                item.get('call_id') in supported_constructors
                and item['reason'] == 'module_callable_instance_unresolved'
                and item.get('cause') == 'constructor_unavailable'))
            if any(isinstance(statement, (ast.If, ast.Try, ast.For, ast.While))
                   for statement in node.body):
                issues.append('context_enter_control_effects_unmodeled')
            effects_known = not issues and (function_effects(node) == ()
                or bool(supported_constructors) and len(supported_constructors) == len(summary.calls))
            completion = ('no_normal_return' if summary.exit_kinds
                and summary.exit_kinds <= {'raise'} else 'normal_possible')
            if summary.incomplete_return:
                issues.append('context_enter_return_unresolved')
            fact = {'paths': copy.deepcopy(summary.normal_returns), 'completion': completion,
                    'parameter': positional[0].arg if positional else None, 'issues': _unique(issues),
                    'effects_status': 'source_modeled' if effects_known else 'unmodeled',
                    'exceptions': _unique(exception for kind, _, _, exception in summary.outcomes
                                          if kind == 'raise')}
            self._context_enter_cache[key] = fact
            return copy.deepcopy(fact)
        finally:
            self._context_enter_stack.pop()

    ## Prove a single-inheritance source chain ending at the unshadowed builtin dict.
    ## 证明单继承源码链最终指向未被遮蔽的内置 dict。
    #
    #  @param class_ref Source class identity; no whole-object builtin shape is inferred.
    #  @param seen Class identities already visited on this path.
    #  @return Source hierarchy, or None for incomplete or customized construction.
    def _dict_subclass_hierarchy(self, class_ref, seen=()):
        identity = (class_ref.module, class_ref.qualname)
        if identity in seen or len(seen) >= 20:
            return None
        matches = self._definition_index.find(*identity, kind='class')
        if len(matches) != 1 or self._class_symbol('.'.join(identity)) != matches[0]:
            return None
        ref, cls = matches[0]
        if cls.decorator_list or cls.keywords or len(cls.bases) != 1:
            return None
        base = cls.bases[0]
        if isinstance(base, ast.Name) and base.id == 'dict':
            if (base.id in self.imports.get(ref.module, {})
                    or base.id in self.module_bindings.get(ref.module, set())
                    or self._definition_index.find(ref.module, base.id)
                    or self._definition_index.find(ref.module, base.id, kind='class')):
                return None
            outer = ref.qualname.rpartition('.')[0]
            scopes = self._definition_index.find(ref.module, outer)
            if any(base.id in self._scope_facts(node).bound for _, node in scopes):
                return None
            return (matches[0],)
        if not isinstance(base, (ast.Name, ast.Attribute)):
            return None
        first = ast.unparse(base).partition('.')[0]
        if not self._stable_import_name(ref.module + '.' + first):
            return None
        inherited = self._resolve_class(ref, ast.unparse(base))
        if inherited is None:
            return None
        hierarchy = self._dict_subclass_hierarchy(inherited[0], seen + (identity,))
        return (matches[0],) + hierarchy if hierarchy else None

    ## Describe a builtin method's source binding without treating a subclass as dict.
    ## 描述内置方法的源码绑定，不将子类直接视为 dict。
    #
    #  @param class_ref Source receiver class.
    #  @param method Exact attribute being looked up.
    #  @return Proof, an explicit scan-budget issue, or None for uncertain lookup/writes.
    def _dict_method_binding(self, class_ref, method):
        if method not in ('setdefault', '__getitem__'):
            return None
        hierarchy = self._dict_subclass_hierarchy(class_ref)
        if hierarchy is None:
            return None
        blocked = {method, '__getattribute__', '__getattr__', '__setattr__',
                   '__delattr__', '__new__', '__init_subclass__'}
        remaining = _CLASS_BINDING_NODE_LIMIT
        for ref, cls in hierarchy:
            if any(blocked.intersection(statement_scope_facts([member]).bound)
                   for member in cls.body):
                return None
            for node in ast.walk(cls):
                remaining -= 1
                if remaining < 0:
                    return {'status': 'unconfirmed', 'reason': 'class_binding_budget'}
                if isinstance(node, ast.Attribute) and (node.attr == '__dict__' or
                        isinstance(node.ctx, (ast.Store, ast.Del)) and node.attr in blocked | {'__class__'}):
                    return None
                if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                    if name in ('setattr', 'delattr', 'vars', 'exec', 'eval', '__setattr__', '__delattr__'):
                        return None
        writes, truncated = self._class_binding_writes(include_escapes=True)
        identities = {(ref.module, ref.qualname) for ref, _ in hierarchy}
        if truncated:
            return {'status': 'unconfirmed', 'reason': 'class_binding_budget'}
        if any((ref.module, ref.qualname) in identities for ref, _, _, _, _ in writes):
            return None
        return {'kind': 'builtin_method_binding', 'builtin': 'dict.' + method,
                'receiver_class': asdict(class_ref), 'status': 'source_bound',
                'basis': 'source_snapshot', 'runtime_target_confirmed': False,
                'assumptions': ['source_snapshot_bindings_hold',
                                'source_class_receiver_without_instance_shadowing',
                                'no_external_monkeypatch_or_import_hook'],
                'hierarchy': hierarchy}

    ## Summarize supported function effects under recursion and work limits.
    ## 在递归和工作量限制下概括受支持的函数效果。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Pair of complete effects or None, and an unresolved reason.
    def _function_effects(self, definition):
        ref, node = definition
        key = (ref, repr(getattr(node, '_flow_conditions', [])))
        if key in self._function_effect_cache:
            return self._function_effect_cache[key]
        if key in self._function_effect_stack:
            return None, 'recursive_helper_effects'
        if len(self._function_effect_stack) >= 16:
            return None, 'mapping_effect_budget'

        # Cache complete outcomes and explicit cutoff reasons for this query.
        # 缓存本次查询中的完整结果及明确的截断原因。
        steps = len(getattr(node, 'body', ())) if isinstance(node, ast.FunctionDef) else 1
        if getattr(node, '_flow_branch_budget', None) is not None:
            result = None, 'literal_branch_budget'
        elif self._effect_fact_functions <= 0 or steps > self._effect_fact_steps:
            result = None, 'mapping_effect_budget'
        else:
            self._effect_fact_functions -= 1
            self._effect_fact_steps -= steps
            self._function_effect_stack.add(key)
            try:
                effects = function_effects(node, lambda statement, aliases:
                    self._nested_mapping_effects(definition, statement, aliases))
                result = effects, self._nested_effect_failures.get(ref, 'unsupported_helper_body')
            finally:
                self._function_effect_stack.remove(key)
        self._function_effect_cache[key] = result
        return result

    ## Compose complete same-module mapping effects from a direct helper call.
    ## 组合直接调用同模块辅助函数所产生的完整映射效果。
    #
    #  @param definition Calling source definition.
    #  @param statement Expression call whose result is unused.
    #  @param aliases Calling ordinary-name bindings, with parameter identity.
    #  @return Remapped complete effects or None for an unproved call.
    def _nested_mapping_effects(self, definition, statement, aliases):
        ref, node = definition
        call = statement.value
        if (not isinstance(call.func, ast.Name)
                or call.func.id in self._scope_facts(node).bound):
            return None
        target = self._resolve(ref, call.func.id)
        if (target is None or target[0].module != ref.module
                or not self._stable_import_name(ref.module + '.' + call.func.id)
                or not isinstance(target[1], ast.FunctionDef) or target[1].decorator_list
                or self._captures(*target)):
            return None
        records, issues = bind_ast_call(call, FunctionSignature.from_ast(target[1].args))
        if issues or any(record['status'] != 'exact' or record.get('target_path')
                         or not isinstance(record['node'], ast.Name)
                         or record['node'].id not in aliases for record in records):
            return None
        incoming = {record['parameter']: aliases[record['node'].id] for record in records}
        effects, cause = self._function_effects(target)
        if effects is None and cause in ('mapping_effect_budget', 'recursive_helper_effects'):
            self._nested_effect_failures[ref] = cause
        if effects is None or any(effect.kind not in (
                'mapping_pop', 'mapping_delete', 'mapping_delete_keys', 'container_clear')
                or effect.target not in incoming
                or effect.source is not None and effect.source not in incoming for effect in effects):
            return None
        return tuple(replace(effect, target=incoming[effect.target],
            source=incoming.get(effect.source), statement=statement,
            sequence_loop=statement if effect.sequence_loop is not None else None)
            for effect in effects)

    ## Summarize supported returns that preserve an argument object identity.
    ## 概括受支持的、保留实参对象身份的返回。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Pair of optional return fact and unresolved reason.
    def _object_returns(self, definition):
        ref, node = definition
        if getattr(node, '_flow_branch_budget', None) is not None:
            return None, 'literal_branch_budget'
        key = (ref, repr(getattr(node, '_flow_conditions', [])))
        if key in self._object_return_cache:
            return self._object_return_cache[key]
        if self._object_fact_functions <= 0:
            return None, 'container_return_budget'
        self._object_fact_functions -= 1
        fact, cause = None, 'unsupported_return_object'
        owner = ref.qualname.rpartition('.')[0]
        if (not isinstance(node, ast.FunctionDef) or contains_yield(node)
                or node.decorator_list
                or self._definition_index.find(ref.module, owner, kind='class')
                or (not owner and not self._stable_import_name(
                    ref.module + '.' + ref.qualname))):
            cause = 'dynamic_return_callable'
        else:
            ordinary = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            aliases = {argument.arg: argument.arg for argument in ordinary}
            evidence = []
            modeled_effects = None
            for statement in node.body:
                if self._object_fact_steps <= 0:
                    cause = 'container_return_budget'
                    break
                self._object_fact_steps -= 1
                if isinstance(statement, ast.Pass) or (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str)):
                    continue
                if (isinstance(statement, (ast.Assign, ast.AnnAssign))
                        and isinstance(statement.value, ast.Name)):
                    targets = (statement.targets if isinstance(statement, ast.Assign)
                               else [statement.target])
                    if all(isinstance(target, ast.Name) for target in targets):
                        parameter = aliases.get(statement.value.id)
                        for target in targets:
                            if parameter is None:
                                aliases.pop(target.id, None)
                            else:
                                aliases[target.id] = parameter
                        evidence.append(statement)
                        continue
                if isinstance(statement, (ast.Expr, ast.Delete, ast.For)):
                    effects, effect_cause = self._function_effects(definition)
                    if (effects is not None
                            and all(effect.kind in ('mapping_pop', 'mapping_delete',
                                                    'mapping_delete_keys', 'container_clear') for effect in effects)
                            and any(effect.statement is statement or effect.sequence_loop is statement
                                    for effect in effects)):
                        modeled_effects = effects
                        evidence.append(statement)
                        continue
                    if effect_cause == 'mapping_effect_budget':
                        cause = 'container_return_budget'
                        break
                if isinstance(statement, ast.Return):
                    if isinstance(statement.value, ast.Name):
                        parameter = aliases.get(statement.value.id)
                        if parameter is not None:
                            fact = {'parameter': parameter, 'identity': 'argument_alias',
                                    'evidence': evidence + [statement]}
                            if modeled_effects:
                                fact['effects'] = modeled_effects
                            cause = None
                        elif node.args.kwarg and statement.value.id == node.args.kwarg.arg:
                            cause = 'fresh_variadic_capture'
                        elif node.args.vararg and statement.value.id == node.args.vararg.arg:
                            cause = 'fresh_variadic_capture'
                    break
                cause = 'unmodeled_helper_effects'
                break
        if fact and getattr(node, '_flow_conditions', None):
            fact['conditions'] = copy.deepcopy(node._flow_conditions)
        self._object_return_cache[key] = (fact, cause)
        return fact, cause

    ## Specialize bounded literal branches for one incoming call context.
    ## 为单个传入调用上下文特化有界字面量分支。
    #
    #  @param definition Source function identity and AST pair.
    #  @param incoming Incoming argument facts keyed by parameter.
    #  @return Original or condition-annotated function definition pair.
    def _selected_definition(self, definition, incoming):
        ref, node = definition
        if not isinstance(node, ast.FunctionDef) or contains_yield(node):
            return definition
        literals = {name: values[0]['literal'] for name, values in incoming.items()
                    if len(values) == 1 and values[0].get('literal')}
        evidence = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
        conditions = []
        branch_budget = None
        pending, body = list(node.body), []
        while pending:
            statement = pending.pop(0)
            test = statement.test if isinstance(statement, ast.If) else None
            operand = test.operand if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) else test
            literal = literals.get(operand.id) if isinstance(operand, ast.Name) else None
            if test is not None and literal is not None and len(conditions) >= 8:
                branch_budget = test
            if test is not None and literal is not None and len(conditions) < 8:
                branch = bool(literal['value'])
                if isinstance(test, ast.UnaryOp):
                    branch = not branch
                conditions.append({'test': evidence.evidence(test), 'branch': branch,
                    'binding': {'parameter': operand.id, 'literal': copy.deepcopy(literal),
                        'evidence': copy.deepcopy(incoming.get(operand.id, []))}})
                pending = list(statement.body if branch else statement.orelse) + pending
                continue
            body.append(statement)
            if isinstance(statement, (ast.Return, ast.Raise)):
                break
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)):
                fact = evidence.literal_fact(statement.value, {})
                if isinstance(statement.value, ast.Name):
                    fact = literals.get(statement.value.id)
                if fact is not None:
                    literals[statement.targets[0].id] = fact
                else:
                    literals.pop(statement.targets[0].id, None)
                if any(isinstance(child, ast.Call) for child in ast.walk(statement.value)):
                    literals.clear()
            elif not (isinstance(statement, ast.Pass) or isinstance(statement, ast.Expr)
                      and isinstance(statement.value, ast.Constant)):
                literals.clear()
        if not conditions:
            return definition
        selected = copy.copy(node)
        selected.body = body
        selected._flow_conditions = conditions
        selected._flow_branch_budget = branch_budget
        return ref, selected

    ## Describe a supported guarded argument-alias return path.
    ## 描述受支持的、受守卫约束的实参别名返回路径。
    #
    #  @param definition Source function identity and AST pair.
    #  @return Partial-path return facts, possibly empty.
    def _guarded_object_returns(self, definition):
        ref, node = definition
        body = [statement for statement in getattr(node, 'body', [])
                if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))] if isinstance(node, ast.FunctionDef) else []
        if (not isinstance(node, ast.FunctionDef) or contains_yield(node)
                or node.decorator_list or not body
                or not isinstance(body[0], ast.If)):
            return []
        branch = body[0]
        operand = (branch.test.operand if isinstance(branch.test, ast.UnaryOp)
                   and isinstance(branch.test.op, ast.Not) else branch.test)
        if not isinstance(operand, ast.Name):
            return []
        if len(branch.body) != 1 or not isinstance(branch.body[0], ast.Return):
            return []
        value = branch.body[0].value
        ordinary = {argument.arg for argument in node.args.posonlyargs
                    + node.args.args + node.args.kwonlyargs}
        if not isinstance(value, ast.Name) or value.id not in ordinary:
            return []
        evidence = _Summary(self, FlowAnalysis(ref, {}), ref, node, 0)
        return [{'parameter': value.id, 'identity': 'argument_alias',
            'conditions': [{'test': evidence.evidence(branch.test), 'branch': True}],
            'completion': 'normal_return', 'completeness': 'partial_paths',
            'requires_literal_guard': operand.id,
            'content_status': 'unchanged_on_this_path',
            'evidence': [evidence.evidence(branch.body[0])]}]

    ## Determine a classmethod or allocator receiver class when uniquely supported.
    ## 在证据唯一时确定类方法或分配器的接收者类。
    #
    #  @param definition Source function identity and AST pair.
    #  @param call Optional call containing receiver argument sources.
    #  @return Source class identity or None when uncertain.
    def _receiver_class(self, definition, call=None):
        ref, node = definition
        positional = node.args.posonlyargs + node.args.args
        if not positional or not (self._descriptor_kind(definition) == 'classmethod'
                                  or getattr(node, 'name', None) == '__new__'):
            return None
        if call is not None:
            values = [value for item in call.argument_sources
                      if item.get('parameter') == positional[0].arg
                      for value in item.get('sources', [])]
            types = [value.get('class_type') for value in values]
            if (values and all(types) and len(_unique(types)) == 1
                    and all(value.get('relation') == 'direct'
                            and not value.get('projection')
                            and not value.get('output_path')
                            and not value.get('value_incomplete') for value in values)):
                return FunctionRef(**types[0])
            return None
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        return classes[0][0] if len(classes) == 1 else None

    ## Summarize source-class return candidates under a bounded context.
    ## 在有界上下文中概括源码类返回候选。
    #
    #  @param definition Source function identity and AST pair.
    #  @param receiver_class Optional source receiver class.
    #  @param incoming Optional incoming parameter facts.
    #  @return Candidate records and an optional recursion or budget reason.
    def _class_returns(self, definition, receiver_class, incoming=None):
        ref, node = definition
        incoming = {parameter: [{'class_lookup_mutations': copy.deepcopy(
            value['class_lookup_mutations'])} for value in values
            if value.get('class_lookup_mutations')]
            for parameter, values in (incoming or {}).items()}
        incoming = {parameter: values for parameter, values in incoming.items() if values}
        key = (ref, receiver_class, repr(getattr(node, '_flow_conditions', [])), repr(incoming))
        if key in self._class_return_cache:
            return self._class_return_cache[key]
        if key in self._class_return_stack:
            return [], 'class_return_recursion'
        if (len(self._class_return_stack) >= 8 or self._fact_functions <= 0
                or self._fact_calls <= 0):
            return [], 'class_return_budget'
        if isinstance(node, ast.AsyncFunctionDef) or contains_yield(node):
            return [], None
        if self._descriptor_kind(definition) == 'classmethod' and receiver_class is None:
            return [], None
        if ('.' not in ref.qualname and not self._stable_import_name(
                ref.module + '.' + ref.qualname)):
            return [], None
        if (getattr(node, 'decorator_list', []) and self._descriptor_kind(definition) is None
                and self._identity_decorator(definition) is None):
            return [], None
        self._fact_functions -= 1
        self._class_return_stack.append(key)
        scratch = FlowAnalysis(ref, {})
        summary = _Summary(self, scratch, ref, node, self._fact_calls,
                           receiver_class, incoming)
        try:
            summary.run()
            values = []
            complete = bool(summary.normal_returns) and not summary.incomplete_return
            for returned in summary.normal_returns:
                known = summary.class_values(returned)
                if not known:
                    complete = False
                values.extend(known)
            values = _unique(values) if complete else _unique([
                dict(value, value_incomplete=True) for value in summary.returns
                if value.get('kind') == 'class' and value.get('class_type')
                and value.get('attribute_provenance')
                and value.get('relation') == 'direct' and not value.get('projection')
                and not value.get('output_path')])
            cause = next((item['reason'] for item in scratch.boundaries
                          if item['reason'] in ('class_return_recursion',
                                                'class_return_budget', 'budget_exceeded')), None)
            if values and not complete and cause is None:
                cause = 'class_attribute_state_unknown'
            self._class_return_cache[key] = (values, cause)
            return values, cause
        finally:
            self._class_return_stack.pop()

    ## Find a source __call__ candidate for one imported module-level instance.
    ## 为导入的模块级实例查找源码 __call__ 候选。
    #
    #  @param caller Function containing the invocation.
    #  @param name Syntactic callee spelling.
    #  @param binding Current lexical binding of the callee's first name.
    #  @return (target, constructor facts, unresolved cause), conservatively.
    def _module_callable_instance(self, caller, name, binding):
        first, dot, rest = name.partition('.')
        if binding is not None and not (
                binding and all(item.get('kind') == 'import' for item in binding)):
            return None, None, None
        if binding and any(value.get('import_modified')
                           or value.get('import_incomplete')
                           or value.get('conditions') for value in binding):
            return None, None, None
        if first in self.module_bindings.get(caller.module, set()) and dot:
            return None, None, None
        imports = self.imports.get(caller.module, {})
        imported = imports.get(first)
        if imported:
            if binding and {item['source'] for item in binding} != {imported}:
                return None, None, None
            qualified = imported + (dot + rest if dot else '')
        elif not dot:
            qualified = caller.module + '.' + first
        else:
            return None, None, None
        module, _, variable = qualified.rpartition('.')
        sources = self.module_bodies.get(module, [])
        if not sources:
            return None, None, None
        if len(sources) != 1:
            return None, None, 'ambiguous_module'
        path, body = sources[0]

        ## Find the root name of an attribute or subscript target.
        ## 查找属性或下标目标的根名称。
        #
        #  @param node Target AST node.
        #  @return Root name or None when unavailable.
        def root_name(node):
            while isinstance(node, (ast.Attribute, ast.Subscript)):
                node = node.value
            return node.id if isinstance(node, ast.Name) else ''

        ## Traverse statements without entering deferred callable bodies.
        ## 遍历语句，不进入延迟执行的可调用体。
        #
        #  @param nodes Statement sequence.
        #  @return Iterator of inspected statements.
        def statements(nodes):
            for statement in nodes:
                yield statement
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.ClassDef)):
                    continue
                children = [child for child in ast.iter_child_nodes(statement)
                            if isinstance(child, ast.stmt)]
                yield from statements(children)

        bindings = []
        dynamic_write = False
        method_write = False
        for statement in statements(body):
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign,
                                      ast.Delete)):
                targets = (statement.targets if isinstance(statement, (ast.Assign, ast.Delete))
                           else [statement.target])
                for target in targets:
                    if root_name(target) != variable:
                        continue
                    if isinstance(target, ast.Name) and isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        bindings.append(statement)
                    else:
                        dynamic_write = True
                        if (isinstance(target, ast.Attribute)
                                and target.attr == '__call__'):
                            method_write = True
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef)) and statement.name == variable:
                bindings.append(statement)
            elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                if any(fact.python_binding == variable for fact in import_facts(statement)):
                    bindings.append(statement)
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                function = statement.value.func
                if isinstance(function, ast.Name) and function.id in (
                        'globals', 'exec', 'eval', 'setattr', 'delattr'):
                    dynamic_write = True
        if any(any(isinstance(node, ast.Global) and variable in node.names
                   for node in ast.walk(statement))
               for statement in body
               if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))):
            dynamic_write = True
        if len(bindings) != 1:
            return None, None, 'multiple_bindings' if bindings else None
        if method_write:
            return None, None, 'dynamic_method_write'
        if dynamic_write:
            return None, None, 'dynamic_binding_write'
        assignment = bindings[0]
        if assignment not in body:
            return None, None, 'conditional_binding'
        value = (assignment.value if isinstance(assignment, (ast.Assign, ast.AnnAssign))
                 else None)
        if not isinstance(value, ast.Call):
            return None, None, 'constructor_unavailable'
        constructor_name = ast.unparse(value.func)
        if constructor_name.partition('.')[0] in self.module_bindings.get(module, set()):
            return None, None, 'constructor_unavailable'
        module_ref = FunctionRef(module, '', path)
        constructed = self._resolve_class(module_ref, constructor_name)
        if constructed is None:
            return None, None, 'constructor_unavailable'
        class_ref, cls = constructed
        if cls.decorator_list or cls.keywords:
            return None, None, 'dynamic_class'
        hierarchy = self._class_mro(class_ref.module, class_ref.qualname)
        if hierarchy is None or any(base.decorator_list for _, base in hierarchy):
            return None, None, 'dynamic_class'
        if any(isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
               and member.name == '__new__'
               for _, base in hierarchy for member in base.body):
            return None, None, 'dynamic_constructor'
        methods = [member for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))]
        init = [member for member in methods if member.name == '__init__']
        if len(init) != 1 or init[0].decorator_list:
            return None, None, 'dynamic_constructor'
        calls = self._definition_index.find(
            class_ref.module, class_ref.qualname + '.__call__')
        if not calls:
            inherited = self._inherited_method(
                class_ref.module, class_ref.qualname, '__call__')
            calls = [inherited] if inherited else []
        if len(calls) != 1 or calls[0][1].decorator_list:
            return None, None, 'dynamic_method_write'
        if any(isinstance(member, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                       and node.id == '__call__' for node in ast.walk(member))
               for member in cls.body):
            return None, None, 'dynamic_method_write'
        class_name = constructor_name.partition('.')[0]
        for statement in statements(body):
            if not isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign,
                                          ast.Delete)):
                continue
            targets = (statement.targets if isinstance(statement, (ast.Assign, ast.Delete))
                       else [statement.target])
            for target in targets:
                if (root_name(target) in (class_name, variable)
                        and isinstance(target, ast.Attribute)
                        and target.attr == '__call__'):
                    return None, None, 'dynamic_method_write'
        selected = init[0].args.posonlyargs + init[0].args.args
        records, reasons = bind_ast_call(
            value, FunctionSignature.from_ast(init[0].args, selected[1:]))
        if reasons or any(record['status'] != 'exact' for record in records):
            return None, None, 'constructor_binding_uncertain'
        return calls[0], {
            'qualified_name': qualified, 'module_ref': module_ref,
            'assignment': assignment, 'constructor': value,
            'class_ref': class_ref, 'arguments': records,
            'source_body': body}, None

    ## Collect transitive lexical captures from known enclosing bindings.
    ## 从已知外层绑定中收集传递性词法捕获。
    #
    #  @param ref Source function identity.
    #  @param node Function or lambda AST.
    #  @return Captured names in stable order.
    def _captures(self, ref, node):
        if ref in self._capture_name_cache:
            return list(self._capture_name_cache[ref])
        outer = set()
        parent = ref.qualname.rpartition('.')[0]
        while parent:
            definitions = self._definition_index.find(ref.module, parent)
            definition = definitions[0][1] if definitions else None
            if definition:
                outer.update(self._scope_facts(definition).bound)
            parent = parent.rpartition('.')[0]
        names = transitive_captured_names(node, outer)
        self._capture_name_cache[ref] = names
        return list(names)

    ## Find indexed modules reachable through static import bindings.
    ## 查找通过静态导入绑定可达的已索引模块。
    #
    #  @param entry_module Starting module name.
    #  @return Set of reachable module names.
    def _reachable_modules(self, entry_module):
        known = set(self.imports)
        known.update(boundary.get('module') for boundary in self.index_boundaries
                     if boundary.get('module'))
        reachable = set()
        pending = [entry_module]
        while pending:
            module = pending.pop()
            if module in reachable:
                continue
            reachable.add(module)
            for imported in self.imports.get(module, {}).values():
                target = next((candidate for candidate in sorted(
                    known, key=len, reverse=True)
                    if imported == candidate or imported.startswith(candidate + '.')), None)
                if target is not None and target not in reachable:
                    pending.append(target)
        return reachable

    ## Identify parameters without visible reads when reflection is absent.
    ## 在没有可见反射能力时识别未被读取的参数。
    #
    #  @param node Function or lambda AST.
    #  @return Parameter records, or empty list when reflection prevents proof.
    def _unreferenced_parameters(self, node):
        arguments = node.args
        parameters = (arguments.posonlyargs + arguments.args + arguments.kwonlyargs +
                      ([arguments.vararg] if arguments.vararg else []) +
                      ([arguments.kwarg] if arguments.kwarg else []))
        statements = [node.body] if isinstance(node, ast.Lambda) else node.body
        body = [child for statement in statements for child in ast.walk(statement)]
        if any((isinstance(child, ast.Name) and child.id in
                ('locals', 'vars', 'eval', 'exec')) or
               (isinstance(child, ast.Attribute) and child.attr in
                ('f_locals', 'currentframe', '_getframe')) for child in body):
            return []
        loaded = {child.id for child in body
                  if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)}
        return [{'kind': 'parameter', 'name': parameter.arg, 'element_path': []}
                for parameter in parameters if parameter.arg not in loaded]

    ## Analyze reachable summaries up to a bounded number of call edges.
    ## 在有限调用边深度内分析可达摘要。
    #
    #  @param entry FunctionRef identifying a function or source class invocation.
    #  @param max_depth Number of call-edge layers, at least one.
    #  @param max_functions Maximum distinct function summaries.
    #  @param max_call_contexts Maximum traversed call edges.
    #  @param conditional_source_state Retain source-class lookup under explicit state predicates.
    #  @param max_class_effect_steps Maximum class-effect fact steps.
    #  @return FlowAnalysis snapshot; cutoffs are explicit boundaries.
    def analyze(self, entry, max_depth=1, max_functions=500, max_call_contexts=2000,
                conditional_source_state=False, max_class_effect_steps=8000):
        if type(conditional_source_state) is not bool:
            raise ValueError('conditional_source_state must be bool')
        if type(max_class_effect_steps) is not int or max_class_effect_steps < 1:
            raise ValueError('max_class_effect_steps must be a positive integer')
        self._conditional_source_state = conditional_source_state
        if min(max_depth, max_functions, max_call_contexts) < 1:
            raise ValueError('Depth and budgets must be positive')
        self._analysis_budget = (AnalysisBudget(self.analysis_limits)
                                 if self.analysis_limits is not None else None)
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        self._index()
        self._fact_functions, self._fact_calls = max_functions, max_call_contexts
        self._object_fact_functions = max_functions
        self._object_fact_steps = max_call_contexts
        self._effect_fact_functions = max_functions
        self._effect_fact_steps = max_call_contexts
        self._class_effect_fact_steps = max_class_effect_steps
        # Resolve entry aliases, constructors and inherited methods only with unique evidence.
        # 仅在证据唯一时解析入口别名、构造函数和继承方法。
        matches = [(r, n) for r, n in self.definitions if _matches(r, entry)]
        entry_binding = None
        entry_alias = None
        if not matches and not entry.file_path and not entry.lineno:
            qualified = entry.module + '.' + entry.qualname
            imported = self._resolve_import_binding(qualified)
            if imported is not None:
                matches = [imported]
            elif self._stable_import_name(qualified):
                imported_class = self._definition_index.resolve_qualified(
                    [qualified], self.imports, kind='class',
                    qualified_guard=self._stable_import_name)
                if imported_class is not None:
                    target = self._constructor_target(imported_class)
                    if target is not None:
                        matches = [target]
                        entry_binding = constructor_entry_binding(self, imported_class, target)
        if not matches:
            classes = [(r, n) for r, n in self.classes if _matches(r, entry)]
            if len(classes) == 1:
                target = self._constructor_target(classes[0])
                if target is not None:
                    matches = [target]
                    entry_binding = constructor_entry_binding(self, classes[0], target)
        if not matches:
            alias = source_entry_alias(self, entry)
            if alias is not None:
                target, entry_alias = alias
                matches = [target]
        if not matches and not entry.lineno and '.' in entry.qualname:
            owner, _, method = entry.qualname.rpartition('.')
            inherited = self._inherited_method(entry.module, owner, method)
            if inherited is not None:
                matches = [inherited]
        if len(matches) != 1:
            raise ValueError('Entry must identify exactly one available definition')
        if conditional_source_state and (
                entry_binding is not None and entry_binding['status'] != 'source_bound'
                or entry_binding is None and not conditional_constructor_entry(matches[0][1])):
            raise ValueError('Conditional state analysis requires a source class binding or bounded constructor query')
        result = FlowAnalysis(matches[0][0], {'source_files': sorted(self.files), 'sha256': dict(self.hashes),
                              'import_roots': list(self.roots), 'max_depth': max_depth,
                              'max_class_effect_steps': max_class_effect_steps,
                              'module_global_rebindings': self._module_global_rebindings(),
                              'return_summaries': copy.deepcopy(self.return_summaries),
                              'parameter_shapes': copy.deepcopy(self.parameter_shapes),
                              'coverage': 'explicit value dependencies and limited local container effects; no general heap or path feasibility proof'})
        if conditional_source_state:
            result.inputs['conditional_source_state'] = True
        if entry_alias is not None:
            result.inputs['entry_alias'] = entry_alias
            result.boundaries.append({'reason': 'source_entry_alias',
                'function': asdict(result.entry), 'boundary_kind': 'assumption',
                'assumptions': copy.deepcopy(entry_alias['assumptions'])})
        elif entry_binding is None:
            declarations = self._module_global_declarations(result.entry)
            if declarations:
                result.boundaries.append({'reason': 'module_callable_binding_unconfirmed',
                    'function': asdict(result.entry), 'nominal_target': asdict(result.entry),
                    'lookup_scope': 'module_entry', 'boundary_kind': 'uncertainty',
                    'declarations': [{'file_path': result.entry.file_path,
                        'lineno': statement.lineno, 'col_offset': statement.col_offset,
                        'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset}
                        for statement in declarations]})
        # Keep source failures as boundaries even when their relation is uncertain.
        # 即使与入口的关系不确定，也将源码失败保留为边界。
        reachable_modules = self._reachable_modules(matches[0][0].module)
        unreferenced = self._unreferenced_parameters(matches[0][1])
        for boundary in self.index_boundaries:
            record = copy.deepcopy(boundary)
            related = record.get('module') in reachable_modules
            record.update(
                affected_scope='unknown' if related else 'none',
                affected_values=[],
                unaffected_values=copy.deepcopy(unreferenced) if related else [],
                entry_relation='possible' if related else 'unrelated',
                relation_basis='static_import_reachability')
            result.boundaries.append(record)
        context = CallContext(matches[0][0].module, matches[0][0], None)
        if entry_binding is not None:
            result.inputs['entry_binding'] = copy.deepcopy(entry_binding)
            result.boundaries.append({'function': asdict(result.entry),
                'reason': 'source_constructor_entry_binding' if entry_binding['status']
                          == 'source_bound' else 'constructor_entry_unconfirmed',
                'boundary_kind': 'assumption' if entry_binding['status'] == 'source_bound'
                                 else 'limitation',
                'assumptions': copy.deepcopy(entry_binding['assumptions']),
                'issues': copy.deepcopy(entry_binding['issues'])})
            if entry_binding['status'] != 'source_bound':
                if self._analysis_budget is not None:
                    self._analysis_budget.checkpoint(force=True)
                publish_source_dependencies(self, result)
                return result
            if entry_binding['phase'] == '__new__':
                result.boundaries.append({'function': asdict(result.entry),
                    'reason': 'constructor_initialization_unmodeled', 'phase': '__init__'})
        self._walk(result, matches[0], max_depth, context, max_functions, max_call_contexts)
        publish_source_dependencies(self, result)
        result.boundaries = _unique(result.boundaries)
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        return result

    ## Expand one call context, retaining recursion and budget cutoffs as boundaries.
    ## 展开单个调用上下文，将递归和预算截断保留为边界。
    #
    #  @param result Mutable analysis snapshot.
    #  @param definition Source function identity and AST pair.
    #  @param depth Remaining call-edge depth.
    #  @param context Current call context.
    #  @param max_functions Maximum context summaries.
    #  @param max_calls Maximum traversed calls.
    #  @return None
    def _walk(self, result, definition, depth, context, max_functions, max_calls):
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        ref, node = definition
        if ref in context.ancestors:
            result.boundaries.append({'function': asdict(ref), 'reason': 'recursion'})
            return
        receiver_class = self._receiver_class(definition, context.edge)
        incoming = self._incoming_facts(definition, context.edge)
        entry_binding = result.inputs.get('entry_binding') if context.edge is None else None
        if entry_binding is not None and entry_binding['status'] == 'source_bound':
            parameter = entry_binding['implicit_binding']['parameter']
            identity = copy.deepcopy(entry_binding['receiver_class'])
            if entry_binding['phase'] == '__new__':
                receiver_class = FunctionRef(**identity)
                incoming[parameter] = [{'class_type': identity,
                    'source_class_origin': {'basis': 'source_symbol', 'class': identity,
                        'evidence': [copy.deepcopy(entry_binding['definition_evidence'])],
                        'call_context': []}}]
            else:
                incoming[parameter] = [{'instance_type': identity}]
                if entry_binding.get('fresh_receiver_origin'):
                    incoming[parameter][0]['fresh_receiver_origin'] = copy.deepcopy(
                        entry_binding['fresh_receiver_origin'])
        # Cache by incoming context so different argument facts do not share summaries.
        # 按传入上下文缓存，避免不同实参事实共用摘要。
        key = (ref, receiver_class, context.edge.id if context.edge else None,
               repr(incoming))
        if key in self._context_summaries:
            calls = self._context_summaries[key]
        else:
            if (len(self._context_summaries) >= max_functions
                    or self._context_call_count >= max_calls):
                result.boundaries.append({'function': asdict(ref), 'reason': 'budget_exceeded'})
                return
            scratch = FlowAnalysis(ref, {})
            selected = self._selected_definition(definition, incoming)
            summary = _Summary(self, scratch, ref, selected[1],
                               max_calls - self._context_call_count, receiver_class,
                               incoming)
            activation = self.definition_conditions.get(ref, ())
            if activation:
                summary.conditions = _unique(summary.conditions + list(copy.deepcopy(activation)))
                scratch.boundaries.append({'function': asdict(ref),
                    'reason': 'conditional_definition_unconfirmed',
                    'conditions': copy.deepcopy(activation), 'affected_scope': 'unknown',
                    'affected_values': []})
            summary.run()
            calls = summary.calls
            if context.edge is not None:
                for call in calls:
                    call.analysis_contexts.append({
                        'incoming_call_id': context.edge.id,
                        'parameter_facts': copy.deepcopy(incoming),
                        'target': asdict(call.target) if call.target else None,
                        'target_candidates': copy.deepcopy(call.target_candidates),
                        'target_status': call.target_status,
                        'binding_status': call.binding_status,
                        'argument_sources': copy.deepcopy(call.argument_sources),
                        'callable_sources': copy.deepcopy(call.callable_sources)})
                    call.analysis_contexts[-1].update(
                        result_sources=copy.deepcopy(call.result_sources),
                        capture_bindings=copy.deepcopy(call.capture_bindings),
                        effects=copy.deepcopy(call.effects),
                        callable_instance_evidence=copy.deepcopy(call.callable_instance_evidence),
                        conditional_returns=copy.deepcopy(call.conditional_returns),
                        class_method_bindings=copy.deepcopy(call.class_method_bindings),
                        class_metadata_bindings=copy.deepcopy(call.class_metadata_bindings),
                        class_read_bindings=copy.deepcopy(call.class_read_bindings),
                        conditional_source_bindings=copy.deepcopy(call.conditional_source_bindings),
                        candidate_paths=copy.deepcopy(call.candidate_paths),
                        constructor_bindings=copy.deepcopy(call.constructor_bindings),
                        instance_method_bindings=copy.deepcopy(call.instance_method_bindings),
                        implicit_protocol=copy.deepcopy(call.implicit_protocol),
                        conditions=copy.deepcopy(call.conditions if self._conditional_source_state
                            else getattr(selected[1], '_flow_conditions', [])))
            self._context_summaries[key] = calls
            self._context_call_count += len(calls)
            self._merge_summary(result, scratch)
        for call in calls:
            if call.target is None:
                if call.target_status not in ('python_protocol', 'local_container_protocol',
                                              'builtin_allocation'):
                    result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                              'reason': call.target_status})
            elif depth > 1:
                result.boundaries = [b for b in result.boundaries if not (b.get('call_id') == call.id and b['reason'] == 'depth_limit')]
                target = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
                child = CallContext(call.caller.module, call.target, call, context)
                self._walk(result, target, depth - 1, child, max_functions, max_calls)
            else:
                result.boundaries.append({'call_id': call.id, 'reason': 'depth_limit'})

    ## Prepare parameter and capture facts from an incoming call edge.
    ## 从传入调用边准备参数和捕获事实。
    #
    #  @param definition Target source function definition.
    #  @param edge Incoming call record, or None at the entry.
    #  @return Incoming facts keyed by local name.
    def _incoming_facts(self, definition, edge):
        if edge is None or edge.binding_status == 'invalid':
            return {}
        normal_binding = edge.binding_status != 'complete'
        fresh_super = [fact for fact in edge.instance_method_bindings
                       if fact.get('kind') == 'fresh_source_super_method'
                       and fact.get('status') == 'source_bound'
                       and fact.get('target') == asdict(definition[0])
                       and edge.target_status == 'super_method']
        fresh_instance = [fact for fact in edge.instance_method_bindings
                          if fact.get('kind') == 'fresh_source_instance_method'
                          and fact.get('status') == 'source_bound'
                          and fact.get('target') == asdict(definition[0])
                          and fact.get('call_id') == edge.id]
        seeded_receiver = {}
        if len(fresh_instance) == 1:
            parameters = definition[1].args.posonlyargs + definition[1].args.args
            fact = fresh_instance[0]
            origin = fact.get('origin')
            identity = fact.get('receiver_class')
            receiver_values = edge.receiver_sources
            receiver_records = [record for record in edge.parameter_bindings
                if record.get('argument') == {'receiver': True}
                and record.get('parameter') == (parameters[0].arg if parameters else None)
                and record.get('status') == 'exact']
            if (parameters and isinstance(origin, dict) and identity == origin.get('allocation', {}).get(
                    'receiver_class') and len(receiver_records) == 1 and receiver_values
                    and all(value.get('fresh_receiver_origin') == origin
                        and value.get('instance_type') in (None, identity)
                        and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in (
                            'projection', 'output_path', 'attribute_provenance',
                            'import_modified', 'import_incomplete'))
                        for value in receiver_values)):
                receiver = {'instance_type': copy.deepcopy(identity),
                    'fresh_receiver_origin': fresh_incoming_origin(fact, parameters[0].arg)}
                mutations = [value.get('class_lookup_mutations', []) for value in receiver_values]
                if all(item == mutations[0] for item in mutations) and mutations[0]:
                    receiver['class_lookup_mutations'] = copy.deepcopy(mutations[0])
                conditions = [value.get('conditions', []) for value in receiver_values]
                if all(item == conditions[0] for item in conditions) and conditions[0]:
                    receiver['conditions'] = copy.deepcopy(conditions[0])
                seeded_receiver[parameters[0].arg] = [receiver]
        if normal_binding and (not edge.binding_issues or any(
                issue.get('kind') != 'dynamic_expansion' for issue in edge.binding_issues)):
            if len(fresh_super) == 1:
                parameters = definition[1].args.posonlyargs + definition[1].args.args
                if parameters:
                    parameter = parameters[0].arg
                    origin = fresh_incoming_origin(fresh_super[0], parameter)
                    identity = copy.deepcopy(origin['allocation']['receiver_class'])
                    return {parameter: [{'instance_type': identity,
                                         'fresh_receiver_origin': origin}]}
            return seeded_receiver
        ordinary = {argument.arg for argument in definition[1].args.posonlyargs
                    + definition[1].args.args + definition[1].args.kwonlyargs}
        incoming = dict(seeded_receiver)
        for parameter in sorted(ordinary):
            if parameter in seeded_receiver:
                continue
            arguments = [argument for argument in edge.argument_sources
                         if argument.get('parameter') == parameter]
            records = [item for item in edge.parameter_bindings
                       if item.get('parameter') == parameter]
            exact_super_receiver = (len(fresh_super) == 1 and len(arguments) == 1
                and arguments[0].get('argument') == {'receiver': True}
                and arguments[0].get('sources')
                and all(value.get('fresh_receiver_origin') == fresh_super[0].get('origin')
                    and value.get('relation') == 'direct'
                    and value.get('source') == fresh_super[0].get('origin', {}).get('parameter')
                    and not any(value.get(flag) for flag in (
                        'projection', 'output_path', 'attribute_provenance',
                        'import_modified', 'import_incomplete', 'value_incomplete'))
                    for value in arguments[0]['sources']))
            exact_class_receiver = (len(arguments) == 1
                and arguments[0].get('argument') == {'receiver': True}
                and any(fact.get('status') == 'source_bound'
                    and fact.get('target') == asdict(definition[0])
                    and fact.get('implicit_binding', {}).get('parameter') == parameter
                    and fact.get('implicit_binding', {}).get('status') == 'static_bound'
                    for fact in edge.class_method_bindings))
            if (not records and (exact_super_receiver or exact_class_receiver)):
                records = [{'argument': {'receiver': True}, 'parameter': parameter, 'status': 'exact'}]
            if (not arguments or any(argument.get('target_path') for argument in arguments)
                    or len(records) != 1 or records[0]['status'] != 'exact'):
                continue
            sources = [value for argument in arguments for value in argument.get('sources', [])]
            containers = [argument.get('container_binding') for argument in arguments]
            if (not normal_binding and containers and all(item and item == containers[0] for item in containers)
                    and containers[0]['status'] == 'exact'):
                incoming[parameter] = [{'container_shape': containers[0]['shape'],
                    'container_binding': copy.deepcopy(containers[0])}]
                literals = [argument.get('literal') for argument in arguments]
                if literals[0] is not None and all(item == literals[0] for item in literals):
                    incoming[parameter][0]['literal'] = copy.deepcopy(literals[0])
                continue
            values = []
            for value in sources:
                if (value.get('kind') == 'constructor_instance' and value.get('instance_type')
                        and records[0].get('argument') == {'constructor_instance': True}
                        and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in (
                            'projection', 'output_path', 'value_incomplete'))
                        and any(fact.get('status') == 'source_bound'
                            and fact.get('phase') == '__init__'
                            and fact.get('target') == asdict(definition[0])
                            and fact.get('receiver_class') == value['instance_type']
                            and fact.get('implicit_binding', {}).get('parameter') == parameter
                            for fact in edge.constructor_bindings)):
                    values.append({'instance_type': copy.deepcopy(value['instance_type']),
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    continue
                if (value.get('kind') in ('parameter', 'call_result')
                        and value.get('instance_type') and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in ('projection', 'output_path',
                            'value_incomplete', 'import_modified', 'import_incomplete',
                            'attribute_provenance'))):
                    values.append({'instance_type': copy.deepcopy(value['instance_type']),
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    bindings = [fact for fact in edge.instance_method_bindings
                                if fact.get('status') == 'source_bound'
                                and fact.get('target') == asdict(definition[0])
                                and records[0].get('argument') == {'receiver': True}]
                    if len(bindings) == 1:
                        values[-1]['fresh_receiver_origin'] = fresh_incoming_origin(bindings[0], parameter)
                    continue
                if value.get('instance_type') or 'instance_candidates' in value:
                    values.append({'instance_candidates': [], 'value_incomplete': True})
                    continue
                origin = value.get('source_class_origin', {})
                if (origin.get('basis') == 'source_symbol' and value.get('class_type')
                        and origin.get('class') == value['class_type']
                        and value.get('relation') == 'direct' and not any(value.get(flag)
                            for flag in ('projection', 'output_path', 'import_modified',
                                         'import_incomplete', 'value_incomplete', 'attribute_provenance'))):
                    origin = copy.deepcopy(origin)
                    origin['call_context'] = origin.get('call_context', []) + [edge.id]
                    values.append({'class_type': copy.deepcopy(value['class_type']),
                        'source_class_origin': origin,
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    continue
                identity = value.get('callable_type')
                if value.get('kind') == 'callable':
                    matches = self._definition_index.find(value.get('module'), value['source'])
                    identity = asdict(matches[0][0]) if len(matches) == 1 else None
                if identity and value.get('relation') == 'direct' and not any(
                        value.get(flag) for flag in ('projection', 'output_path',
                            'import_modified', 'import_incomplete', 'value_incomplete')):
                    values.append({'callable_type': identity,
                        'callable_evidence': _unique(value.get('callable_evidence', [])
                            + value.get('evidence', [])),
                        'conditions': value.get('conditions', [])})
            literals = [argument.get('literal') for argument in arguments]
            literal = (literals[0] if all(item == literals[0] for item in literals) else None)
            if normal_binding and literal is not None and literal['type'] in ('tuple', 'list'):
                literal = None
            if literal is not None:
                values = [dict(value, literal=copy.deepcopy(literal)) for value in values] or [
                    {'literal': copy.deepcopy(literal),
                     'literal_evidence': _unique([evidence for argument in arguments
                         for evidence in argument.get('value_evidence', [])])}]
            if values:
                mutations = _unique([effect for value in sources
                    for effect in value.get('class_lookup_mutations', [])])
                if mutations:
                    for value in values:
                        if value.get('class_type') or value.get('instance_type'):
                            value['class_lookup_mutations'] = copy.deepcopy(mutations)
                incomplete = len(values) != len(sources) or any(
                    not argument.get('sources') for argument in arguments)
                if literal is not None:
                    incomplete = False
                incoming[parameter] = [dict(value, value_incomplete=True)
                                       if incomplete else value for value in values]
                if normal_binding:
                    condition = {'normal_call_binding': {
                        'call_id': edge.id, 'parameter': parameter,
                        'argument': copy.deepcopy(records[0]['argument'])}}
                    for value in incoming[parameter]:
                        value['conditions'] = _unique(value.get('conditions', []) + [condition])
        if normal_binding:
            return incoming
        for name in self._captures(*definition):
            records = [item for item in edge.capture_bindings if item.get('capture') == name]
            if len(records) != 1:
                continue
            binding = records[0].get('container_binding', {})
            contents = records[0].get('current_sources', [])
            if (binding.get('status') == 'exact' and not binding.get('contents_unknown')
                    and binding.get('shape') in ('dict', 'list', 'tuple')
                    and any(value.get('kind') in ('parameter', 'capture')
                        and value.get('relation') == 'contained' and value.get('output_path') == ['*']
                        and not value.get('projection') and not value.get('value_incomplete')
                        and value.get('container_role') != 'key' for value in contents)):
                incoming[name] = [{'capture_container_binding': copy.deepcopy(binding)}]
        return incoming

    ## Merge fresh mapping checks only when their lookup proofs agree.
    ## 仅在查找证明一致时合并新建映射检查。
    #
    #  @param previous Previously collected checks.
    #  @param current Checks from another context.
    #  @return Bounded merged alternatives, or an empty list when incompatible.
    @staticmethod
    def _merge_fresh_mapping_checks(previous, current):
        """Keep bounded receiver alternatives only when their lookup proof agrees."""
        if previous == current:
            return copy.deepcopy(previous)
        if (not previous or not current or len(previous) > 8 or len(current) > 8
                or any(not isinstance(item, dict) for item in previous + current)):
            return []
        shared_fields = (
            'kind', 'status', 'function', 'mapping_parameter', 'receiver_parameter',
            'key_variable', 'value_variable', 'lookup_variable', 'attribute_template',
            'iteration_evidence', 'lookup_evidence', 'guard_evidence', 'raise_evidence',
            'invocation_evidence', 'key_conditions', 'attribute_requires_nondunder',
            'runtime_lookup_confirmed', 'runtime_rejection_confirmed', 'receiver_class',
            'member_names', 'source_hash', 'source_hashes', 'assumptions')
        reference = previous[0]
        if any(any(item.get(field) != reference.get(field) for field in shared_fields)
               for item in previous[1:] + current):
            return []
        merged = _unique(copy.deepcopy(previous) + copy.deepcopy(current))
        return merged if len(merged) <= 8 else []

    ## Merge one context summary while retaining unresolved alternatives.
    ## 合并单个上下文摘要，同时保留未解析候选的不确定性。
    #
    #  @param result Mutable combined analysis snapshot.
    #  @param summary Context-specific summary snapshot.
    #  @return None
    def _merge_summary(self, result, summary):
        result.boundaries.extend(summary.boundaries)
        for function in summary.functions:
            previous = next((item for item in result.functions
                             if item['function'] == function['function']), None)
            if previous is None:
                result.functions.append(copy.deepcopy(function))
            else:
                previous['fresh_mapping_member_checks'] = self._merge_fresh_mapping_checks(
                    previous.get('fresh_mapping_member_checks', []),
                    function.get('fresh_mapping_member_checks', []))
                for field in ('returns', 'mapping_effects', 'loops', 'receiver_contexts',
                              'return_objects', 'decorator_effects', 'context_managers',
                              'cached_local_imports', 'source_wrapper_forwarding',
                              'native_callable_metadata_queries', 'native_class_metadata_observers'):
                    if field in function:
                        previous[field] = _unique(previous.get(field, []) + function[field])
        for call in summary.calls:
            previous = next((item for item in result.calls if item.id == call.id), None)
            if previous is None:
                result.calls.append(copy.deepcopy(call))
            else:
                unresolved = any(item.target is None and item.target_status not in (
                    'bounded_alternatives', 'builtin_allocation', 'python_protocol',
                    'local_container_protocol') for item in (previous, call))
                if previous.target != call.target:
                    previous.target = None
                    previous.target_status = 'bounded_alternatives'

                # An unresolved context prevents a unique target and complete value proof.
                # 未解析的上下文会阻止唯一目标和完整值的证明。
                if unresolved:
                    previous.target = None
                    previous.target_status = ('receiver_unresolved'
                        if '.' in previous.callee_name else 'definition_unavailable')
                for field in ('target_candidates', 'argument_sources', 'argument_flows',
                              'parameter_bindings', 'parameter_flows', 'return_flows',
                              'receiver_sources', 'receiver_type_evidence',
                              'binding_issues', 'mutation_flows', 'effects', 'capture_bindings',
                              'return_dependencies', 'decorator_identity_evidence'):
                    setattr(previous, field, _unique(getattr(previous, field) + getattr(call, field)))
                for field in ('callable_sources', 'analysis_contexts', 'conditional_returns',
                              'class_method_bindings', 'constructor_bindings', 'instance_method_bindings', 'class_metadata_bindings',
                              'class_read_bindings', 'conditional_source_bindings', 'candidate_paths'):
                    setattr(previous, field, _unique(getattr(previous, field) + getattr(call, field)))
                if previous.callable_instance_evidence != call.callable_instance_evidence:
                    previous.callable_instance_evidence = {}
                previous.result_sources = _merge_result_sources(
                    previous.result_sources, call.result_sources)
                if unresolved:
                    previous.result_sources = [dict(value, value_incomplete=True)
                        if value.get('class_type') or value.get('instance_type') or value.get('instance_candidates')
                        or value.get('container_object') else value
                        for value in previous.result_sources]
                if previous.binding_status != call.binding_status:
                    previous.binding_status = 'uncertain'

    ## Expand the selected call target, retaining existing function summaries.
    ## 展开选定调用目标，并保留已有函数摘要。
    #
    #  @param result Previous snapshot from this source set.
    #  @param call_id Exact call-site identifier.
    #  @param additional_depth Layers below the selected target.
    #  @param isolate Return only the selected incoming context, without merging the caller snapshot.
    #  @param preserve_lineage Retain available origin call facts in isolated expansion.
    #  @return New snapshot, leaving result unchanged.
    def expand(self, result, call_id, additional_depth=1, isolate=False,
               preserve_lineage=False):
        if type(isolate) is not bool:
            raise ValueError('isolate must be bool')
        if type(preserve_lineage) is not bool:
            raise ValueError('preserve_lineage must be bool')
        if preserve_lineage and not isolate:
            raise ValueError('preserve_lineage requires isolate=True')
        if additional_depth < 1:
            raise ValueError('additional_depth must be positive')
        max_class_effect_steps = result.inputs.get('max_class_effect_steps', 8000)
        if type(max_class_effect_steps) is not int or max_class_effect_steps < 1:
            raise ValueError('Class-effect analysis budget must be a positive integer')
        dependencies = result.inputs.get('supporting_source_sha256', {})
        if dependencies and not self.support_source_protocols:
            raise ValueError('Supporting source protocols are not enabled for expansion')
        validate_source_dependencies(dependencies, self._analysis_budget)
        self._index(preserve_source_facts=True)
        # Expansion is part of the same query snapshot. Keep its class-effect
        # allowance aligned with the budget that produced the parent facts.
        self._class_effect_fact_steps = max_class_effect_steps
        self._conditional_source_state = result.inputs.get('conditional_source_state') is True
        self._supporting_source_hashes.update(dependencies)
        # The parent snapshot and the expansion must use the same sources and contracts.
        # 父快照与本次展开必须使用相同源码和契约。
        if (self.hashes != result.inputs['sha256'] or sorted(self.files) != result.inputs['source_files']
                or self.return_summaries != result.inputs.get('return_summaries', {})
                or self.parameter_shapes != result.inputs.get('parameter_shapes', {})):
            raise ValueError('Sources changed; call analyze again before expand')
        call = next(c for c in result.calls if c.id == call_id)
        if isolate:
            if call.target is None or call.binding_status == 'invalid':
                raise ValueError('Isolated expansion requires a unique usable target')
            definition = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
            inputs = copy.deepcopy(result.inputs)
            if not preserve_lineage:
                inputs.pop('entry_binding', None)
                inputs.pop('entry_alias', None)
            inputs['expansion_context'] = {'incoming_call_id': call.id,
                'caller': asdict(call.caller), 'target': asdict(call.target),
                'parameter_facts': copy.deepcopy(self._incoming_facts(definition, call))}
            updated = FlowAnalysis(call.target, inputs)
            if preserve_lineage:
                lineage_ids = {call.id}
                for binding in getattr(call, 'instance_method_bindings', ()):
                    origin = binding.get('origin') if isinstance(binding, dict) else None
                    if isinstance(origin, dict) and isinstance(origin.get('path'), (list, tuple)):
                        lineage_ids.update(item for item in origin['path'] if isinstance(item, str))
                for value in getattr(call, 'receiver_sources', ()):
                    origin = value.get('fresh_receiver_origin') if isinstance(value, dict) else None
                    if isinstance(origin, dict) and isinstance(origin.get('path'), (list, tuple)):
                        lineage_ids.update(item for item in origin['path'] if isinstance(item, str))
                lineage_calls = [item for item in result.calls if item.id in lineage_ids]
                if ({item.id for item in lineage_calls} != lineage_ids
                        or sum(item.id == call.id for item in lineage_calls) != 1):
                    raise ValueError('Expansion lineage call facts are incomplete')
                updated.calls = copy.deepcopy(lineage_calls)
                updated.boundaries = copy.deepcopy([
                    item for item in result.boundaries
                    if item.get('call_id') in lineage_ids
                    or item.get('reason') == 'source_constructor_entry_binding'])
            # The selected edge starts a bounded context. Recursion below this
            # entry is still checked by _walk; no root facts are merged into it.
            # 选定边作为独立有界上下文，后续递归仍由 _walk 检查。
            context = CallContext(call.caller.module, call.target, copy.deepcopy(call))
            self._walk(updated, definition, additional_depth, context, 500, 2000)
            updated.boundaries = _unique(updated.boundaries)
            publish_source_dependencies(self, updated)
            return updated
        updated = copy.deepcopy(result)
        if call.target is not None:
            updated.boundaries = [b for b in updated.boundaries if not (b.get('call_id') == call_id and b['reason'] == 'depth_limit')]
            # Selected expansion retains its original caller-only recursion
            # ancestry; it does not infer an entry path from the merged graph.
            parent = CallContext(call.caller.module, call.caller, None)
            selected = next(c for c in updated.calls if c.id == call_id)
            context = CallContext(call.caller.module, call.target, selected, parent)
            definition = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
            self._walk(updated, definition, additional_depth, context, 500, 2000)
        updated.boundaries = _unique(updated.boundaries)
        publish_source_dependencies(self, updated)
        return updated


## Summarize one function under a bounded incoming call context.
## 在有界传入调用上下文下概括单个函数。
class _Summary:
    ## Initialize query-local evidence, effects and control-flow state.
    ## 初始化本次查询的证据、效果和控制流状态。
    #
    #  @param analyzer Owning flow analyzer.
    #  @param result Snapshot receiving boundaries and facts.
    #  @param ref Source function identity.
    #  @param node Function AST.
    #  @param remaining Remaining call budget.
    #  @param receiver_class Optional proven receiver class.
    #  @param incoming Optional incoming parameter facts.
    #  @return None
    def __init__(self, analyzer, result, ref, node, remaining, receiver_class=None,
                 incoming=None):
        self.analyzer, self.result, self.ref, self.node = analyzer, result, ref, node
        self.calls = []
        self.returns = []
        self.conditions = copy.deepcopy(getattr(node, '_flow_conditions', []))
        self.remaining = remaining
        self.evaluated_calls = set()
        self.loops = []
        self.yields = []
        self.source_lines = [line.encode('utf-8') for line in
                             self.analyzer.texts[ref.file_path].split('\n')]
        self.evidence_cache = {}
        self.mapping_effects = []
        self.cached_local_imports = []
        self.receiver_class = receiver_class
        self.normal_returns = []
        self.incomplete_return = False
        self.exit_kinds = set()
        self.context_managers = []
        self.context_execution = False
        self.context_cleanup_order = [0]
        self.outcomes = []
        self.modified_return_callables = set()
        self.incoming = incoming or {}

    ## Resolve bounded callable candidates and report whether they are complete.
    ## 解析有界可调用候选，并报告候选是否完整。
    #
    #  @param values Candidate source records.
    #  @return Candidate definitions and completeness flag.
    def callable_targets(self, values):
        if len(values) > 64:
            self.result.boundaries.append({'function': asdict(self.ref),
                                           'reason': 'callable_candidate_budget'})
            return [], False
        targets, complete = [], bool(values)
        for value in values:
            identity = value.get('callable_type')
            if value.get('kind') == 'callable':
                matches = self.analyzer._definition_index.find(
                    value.get('module', self.ref.module), value['source'])
                identity = asdict(matches[0][0]) if len(matches) == 1 else None
            if not identity or value.get('relation') != 'direct' or any(
                    value.get(flag) for flag in ('projection', 'output_path',
                        'import_modified', 'import_incomplete')):
                complete = False
                continue
            key = identity['module'], identity['qualname']
            if key in self.modified_return_callables:
                complete = False
                continue
            matches = self.analyzer._definition_index.find(*key)
            if len(matches) != 1 or ('.' not in key[1]
                    and not self.analyzer._stable_import_name('.'.join(key))):
                complete = False
                continue
            targets.append(matches[0])
            complete = complete and not value.get('value_incomplete')
        return _unique(targets), complete

    ## Extract a finite literal or a uniformly known literal binding.
    ## 提取有限字面量或一致已知的字面量绑定。
    #
    #  @param node Expression AST.
    #  @param env Current abstract environment.
    #  @return Literal fact or None when unsupported or uncertain.
    def literal_fact(self, node, env):
        if isinstance(node, ast.Name):
            values = env.get(node.id, [])
            facts = [value.get('literal') for value in values]
            return facts[0] if facts and all(fact == facts[0] and fact is not None
                and not value.get('value_incomplete')
                and value.get('relation') == 'direct'
                and not value.get('projection') and not value.get('output_path')
                for fact, value in zip(facts, values)) else None
        if node is None or sum(1 for _ in ast.walk(node)) > 128:
            return None
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            return None
        if type(value) is float and not abs(value) < float('inf'):
            return None
        if type(value) in (str, int, float, bool, type(None)):
            return {'type': type(value).__name__, 'value': value}
        if type(value) in (tuple, list) and len(value) <= 64 and all(
                type(item) in (str, int, float, bool, type(None))
                and (type(item) is not float or abs(item) < float('inf')) for item in value):
            return {'type': type(value).__name__, 'value': list(value)}
        return None

    ## Remove literal assumptions for aliases of affected containers.
    ## 移除受影响容器别名上的字面量假设。
    #
    #  @param values Affected source records.
    #  @param env Mutable abstract environment.
    #  @return None
    def invalidate_literals(self, values, env):
        identities = {value['source'] for value in self.container_values(values)
                      if value.get('kind') == 'container'}
        for name, items in env.items():
            env[name] = [{key: item for key, item in value.items() if key != 'literal'}
                         if value.get('source') in identities else value for value in items]

    ## Resolve a closed literal module dispatch table under source restrictions.
    ## 在源码约束下解析封闭的模块级字面量分派表。
    #
    #  @param name Dispatch table binding name.
    #  @param env Mutable abstract environment.
    #  @return Source records or an empty list when unproven.
    def module_dispatch(self, name, env):
        if name in env:
            return env[name]
        bodies = self.analyzer.module_bodies.get(self.ref.module, [])
        facts = self.analyzer.import_binding_facts.get(self.ref.module, [])
        if len(bodies) != 1 or len(facts) != 1:
            return []
        statements = facts[0].get(name, [])
        if len(statements) != 1 or not isinstance(statements[0], ast.Assign):
            return []
        assignment = statements[0]
        expression = assignment.value
        if isinstance(expression, ast.DictComp):
            ## Check that a generated table entry names one stable source function.
            ## 检查生成表项是否指向唯一稳定的源码函数。
            #
            #  @param symbol Candidate function name.
            #  @return True only for a supported stable definition.
            def stable_function(symbol):
                matches = self.analyzer._definition_index.find(self.ref.module, symbol)
                return (len(matches) == 1 and not matches[0][1].decorator_list
                    and matches[0][0].lineno < expression.lineno
                    and '.' not in symbol and self.analyzer._stable_import_name(
                        self.ref.module + '.' + symbol))
            try:
                expression = generated_dict(expression, bodies[0][1], facts[0], stable_function)
            except DispatchLimit:
                self.add_boundary('generated_dispatch_budget', assignment, env)
                return []
        if (assignment not in bodies[0][1] or len(assignment.targets) != 1
                or not isinstance(expression, ast.Dict)
                or any(not isinstance(key, ast.Constant) or not isinstance(key.value, str)
                       for key in expression.keys)):
            return []
        if len(expression.keys) > 64:
            self.add_boundary('literal_dispatch_budget', assignment, env)
            return []
        # Any use other than a read-only subscript can invalidate the closed table.
        # 只读下标以外的使用可能使封闭表假设失效。
        for statement in bodies[0][1]:
            for parent in ast.walk(statement):
                for child in ast.iter_child_nodes(parent):
                    if isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load):
                        if not (isinstance(parent, ast.Subscript) and parent.value is child
                                and isinstance(parent.ctx, ast.Load)):
                            return []
        module_ref = FunctionRef(self.ref.module, '', bodies[0][0], 0)
        summary = _Summary(self.analyzer, self.result, module_ref, self.node,
                           self.remaining)
        module_env = {}
        values = summary.expression(expression, module_env)
        env.update({key: value for key, value in module_env.items()
                    if key.startswith('$heap:')})
        self.remaining = summary.remaining
        return self.marked(values, assignment)

    ## Build a class source record with current lookup-state evidence.
    ## 构建带当前查找状态证据的类来源记录。
    #
    #  @param class_ref Source class identity.
    #  @param node Source evidence AST node.
    #  @param env Current abstract environment.
    #  @return Class source record.
    def class_value(self, class_ref, node, env):
        value = {'kind': 'class', 'module': class_ref.module,
                'source': class_ref.qualname, 'class_type': asdict(class_ref),
                'source_class_origin': {'basis': 'source_symbol', 'class': asdict(class_ref),
                    'evidence': [self.evidence(node)], 'call_context': []},
                'relation': 'direct', 'evidence': [self.evidence(node)],
                'conditions': list(self.conditions)}
        if self.class_origin_invalid(asdict(class_ref), env):
            value['value_incomplete'] = True
        effects = self.class_lookup_effects(asdict(class_ref), env)
        if effects:
            value['class_lookup_mutations'] = copy.deepcopy(effects)
        return value

    ## Resolve class alternatives without silently dropping uncertain candidates.
    ## 解析类候选，不悄然丢弃不确定项。
    #
    #  @param values Candidate source records.
    #  @param allow_incomplete Whether incomplete class values may be retained.
    #  @param env Optional current environment for lookup invalidation.
    #  @return Resolved class records, or an empty list when unproven.
    def class_values(self, values, allow_incomplete=False, env=None):
        known = []
        for value in values:
            if (value.get('relation') != 'direct' or value.get('projection')
                    or value.get('output_path') or value.get('import_modified')
                    or value.get('import_incomplete')
                    or value.get('value_incomplete') and not allow_incomplete):
                return []
            if value.get('kind') == 'class' or value.get('class_type'):
                identity = value.get('class_type')
                matches = self.analyzer._definition_index.find(
                    identity['module'] if identity else value['module'],
                    identity['qualname'] if identity else value['source'], kind='class')
                if len(matches) != 1:
                    return []
                known.append(dict(value, kind='class', module=matches[0][0].module,
                                  source=matches[0][0].qualname,
                                  class_type=asdict(matches[0][0])))
            elif value.get('kind') == 'import':
                target = self.analyzer._class_symbol(value['source'])
                if target is None:
                    return []
                known.append(dict(value, kind='class', module=target[0].module,
                                  source=target[0].qualname,
                                  class_type=asdict(target[0])))
            elif value.get('kind') == 'call_result':
                call = next((call for call in self.calls if call.id == value['source']), None)
                if call is None or call.target is None:
                    return []
                matches = self.analyzer._definition_index.find(
                    call.target.module, call.target.qualname)
                definition = next((item for item in matches if item[0] == call.target), None)
                if definition is None:
                    return []
                definition = self.analyzer._selected_definition(
                    definition, self.analyzer._incoming_facts(definition, call))
                returned, cause = self.analyzer._class_returns(
                    definition, self.analyzer._receiver_class(definition, call),
                    self.analyzer._incoming_facts(definition, call))
                if cause:
                    self.result.boundaries.append({'call_id': call.id,
                        'reason': cause, 'callee_name': call.callee_name})
                if not returned:
                    return []
                returned = [dict(item,
                    evidence=item.get('evidence', []) + value.get('evidence', []),
                    conditions=item.get('conditions', []) + value.get('conditions', []))
                    for item in returned]
                call.result_sources = _unique(call.result_sources + returned)
                if not allow_incomplete and any(value.get('value_incomplete') for value in returned):
                    return []
                known.extend(returned)
            else:
                return []
        if env is not None:
            for value in known:
                effects = self.class_lookup_effects(value['class_type'], env)
                if effects:
                    value['class_lookup_mutations'] = _unique(
                        value.get('class_lookup_mutations', []) + copy.deepcopy(effects))
                if self.class_origin_invalid(value['class_type'], env):
                    value['value_incomplete'] = True
        return _unique(known)

    ## Build a class-attribute environment key for one unique source class.
    ## 为唯一源码类构建类属性环境键。
    #
    #  @param node Attribute expression.
    #  @param env Current abstract environment.
    #  @return Key and class identity, or None when lookup is uncertain.
    def attribute_key(self, node, env):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            return None
        values = self.class_values(env.get(node.value.id, []), env=env)
        identities = _unique([value['class_type'] for value in values])
        if len(identities) != 1:
            return None
        identity = identities[0]
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        if hierarchy is None or any(cls.decorator_list or cls.keywords for _, cls in hierarchy):
            return None
        if any(self.analyzer._definition_index.find(ref.module, ref.qualname + '.' + node.attr)
               for ref, _ in hierarchy):
            return None
        attribute = node.attr
        owner = self.ref.qualname.rpartition('.')[0].rpartition('.')[2].lstrip('_')
        if attribute.startswith('__') and not attribute.endswith('__') and owner:
            attribute = '_' + owner + attribute
        return '$attribute:%s:%s:%s' % (identity['module'], identity['qualname'], attribute), identity

    ## Clear modeled class-attribute values after an unknown mutation.
    ## 未知修改后清空已建模的类属性值。
    #
    #  @param env Mutable abstract environment.
    #  @return None
    def invalidate_attributes(self, env):
        for key in list(env):
            if key.startswith('$attribute:'):
                env[key] = []

    ## Gather recorded lookup mutations for a class and its known hierarchy.
    ## 收集类及其已知继承层次的已记录查找修改。
    #
    #  @param identity Source class identity dictionary.
    #  @param env Current abstract environment.
    #  @return Deduplicated lookup effect records.
    def class_lookup_effects(self, identity, env):
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        owners = [asdict(ref) for ref, _ in hierarchy] if hierarchy else [identity]
        return _unique([effect for owner in owners for effect in env.get(_class_lookup_key(owner), [])])

    ## Record a class lookup effect and propagate it to existing aliases.
    ## 记录类查找效果并传播给已有别名。
    #
    #  @param effect Class lookup effect record.
    #  @param env Mutable abstract environment.
    #  @return None
    def register_class_lookup_effect(self, effect, env):
        key = _class_lookup_key(effect['receiver_class'])
        env[key] = _unique(env.get(key, []) + [copy.deepcopy(effect)])
        for name, values in list(env.items()):
            updated = []
            for value in values:
                identity = value.get('class_type') or value.get('instance_type')
                effects = self.class_lookup_effects(identity, env) if identity else []
                updated.append(dict(value, class_lookup_mutations=_unique(
                    value.get('class_lookup_mutations', []) + copy.deepcopy(effects)))
                    if effects else value)
            env[name] = updated

    ## Check whether recorded lookup mutations touch requested attributes.
    ## 检查已记录的查找修改是否涉及指定属性。
    #
    #  @param values Source records with lookup mutations.
    #  @param attributes Attributes being queried.
    #  @return True when any recorded effect intersects the attributes.
    def class_lookup_affected(self, values, attributes):
        return any(set(effect.get('attributes', [])) & set(attributes)
                   for value in values for effect in value.get('class_lookup_mutations', []))

    ## Prove bounded class-attribute effects for an exact source call.
    ## 为精确源码调用证明有界类属性效果。
    #
    #  @param definition Source target identity and AST pair.
    #  @param call Current flow call.
    #  @param captures Captured source records.
    #  @param env Mutable abstract environment.
    #  @param node Call-site AST node.
    #  @return Class identity records for proved effects.
    def class_attribute_effect(self, definition, call, captures, env, node):
        if (call.binding_status == 'invalid' or call.target != definition[0]
                or (definition[0].module, definition[0].qualname) in self.modified_return_callables
                or not getattr(definition[1], 'decorator_list', [])
                    and '.' not in definition[0].qualname
                    and not self.analyzer._stable_import_name(
                        definition[0].module + '.' + definition[0].qualname)
                or getattr(definition[1], 'decorator_list', []) and not any(
                    fact.get('status') == 'source_bound' for fact in call.class_method_bindings)):
            return []
        ordinary = {arg.arg for arg in definition[1].args.posonlyargs + definition[1].args.args
                    + definition[1].args.kwonlyargs}
        preserved = []
        for argument in call.argument_sources:
            parameter, values = argument.get('parameter'), argument.get('sources', [])
            if (parameter not in ordinary or argument.get('target_path') or not values
                    or not all(value.get('class_type') and value.get('relation') == 'direct'
                        and (value.get('kind') == 'class' or value.get('source_class_origin', {}).get(
                            'basis') == 'source_symbol')
                        and not any(value.get(flag) for flag in ('projection', 'output_path',
                            'value_incomplete', 'import_modified', 'import_incomplete',
                            'attribute_provenance')) for value in values)):
                continue
            identities = _unique(value['class_type'] for value in values)
            if len(identities) != 1:
                continue
            identity = identities[0]
            hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
            if not hierarchy or len(hierarchy) > 64 or any(cls.decorator_list or cls.keywords
                                                          for _, cls in hierarchy):
                continue
            owners = [asdict(ref) for ref, _ in hierarchy]
            other = [value for item in call.argument_sources if item is not argument
                     for value in item.get('sources', [])]
            other.extend(value for contents in captures.values() for value in contents)
            related = False
            for value in other + self.materialize(other, env):
                other_class = value.get('class_type')
                if not other_class:
                    continue
                other_mro = self.analyzer._class_mro(other_class['module'], other_class['qualname'])
                if (other_class in owners or other_mro is None
                        or any(asdict(ref) in owners for ref, _ in other_mro)):
                    related = True
            if related:
                continue
            records = [record for record in call.parameter_bindings
                       if record.get('parameter') == parameter]
            implicit = any(fact.get('status') == 'source_bound'
                and fact.get('implicit_binding', {}).get('parameter') == parameter
                for fact in call.class_method_bindings)
            if not (len(records) == 1 and records[0]['status'] == 'exact' or not records and implicit):
                continue
            args = definition[1].args
            uncertain = {arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs
                         + [arg for arg in (args.vararg, args.kwarg) if arg is not None]}
            uncertain.discard(parameter)
            uncertain.update(captures)
            string_literals, name_bindings = {}, []
            for item in call.argument_sources:
                literal = item.get('literal')
                if literal and literal.get('type') in ('str', 'int', 'float', 'bool', 'NoneType'):
                    uncertain.discard(item.get('parameter'))
                bindings = [record for record in call.parameter_bindings
                            if record.get('parameter') == item.get('parameter')]
                arguments = [argument for argument in call.argument_sources
                             if argument.get('parameter') == item.get('parameter')]
                if (literal and literal.get('type') == 'str' and type(literal.get('value')) is str
                        and item.get('parameter') in ordinary and item.get('parameter') != parameter
                        and not item.get('target_path') and len(arguments) == 1
                        and len(bindings) == 1 and bindings[0].get('status') == 'exact'
                        and bindings[0].get('argument') == item.get('argument')
                        and bindings[0].get('binding_kind') != 'default'):
                    string_literals[item['parameter']] = literal['value']
                    name_bindings.append({'parameter': item['parameter'],
                        'argument': copy.deepcopy(item['argument']), 'literal': copy.deepcopy(literal),
                        'evidence': copy.deepcopy(item.get('value_evidence', []))})
            defaults = {arg.arg: default for arg, default in zip(
                (args.posonlyargs + args.args)[-len(args.defaults):], args.defaults)}
            defaults.update({arg.arg: default for arg, default in zip(args.kwonlyargs, args.kw_defaults)
                             if default is not None})
            for record in call.parameter_bindings:
                default = defaults.get(record.get('parameter'))
                if (record.get('binding_kind') == 'default' and record.get('status') == 'exact'
                        and any(fact.get('status') == 'source_bound'
                            and fact.get('target') == asdict(definition[0])
                            for fact in call.class_method_bindings)
                        and isinstance(default, ast.Constant)
                        and type(default.value) in (str, int, float, bool, type(None))):
                    uncertain.discard(record['parameter'])
            ## Identify a name whose class write must remain protected.
            ## 判断名称是否属于必须保护的类写入范围。
            #
            #  @param source Name AST node.
            #  @return True when uncertain or within the receiver hierarchy.
            def protected(source):
                if source.id in uncertain:
                    return True
                match = self.analyzer._resolve_class(definition[0], source.id)
                return match is not None and asdict(match[0]) in owners

            ## Charge work against the shared class-effect budget.
            ## 将工作量计入共享类效果预算。
            #
            #  @param count Number of steps to charge.
            #  @return None
            def charge(count):
                self.analyzer._class_effect_fact_steps -= count

            metadata = []
            read_bindings = {}

            ## Obtain and cache an independent class-attribute read premise.
            ## 获取并缓存独立的类属性读取前提。
            #
            #  @param attribute Attribute name.
            #  @return True when the binding is source-bound.
            def class_read(attribute):
                if attribute not in read_bindings:
                    binding = source_class_read_binding(self, identity, definition, parameter, call, node, attribute)
                    read_bindings[attribute] = binding
                    if binding is not None and binding not in call.class_read_bindings:
                        call.class_read_bindings.append(copy.deepcopy(binding))
                binding = read_bindings[attribute]
                return binding is not None and binding.get('status') == 'source_bound'

            ## Obtain the independently proved source class-name literal.
            ## 获取独立证明的源码类名字面量。
            #
            #  @param source Name expression supplied by the effect scanner.
            #  @return Literal class name or None when unproven.
            def class_name(source):
                if not metadata:
                    binding = source_class_name_binding(self, identity, definition, parameter, call, node)
                    metadata.append(binding)
                    if binding is not None and binding not in call.class_metadata_bindings:
                        call.class_metadata_bindings.append(copy.deepcopy(binding))
                binding = metadata[0]
                return (binding.get('literal', {}).get('value') if binding is not None
                        and binding.get('status') == 'source_bound' else None)

            try:
                proof = class_attribute_writes(definition[1], parameter,
                    lambda name: self.analyzer._builtin_name_status(definition[0], definition[1], name)
                        == 'confirmed_builtin', protected,
                    self.analyzer._lexical_class_name(definition[0]),
                    min(2000, self.analyzer._class_effect_fact_steps), charge,
                    string_literals=string_literals, class_name=class_name, class_read=class_read)
            except _ClassEffectLimit:
                self.add_boundary('class_attribute_effect_budget', node, env, values, call_id=call.id)
                continue
            if proof is None:
                continue
            paths = {ref.file_path for ref, _ in hierarchy} | {
                definition[0].file_path, self.ref.file_path}
            if proof.metadata_evidence:
                paths.update(metadata[0]['source_hashes'])
            for attribute, _ in proof.read_evidence:
                paths.update(read_bindings[attribute]['source_hashes'])
            effect = {'kind': 'class_attribute_write_set', 'status': 'bounded',
                'preserved_scope': 'other_class_attributes', 'completion': 'normal_return',
                'value_completeness': 'unmodeled', 'receiver_class': copy.deepcopy(identity),
                'target': asdict(definition[0]), 'parameter': parameter,
                'attributes': list(proof.attributes), 'call_id': call.id,
                'call_evidence': self.evidence(node),
                'evidence': [self.evidence_at(definition[0], item) for item in proof.evidence],
                'source_hashes': {path: self.analyzer.hashes[path] for path in sorted(paths)
                                  if path in self.analyzer.hashes},
                'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_attribute_writes',
                    'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']}
            if name_bindings:
                effect['name_bindings'] = name_bindings
            if proof.read_evidence:
                effect['read_basis'] = 'source_class_attribute_invariant'
                effect['read_premises'] = [copy.deepcopy(read_bindings[name])
                    for name in _unique([name for name, _ in proof.read_evidence])]
                effect['read_evidence'] = [{'attribute': name, 'operation': 'hasattr',
                    'evidence': self.evidence_at(definition[0], source)} for name, source in proof.read_evidence]
            if proof.metadata_evidence:
                effect['name_basis'] = 'source_class_metadata'
                effect['name_metadata'] = copy.deepcopy(metadata[0])
                effect['name_evidence'] = [self.evidence_at(definition[0], item)
                                           for item in proof.metadata_evidence]
            call.effects.append(effect)
            self.register_class_lookup_effect(effect, env)
            preserved.append(identity)
        return preserved

    ## Check whether class lookup depends on an invalidated source class or base.
    ## 检查类查找是否依赖已失效的源码类或基类。
    #
    #  @param identity Source class identity.
    #  @param env Current path's invalidation markers.
    #  @param exposed Additional exposed class identities.
    #  @return True if the class or a known source base has lost its proof.
    def class_origin_invalid(self, identity, env, exposed=()):
        if not exposed and not any(key.startswith('$class_origin_invalid:') for key in env):
            return False
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        owners = [asdict(ref) for ref, _ in hierarchy] if hierarchy else [identity]
        return any(owner in exposed or env.get(_class_origin_key(owner)) for owner in owners)

    ## Invalidate source class identity proofs after an unmodeled write or escape.
    ## 未建模写入或逃逸后使源码类身份证明失效。
    #
    #  @param values Class provenance exposed to the operation.
    #  @param env Current lexical/heap values, including aliases of those classes.
    #  @param call Optional call responsible for the exposure.
    #  @return None
    def invalidate_class_origins(self, values, env, call=None):
        identities = [value['class_type'] for value in values + self.materialize(values, env)
                      if value.get('source_class_origin') and value.get('class_type')]
        if identities:
            if (getattr(self.analyzer, '_conditional_source_state', False) and call is not None
                    and self.condition_class_state(identities, values, env, call)):
                return
            for identity in _unique(identities):
                key = _class_origin_key(identity)
                env[key] = [{'kind': 'class_state', 'source': key,
                    'relation': 'direct', 'evidence': [], 'conditions': [],
                    'cause': 'unmodeled_call' if call is not None else 'write'}]
            for name, sources in env.items():
                env[name] = [dict(value, value_incomplete=True)
                    if value.get('class_type') and self.class_origin_invalid(
                        value['class_type'], env, identities) else value for value in sources]

    ## Retain an explicit subsequent-lookup predicate, without proving the effect.
    ## 保留显式后续查找谓词，但不据此证明效果。
    #
    #  @param identities Source class objects exposed to the call.
    #  @param values Actual input provenance, checked for prior incompleteness.
    #  @param env Current path state to annotate without materializing class data.
    #  @param call Evaluated source call whose effects remain unknown.
    #  @return Whether source lookup may continue under an unproved state predicate.
    def condition_class_state(self, identities, values, env, call):
        # A state predicate describes a required source lookup, never an effect
        # proof or a runtime target. Explicit writes still use normal invalidation.
        if any(value.get('value_incomplete') for value in values if value.get('class_type')):
            return False
        if call.target is None:
            return False
        selected = self.analyzer._definition_index.find(call.target.module, call.target.qualname)
        if len(selected) != 1:
            return False
        function = selected[0][1]
        parameters = function.args.posonlyargs + function.args.args
        if not parameters:
            return False
        # Do not hide source-known writes to the method namespace or MRO.
        methods = {'__class__', '__bases__', '__dict__'}
        for identity in identities:
            hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
            if not hierarchy:
                return False
            for _, cls in hierarchy:
                for member in cls.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(member.name)
                        if member.name.startswith('__') and not member.name.endswith('__') and cls.name.lstrip('_'):
                            methods.add('_' + cls.name.lstrip('_') + member.name)
        for count, item in enumerate(ast.walk(function)):
            if count >= 2000 or self.analyzer._class_effect_fact_steps <= 0:
                self.result.boundaries.append({'call_id': call.id, 'reason': 'conditional_source_budget'})
                return False
            self.analyzer._class_effect_fact_steps -= 1
            if (isinstance(item, ast.Attribute) and isinstance(item.ctx, (ast.Store, ast.Del))
                    and item.attr in methods):
                return False
            if (isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                    and item.func.id in ('setattr', 'delattr') and len(item.args) >= 2):
                name = (class_write_name(item.args[1], function, item.args[0].id, None, item.lineno)
                        if isinstance(item.args[0], ast.Name) else None)
                if name in methods:
                    return False
        predicates = []
        for identity in _unique(identities):
            if self.class_origin_invalid(identity, env):
                return False
            predicate = {'kind': 'source_state_preserved', 'status': 'required',
                'runtime_confirmed': False, 'receiver_class': copy.deepcopy(identity),
                'effect_call': call.id, 'effect_target': asdict(call.target),
                'evidence': {'file_path': call.caller.file_path, 'lineno': call.lineno,
                    'col_offset': call.col_offset, 'end_lineno': call.end_lineno,
                    'end_col_offset': call.end_col_offset},
                'scope': 'subsequent_source_lookup', 'feasibility': 'not_proven'}
            predicates.append(predicate)
            self.result.boundaries.append({'call_id': call.id, 'reason': 'conditional_source_state',
                'boundary_kind': 'required_condition', 'condition': copy.deepcopy(predicate)})
        for name, sources in env.items():
            env[name] = [dict(value, conditions=_unique(value.get('conditions', []) +
                [copy.deepcopy(predicate) for predicate in predicates
                 if predicate['receiver_class'] == value.get('class_type')]))
                if value.get('class_type') else value for value in sources]
        return True

    ## Mark exposed instance aliases incomplete after an unknown effect.
    ## 未知效果后将暴露的实例别名标记为不完整。
    #
    #  @param values Exposed source records.
    #  @param env Mutable abstract environment.
    #  @return None
    def invalidate_instance_receivers(self, values, env):
        exposed = {(value.get('source'), repr(value['instance_type']))
                   for value in values + self.materialize(values, env)
                   if value.get('instance_type')}
        if exposed:
            for name, sources in env.items():
                env[name] = [dict(value, value_incomplete=True, instance_candidates=[])
                    if value.get('instance_type') and (value.get('source'),
                        repr(value['instance_type'])) in exposed else value for value in sources]

    ## Detect an explicit keyword conflicting with an implicit binding.
    ## 检测与隐式绑定冲突的显式关键字。
    #
    #  @param call Current flow call.
    #  @param parameter Implicitly bound parameter name.
    #  @param slot Implicit argument location.
    #  @param positional_only Positional-only parameter names.
    #  @return True when a duplicate binding was recorded.
    def implicit_keyword_conflict(self, call, parameter, slot, positional_only):
        if parameter in positional_only:
            return False
        keyword = {'keyword': parameter}
        duplicates = [record for record in call.parameter_bindings
                      if record.get('argument') == keyword]
        if not duplicates:
            return False
        for record in duplicates:
            record.update(parameter=parameter, status='duplicate',
                          conflicts_with=slot, destination_kind='parameter')
            record.pop('target_path', None)
        for argument in call.argument_sources:
            if argument.get('argument') == keyword:
                argument['parameter'] = parameter
                argument.pop('target_path', None)
        for value in call.argument_flows + call.parameter_flows:
            if value.get('argument') == keyword:
                value.update(target_parameter=parameter, target_path=[])
        call.binding_status = 'invalid'
        call.binding_issues.append({'kind': 'duplicate_binding',
            'parameter': parameter, 'argument': keyword, 'conflicts_with': slot})
        self.result.boundaries.append({'call_id': call.id, 'reason': 'duplicate_argument_binding'})
        return True

    ## Explain a source classmethod binding under explicit snapshot assumptions.
    ## 在显式快照假设下解释源码类方法绑定。
    #
    #  @param node Attribute call expression.
    #  @param target Selected static method candidate, when available.
    #  @param receiver Raw receiver provenance, before dependency materialization.
    #  @return Conditional binding facts, or None without a classmethod candidate.
    def class_method_binding(self, node, target, receiver):
        if not isinstance(node.func, ast.Attribute):
            return None
        classes = _unique([value['class_type'] for value in receiver if value.get('class_type')])
        receiver_ref = FunctionRef(**classes[0]) if len(classes) == 1 else None
        if receiver_ref is None and isinstance(node.func.value, (ast.Name, ast.Attribute)):
            match = self.analyzer._resolve_class(self.ref, ast.unparse(node.func.value))
            if match:
                receiver_ref = match[0]
        if target is None and receiver_ref:
            matches = self.analyzer._definition_index.find(receiver_ref.module,
                receiver_ref.qualname + '.' + node.func.attr)
            target = matches[0] if len(matches) == 1 else self.analyzer._inherited_method(
                receiver_ref.module, receiver_ref.qualname, node.func.attr)
        if target is None or not any(isinstance(decorator, ast.Name)
                and decorator.id == 'classmethod' for decorator in getattr(target[1], 'decorator_list', [])):
            return None
        ref, method = target
        owners = self.analyzer._definition_index.find(ref.module, ref.qualname.rpartition('.')[0], kind='class')
        owner_ref = owners[0][0] if len(owners) == 1 else None
        descriptor = self.analyzer._descriptor_kind(target)
        issues = []
        evidence = _unique([self.evidence(node)] + [item for value in receiver
            for item in value.get('evidence', [])] + [self.evidence_at(ref, method)])
        binding_evidence = [item for value in receiver for item in value.get('evidence', [])]
        first = ast.unparse(node.func.value).partition('.')[0]
        bodies = self.analyzer.module_bodies.get(self.ref.module, [])
        bindings = self.analyzer.import_binding_facts.get(self.ref.module, [])
        if len(bodies) == 1 and len(bindings) == 1:
            module_ref = FunctionRef(self.ref.module, '', bodies[0][0])
            binding_evidence.extend(self.evidence_at(module_ref, statement)
                                    for statement in bindings[0].get(first, [])
                                    if hasattr(statement, 'lineno'))

        ## Record a classmethod binding issue with optional source evidence.
        ## 记录类方法绑定问题及可选源码证据。
        #
        #  @param reason Issue reason code.
        #  @param source_ref Optional source identity.
        #  @param source_node Optional evidence AST node.
        #  @return None
        def issue(reason, source_ref=None, source_node=None):
            item = {'reason': reason}
            if source_node is not None:
                item['evidence'] = self.evidence_at(source_ref, source_node)
            issues.append(item)

        direct = (receiver_ref is not None and receiver and len(classes) == 1
            and isinstance(node.func.value, (ast.Name, ast.Attribute)) and all(
                (value.get('kind') == 'class' or value.get('source_class_origin', {}).get(
                    'basis') == 'source_symbol' and value.get('source_class_origin', {}).get(
                    'class') == value.get('class_type')) and value.get('relation') == 'direct'
                and not any(value.get(flag) for flag in ('projection', 'output_path',
                    'value_incomplete', 'import_modified', 'import_incomplete', 'attribute_provenance'))
                for value in receiver))
        if not direct:
            issue('receiver_origin_unconfirmed')
        mutations = _unique([effect for value in receiver
                            for effect in value.get('class_lookup_mutations', [])])
        if (any(effect.get('attributes') for effect in mutations)
                and node.func.attr.startswith('__') and not node.func.attr.endswith('__')):
            issue('private_lookup_after_class_write_unconfirmed')
        if self.class_lookup_affected(receiver, (node.func.attr, '__class__', '__bases__')):
            issue('class_lookup_write')
        if descriptor != 'classmethod':
            issue('descriptor_unconfirmed', ref, method)
        parts = ref.qualname.split('.')
        for length in range(1, len(parts) - 1):
            for enclosing_ref, enclosing in self.analyzer._definition_index.find(
                    ref.module, '.'.join(parts[:length])):
                if 'classmethod' in self.analyzer._scope_facts(enclosing).bound:
                    issue('descriptor_unconfirmed', enclosing_ref, enclosing)
        hierarchy = (self.analyzer._class_mro(receiver_ref.module, receiver_ref.qualname)
                     if receiver_ref else None)
        lookup = 'local_class_dictionary' if receiver_ref == owner_ref else 'source_mro'
        if lookup == 'source_mro' and hierarchy is None:
            issue('mro_unavailable')
        checked, pending, unresolved_bases = [], [receiver_ref] if receiver_ref else [], False
        while pending and len(checked) < 64:
            current = pending.pop(0)
            if current in checked:
                continue
            checked.append(current)
            matches = self.analyzer._definition_index.find(current.module, current.qualname, kind='class')
            if len(matches) != 1:
                issue('class_definition_unavailable')
                continue
            class_ref, cls = matches[0]
            if cls.decorator_list or cls.keywords:
                issue('class_lookup_customization', class_ref, cls)
            if current != receiver_ref and any('__init_subclass__' in
                    statement_scope_facts([statement]).bound for statement in cls.body):
                issue('class_creation_hook', class_ref, cls)
            members = [statement for statement in cls.body
                       if node.func.attr in statement_scope_facts([statement]).bound]
            if current == owner_ref:
                if members != [method]:
                    issue('method_member_binding_unconfirmed', class_ref, cls)
                preceding = cls.body[:cls.body.index(method)] if method in cls.body else cls.body
                if 'classmethod' in statement_scope_facts(preceding).bound:
                    issue('descriptor_unconfirmed', class_ref, cls)
            bases = self.analyzer._base_classes(current.module, current.qualname)
            if bases is None:
                unresolved_bases = True
            else:
                pending.extend(base[0] for base in bases)
        if pending:
            issue('class_binding_budget')
        if hierarchy:
            selected = next(((class_ref, cls) for class_ref, cls in hierarchy
                if any(node.func.attr in statement_scope_facts([statement]).bound
                       for statement in cls.body)), None)
            if selected and selected[0] != owner_ref:
                issue('method_lookup_conflict', selected[0], selected[1])
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            issue('class_binding_budget')
        identities = {(item.module, item.qualname) for item in checked}
        for written, attribute, reason, source_ref, source_node in writes:
            if ((written.module, written.qualname) in identities
                    and attribute in (node.func.attr, '*', '__bases__', '__class__')):
                issue(reason, source_ref, source_node)
                issues[-1]['reachability'] = 'not_proven'
        for previous in self.calls:
            if (previous.target_status not in (
                    'python_protocol', 'local_container_protocol', 'builtin_allocation')
                    and not (previous.target_status == 'builtin_boundary'
                             and previous.callee_name in ('isinstance', 'issubclass'))):
                if any((value.get('class_type', {}).get('module'),
                        value.get('class_type', {}).get('qualname')) in identities
                       for argument in previous.argument_sources
                       if argument['argument'] != {'receiver': True}
                       for value in argument['sources']) and not any(
                        effect.get('kind') == 'class_attribute_write_set'
                        and effect.get('status') == 'bounded'
                        and (effect['receiver_class']['module'],
                             effect['receiver_class']['qualname']) in identities
                        for effect in previous.effects):
                    issue('class_escape')
                    issues[-1]['evidence'] = {'file_path': previous.caller.file_path,
                        'lineno': previous.lineno, 'col_offset': previous.col_offset,
                        'callee_name': previous.callee_name}
        parameters = method.args.posonlyargs + method.args.args
        if not parameters:
            issue('implicit_receiver_parameter_missing', ref, method)
        assumptions = ['source_snapshot_bindings_hold', 'builtin_classmethod_and_type_lookup',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']
        if unresolved_bases:
            assumptions.append('unresolved_bases_use_standard_metaclass_lookup')
        fact = {'status': 'unconfirmed' if issues else 'source_bound',
            'basis': 'source_snapshot', 'runtime_target_confirmed': False,
            'receiver_class': asdict(receiver_ref) if receiver_ref else None,
            'definition_class': asdict(owner_ref) if owner_ref else None,
            'target': asdict(ref), 'lookup': lookup,
            'descriptor': {'kind': 'builtin_classmethod' if descriptor == 'classmethod' else 'unconfirmed',
                'evidence': [self.evidence_at(ref, decorator) for decorator in method.decorator_list]},
            'implicit_binding': {'parameter': parameters[0].arg if parameters else None,
                'argument': {'receiver': True},
                'status': 'unconfirmed' if issues else 'static_bound',
                'receiver_class': asdict(receiver_ref) if receiver_ref else None},
            'evidence': evidence, 'conditions': copy.deepcopy(self.conditions),
            'receiver_binding_evidence': _unique(binding_evidence),
            'source_hashes': {path: self.analyzer.hashes[path] for path in sorted(
                {item.file_path for item in checked} | {ref.file_path, self.ref.file_path})
                if path in self.analyzer.hashes},
            'assumptions': assumptions, 'issues': _unique(issues)}
        if mutations:
            fact['lookup_preservation'] = copy.deepcopy(mutations)
            fact['lookup_hierarchy'] = [asdict(owner) for owner, _ in hierarchy] if hierarchy else []
            for effect in mutations:
                fact['source_hashes'].update(effect.get('source_hashes', {}))
        return fact

    ## Capture source evidence in the current function.
    ## 捕获当前函数中的源码证据。
    #
    #  @param node Source AST node.
    #  @return Source evidence dictionary.
    def evidence(self, node):
        return self.evidence_at(self.ref, node)

    ## Capture source evidence for an explicitly selected function.
    ## 为显式选定的函数捕获源码证据。
    #
    #  @param ref Source function identity.
    #  @param node Source AST node.
    #  @return Source evidence dictionary.
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

    ## Assemble evidence for a module-level callable instance.
    ## 为模块级可调用实例组装证据。
    #
    #  @param facts Collected callable-instance facts.
    #  @param node Call-site AST node.
    #  @return Callable-instance evidence record.
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

    ## Attach current source evidence and conditions to value records.
    ## 为值记录附加当前源码证据和条件。
    #
    #  @param values Source value records.
    #  @param node Evidence AST node.
    #  @param relation Optional replacement dependency relation.
    #  @return Marked value records.
    def marked(self, values, node, relation=None):
        result = [dict(v, relation=relation or v['relation'], evidence=v['evidence'] + [self.evidence(node)],
                       conditions=v.get('conditions', []) + list(self.conditions)) for v in values]
        if relation and relation != 'direct':
            for value in result:
                value.pop('python_shape', None)
                value.pop('container_object', None)
        return result

    ## Identify input roots potentially affected by an analysis boundary.
    ## 识别可能受分析边界影响的输入根。
    #
    #  @param values Source values to inspect.
    #  @param env Current abstract environment.
    #  @return Input-root records and an unknown-scope flag.
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

    ## Append an explicit boundary with affected-input evidence.
    ## 附加带受影响输入证据的显式边界。
    #
    #  @param reason Boundary reason code.
    #  @param node Evidence AST node.
    #  @param env Current abstract environment.
    #  @param values Potentially affected source records.
    #  @param fields Additional boundary fields.
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

    ## Build a source callable value with optional declaration defaults.
    ## 构建带可选声明默认值的源码可调用值。
    #
    #  @param target Source function identity.
    #  @param node Evidence AST node.
    #  @param defaults Optional parameter default facts.
    #  @return Callable source record.
    def callable_value(self, target, node, defaults=None):
        return {'kind': 'callable', 'source': target.qualname, 'module': target.module,
                'defaults': defaults or {}, 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}

    ## Attach analysis boundaries to the pure syntax binder's result.
    ## 为纯语法绑定结果附加分析边界。
    #
    #  @param node Call expression.
    #  @param params Callee ast.arguments.
    #  @param positional Positional nodes after receiver binding.
    #  @param call Flow call record receiving binding issues.
    #  @return Existing flow binding records with AST payloads.
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

    ## Evaluate supported source syntax into abstract dependency records.
    ## 将受支持的源码语法求值为抽象依赖记录。
    #
    #  @param node Expression AST, or None.
    #  @param env Mutable abstract environment.
    #  @return Dependency records; unsupported behavior is retained as boundaries.
    def expression(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        if node is None:
            return []
        if (self.context_execution and isinstance(node, (ast.Tuple, ast.List, ast.Dict))
                and any(isinstance(child, ast.Call) for child in ast.walk(node))):
            self.add_boundary('context_exit_nested_expression_unmodeled', node, env,
                              affected_scope='unknown')
        if self.context_execution and (isinstance(node, (ast.Attribute, ast.Subscript,
                ast.BinOp, ast.BoolOp, ast.IfExp, ast.NamedExpr, ast.Lambda,
                ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                or isinstance(node, ast.Compare) and not all(
                    isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
                or isinstance(node, ast.UnaryOp) and self.context_truth(node, env) is None):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                              affected_scope='unknown')
        if self.context_execution and (isinstance(node, ast.Set) or isinstance(node, ast.Dict)
                and any(not isinstance(key, ast.Constant) or type(key.value) not in (str, int, bool, type(None))
                        for key in node.keys)):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env, affected_scope='unknown')
        if isinstance(node, ast.Name):
            if self.context_execution and not env.get(node.id):
                self.add_boundary('context_exit_name_unresolved', node, env, affected_scope='unknown')
            if node.id in env:
                if env[node.id] and all(value.get('kind') == 'import' for value in env[node.id]):
                    classes = self.class_values(env[node.id], env=env)
                    if classes:
                        return self.marked(classes, node)
                return env[node.id]
            imported = self.analyzer.imports.get(self.ref.module, {}).get(node.id)
            stable_import = not imported or self.analyzer._stable_import_name(
                self.ref.module + '.' + node.id)
            class_target = self.analyzer._class_symbol(
                imported or self.ref.module + '.' + node.id) if stable_import else None
            if class_target is not None:
                return [self.class_value(class_target[0], node, env)]
            target = self.analyzer._resolve(self.ref, node.id)
            if target and stable_import:
                return [self.callable_value(target[0], node)]
            if imported:
                return [{'kind': 'import', 'source': imported, 'relation': 'direct',
                         'import_modified': not stable_import,
                         'evidence': [self.evidence(node)],
                         'conditions': list(self.conditions)}]
            return []
        if isinstance(node, ast.Attribute):
            attribute = self.attribute_key(node, env)
            if attribute is not None and attribute[0] in env:
                values = self.marked(env[attribute[0]], node)
                return [dict(value, attribute_provenance=[dict(fact, read=self.evidence(node))
                            for fact in value.get('attribute_provenance', [])]) for value in values]
            name = ast.unparse(node)
            first, dot, rest = name.partition('.')
            binding = env.get(first)
            if binding and all(value.get('kind') == 'import' and not any(
                    value.get(flag) for flag in ('import_modified', 'import_incomplete'))
                    for value in binding):
                identities = {value['source'] + dot + rest for value in binding}
                class_target = self.analyzer._class_symbol(next(iter(identities))) if len(identities) == 1 else None
            elif first not in env:
                imported = self.analyzer.imports.get(self.ref.module, {}).get(first)
                class_target = self.analyzer._class_symbol(
                    imported + dot + rest if imported else self.ref.module + '.' + name
                ) if not imported or self.analyzer._stable_import_name(
                    self.ref.module + '.' + first) else None
            else:
                class_target = None
            if class_target is not None:
                return [self.class_value(class_target[0], node, env)]
            qualified = None
            if binding and all(value.get('kind') == 'import' and not any(
                    value.get(flag) for flag in ('import_modified', 'import_incomplete'))
                    for value in binding):
                identities = {value['source'] + dot + rest for value in binding}
                qualified = next(iter(identities)) if len(identities) == 1 else None
            elif first not in env and self.analyzer._stable_import_name(self.ref.module + '.' + first):
                imported = self.analyzer.imports.get(self.ref.module, {}).get(first)
                qualified = imported + dot + rest if imported else None
            target = self.analyzer._resolve_import_binding(qualified) if qualified else None
            if target is not None:
                return [self.callable_value(target[0], node)]
        if isinstance(node, ast.Constant):
            return []
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            values = self.expression(node.value, env)
            if isinstance(node, ast.YieldFrom):
                values = self.project(values, '*', env)
            values = self.materialize(values, env)
            self.yields.extend(self.marked([
                dict(value, output_path=['*'] + value.get('output_path', []))
                for value in values], node, 'contained'))
            return []
        if isinstance(node, ast.Lambda):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):],
                                node.args.defaults))
            defaults += [(argument, default) for argument, default in
                         zip(node.args.kwonlyargs, node.args.kw_defaults) if default is not None]
            values = {argument.arg: self.expression(default, env)
                      for argument, default in defaults}
            target = FunctionRef(self.ref.module,
                self.ref.qualname + '.<lambda>@%s:%s' % (node.lineno, node.col_offset),
                self.ref.file_path, node.lineno)
            return [self.callable_value(target, node, values)]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            key = '$heap:%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
            items = []
            keys = []
            elements = list(zip(node.keys, node.values)) if isinstance(node, ast.Dict) else list(enumerate(node.elts))
            for index, element in elements:
                if isinstance(node, ast.Dict):
                    if index is None:
                        mapping = self.container_values(self.expression(element, env))
                        roots, unknown = self.affected_values(mapping, env)
                        self.mapping_effects.append({
                            'operation': 'merge', 'mapping': roots,
                            'element_path': ['*'], 'output_container': key,
                            'status': 'unknown_source' if unknown else 'bounded',
                            'conditions': list(self.conditions),
                            'evidence': self.evidence(element)})
                        copied = False
                        for reference in mapping:
                            if (reference.get('kind') == 'container'
                                    and reference.get('container_shape') == 'dict'):
                                items.extend(copy.deepcopy(env.get(reference['source'], [])))
                                keys.extend(copy.deepcopy(env.get(reference['source'] + '$keys', [])))
                                copied = True
                        if not copied:
                            values = self.marked(self.materialize(mapping, env), element, 'contained')
                            items.extend(dict(v, output_path=['*'] + v.get('output_path', []))
                                         for v in values)
                            keys.append({'kind': 'key', 'source': '*', 'key': '*'})
                        continue
                    slot = index.value if isinstance(index, ast.Constant) and isinstance(index.value, (str, int)) else '*'
                    key_values = self.marked(self.materialize(self.expression(index, env), env),
                                             index, 'contained')
                else:
                    slot = index if not isinstance(node, ast.Set) else '*'
                keys.append({'kind': 'key', 'source': repr(slot), 'key': slot})
                if isinstance(node, ast.Dict) and slot != '*':
                    updated = []
                    for value in items:
                        path = value.get('output_path', [None])
                        if path[0] == slot:
                            continue
                        if path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[slot]]))
                        updated.append(value)
                    items = updated
                    for marker in keys[:-1]:
                        if marker['key'] == '*':
                            marker.setdefault('excluded_keys', []).append(slot)
                if isinstance(node, ast.Dict):
                    items.extend(dict(v, output_path=[slot] + v.get('output_path', []),
                                      container_role='key') for v in key_values)
                values = self.expression(element, env)
                items.extend(dict(v, output_path=[slot] + v.get('output_path', [])) for v in values)
            env[key] = items
            env[key + '$keys'] = keys
            reference = {'kind': 'container', 'source': key, 'container_shape': type(node).__name__.lower(),
                         'relation': 'direct', 'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}
            literal = self.literal_fact(node, env)
            if literal is not None:
                reference['literal'] = literal
            return [reference]
        if isinstance(node, ast.Subscript):
            raw = (self.module_dispatch(node.value.id, env)
                   if isinstance(node.value, ast.Name) else self.expression(node.value, env))
            values = self.container_values(raw)
            self.expression(node.slice, env)
            if isinstance(node.slice, (ast.Slice, ast.UnaryOp)):
                selected = []
                for value in values:
                    keys = env.get(value['source'] + '$keys', [])
                    slots = [k['key'] for k in keys]
                    if value.get('container_shape') not in ('list', 'tuple') or slots != list(range(len(slots))):
                        selected.extend(self.project([value], '*', env))
                        continue
                    try:
                        if isinstance(node.slice, ast.Slice):
                            bounds = [ast.literal_eval(n) if n is not None else None
                                      for n in (node.slice.lower, node.slice.upper, node.slice.step)]
                            indices = list(range(len(slots)))[slice(*bounds)]
                            for position, index in enumerate(indices):
                                selected.extend(dict(v, output_path=[position] + v.get('output_path', []))
                                                for v in self.project([value], index, env))
                        else:
                            index = ast.literal_eval(node.slice)
                            index = list(range(len(slots)))[index]
                            selected.extend(self.project([value], index, env))
                    except IndexError:
                        pass
                    except (ValueError, TypeError):
                        selected.extend(self.project([value], '*', env))
                return self.marked(selected, node)
            index = node.slice.value if isinstance(node.slice, ast.Constant) else '*'
            return self.marked(self.project(values, index, env), node)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)) and not any(g.is_async for g in node.generators):
            local = copy.deepcopy(env)
            for generator in node.generators:
                iterable = self.expression(generator.iter, local)
                if iterable and all(v['kind'] == 'container' and
                                    local.get(v['source'] + '$keys') == [] for v in iterable):
                    return []
                values = self.project(iterable, '*', local)
                self.assign_target(generator.target, values, local, generator.target)
                for condition in generator.ifs:
                    self.expression(condition, local)
                    if isinstance(condition, ast.Constant) and not condition.value:
                        return []
                    if not self.refine_guard(condition, local):
                        return []
            elements = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            values = [v for element in elements for v in self.materialize(self.expression(element, local), local)]
            for key in set(env) | set(local):
                if key.startswith('$heap:'):
                    env[key] = _unique(env.get(key, []) + local.get(key, []))
            return self.marked([dict(v, output_path=['*'] + v.get('output_path', [])) for v in values], node, 'contained')
        if isinstance(node, ast.IfExp):
            self.expression(node.test, env)
            before = list(self.conditions)
            positive, negative = copy.deepcopy(env), copy.deepcopy(env)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            possible_left = self.refine_guard(node.test, positive)
            left = self.marked(self.expression(node.body, positive), node.body) if possible_left else []
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            possible_right = self.refine_guard(node.test, negative, positive=False)
            right = self.marked(self.expression(node.orelse, negative), node.orelse) if possible_right else []
            env.clear()
            env.update(_merge_env(([positive] if possible_left else [])
                                  + ([negative] if possible_right else [])))
            self.conditions = before
            values = left + right
            if possible_left and not left or possible_right and not right:
                values = [dict(value, value_incomplete=True) for value in values]
            return values
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.In, ast.NotIn))
                and len(node.comparators) == 1):
            key_values = self.expression(node.left, env)
            compared_values = self.expression(node.comparators[0], env)
            mappings = self.container_values(compared_values)
            if mappings and all(value.get('kind') == 'container'
                                and value.get('container_shape') == 'dict'
                                for value in mappings):
                try:
                    key = ast.literal_eval(node.left)
                except (ValueError, TypeError):
                    key = '*'
                roots, unknown = self.affected_values(mappings, env)
                self.mapping_effects.append({
                    'operation': 'membership', 'mapping': roots,
                    'element_path': [key], 'state_after': 'unchanged',
                    'status': 'unknown_key' if key == '*' or unknown else 'bounded',
                    'conditions': list(self.conditions),
                    'evidence': self.evidence(node)})
                return self.marked(
                    self.materialize(mappings, env) + key_values,
                    node, 'derived')
            # Both operands have already executed, even when their shape is
            # unknown. Falling through to generic traversal repeats effects
            # and can replace the first invocation's target/binding facts.
            return self.marked(self.materialize(key_values, env)
                               + self.materialize(compared_values, env), node, 'derived')
        if isinstance(node, ast.BoolOp):
            current = copy.deepcopy(env)
            before = list(self.conditions)
            values = []
            exits = []
            for operand in node.values:
                values.extend(self.marked(self.materialize(self.expression(operand, current), current), operand))
                exits.append(copy.deepcopy(current))
                self.conditions = self.conditions + [{'test': self.evidence(operand), 'branch': isinstance(node.op, ast.And)}]
                if not self.refine_guard(operand, current, positive=isinstance(node.op, ast.And)):
                    break
            env.clear()
            env.update(_merge_env(exits))
            self.conditions = before
            return values
        if isinstance(node, ast.Call):
            fresh_instance_method_bindings = []
            location = _call_span(node)
            if location not in self.evaluated_calls and self.analyzer._class_return_stack:
                if self.analyzer._fact_calls <= 0:
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'class_return_budget', 'evidence': self.evidence(node)})
                    return []
                self.analyzer._fact_calls -= 1
            if location not in self.evaluated_calls and self.remaining <= 0:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'budget_exceeded', 'evidence': self.evidence(node)})
                return []
            if location not in self.evaluated_calls:
                self.remaining -= 1
                self.evaluated_calls.add(location)
            name = ast.unparse(node.func)
            binding = env.get(name.split('.')[0])
            builtin_status = (self.analyzer._builtin_name_status(self.ref, self.node, name, env)
                              if isinstance(node.func, ast.Name) and hasattr(builtins, name) else None)
            callable_sources = (self.expression(node.func, env)
                                if isinstance(node.func, ast.Subscript) else binding or [])
            protocol = getattr(node, '_flow_implicit_protocol', {})
            target = (getattr(node, '_flow_protocol_target', None) if protocol else
                      self.analyzer._resolve(self.ref, name) if binding is None else None)
            global_rebound = False
            global_declarations = []
            nominal_target = target
            if target and not protocol and '.' not in target[0].qualname:
                global_declarations = self.analyzer._module_global_declarations(target[0])
                global_rebound = bool(global_declarations)
                if global_rebound:
                    target = None
            canonical = self.ref.module + '.' + name
            constructor_class = None
            allocation_class = None
            allocation_values = []
            allocation_candidates = []
            construction_safe = False
            callable_instance_fact = None
            callable_instance_cause = None
            bounded_targets = []
            callable_incomplete = global_rebound
            receiver_values = (self.expression(node.func.value, env)
                                if isinstance(node.func, ast.Attribute) else [])
            receiver_sources = self.materialize(receiver_values, env)
            returned_field_receiver = bool(receiver_values) and all(
                value.get('receiver_type_evidence') for value in receiver_values)
            bound_receiver = bool(protocol and target)
            dispatch_kind = 'receiver_type_evidence' if bound_receiver else None
            field_evidence = None
            owner = self.ref.qualname.rpartition('.')[0]
            function_names = self.analyzer._definition_index.scopes(self.ref.module)
            callee_classes = self.class_values(binding, env=env) if binding and isinstance(node.func, ast.Name) else []
            construction_candidates = []
            if binding and isinstance(node.func, ast.Name) and not callee_classes:
                classes = self.class_values(binding, allow_incomplete=True, env=env)
                if classes and all(value.get('attribute_provenance') for value in classes):
                    construction_candidates = [value for value in classes
                        if self.analyzer._ordinary_construction(FunctionRef(**value['class_type']))]
                    if len(construction_candidates) != len(classes):
                        construction_candidates = [dict(value, value_incomplete=True)
                                                   for value in construction_candidates]
                    allocation_candidates = construction_candidates
                    allocation_values = construction_candidates
            if target is None:
                if callee_classes:
                    identities = {(value['module'], value['source'])
                                  for value in callee_classes}
                    class_target = None
                    if len(identities) == 1:
                        module, qualname = next(iter(identities))
                        matches = self.analyzer._definition_index.find(
                            module, qualname, kind='class')
                        class_target = matches[0] if len(matches) == 1 else None
                elif binding is None:
                    class_target = self.analyzer._resolve_class(self.ref, name)
                    alias = name.split('.')[0]
                    if (alias in self.analyzer.imports.get(self.ref.module, {})
                            and not self.analyzer._stable_import_name(
                                self.ref.module + '.' + alias)):
                        class_target = None
                    if class_target and not self.analyzer._stable_import_name(
                            class_target[0].module + '.' + class_target[0].qualname):
                        class_target = None
                elif all(value.get('kind') == 'import' for value in binding):
                    callee_classes = self.class_values([dict(value,
                        source=value['source'] + ('.' + name.split('.', 1)[1]
                            if '.' in name else '')) for value in binding])
                    class_target = None
                    identities = {(value['module'], value['source']) for value in callee_classes}
                    if len(identities) == 1:
                        module, qualname = next(iter(identities))
                        matches = self.analyzer._definition_index.find(module, qualname, kind='class')
                        class_target = matches[0] if len(matches) == 1 else None
                else:
                    class_target = None
                if class_target is not None:
                    constructor = self.analyzer._constructor_target(class_target)
                    constructor_class = class_target[0]
                    construction_safe = self.analyzer._ordinary_construction(constructor_class)
                    if constructor is not None:
                        target = constructor
                        bound_receiver = True
                        dispatch_kind = 'constructor'
                    else:
                        dispatch_kind = 'constructor_unavailable'
                    canonical = (constructor_class.module + '.' +
                                 constructor_class.qualname)
            receiver_types = {tuple((value.get('class_type') or {}).get(key, '')
                              for key in ('module', 'qualname')) for value in receiver_values}
            if (target is None and isinstance(node.func, ast.Attribute)
                    and receiver_values and all(value.get('class_type')
                                                and not value.get('value_incomplete')
                                                and value.get('relation') == 'direct'
                                                and not value.get('projection')
                                                and not value.get('output_path')
                                                for value in receiver_values)
                    and len(receiver_types) == 1):
                module, class_name = next(iter(receiver_types))
                matches = self.analyzer._definition_index.find(module, class_name + '.' + node.func.attr)
                candidate = matches[0] if len(matches) == 1 else self.analyzer._inherited_method(
                    module, class_name, node.func.attr)
                if candidate is not None:
                    target = candidate
                    bound_receiver = False
                    dispatch_kind = 'class_receiver_candidate'
            if (target is None and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and owner and owner not in function_names
                    and (self.node.args.posonlyargs or self.node.args.args)
                    # Incoming instance facts take precedence over the method's
                    # lexical owner, including incomplete/empty candidates.
                    and not any('instance_type' in value or 'instance_candidates' in value
                                for value in receiver_values + receiver_sources)
                    and receiver_sources and all(v['kind'] == 'parameter' and v['relation'] == 'direct'
                        and not v.get('value_incomplete')
                        and v['source'] == (self.node.args.posonlyargs + self.node.args.args)[0].arg
                        for v in receiver_sources)):
                matches = self.analyzer._definition_index.find(self.ref.module, owner + '.' + node.func.attr)
                if not matches:
                    inherited = self.analyzer._inherited_method(self.ref.module, owner, node.func.attr)
                    matches = [inherited] if inherited else []
                if len(matches) == 1:
                    target = matches[0]
                    bound_receiver = True
                    dispatch_kind = 'instance_method'
            if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name)
                    and not getattr(self.node, 'decorator_list', [])):
                args = self.node.args.posonlyargs + self.node.args.args
                bases = env.get(node.func.value.value.id, [])
                if args and bases and all(v['kind'] == 'parameter' and v['source'] == args[0].arg
                                         and v['relation'] == 'direct' for v in bases):
                    candidate = self.analyzer._field_candidate(self.ref, node.func.value.attr, node.func.attr)
                    if candidate:
                        target, field_evidence = candidate
                        bound_receiver = True
                        dispatch_kind = 'field_method'
            is_zero_super = (isinstance(node.func, ast.Attribute)
                             and isinstance(node.func.value, ast.Call)
                             and isinstance(node.func.value.func, ast.Name)
                             and node.func.value.func.id == 'super'
                             and not node.func.value.args and not node.func.value.keywords)
            is_explicit_super = (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == 'super'
                and len(node.func.value.args) == 2
                and not node.func.value.keywords
                and isinstance(node.func.value.args[0], ast.Name)
                and isinstance(node.func.value.args[1], ast.Name)
                and node.func.value.args[0].id == owner.rpartition('.')[2])
            current_descriptor = self.analyzer._descriptor_kind(
                (self.ref, self.node))
            builtin_super = ('super' not in env
                and 'super' not in self.analyzer.imports.get(self.ref.module, {})
                and 'super' not in self.analyzer.module_bindings.get(self.ref.module, set())
                and self.analyzer._resolve(self.ref, 'super') is None
                and self.analyzer._resolve_class(self.ref, 'super') is None)
            current_class_known = (not is_explicit_super or (
                node.func.value.args[0].id not in env
                and self.analyzer._class_symbol(self.ref.module + '.' + owner)
                is not None))
            if ((is_zero_super or is_explicit_super) and owner and builtin_super
                    and current_class_known):
                inherited = self.analyzer._inherited_method(
                    self.ref.module, owner, node.func.attr,
                    skip_current_members=True)
                args = self.node.args.posonlyargs + self.node.args.args
                receiver_name = (node.func.value.args[1].id
                                 if is_explicit_super else args[0].arg if args else '')
                if (inherited and args and receiver_name == args[0].arg
                        and env.get(receiver_name)):
                    target = inherited
                    bound_receiver = node.func.attr != '__new__'
                    dispatch_kind = ('super_new' if node.func.attr == '__new__'
                                     else 'super_method')
                    receiver_values = env.get(receiver_name, [])
                    receiver_sources = self.materialize(receiver_values, env)
                if (inherited is None and node.func.attr == '__new__'
                        and len(node.args) == 1 and not node.keywords):
                    receiver = self.class_values(env.get(receiver_name, []), env=env)
                    types = _unique([value.get('class_type') for value in receiver])
                    if (receiver and all(types) and len(types) == 1
                            and not any(value.get('value_incomplete') for value in receiver)):
                        class_ref = FunctionRef(**types[0])
                        hierarchy = self.analyzer._class_mro(class_ref.module, class_ref.qualname)
                        owner_index = next((index for index, (ref, _) in enumerate(hierarchy or ())
                            if ref.module == self.ref.module and ref.qualname == owner), None)
                        writes, truncated = self.analyzer._class_binding_writes()
                        changed = truncated or any(attribute in ('__new__', '__class__', '__bases__', '*')
                            and any(written == ref for ref, _ in hierarchy or ())
                            for written, attribute, _, _, _ in writes)
                        if owner_index is not None and not changed and not any(
                                '__new__' in statement_scope_facts(cls.body).bound
                                or cls.keywords or cls.decorator_list
                                for ref, cls in hierarchy[owner_index + 1:]):
                            classes = self.class_values(self.expression(node.args[0], env),
                                                        allow_incomplete=True, env=env)
                            if classes:
                                if (len({(value['module'], value['source']) for value in classes}) == 1
                                        and not any(value.get('value_incomplete') for value in classes)):
                                    allocation_class = FunctionRef(**classes[0]['class_type'])
                                allocation_values = classes
                                allocation_candidates = classes
                                dispatch_kind = 'builtin_allocation'
            if (target is None and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == 'object' and node.func.attr == '__new__'
                    and len(node.args) == 1 and not node.keywords
                    and 'object' not in env
                    and 'object' not in self.analyzer.imports.get(self.ref.module, {})
                    and 'object' not in self.analyzer.module_bindings.get(self.ref.module, set())
                    and self.analyzer._resolve(self.ref, 'object') is None
                    and self.analyzer._resolve_class(self.ref, 'object') is None):
                classes = self.class_values(self.expression(node.args[0], env), allow_incomplete=True, env=env)
                if classes and len({(value['module'], value['source']) for value in classes}) == 1:
                    if not any(value.get('value_incomplete') for value in classes):
                        allocation_class = FunctionRef(**classes[0]['class_type'])
                    allocation_values = classes
                    allocation_candidates = classes
                    dispatch_kind = 'builtin_allocation'
                elif classes:
                    allocation_candidates = classes
                    allocation_values = classes
                    dispatch_kind = 'builtin_allocation'
            possible_allocations = allocation_candidates
            allocation_candidates = [value for value in possible_allocations
                if (self.analyzer._ordinary_construction if construction_candidates
                    else self.analyzer._explicit_object_allocation)(FunctionRef(**value['class_type']))]
            if len(allocation_candidates) != len(possible_allocations):
                allocation_candidates = [dict(value, value_incomplete=True) for value in allocation_candidates]
            if allocation_class and not self.analyzer._explicit_object_allocation(allocation_class):
                allocation_class = None
            if not allocation_candidates and allocation_class is None and dispatch_kind == 'builtin_allocation':
                dispatch_kind = None
            receiver_values = fresh_lookup_receiver(self, node, receiver_values)
            if (target is None and isinstance(node.func, ast.Attribute)
                    and receiver_values and all((value.get('instance_type') and (
                                                    not value.get('value_incomplete')
                                                    or value.get('fresh_receiver_origin'))
                                                or value.get('instance_candidates'))
                                                and value.get('relation') == 'direct'
                                                and not value.get('projection')
                                                and not value.get('output_path')
                                                for value in receiver_values)):
                instance_types = {
                    (identity['module'], identity['qualname'])
                    for value in receiver_values
                    for identity in ([value['instance_type']] if value.get('instance_type')
                                     else value.get('instance_candidates', []))}
                candidates = []
                complete_candidates = True
                for module, class_name in sorted(instance_types):
                    candidate = self.analyzer._instance_method_candidate(
                        module, class_name, node.func.attr)
                    if self.class_lookup_affected(receiver_values,
                            (node.func.attr, '__class__', '__bases__')):
                        candidate = None
                    if candidate is None:
                        complete_candidates = False
                    elif candidate not in candidates:
                        candidates.append(candidate)
                receiver_complete = all(not value.get('value_incomplete') for value in receiver_values)
                if complete_candidates and len(candidates) == 1:
                    candidate = candidates[0]
                    fresh_binding = (fresh_method_binding(
                        self, node, candidate, receiver_values) if not receiver_complete else None)
                    if receiver_complete or fresh_binding is not None:
                        target = candidate
                        bound_receiver = True
                        dispatch_kind = ('returned_field_candidate'
                                         if returned_field_receiver else
                                         'receiver_type_evidence')
                        if fresh_binding is not None:
                            fresh_instance_method_bindings = [fresh_binding]
                elif candidates and (complete_candidates or any(
                        value.get('instance_candidates') for value in receiver_values)):
                    bounded_targets = candidates
                    dispatch_kind = ('bounded_alternatives' if receiver_complete
                                     and complete_candidates else 'receiver_unresolved')
            if target is None and binding and all(v['kind'] == 'import' for v in binding):
                imported = {v['source'] for v in binding}
                if len(imported) == 1:
                    canonical = next(iter(imported)) + ('.' + name.split('.', 1)[1] if '.' in name else '')
                    target = (self.analyzer._resolve_import_binding(canonical)
                              if not any(value.get('conditions')
                                         or value.get('import_modified')
                                         or value.get('import_incomplete')
                                         for value in binding) else None)
            elif binding is None:
                alias, dot, rest = name.partition('.')
                imported = self.analyzer.imports.get(self.ref.module, {}).get(alias)
                if imported:
                    canonical = imported + (dot + rest if dot else '')
            if callable_sources and isinstance(node.func, (ast.Name, ast.Subscript)):
                candidates, complete = self.callable_targets(callable_sources)
                callable_incomplete = bool(candidates) and not complete
                if isinstance(node.func, ast.Subscript) and not isinstance(node.func.slice, ast.Constant):
                    complete = False
                if complete and len(candidates) == 1:
                    target = candidates[0]
                    dispatch_kind = ('literal_dispatch' if isinstance(node.func, ast.Subscript)
                                     else 'incoming_callable' if any(
                                         value.get('callable_type') for value in callable_sources)
                                     else None)
                elif candidates:
                    target = None
                    bounded_targets = candidates
            if target is None:
                target, callable_instance_fact, callable_instance_cause = (
                    self.analyzer._module_callable_instance(
                        self.ref, name, binding))
                if target is not None:
                    bound_receiver = True
                    dispatch_kind = 'callable_instance_candidate'
                    assignment_evidence = self.evidence_at(
                        callable_instance_fact['module_ref'],
                        callable_instance_fact['assignment'])
                    receiver_sources = [{
                        'kind': 'module_callable_instance',
                        'source': callable_instance_fact['qualified_name'],
                        'instance_type': asdict(
                            callable_instance_fact['class_ref']),
                        'relation': 'direct',
                        'evidence': [assignment_evidence, self.evidence(node)],
                        'conditions': list(self.conditions)}]
            decorated_target_candidate = False
            if (isinstance(node.func, ast.Attribute) and (
                    any(value.get('class_type') and value.get('value_incomplete')
                        for value in receiver_values)
                    or self.class_lookup_affected(receiver_values,
                        (node.func.attr, '__class__', '__bases__'))
                    or node.func.attr.startswith('__') and not node.func.attr.endswith('__')
                    and any(effect.get('attributes') for value in receiver_values
                            for effect in value.get('class_lookup_mutations', [])))):
                if (target and dispatch_kind == 'super_new' and receiver_values
                        and all(value.get('source_class_origin', {}).get('basis') == 'source_symbol'
                                for value in receiver_values)
                        and not self.class_lookup_affected(receiver_values,
                            (node.func.attr, '__class__', '__bases__'))
                        and any(value.get('cause') == 'unmodeled_call' for key, values in env.items()
                                if key.startswith('$class_origin_invalid:') for value in values)
                        and not any(value.get('cause') == 'write' for key, values in env.items()
                                    if key.startswith('$class_origin_invalid:') for value in values)):
                    self.result.boundaries.append({'reason': 'source_lookup_candidate',
                        'call_id': _call_key(self.ref.file_path, node),
                        'target': asdict(target[0]), 'evidence': self.evidence(node)})
                target, bounded_targets, bound_receiver, dispatch_kind = None, [], False, None
            identity_decorator = None
            wrapper_forwarding_candidate = False
            descriptor_kind = self.analyzer._descriptor_kind(target) if target else None
            if target and getattr(target[1], 'decorator_list', []) and descriptor_kind is None:
                identity_decorator = self.analyzer._identity_decorator(target)
                decoration_facts = self.analyzer._binding_decoration_facts(target)
                body_preserved = (len(decoration_facts) == 1
                    and decoration_facts[0]['body_binding_status'] == 'preserved')
                if identity_decorator is not None or body_preserved:
                    decorated_target_candidate = body_preserved and identity_decorator is None
                elif (factory_wrapper(self.analyzer, target) or {}).get('forwarding') is not None:
                    # Preserve only the nominal original body. This wrapper's
                    # path condition requires concrete invocation arguments;
                    # generic ownership/value-flow consumers retain a boundary.
                    wrapper_forwarding_candidate = True
                    decorated_target_candidate = True
                elif dispatch_kind in (
                        'constructor', 'instance_method', 'field_method',
                        'receiver_type_evidence', 'returned_field_candidate',
                        'super_method', 'super_new'):
                    decorated_target_candidate = True
                else:
                    replacement = self.analyzer._decorated_target(target)
                    if replacement:
                        target = replacement
                        dispatch_kind = 'decorator_replacement'
                    else:
                        target = None
            elif descriptor_kind == 'staticmethod':
                dispatch_kind = 'constructor' if constructor_class is not None else 'staticmethod'
            elif descriptor_kind == 'classmethod':
                bound_receiver = True
                dispatch_kind = 'constructor' if constructor_class is not None else 'classmethod'
            call_id = _call_key(self.ref.file_path, node)
            if target and (not namespace_unmodified(self.analyzer, self.ref.module + '.' + name)
                    or not namespace_unmodified(self.analyzer,
                        target[0].module + '.' + target[0].qualname)):
                self.result.boundaries.append({'call_id': call_id,
                    'reason': 'dynamic_source_namespace_binding', 'boundary_kind': 'uncertainty',
                    'target': asdict(target[0]), 'evidence': self.evidence(node)})
            constructor_values = (self.expression(node.func, env)
                if constructor_class is not None and target
                and dispatch_kind == 'constructor' else [])
            call = FlowCall(call_id, self.ref, name, node.lineno, node.col_offset,
                            node.end_lineno, node.end_col_offset, target[0] if target else None)
            call.instance_method_bindings = fresh_instance_method_bindings
            call.implicit_protocol = copy.deepcopy(protocol)
            if global_rebound:
                self.result.boundaries.append({'call_id': call_id,
                    'reason': 'module_callable_binding_unconfirmed',
                    'boundary_kind': 'uncertainty', 'nominal_target': asdict(nominal_target[0]),
                    'declarations': [self.evidence_at(nominal_target[0], declaration)
                                     for declaration in global_declarations],
                    'evidence': self.evidence(node)})
            if getattr(self.analyzer, '_conditional_source_state', False):
                contexts = [context for value in receiver_sources
                            for context in value.get('instance_candidate_contexts', [])] or receiver_sources
                common = (contexts[0].get('conditions', []) if contexts else [])
                call.conditions = _unique(copy.deepcopy(self.conditions) + [condition for condition in common
                    if all(condition in value.get('conditions', []) for value in contexts)])
                parameters = self.node.args.posonlyargs + self.node.args.args
                ambient = env.get(parameters[0].arg, []) if parameters else []
                if ambient:
                    call.conditions = _unique(call.conditions + [condition
                        for condition in ambient[0].get('conditions', [])
                        if all(condition in value.get('conditions', []) for value in ambient)
                        and condition.get('kind') == 'source_state_preserved'])
                for context in contexts:
                    identity = context.get('instance_type')
                    candidate = (self.analyzer._instance_method_candidate(identity['module'],
                        identity['qualname'], node.func.attr) if identity and isinstance(node.func, ast.Attribute)
                        else None)
                    if candidate and candidate in bounded_targets:
                        call.candidate_paths.append({'target': asdict(candidate[0]), 'call_id': call.id,
                            'receiver_class': copy.deepcopy(identity),
                            'conditions': copy.deepcopy(context.get('conditions', []))})
            call.callable_sources = copy.deepcopy(callable_sources)
            if callable_incomplete:
                self.add_boundary('callable_identity_incomplete', node, env,
                    callable_sources, call_id=call_id)
            if (isinstance(node.func, ast.Subscript) and callable_sources
                    and not isinstance(node.func.slice, ast.Constant)):
                self.add_boundary('literal_dispatch_key_unknown', node, env,
                                  callable_sources, call_id=call_id)
            if target:
                call.target_candidates = [asdict(target[0])]
            elif bounded_targets:
                call.target_candidates = [asdict(candidate[0])
                                          for candidate in bounded_targets]
            call.receiver_sources = receiver_sources
            call.receiver_type_evidence.extend({'kind': 'context_manager_enter_return',
                'instance_type': copy.deepcopy(value.get('instance_type')),
                'return_binding': copy.deepcopy(value['context_manager_return']),
                'evidence': copy.deepcopy(value.get('evidence', [])),
                'conditions': copy.deepcopy(value.get('conditions', [])),
                'basis': 'source_snapshot', 'runtime_target_confirmed': False}
                for value in receiver_values if value.get('context_manager_return'))
            class_binding = self.class_method_binding(node, target, receiver_values)
            if class_binding:
                call.class_method_bindings = [class_binding]
                if class_binding['status'] != 'source_bound':
                    self.result.boundaries.append({'call_id': call_id,
                        'reason': 'class_method_binding_unconfirmed', 'boundary_kind': 'uncertainty',
                        'issues': copy.deepcopy(class_binding['issues']), 'evidence': self.evidence(node)})
            if (target and receiver_sources and (descriptor_kind == 'classmethod'
                    or any(value.get('class_type') for value in receiver_sources))):
                self.result.boundaries.append({'call_id': call_id,
                    'reason': 'dynamic_class_receiver_override_possible',
                    'boundary_kind': 'assumption' if class_binding and class_binding['status'] == 'source_bound' else 'uncertainty',
                    'binding_status': class_binding['status'] if class_binding else 'unconfirmed',
                    'assumptions': copy.deepcopy(class_binding['assumptions']) if class_binding else [],
                    'evidence': self.evidence(node)})
            if identity_decorator is not None:
                call.decorator_identity_evidence = [{
                    'decorator': asdict(identity_decorator['decorator']),
                    'parameter': identity_decorator['parameter'],
                    'returns': [self.evidence_at(
                        identity_decorator['decorator'], returned)
                        for returned in identity_decorator['returns']]}]
                if (identity_decorator['effects_unmodeled'] and not (body_preserved
                        and decoration_facts[0].get('kind') == 'source_fresh_function_decoration')):
                    self.result.boundaries.append({
                        'call_id': call_id, 'callee_name': name,
                        'reason': 'identity_decorator_effects_unmodeled',
                        'affected_scope': 'unknown', 'affected_values': [],
                        'evidence': self.evidence_at(
                            identity_decorator['decorator'],
                            identity_decorator['definition'])})
            if wrapper_forwarding_candidate:
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                    'reason': 'identity_decorator_effects_unmodeled',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence_at(target[0], target[1])})
            if callable_instance_fact is not None:
                call.callable_instance_evidence = self.module_callable_evidence(
                    callable_instance_fact, node)
                call.callable_instance_evidence['binding'] = source_binding(
                    self, callable_instance_fact, target)
            if returned_field_receiver:
                call.receiver_type_evidence = _unique([
                    dict(fact, receiver_call=self.evidence(node))
                    for value in receiver_values
                    for fact in value['receiver_type_evidence']])
            call.target_status = ('bounded_alternatives' if bounded_targets else
                                  'constructor_unavailable' if construction_candidates else
                                  'builtin_allocation' if allocation_class or allocation_candidates else
                                  dispatch_kind if target and dispatch_kind else
                                  'constructor_unavailable' if constructor_class else
                                  'lexical_method_candidate' if target and bound_receiver else
                                  'resolved' if target else 'receiver_unresolved' if isinstance(node.func, ast.Attribute)
                                  else 'builtin_boundary' if builtin_status == 'confirmed_builtin'
                                  else 'definition_unavailable')
            if (target is None and builtin_status in ('source_binding', 'unconfirmed')
                    and name in ('dict', 'list', 'tuple', 'set', 'str', 'repr', 'bool', 'len', 'next')):
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                    'function': asdict(self.ref), 'reason': 'builtin_name_unconfirmed',
                    'builtin_name_status': builtin_status, 'affected_scope': 'unknown',
                    'affected_values': [], 'conditions': list(self.conditions),
                    'evidence': self.evidence(node)})
            if dispatch_kind == 'receiver_unresolved' and bounded_targets:
                call.target_status = 'receiver_unresolved'
                self.add_boundary('class_attribute_state_unknown', node, env,
                    receiver_values, call_id=call_id)
            if callable_incomplete:
                call.target_status = 'definition_unavailable'
            if constructor_class is not None and not construction_safe:
                self.result.boundaries.append({'call_id': call_id,
                    'reason': 'dynamic_construction', 'evidence': self.evidence(node)})
                if (self.analyzer._class_binding_write_cache is not None
                        and self.analyzer._class_binding_write_cache[1]):
                    self.result.boundaries.append({'call_id': call_id,
                        'reason': 'constructor_binding_budget', 'evidence': self.evidence(node)})
                if target and target[1].name == '__new__':
                    self.result.boundaries.append({'call_id': call_id,
                        'reason': 'constructor_initialization_unmodeled',
                        'phase': '__init__', 'evidence': self.evidence(node)})
            if allocation_class is not None or allocation_candidates and not construction_candidates:
                self.result.boundaries.append({'call_id': call_id,
                    'reason': 'builtin_allocator_source_unavailable',
                    'evidence': self.evidence(node)})
            if field_evidence:
                call.target_status = 'constructor_field_candidate'
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                    'reason': 'constructor_field_assumption', 'evidence': self.evidence(field_evidence)})
            if callable_instance_cause is not None:
                self.result.boundaries.append({
                    'call_id': call_id, 'callee_name': name,
                    'reason': 'module_callable_instance_unresolved',
                    'cause': callable_instance_cause,
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence(node)})
            if callable_instance_fact is not None:
                callable_binding = call.callable_instance_evidence['binding']
                self.result.boundaries.append({
                    'call_id': call_id, 'callee_name': name,
                    'reason': 'dynamic_callable_instance_override_possible',
                    'boundary_kind': 'assumption' if callable_binding['status'] == 'source_bound' else 'uncertainty',
                    'binding_status': callable_binding['status'],
                    'assumptions': copy.deepcopy(callable_binding['assumptions']),
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence(node)})
            if (target and dispatch_kind in (
                    'super_method', 'super_new', 'instance_method')
                    and getattr(self.node, 'decorator_list', [])
                    and current_descriptor not in ('classmethod', 'staticmethod')):
                self.result.boundaries.append({
                    'call_id': call_id, 'callee_name': name,
                    'reason': 'decorated_caller_semantics',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence(self.node)})
                facts = self.analyzer._binding_decoration_facts((self.ref, self.node))
                if len(facts) == 1 and facts[0]['body_binding_status'] == 'preserved':
                    self.result.boundaries[-1].update(boundary_kind='assumption',
                        body_binding_status='preserved', function=asdict(self.ref),
                        assumptions=copy.deepcopy(facts[0]['assumptions']))
            if target and decorated_target_candidate:
                self.result.boundaries.append({
                    'call_id': call_id, 'callee_name': name,
                    'reason': 'decorated_target_candidate',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence_at(target[0], target[1])})
                facts = self.analyzer._binding_decoration_facts(target)
                if len(facts) == 1 and facts[0]['body_binding_status'] == 'preserved':
                    self.result.boundaries[-1].update(boundary_kind='assumption',
                        body_binding_status='preserved', function=asdict(target[0]),
                        assumptions=copy.deepcopy(facts[0]['assumptions']))
            if target and owner and dispatch_kind in (
                    'instance_method', 'super_method', 'super_new'):
                hierarchy = self.analyzer._class_mro(self.ref.module, owner)
                decorated_class = next(((ref, cls) for ref, cls in (hierarchy or ())
                                        if cls.decorator_list), None)
                if decorated_class is not None:
                    self.result.boundaries.append({
                        'call_id': call_id, 'callee_name': name,
                        'reason': 'decorated_class_candidate',
                        'affected_scope': 'unknown', 'affected_values': [],
                        'evidence': self.evidence_at(*decorated_class)})
            string_arity = {'split': (0, 2), 'rsplit': (0, 2),
                            'strip': (0, 1), 'lstrip': (0, 1), 'rstrip': (0, 1),
                            'startswith': (1, 3), 'endswith': (1, 3),
                            'partition': (1, 1), 'rpartition': (1, 1)}
            method = node.func.attr if isinstance(node.func, ast.Attribute) else ''
            limits = string_arity.get(method)
            string_protocol = (target is None and isinstance(node.func, ast.Attribute)
                               and isinstance(node.func.value, ast.Name)
                               and limits is not None and limits[0] <= len(node.args) <= limits[1]
                               and not node.keywords
                               and not any(isinstance(argument, ast.Starred)
                                           for argument in node.args)
                               and receiver_sources
                               and all(v.get('python_shape') == 'str'
                                       for v in receiver_sources))
            if string_protocol:
                call.target_status = 'python_protocol'
                call.argument_sources.append({'argument': {'receiver': True}, 'parameter': '$receiver',
                                              'sources': receiver_sources})
                if method in ('partition', 'rpartition'):
                    call.return_dependencies = [
                        {'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                         'output_path': [index],
                         'evidence': [{'provenance':
                            'Guarded or trusted str partition result dependency'}],
                         'conditions': list(self.conditions)} for index in range(3)]
                else:
                    call.return_dependencies = [{
                        'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                        'evidence': [{'provenance':
                            'Guarded str receiver dependency; builtin method implementation assumed'}],
                        'conditions': list(self.conditions)}]
                    self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                                   'reason': 'string_subclass_override_possible'})
                if method in ('partition', 'rpartition'):
                    self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                                                   'reason': 'string_subclass_override_possible'})
            literal_join = (target is None and isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)
                            and node.func.attr == 'join' and len(node.args) == 1 and not node.keywords
                            and not isinstance(node.args[0], ast.Starred))
            if target and dispatch_kind == 'super_method':
                # The dedicated proof revalidates the exact builtin super()
                # receiver, MRO target and fresh-origin lineage itself. Do not
                # gate that proof on the generic receiver-binding flag: other
                # uncertainty in argument expansion can clear that flag even
                # when the super lookup remains statically exact.
                fresh = fresh_super_method_binding(self, node, target, receiver_values)
                if fresh is not None:
                    call.instance_method_bindings = [fresh]
            if target and bound_receiver and dispatch_kind in (
                    'instance_method', 'field_method', 'receiver_type_evidence',
                    'returned_field_candidate'):
                fresh = fresh_method_binding(self, node, target, receiver_values)
                if fresh is not None:
                    call.instance_method_bindings = [fresh]
                self.result.boundaries.append({'call_id': call_id, 'callee_name': name,
                    'reason': 'dynamic_method_override_possible',
                    **({'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                        'assumptions': copy.deepcopy(fresh['assumptions'])} if fresh is not None else {})})
            if returned_field_receiver and (target or bounded_targets):
                self.result.boundaries.append({
                    'call_id': call_id, 'callee_name': name,
                    'reason': 'dynamic_accessor_override_possible',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence(node)})
            capture_values = {}
            params = target[1].args if target else None
            contract = self.analyzer.return_summaries.get(canonical) if target is None else None
            if (contract is None and target is None and name == 'isinstance'
                    and builtin_status == 'confirmed_builtin' and len(node.args) == 2
                    and not node.keywords and isinstance(node.args[0], ast.Name)
                    and isinstance(node.args[1], ast.Name) and node.args[1].id == 'str'
                    and self.analyzer._builtin_name_status(self.ref, self.node, 'str', env)
                        == 'confirmed_builtin'):
                functions, closed = self.callable_targets(env.get(node.args[0].id, []))
                if (functions and closed and all(not function.decorator_list
                        and '.' not in ref.qualname for ref, function in functions)):
                    contract = {'parameters': ['object', 'classinfo'], 'returns': [],
                        'provenance': 'Closed source function object is not a builtin str'}
                    call.target_status = 'python_protocol'
                    call.implicit_protocol = {'kind': 'source_function_isinstance',
                        'type': 'str', 'result': False, 'evidence': self.evidence(node)}
            if (contract is None and target is None and builtin_status == 'confirmed_builtin'
                    and name in ('str', 'repr', 'bool', 'len', 'list', 'tuple', 'set', 'callable')
                    and canonical == self.ref.module + '.' + name
                    and len(node.args) == 1 and not node.keywords
                    and not isinstance(node.args[0], ast.Starred)):
                contract = {'parameters': ['object'], 'returns': [
                    {'parameter': 'object', 'relation': 'derived'}],
                    'provenance': 'Python builtin result dependency (not owner preservation)'}
                call.target_status = 'python_protocol'
                if name == 'callable':
                    call.implicit_protocol = {'kind': 'builtin_exact_callability',
                        'builtin': 'callable', 'status': 'requires_exact_input',
                        'runtime_input_confirmed': False,
                        'precondition': {'argument': {'position': 0}, 'exact_types': [
                            'NoneType', 'bool', 'int', 'float', 'str', 'bytes',
                            'dict', 'list', 'tuple', 'set', 'frozenset']},
                        'result': False, 'dependency': 'input_object_type_only',
                        'completion': 'normal_return_if_precondition',
                        'effects': 'none_if_precondition', 'call_id': call.id,
                        'source_hash': self.analyzer.hashes[self.ref.file_path],
                        'evidence': self.evidence(node)}
                elif name == 'bool':
                    call.implicit_protocol = {'kind': 'builtin_scalar_truth', 'builtin': 'bool',
                        'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                        'precondition': {'argument': {'position': 0},
                            'exact_types': ['NoneType', 'bool', 'int', 'float', 'str', 'bytes']},
                        'completion': 'normal_return_if_precondition',
                        'effects': 'none_if_precondition', 'call_id': call.id,
                        'source_hash': self.analyzer.hashes[self.ref.file_path],
                        'evidence': self.evidence(node)}
                elif name == 'len':
                    call.implicit_protocol = {'kind': 'builtin_container_length', 'builtin': 'len',
                        'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                        'precondition': {'argument': {'position': 0},
                            'exact_types': ['dict', 'list', 'tuple', 'str', 'bytes',
                                            'set', 'frozenset']},
                        'completion': 'normal_return_if_precondition',
                        'effects': 'none_if_precondition', 'call_id': call.id,
                        'source_hash': self.analyzer.hashes[self.ref.file_path],
                        'evidence': self.evidence(node)}
            if (contract is None and target is None and builtin_status == 'confirmed_builtin' and name == 'next'
                    and canonical == self.ref.module + '.next'
                    and len(node.args) == 1 and not node.keywords
                    and not isinstance(node.args[0], ast.Starred)):
                contract = {'parameters': ['iterator'], 'returns': [
                    {'parameter': 'iterator', 'projection': ['*'], 'relation': 'direct'}],
                    'provenance': 'Python next returns an element produced by its iterator'}
                call.target_status = 'python_protocol'
            if contract and (binding is None or all(v['kind'] == 'import' for v in binding)):
                params = ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in contract['parameters']],
                                       vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
                call.return_dependencies = [
                    {'kind': 'parameter', 'source': d['parameter'], 'relation': d['relation'],
                     'projection': d.get('projection', []),
                     'evidence': [{'provenance': contract['provenance'], 'callable': canonical}], 'conditions': []}
                    for d in contract.get('returns', [])]
            positional = params.posonlyargs + params.args if params else []
            instance_parameter = None
            if bound_receiver and target and positional:
                if dispatch_kind != 'constructor':
                    call.argument_sources.append({
                        'argument': {'receiver': True},
                        'parameter': positional[0].arg,
                        'sources': receiver_sources})
                    if (descriptor_kind is None and not target[1].decorator_list
                            and receiver_sources and all(value.get('instance_type')
                                for value in receiver_sources)):
                        instance_parameter = positional[0].arg
                        call.parameter_bindings.append({'argument': {'receiver': True},
                            'parameter': instance_parameter, 'status': 'exact',
                            'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'})
                positional = positional[1:]
            records = self.bind_call_arguments(node, params, positional, call) if params else [
                {'argument': {'position': i}, 'node': arg.value if isinstance(arg, ast.Starred) else arg,
                 'parameter': None, 'target_path': [], 'status': 'unresolved',
                  'binding_kind': 'dynamic_starred' if isinstance(arg, ast.Starred) else 'explicit',
                  'destination_kind': 'unresolved'}
                for i, arg in enumerate(node.args)] + [
                {'argument': {'keyword': kw.arg}, 'node': kw.value, 'parameter': None,
                  'target_path': [], 'status': 'unresolved', 'binding_kind': 'explicit',
                  'destination_kind': 'unresolved'}
                for kw in node.keywords]
            if not params:
                call.binding_status = 'unavailable'
            invalid_binding = bool(params) and any(
                record['status'] == 'unresolved'
                and record['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
                for record in records)
            invalid_binding = invalid_binding or any(
                record['status'] in ('missing', 'duplicate') for record in records)
            actual_values = {}
            protocol_values = {}
            for record in records:
                slot, arg = record['argument'], record['node']
                parameter, target_path = record['parameter'], record['target_path']
                binding_record = {'argument': slot, 'parameter': parameter,
                                  'status': record['status'],
                                  'destination_kind': record.get('destination_kind', 'unresolved')}
                if target_path:
                    binding_record['target_path'] = target_path
                if record['binding_kind'] != 'explicit':
                    binding_record['binding_kind'] = record['binding_kind']
                call.parameter_bindings.append(binding_record)
                if arg is None:
                    continue
                raw_values = self.expression(arg, env)
                if isinstance(slot, dict) and 'position' in slot:
                    protocol_values[slot['position']] = raw_values
                raw_values = [dict(value, value_incomplete=True)
                    if ((value.get('callable_type') or {}).get('module', value.get('module')),
                        (value.get('callable_type') or {}).get('qualname', value.get('source')))
                        in self.modified_return_callables else value for value in raw_values]
                actual_values[parameter] = _unique(actual_values.get(parameter, []) + raw_values)
                values = self.marked(self.materialize(raw_values, env), arg)
                argument_record = {'argument': slot, 'parameter': parameter, 'sources': values}
                container = self.exact_container(raw_values, ('dict', 'list', 'tuple'), env)
                if container is not None and not target_path and not any(
                        isinstance(child, ast.Call) for argument in node.args
                        + [keyword.value for keyword in node.keywords] for child in ast.walk(argument)):
                    argument_record['container_binding'] = {'status': 'exact',
                        'shape': container['container_shape'],
                        'source': container['source'],
                        'contents_unknown': bool(env.get(container['source'] + '$state')),
                        'evidence': [self.evidence(arg)], 'conditions': copy.deepcopy(self.conditions)}
                elif raw_values and not target_path and all(
                        value.get('kind') == 'parameter' and value.get('relation') == 'direct'
                        and value.get('container_binding', {}).get('status') == 'exact'
                        and not any(value.get(flag) for flag in ('projection', 'output_path', 'value_incomplete'))
                        for value in raw_values):
                    incoming_bindings = [value['container_binding'] for value in raw_values]
                    if all(value == incoming_bindings[0] for value in incoming_bindings):
                        forwarded = copy.deepcopy(incoming_bindings[0])
                        aliases = {name for name, facts in self.incoming.items() if any(
                            fact.get('container_binding', {}).get('source') == forwarded['source']
                            for fact in facts)}
                        if any(value.get('source') in aliases for previous in self.calls
                                for value in previous.receiver_sources + [value for item in previous.argument_sources
                                    for value in item.get('sources', [])]):
                            forwarded['contents_unknown'] = True
                        argument_record['container_binding'] = forwarded
                literal = self.literal_fact(arg, env)
                if literal is not None:
                    argument_record.update(literal=literal, value_evidence=[self.evidence(arg)])
                if target_path:
                    argument_record['target_path'] = target_path
                call.argument_sources.append(argument_record)
                for value in values:
                    call.argument_flows.append(dict(value, target_parameter=parameter,
                                                    target_path=target_path, argument=slot,
                                                    status='flow_found'))
                    if value['kind'] == 'parameter':
                        call.parameter_flows.append(dict(value, source_parameter=value['source'],
                                                         target_parameter=parameter,
                                                         target_path=target_path,
                                                         argument=slot, status='flow_found'))
            fresh_super = (call.instance_method_bindings[0]
                if len(call.instance_method_bindings) == 1
                and call.instance_method_bindings[0].get('kind') == 'fresh_source_super_method'
                and call.instance_method_bindings[0].get('status') == 'source_bound'
                else None)
            receiver_parameters = (target[1].args.posonlyargs + target[1].args.args
                if target is not None else [])
            if (fresh_super is not None and receiver_parameters
                    and fresh_super.get('call_id') == call.id
                    and fresh_super.get('target') == asdict(target[0])
                    and call.receiver_sources and all(
                        value.get('fresh_receiver_origin') == fresh_super.get('origin')
                        and value.get('relation') == 'direct'
                        and value.get('source') == fresh_super.get('origin', {}).get('parameter')
                        and not any(value.get(flag) for flag in (
                            'projection', 'output_path', 'attribute_provenance',
                            'import_modified', 'import_incomplete', 'value_incomplete'))
                        for value in call.receiver_sources)
                    and not any(binding.get('argument') == {'receiver': True}
                        and binding.get('parameter') == receiver_parameters[0].arg
                        for binding in call.parameter_bindings)):
                call.parameter_bindings.append({'argument': {'receiver': True},
                    'parameter': receiver_parameters[0].arg, 'status': 'exact',
                    'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter',
                    'basis': 'source_bound_super_method_wrapper'})
            if literal_join:
                call.target_status = 'python_protocol'
                call.argument_sources[0]['parameter'] = 'iterable'
                call.parameter_bindings[0].update(parameter='iterable', status='exact')
                for value in call.argument_flows + call.parameter_flows:
                    value['target_parameter'] = 'iterable'
                call.return_dependencies = [{'kind': 'parameter', 'source': 'iterable', 'projection': ['*'],
                    'relation': 'derived', 'evidence': [{'provenance': 'Python str.join iterable elements'}],
                    'conditions': list(self.conditions)}]
            if params:
                supplied = {b['parameter'] for b in call.parameter_bindings if b['status'] == 'exact'}
                defaults = list(zip(positional[len(positional) - len(params.defaults):], params.defaults))
                defaults += [(a, d) for a, d in zip(params.kwonlyargs, params.kw_defaults) if d is not None]
                for param, default in defaults:
                    unknown_keywords = any(keyword.arg is None and not isinstance(keyword.value, ast.Dict)
                                           for keyword in node.keywords)
                    unknown_positions = any(isinstance(argument, ast.Starred)
                                            and not isinstance(argument.value, (ast.Tuple, ast.List))
                                            for argument in node.args)
                    possibly_expanded = unknown_keywords or (unknown_positions and param in positional)
                    if param.arg not in supplied and not possibly_expanded:
                        call.parameter_bindings.append({'argument': None, 'parameter': param.arg,
                                                        'binding_kind': 'default', 'status': 'exact',
                                                        'source_text': ast.unparse(default)})
                        if binding and all(v['kind'] == 'callable' for v in binding):
                            call.argument_sources.append({'argument': None, 'parameter': param.arg,
                                'sources': _unique([v for b in binding for v in b.get('defaults', {}).get(param.arg, [])])})
            if (constructor_class is not None and target
                    and call.target_status == 'constructor'):
                fact = constructor_source_binding(self, node, constructor_class, target,
                    constructor_values, self.class_origin_invalid(asdict(constructor_class), env)
                    or self.class_lookup_affected([{'class_lookup_mutations':
                        self.class_lookup_effects(asdict(constructor_class), env)}],
                        ('__new__', '__init__', '__class__', '__bases__')))
                call.constructor_bindings = [fact]
                if fact['status'] == 'source_bound':
                    parameter = fact['implicit_binding']['parameter']
                    slot = copy.deepcopy(fact['implicit_binding']['argument'])
                    sources = ([{'kind': 'constructor_instance', 'source': call.id,
                        'instance_type': asdict(constructor_class), 'relation': 'direct',
                        'evidence': [self.evidence(node)],
                        'conditions': copy.deepcopy(self.conditions)}]
                        if fact['phase'] == '__init__' else copy.deepcopy(constructor_values))
                    if fact['phase'] == '__new__':
                        for value in sources:
                            value.setdefault('source_class_origin', {
                                'basis': 'source_symbol', 'class': asdict(constructor_class),
                                'evidence': copy.deepcopy(value.get('evidence', [])), 'call_context': []})
                    call.argument_sources.insert(0, {'argument': slot, 'parameter': parameter,
                                                    'sources': sources})
                    call.parameter_bindings.insert(0, {'argument': slot, 'parameter': parameter,
                        'status': 'exact', 'binding_kind': 'implicit_receiver',
                        'destination_kind': 'parameter'})
                    if self.implicit_keyword_conflict(call, parameter, slot,
                            {arg.arg for arg in target[1].args.posonlyargs}):
                        invalid_binding = True
                    actual_values[parameter] = sources
                    for value in sources:
                        call.argument_flows.append(dict(value, target_parameter=parameter,
                            argument=slot, status='flow_found'))
                    self.result.boundaries.append({'call_id': call.id,
                        'reason': 'source_constructor_' + fact['phase'].strip('_') + '_binding',
                        'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                        'execution_scope': fact['execution_scope'],
                        'assumptions': copy.deepcopy(fact['assumptions']),
                        'evidence': self.evidence(node)})
                else:
                    self.result.boundaries.append({'call_id': call.id,
                        'reason': 'constructor_binding_unconfirmed',
                        'issues': copy.deepcopy(fact['issues']), 'evidence': self.evidence(node)})
                    conditional = conditional_constructor_signature(self, node, fact, call.id)
                    if conditional is not None and call.binding_status != 'invalid':
                        conditional.update(call_id=call.id, call_evidence=self.evidence(node))
                        call.conditional_source_bindings = [conditional]
                        call.conditions = copy.deepcopy(conditional['conditions'])
                        self.result.boundaries.append({'call_id': call.id,
                            'reason': 'conditional_constructor_signature',
                            'boundary_kind': 'required_condition',
                            'condition': copy.deepcopy(conditional['conditions'][-1])})
            if instance_parameter is not None:
                if self.implicit_keyword_conflict(call, instance_parameter, {'receiver': True},
                        {arg.arg for arg in target[1].args.posonlyargs}):
                    invalid_binding = True
                invalid_receivers = {(value.get('source'), repr(value.get('instance_type')))
                    for values in env.values() for value in values
                    if value.get('instance_type') and value.get('value_incomplete')}
                for argument in call.argument_sources:
                    if argument.get('argument') == {'receiver': True}:
                        argument['sources'] = [dict(value, value_incomplete=True)
                            if (value.get('source'), repr(value.get('instance_type')))
                                in invalid_receivers else value for value in argument['sources']]
                        actual_values[instance_parameter] = argument['sources']
            if (descriptor_kind == 'classmethod' and target and any(
                    fact.get('status') == 'source_bound' for fact in call.class_method_bindings)):
                parameters = target[1].args.posonlyargs + target[1].args.args
                if parameters and self.implicit_keyword_conflict(call, parameters[0].arg,
                        {'receiver': True}, {arg.arg for arg in target[1].args.posonlyargs}):
                    invalid_binding = True
            for argument in call.argument_sources:
                updated = []
                for value in argument.get('sources', []):
                    if value.get('class_type'):
                        mutations = self.class_lookup_effects(value['class_type'], env)
                        if mutations:
                            value = dict(value, class_lookup_mutations=_unique(
                                value.get('class_lookup_mutations', []) + copy.deepcopy(mutations)))
                        if self.class_origin_invalid(value['class_type'], env):
                            value = dict(value, value_incomplete=True)
                    updated.append(value)
                argument['sources'] = updated
            effects_complete = False
            if target:
                # Closure cells are read at invocation, after all argument expressions.
                for capture in self.analyzer._captures(*target):
                    capture_values[capture] = copy.deepcopy(env.get(capture, []))
                    record = {'capture': capture, 'sources': capture_values[capture],
                        'current_sources': copy.deepcopy(self.materialize(capture_values[capture], env))}
                    container = self.exact_container(capture_values[capture], ('dict', 'list', 'tuple'), env)
                    if container is not None:
                        record['container_binding'] = {'status': 'exact',
                            'shape': container['container_shape'], 'source': container['source'],
                            'contents_unknown': bool(env.get(container['source'] + '$state')),
                            'evidence': [self.evidence(node)], 'conditions': copy.deepcopy(self.conditions)}
                    call.capture_bindings.append(record)
            selected_target = (self.analyzer._selected_definition(target,
                self.analyzer._incoming_facts(target, call)) if target else None)
            if target:
                call.conditional_returns = self.analyzer._guarded_object_returns(target)
                for fact in call.conditional_returns:
                    values = self.container_values(actual_values.get(fact['parameter'], []))
                    if (call.binding_status == 'complete' and values and all(
                            value.get('kind') == 'container'
                            and value.get('container_shape') in ('dict', 'list', 'tuple')
                            and value.get('relation') == 'direct' and not value.get('value_incomplete')
                            and not value.get('projection') and not value.get('output_path')
                            and value['source'] in env for value in values)
                            and len({value['source'] for value in values}) == 1):
                        fact.update(container_shape=values[0]['container_shape'],
                            object_source=values[0]['source'],
                            binding=copy.deepcopy(next(binding for binding in call.parameter_bindings
                                if binding.get('parameter') == fact['parameter'])),
                            input_evidence=_unique([evidence for value in values
                                for evidence in value.get('evidence', [])]))
            self.invalidate_attributes(env)
            if target and not invalid_binding and not getattr(node, '_flow_skip_effects', False):
                effects_complete = self.apply_effects(
                    selected_target, actual_values, capture_values, call, env, node)
                scope = self.analyzer._scope_facts(selected_target[1])
                unmodeled = (scope.nonlocals & scope.bound) - {
                    effect['target'] for effect in call.effects
                    if effect.get('kind') == 'nonlocal_write' and effect.get('status') == 'exact'}
                if unmodeled:
                    affected = [value for name in unmodeled for value in capture_values.get(name, [])]
                    self.add_boundary('capture_binding_write_unmodeled', node, env, affected,
                                      call_id=call.id)
                    for name in unmodeled:
                        self.unknown_container_contents(capture_values.get(name, []), env)
                        env[name] = [dict(value, value_incomplete=True)
                                     for value in env.get(name, [])]
                    effects_complete = False
            container_result = self.container_call(node, receiver_values, call, env, protocol_values)
            if container_result is None and isinstance(node.func, ast.Attribute) and node.func.attr == 'copy':
                incoming_receiver = self.incoming_copy_receiver(node, receiver_values, call, env)
                if incoming_receiver is not None:
                    container_result = self.container_call(node, incoming_receiver, call, env, protocol_values)
            if target is None and container_result is None:
                self.inherited_setdefault(node, receiver_values, call, env)
            if target is None and container_result is None and isinstance(node.func, ast.Name):
                container_result = self.container_constructor(node, call, env, protocol_values)
            if (target is None and not bounded_targets
                    and call.target_status not in ('python_protocol', 'local_container_protocol',
                                                  'builtin_allocation')):
                for values in actual_values.values():
                    self.invalidate_literals(values, env)
                    candidates, _ = self.callable_targets(values)
                    self.modified_return_callables.update(
                        (candidate[0].module, candidate[0].qualname) for candidate in candidates)
                    for reference in self.container_values(values):
                        if reference.get('kind') == 'container':
                            source = reference['source']
                            env[source] = [dict(value, value_incomplete=True)
                                if value.get('kind') == 'callable' or value.get('callable_type')
                                else value for value in env.get(source, [])]
                    self.unknown_container_contents(values, env)
                self.unknown_container_contents(receiver_values, env)
            source_super = (name == 'super' and builtin_status == 'confirmed_builtin'
                and len(node.args) == 2 and not node.keywords
                and not any(isinstance(argument, ast.Starred) for argument in node.args)
                and all(known and not any(value.get('value_incomplete') for value in known)
                        for known in (self.class_values(values, env=env)
                                      for values in actual_values.values())))
            preserved_classes = (self.class_attribute_effect(
                selected_target, call, capture_values, env, node)
                if selected_target and not invalid_binding
                and not getattr(node, '_flow_skip_effects', False) else [])
            if not effects_complete and not source_super and call.target_status not in (
                    'python_protocol', 'local_container_protocol', 'builtin_allocation'):
                self.invalidate_instance_receivers(
                    [value for values in actual_values.values() for value in values]
                    + receiver_values
                    + [value for values in capture_values.values() for value in values], env)
                self.invalidate_class_origins(
                    [value for value in [value for values in actual_values.values() for value in values]
                    + receiver_values
                    + [value for values in capture_values.values() for value in values]
                     if value.get('class_type') not in preserved_classes], env, call)
            self.calls.append(call)
            if invalid_binding:
                return []
            if (getattr(self.analyzer, '_conditional_source_state', False) and call.target is not None
                    and call.target_status in ('super_new', 'super_method', 'classmethod')):
                required = [condition for condition in call.conditions
                            if condition.get('kind') == 'source_state_preserved']
                if required:
                    call.conditional_source_bindings = [{'kind': 'conditional_source_lookup',
                        'status': 'required', 'target': asdict(call.target), 'call_id': call.id,
                        'call_evidence': self.evidence(node), 'conditions': copy.deepcopy(call.conditions),
                        'receiver_classes': _unique([value['class_type'] for value in receiver_sources
                            if value.get('class_type')]), 'runtime_target_confirmed': False,
                        'source_hashes': dict(self.analyzer.hashes), 'feasibility': 'not_proven'}]
            if container_result is not None:
                return container_result
            result_value = {'kind': 'call_result', 'source': call_id,
                            'relation': 'direct',
                            'evidence': [self.evidence(node)],
                            'conditions': list(self.conditions)}
            if any(effect.get('kind') == 'mapping_remainder' and effect.get('return_path')
                   for effect in call.effects):
                return call.result_sources
            returned_object = self.returned_container(
                selected_target, call, actual_values, env, node, effects_complete)
            if returned_object is not None:
                result_value['container_object'] = returned_object
                result_value['object_only'] = True
                result_value['conditions'] = _unique(result_value['conditions'] +
                    returned_object.get('conditions', []))
                result_value['evidence'] = _unique(result_value['evidence'] +
                    returned_object.pop('evidence'))
                call.result_sources = [result_value]
                return [result_value]
            if effects_complete and call.result_sources:
                return [result_value] + call.result_sources
            if constructor_class is not None and construction_safe:
                result_value['instance_type'] = asdict(constructor_class)
                mutations = self.class_lookup_effects(asdict(constructor_class), env)
                if mutations:
                    result_value['class_lookup_mutations'] = copy.deepcopy(mutations)
                result_value['evidence'] = _unique(result_value['evidence'] + [
                    evidence for value in callee_classes
                    for evidence in value.get('evidence', [])])
                call.result_sources = [result_value]
            elif allocation_class is not None:
                result_value['instance_type'] = asdict(allocation_class)
                result_value['evidence'] = _unique(result_value['evidence'] + [
                    evidence for value in allocation_values
                    for evidence in value.get('evidence', [])])
                call.result_sources = [result_value]
                result_value['attribute_provenance'] = _unique([
                    fact for value in allocation_values for fact in value.get('attribute_provenance', [])])
                result_value['conditions'] = _unique(result_value['conditions'] + [
                    condition for value in allocation_values for condition in value.get('conditions', [])])
            elif allocation_candidates:
                result_value.update(instance_candidates=_unique([
                    value['class_type'] for value in allocation_candidates]),
                    value_incomplete=any(value.get('value_incomplete') for value in allocation_candidates),
                    attribute_provenance=_unique([fact for value in allocation_candidates
                        for fact in value.get('attribute_provenance', [])]),
                    conditions=_unique(result_value['conditions'] + [condition
                        for value in allocation_candidates for condition in value.get('conditions', [])]),
                    evidence=_unique(result_value['evidence'] + [evidence
                        for value in allocation_candidates for evidence in value.get('evidence', [])]))
                call.result_sources = [result_value]
                if getattr(self.analyzer, '_conditional_source_state', False):
                    result_value['instance_candidate_contexts'] = [
                        {'instance_type': copy.deepcopy(value['class_type']),
                         'conditions': copy.deepcopy(value.get('conditions', []))}
                        for value in allocation_candidates]
            elif (target and dispatch_kind == 'instance_method'
                  and isinstance(node.func, ast.Attribute)
                  and isinstance(node.func.value, ast.Name)
                  and call.binding_status == 'complete'):
                field_types = self.analyzer._returned_field_instances(target)
                if field_types:
                    values = []
                    for item in field_types:
                        fact = {'field': item['field'],
                                'instance_type': item['instance_type'],
                                'assignment': self.evidence_at(
                                    item['assignment_ref'], item['assignment_node']),
                                'returns': [self.evidence_at(item['return_ref'], path)
                                            for path in item['return_nodes']],
                                'accessor_call': self.evidence(node)}
                        call.receiver_type_evidence.append(fact)
                        values.append(dict(result_value,
                            instance_type=item['instance_type'],
                            receiver_type_evidence=[fact],
                            evidence=result_value['evidence'] +
                                     [fact['assignment']] + fact['returns']))
                    return values
            return [result_value]
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_expression', 'evidence': self.evidence(node)})
            return []
        values = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                values.extend(self.materialize(self.expression(child, env), env))
        relation = 'contained' if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) else 'derived'
        return self.marked(values, node, relation)

    ## Convert proven container endpoints into their tracked object references.
    ## 将已证明的容器端点转换为被跟踪的对象引用。
    #
    #  @param values Source records.
    #  @param allow_contained Permit endpoints within an output path.
    #  @return Converted records, preserving uncertain values.
    def container_values(self, values, allow_contained=False):
        converted = []
        for value in values:
            obj = value.get('container_object')
            if (obj and value.get('relation') == 'direct'
                    and not value.get('projection')
                    and (allow_contained or not value.get('output_path'))
                    and not value.get('value_incomplete')):
                converted.append(dict(value, kind='container', source=obj['source'],
                    container_shape=obj['container_shape'],
                    parameter_container=obj.get('parameter_container')))
            else:
                converted.append(value)
        return converted

    ## Preserve only the builtin copy protocol of an exact incoming dict.
    ## 仅为精确传入字典保留内置复制协议。
    #
    #  @param node Copy call expression, with no arguments.
    #  @param values Receiver roots, retaining generic return/alias facts.
    #  @param call Current source call.
    #  @param env Current lexical frame.
    #  @return Symbolic copy receiver or None after any unproved prior use.
    def incoming_copy_receiver(self, node, values, call, env):
        if node.args or node.keywords or not values or not all(
                value.get('kind') == 'parameter' and value.get('relation') == 'direct'
                and not any(value.get(flag) for flag in ('projection', 'output_path', 'value_incomplete'))
                for value in values):
            return None
        bindings = [self.incoming.get(value['source'], []) for value in values]
        if not all(len(items) == 1 and items[0].get('container_shape') == 'dict'
                and items[0].get('container_binding', {}).get('status') == 'exact'
                and not items[0]['container_binding'].get('contents_unknown') for items in bindings):
            return None
        origins = {items[0]['container_binding']['source'] for items in bindings}
        aliases = {name for name, facts in self.incoming.items() if any(
            fact.get('container_binding', {}).get('source') in origins for fact in facts)}
        if any(value.get('source') in aliases for previous in self.calls
                for value in previous.receiver_sources + [value for argument in previous.argument_sources
                    for value in argument.get('sources', [])]):
            return None
        if any(boundary.get('affected_scope') == 'unknown' or any(
                value.get('name', value.get('source')) in aliases
                for value in boundary.get('affected_values', [])) for boundary in self.result.boundaries
                if boundary.get('function') == asdict(self.ref)):
            return None
        heap = '$incoming_copy:' + call.id
        env[heap] = [dict(value, relation='contained', output_path=['*']) for value in values]
        env[heap + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
        return [{'kind': 'container', 'source': heap, 'container_shape': 'dict',
                 'relation': 'direct', 'evidence': [self.evidence(node.func.value)], 'conditions': []}]

    ## Resolve a returned container identity from complete source evidence.
    ## 根据完整源码证据解析返回容器的身份。
    #
    #  @param target Optional source callee definition.
    #  @param call Current flow call.
    #  @param actuals Argument source records.
    #  @param env Current abstract environment.
    #  @param node Call-site AST node.
    #  @param effects_complete Whether required callee effects were fully modeled.
    #  @return Object identity record or None with an appropriate boundary.
    def returned_container(self, target, call, actuals, env, node, effects_complete=False):
        references = [value for values in actuals.values()
                      for value in self.container_values(values)
                      if value.get('kind') == 'container']
        if target is None or not references:
            return None
        remainder = next((effect for effect in call.effects
                          if effect.get('kind') == 'mapping_remainder'
                          and effect.get('return_path') == []), None)
        if remainder is not None:
            return copy.deepcopy(remainder['return_object'])
        fact, cause = self.analyzer._object_returns(target)
        if (target[0].module, target[0].qualname) in self.modified_return_callables:
            fact, cause = None, 'modified_return_callable'
        values = self.container_values(actuals.get(fact['parameter'], [])) if fact else []
        if fact and call.binding_status != 'complete':
            cause = 'uncertain_object_binding'
        elif fact and fact.get('effects') and not effects_complete:
            cause = 'unmodeled_helper_effects'
        elif fact and not (values and all(
                value.get('kind') == 'container' and value.get('relation') == 'direct'
                and not value.get('value_incomplete') and not value.get('projection')
                and not value.get('output_path') and value['source'] in env
                and value.get('container_shape') in ('dict', 'list', 'tuple')
                for value in values) and len({value['source'] for value in values}) == 1):
            cause = 'unproven_input_object'
        if cause:
            affected = [value for inputs in actuals.values() for value in inputs]
            self.add_boundary('container_return_unproven', node, env, affected,
                              call_id=call.id, detail=cause)
            if cause == 'container_return_budget':
                self.result.boundaries.append({'call_id': call.id, 'reason': cause})
            return None
        obj = values[0]
        return {'source': obj['source'], 'container_shape': obj['container_shape'],
                'parameter_container': obj.get('parameter_container'),
                'identity': 'argument_alias', 'parameter': fact['parameter'],
                'function': asdict(target[0]),
                'conditions': copy.deepcopy(fact.get('conditions', [])),
                'evidence': _unique([item for value in values
                                    for item in value.get('evidence', [])] +
                    [self.evidence_at(target[0], statement) for statement in fact['evidence']])}

    ## Expand tracked container contents into dependency records.
    ## 将被跟踪容器内容展开为依赖记录。
    #
    #  @param values Source records to expand.
    #  @param env Current abstract environment.
    #  @param visited Container identities already expanded on this path.
    #  @return Materialized dependency records.
    def materialize(self, values, env, visited=()):
        result = []
        for value in values:
            if value.get('container_object'):
                converted = self.container_values([value], allow_contained=True)[0]
                if converted['kind'] == 'container':
                    result.append(value)
                    value = converted
            if value['kind'] != 'container':
                result.append(value)
                continue
            # Stop object cycles without claiming their missing contents are empty.
            # 遇到对象环时停止展开，不据此断言缺失内容为空。
            if value['source'] in visited:
                continue
            for item in self.materialize(env.get(value['source'], []), env, visited + (value['source'],)):
                prefix = value.get('output_path', [])
                materialized = dict(item, relation='contained',
                    output_path=prefix + item.get('output_path', []),
                    evidence=item['evidence'] + value['evidence'])
                if item.get('excluded_paths'):
                    materialized['excluded_paths'] = [prefix + path
                                                      for path in item['excluded_paths']]
                result.append(materialized)
        return result

    ## Project value dependencies through a container element path.
    ## 通过容器元素路径投影值依赖。
    #
    #  @param values Container or dependency records.
    #  @param index Element index, key, or wildcard.
    #  @param env Current abstract environment.
    #  @return Projected dependency records.
    def project(self, values, index, env):
        result = []
        for value in self.container_values(values):
            if value['kind'] == 'container':
                if (value['source'].startswith('$remainder_tuple:')
                        and (type(index) is not int or index < 0)):
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'container_projection_unproven',
                        'object_source': value['source']})
                    continue
                content = [item for item in env.get(value['source'], [])
                           if item.get('container_role') != 'key']
                if value.get('parameter_container') and index != '*':
                    for item in content:
                        if item.get('output_path') == ['*']:
                            if [index] in item.get('excluded_paths', []):
                                continue
                            projected = dict(
                                item, projection=item.get('projection', []) + [index])
                            projected.pop('output_path', None)
                            result.append(projected)
                        else:
                            result.extend(select_dependencies([item], [index]))
                else:
                    result.extend(select_dependencies(content, [index]))
            else:
                result.extend(select_dependencies([value], [index]))
        return result

    ## Widen tracked container contents and key presence after an unknown effect.
    ## 未知效果后扩大被跟踪容器内容和键存在性的可能范围。
    #
    #  @param values Potentially affected container records.
    #  @param env Mutable abstract environment.
    #  @return None
    def unknown_container_contents(self, values, env):
        for reference in self.container_values(values):
            if reference.get('kind') != 'container' or reference['source'] not in env:
                continue
            source = reference['source']
            env[source + '$state'] = [{'kind': 'container_state', 'source': source,
                                       'contents_unknown': True}]
            env[source] = [dict(value, excluded_paths=[]) if value.get('excluded_paths') else value
                           for value in env[source]]
            env[source + '$keys'] = _unique([
                dict(marker, excluded_keys=[], presence_unconfirmed=True)
                for marker in env.get(source + '$keys', [])] +
                [{'kind': 'key', 'source': '*', 'key': '*'}])

    ## Select one direct tracked container only when every candidate agrees.
    ## 仅当所有候选一致时选择唯一的直接跟踪容器。
    #
    #  @param values Candidate source records.
    #  @param shapes Allowed container shapes.
    #  @param env Current abstract environment.
    #  @return Container reference or None when identity or shape is uncertain.
    def exact_container(self, values, shapes, env):
        references = self.container_values(values)
        if (not references or not all(value.get('kind') == 'container'
                and value.get('container_shape') in shapes
                and value.get('relation') == 'direct' and not value.get('value_incomplete')
                and not value.get('projection') and not value.get('output_path')
                and value['source'] in env for value in references)
                or len({value['source'] for value in references}) != 1):
            return None
        return references[0]

    ## Build an object-only call result with optional container identity.
    ## 构建仅表示对象的调用结果，可附带容器身份。
    #
    #  @param call Current flow call.
    #  @param node Call-site AST node.
    #  @param obj Optional tracked container identity.
    #  @return Call-result source record.
    def container_endpoint(self, call, node, obj=None):
        value = {'kind': 'call_result', 'source': call.id, 'relation': 'direct',
                 'object_only': True, 'evidence': [self.evidence(node)],
                 'conditions': copy.deepcopy(self.conditions)}
        if obj is not None:
            value['container_object'] = obj
        return value

    ## Model a proven shallow container copy or tuple identity reuse.
    ## 建模已证明的容器浅复制或元组身份复用。
    #
    #  @param values Input container source records.
    #  @param shape Requested output shape.
    #  @param node Call-site AST node.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @return Result records or None when the copy is unproven.
    def copy_container(self, values, shape, node, call, env):
        allowed = ('dict',) if shape == 'dict' else ('list', 'tuple')
        reference = self.exact_container(values, allowed, env)
        if (reference is None or any(marker.get('contents_unknown')
                for marker in env.get(reference['source'] + '$state', []))):
            self.add_boundary('container_copy_unproven', node, env, values,
                              call_id=call.id, detail='unproven_input_shape_identity_or_contents')
            return None
        source = reference['source']
        alias = shape == reference['container_shape'] == 'tuple'
        output = source if alias else '$copy:' + call.id
        if not alias:
            env[output] = copy.deepcopy(env.get(source, []))
            env[output + '$keys'] = copy.deepcopy(env.get(source + '$keys', []))
            env.pop(output + '$state', None)
        obj = {'source': output, 'container_shape': shape,
               'parameter_container': reference.get('parameter_container'),
               'identity': 'argument_alias' if alias else 'shallow_copy',
               'copied_from': source}
        result = self.container_endpoint(call, node, obj)
        result['evidence'] = _unique(reference['evidence'] + result['evidence'])
        call.result_sources = [result]
        # Contents are read through the object at each use, never through a stale
        # whole-input dependency. Nested container IDs remain shallow aliases.
        # 每次使用时读取当前容器内容；嵌套容器身份仍为浅层别名。
        call.return_dependencies = []
        roots, unknown = self.affected_values(values, env)
        effect = {'kind': 'container_copy', 'operation': 'copy',
                  'input_container': source, 'output_container': output,
                  'container_shape': shape, 'identity': obj['identity'],
                  'mapping': roots, 'status': 'unknown_source' if unknown else 'bounded',
                  'completion': 'normal_return',
                  'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)}
        call.effects.append(effect)
        if shape == 'dict':
            self.mapping_effects.append(effect)
        return [result]

    ## Model a supported builtin container constructor from one exact input.
    ## 根据一个精确输入建模受支持的内置容器构造器。
    #
    #  @param node Constructor call AST.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @param actuals Argument sources by position.
    #  @return Result records or None when the constructor is unproven.
    def container_constructor(self, node, call, env, actuals):
        name = node.func.id
        if (name not in ('dict', 'list', 'tuple')
                or self.analyzer._builtin_name_status(self.ref, self.node, name, env) != 'confirmed_builtin'
                or len(node.args) != 1 or node.keywords or isinstance(node.args[0], ast.Starred)):
            return None
        values = actuals.get(0, [])
        result = self.copy_container(values, name, node, call, env)
        if result is None:
            return None
        call.target_status = 'local_container_protocol'
        call.binding_status = 'complete'
        for binding in call.parameter_bindings:
            binding.update(parameter='object', status='exact', destination_kind='parameter')
        for argument in call.argument_sources:
            argument['parameter'] = 'object'
        for flow in call.argument_flows + call.parameter_flows:
            flow['target_parameter'] = 'object'
        return result

    ## Classify a tracked mapping key as present, absent or unknown.
    ## 将被跟踪映射键分类为存在、缺失或未知。
    #
    #  @param reference Tracked mapping reference.
    #  @param key Key or wildcard.
    #  @param env Current abstract environment.
    #  @return Key presence status string.
    def mapping_key_state(self, reference, key, env):
        if key == '*' or any(marker.get('contents_unknown')
                for marker in env.get(reference['source'] + '$state', [])):
            return 'unknown'
        markers = env.get(reference['source'] + '$keys', [])
        if any(marker['key'] == key and not marker.get('presence_unconfirmed') for marker in markers):
            return 'present'
        if any(marker['key'] == key or marker['key'] == '*'
               and key not in marker.get('excluded_keys', []) for marker in markers):
            return 'unknown'
        return 'absent'

    ## Model dict.setdefault for an exact receiver and bounded literal key.
    ## 为精确接收者和有界字面量键建模 dict.setdefault。
    #
    #  @param node Call AST node.
    #  @param receiver Receiver source records.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @param actuals Argument source records by position.
    #  @return Result records or None when the effect is unproven.
    def mapping_setdefault(self, node, receiver, call, env, actuals):
        reference = self.exact_container(receiver, ('dict',), env)
        literal = self.literal_fact(node.args[0], env)
        key = (literal['value'] if literal and literal['type'] in ('str', 'int')
               and literal['value'] != '*' else '*')
        if reference is None or key == '*':
            self.add_boundary('container_effect_unknown', node, env, receiver,
                              call_id=call.id, detail='setdefault_key_or_receiver_unproven')
            self.unknown_container_contents(receiver, env)
            return None
        source = reference['source']
        roots, unknown = self.mapping_affected_values(receiver, env)
        state = self.mapping_key_state(reference, key, env)
        call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                      'sources': copy.deepcopy(self.materialize(receiver, env))})
        existing = self.project(receiver, key, env)
        default = actuals.get(1, [])
        previous, inserted = [], []
        present = {'mapping_membership': {'object_source': source, 'element_path': [key],
                                          'state': 'present'}, 'evidence': self.evidence(node)}
        absent = {'mapping_membership': {'object_source': source, 'element_path': [key],
                                         'state': 'absent'}, 'evidence': self.evidence(node)}
        if state != 'absent':
            previous = self.marked(existing, node)
            if state == 'unknown':
                previous = [dict(value, conditions=value.get('conditions', []) + [present])
                            for value in previous]
        if state != 'present':
            inserted = self.marked(default, node)
            if state == 'unknown':
                inserted = [dict(value, conditions=value.get('conditions', []) + [absent])
                            for value in inserted]
            # Separate this slot from the open remainder, retaining both guarded
            # existing/default alternatives instead of overriding an unknown key.
            # 将该槽位与开放余项分开，保留受条件约束的已有值和默认值候选。
            remainder = []
            for value in env.get(source, []):
                path = value.get('output_path', [])
                if path and path[0] == key:
                    continue
                if path and path[0] == '*':
                    value = dict(value, excluded_paths=_unique(value.get('excluded_paths', []) + [[key]]))
                remainder.append(value)
            slot = previous + inserted
            env[source] = remainder + [dict(value, output_path=[key] + value.get('output_path', []))
                                       for value in slot]
            markers = []
            for marker in env.get(source + '$keys', []):
                if marker['key'] == key:
                    continue
                if marker['key'] == '*':
                    marker = dict(marker, excluded_keys=_unique(marker.get('excluded_keys', []) + [key]))
                markers.append(marker)
            env[source + '$keys'] = markers + [{'kind': 'key', 'source': repr(key), 'key': key}]
            call.mutation_flows.extend(dict(value, target_container=source,
                effect_summary='mapping_setdefault') for value in self.materialize([
                    dict(value, output_path=[key] + value.get('output_path', [])) for value in inserted], env))
        effect = {'kind': 'mapping_element', 'operation': 'setdefault', 'mapping': roots,
                  'object_source': source, 'element_path': [key], 'state_before': state,
                  'state_after': 'conditional' if self.conditions else 'present',
                  'insertion': 'never' if state == 'present' else 'always' if state == 'absent' else 'conditional',
                  'status': 'bounded', 'completion': 'normal_return',
                  'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)}
        self.mapping_effects.append(effect)
        call.effects.append(effect)
        selected = previous + inserted
        obj = self.exact_container(selected, ('dict', 'list', 'tuple', 'set'), env)
        endpoint = self.container_endpoint(call, node,
            {'source': obj['source'], 'container_shape': obj['container_shape'],
             'parameter_container': obj.get('parameter_container'), 'identity': 'element_alias'} if obj else None)
        endpoint['evidence'] = _unique(endpoint['evidence'] + [span for value in selected
                                                              for span in value.get('evidence', [])])
        call.return_dependencies = []
        call.result_sources = [endpoint] if obj else [endpoint] + selected
        return call.result_sources

    ## Model an inherited dict.setdefault binding under source-class premises.
    ## 在源码类前提下建模继承的 dict.setdefault 绑定。
    #
    #  @param node Call AST node.
    #  @param receiver Receiver source records.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @return Modeled result or None when the binding is unproven.
    def inherited_setdefault(self, node, receiver, call, env):
        if (not isinstance(node.func, ast.Attribute) or node.func.attr != 'setdefault'
                or node.keywords or any(isinstance(item, ast.Starred) for item in node.args)
                or getattr(self.node, 'decorator_list', [])):
            return
        contract = container_method_effect(node.func.attr, ('dict',), len(node.args))
        parameters = self.node.args.posonlyargs + self.node.args.args
        if (contract is None or not parameters or not receiver or not all(
                value['kind'] == 'parameter' and value['source'] == parameters[0].arg
                and value.get('relation') == 'direct' and not value.get('projection')
                and not value.get('output_path') for value in receiver)):
            return
        owner = self.ref.qualname.rpartition('.')[0]
        matches = self.analyzer._definition_index.find(self.ref.module, owner, kind='class')
        proof = self.analyzer._dict_method_binding(matches[0][0], 'setdefault') if len(matches) == 1 else None
        if proof is None:
            return
        if proof['status'] != 'source_bound':
            self.add_boundary(proof['reason'], node, env, receiver, call_id=call.id)
            return
        proof = dict(proof)
        proof['evidence'] = [self.evidence_at(ref, cls) for ref, cls in proof.pop('hierarchy')]
        proof['evidence'].append(self.evidence(node))
        call.receiver_type_evidence.append(proof)
        call.target_status = 'builtin_method_candidate'
        call.binding_status = 'complete'
        for index, argument in enumerate(call.argument_sources):
            argument['parameter'] = contract.parameters[index]
            call.parameter_bindings[index].update(parameter=contract.parameters[index],
                                                 status='exact', destination_kind='parameter')
        for value in call.argument_flows + call.parameter_flows:
            position = value['argument'].get('position')
            if position is not None:
                value['target_parameter'] = contract.parameters[position]
        call.argument_sources.append({'argument': {'receiver': True}, 'parameter': 'self',
                                      'sources': self.materialize(receiver, env)})
        call.parameter_bindings.append({'argument': {'receiver': True}, 'parameter': 'self',
            'status': 'exact', 'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'})
        key = node.args[0].value if isinstance(node.args[0], ast.Constant) and isinstance(
            node.args[0].value, (str, int)) else '*'
        roots, _ = self.affected_values(receiver, env)
        effect = {'kind': 'mapping_element', 'operation': 'setdefault', 'mapping': roots,
                  'element_path': [key], 'state_before': 'unknown', 'state_after': 'conditional',
                  'insertion': 'conditional', 'status': 'unknown_key' if key == '*' else 'source_candidate',
                  'completion': 'normal_return', 'conditions': copy.deepcopy(self.conditions),
                  'evidence': self.evidence(node), 'method_binding': copy.deepcopy(proof)}
        call.effects.append(effect)
        self.mapping_effects.append(effect)
        self.add_boundary('dynamic_method_override_possible', node, env, receiver, call_id=call.id)
        if key == '*':
            self.add_boundary('container_effect_unknown', node, env, receiver,
                              call_id=call.id, detail='dynamic_key_protocol_unconfirmed')

    ## Model supported builtin container method calls and their effects.
    ## 建模受支持的内置容器方法调用及其效果。
    #
    #  @param node Call AST node.
    #  @param receiver Receiver source records.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @param actuals Optional argument sources by position.
    #  @return Modeled result or None when no exact protocol applies.
    def container_call(self, node, receiver, call, env, actuals=None):
        receiver = self.container_values(receiver)
        if (not isinstance(node.func, ast.Attribute) or not receiver or not all(
                v['kind'] == 'container' and v.get('relation') == 'direct'
                and not v.get('value_incomplete') and not v.get('projection')
                and not v.get('output_path') for v in receiver)):
            return None
        shapes = {v['container_shape'] for v in receiver}
        method = node.func.attr
        effect = container_method_effect(method, shapes, len(node.args))
        update_keywords = (method == 'update'
                           and all(keyword.arg is not None
                                   for keyword in node.keywords))
        if (effect is None or (node.keywords and not update_keywords)
                or any(isinstance(a, ast.Starred) for a in node.args)):
            self.result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                           'reason': 'container_effect_unknown'})
            return None
        if self.context_execution:
            safe = method in ('clear', 'copy') and not node.args
            if method in ('pop', 'get', 'setdefault') and shapes == {'dict'} and node.args:
                key = self.literal_fact(node.args[0], env)
                safe = bool(key and key['type'] in ('str', 'int') and key['value'] != '*')
            if method == 'update':
                safe = all(self.exact_container((actuals or {}).get(index, []), ('dict',), env)
                           for index in range(len(node.args)))
                safe = safe and all(isinstance(key, (str, int)) for argument in node.args
                    if isinstance(argument, ast.Dict) for key in [
                        item.value if isinstance(item, ast.Constant) else None for item in argument.keys])
            safe = safe and not any(isinstance(child, ast.Call) for argument in
                node.args + [keyword.value for keyword in node.keywords] for child in ast.walk(argument))
            if not safe:
                self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                                  call_id=call.id, affected_scope='unknown')
        call.target_status = 'local_container_protocol'
        call.binding_status = 'complete'
        if effect.mutates_receiver:
            self.invalidate_literals(receiver, env)
        parameters = effect.parameters
        for index, argument in enumerate(call.argument_sources):
            parameter = (parameters[index] if index < len(parameters)
                         else 'other' if method == 'update' else None)
            argument['parameter'] = parameter
            if (method == 'update'
                    and isinstance(argument.get('argument'), dict)
                    and argument['argument'].get('keyword') is not None):
                argument['target_path'] = [argument['argument']['keyword']]
            call.parameter_bindings[index].update(
                parameter=parameter, status='exact',
                destination_kind='parameter')
            if argument.get('target_path'):
                call.parameter_bindings[index]['target_path'] = argument['target_path']
        for flow in call.argument_flows + call.parameter_flows:
            slot = flow['argument']
            if 'position' in slot:
                flow['target_parameter'] = (parameters[slot['position']]
                                            if slot['position'] < len(parameters)
                                            else 'other')
            elif method == 'update' and slot.get('keyword') is not None:
                flow['target_parameter'] = 'other'
                flow['target_path'] = [slot['keyword']]
        if method == 'copy':
            return self.copy_container(receiver, 'dict', node, call, env)
        if method == 'setdefault':
            return self.mapping_setdefault(node, receiver, call, env, actuals or {})
        if method == 'get':
            index = node.args[0].value if isinstance(node.args[0], ast.Constant) else '*'
            known = all(self.mapping_key_state(value, index, env) == 'present'
                        for value in receiver)
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': self.materialize(receiver, env)})
            call.result_sources = self.marked(
                self.project(receiver, index, env), node)
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if len(node.args) == 2 and not known:
                call.return_dependencies.append({'kind': 'parameter', 'source': 'default',
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)})
            return None  # Preserve the call-result endpoint as well as its dependencies.
        if method == 'pop':
            requested = -1 if shapes == {'list'} else '*'
            if node.args:
                try:
                    requested = ast.literal_eval(node.args[0])
                except (ValueError, TypeError):
                    requested = '*'
                if (shapes == {'list'} and not isinstance(requested, int)):
                    requested = '*'
                if (shapes == {'dict'} and not isinstance(requested, (str, int))):
                    requested = '*'
            index = requested
            valid_index = True
            if (shapes == {'list'} and requested != '*'
                    and len({value['source'] for value in receiver}) == 1):
                reference = receiver[0]
                keys = [key['key'] for key in env.get(reference['source'] + '$keys', [])]
                if keys == list(range(len(keys))):
                    try:
                        index = list(range(len(keys)))[requested]
                    except IndexError:
                        valid_index = False
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': copy.deepcopy(self.materialize(receiver, env))})
            if not valid_index:
                return []
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            call.result_sources = self.marked(
                self.project(receiver, index, env), node)
            if shapes == {'dict'} and len(node.args) == 2:
                call.return_dependencies.append({
                    'kind': 'parameter', 'source': 'default',
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)})
            if index != '*' and len({v['source'] for v in receiver}) == 1:
                for ref in receiver:
                    keys = [key['key'] for key in env.get(ref['source'] + '$keys', [])]
                    remaining = []
                    for value in env.get(ref['source'], []):
                        path = value.get('output_path', [])
                        if path and path[0] == index:
                            continue
                        if (shapes == {'list'} and path
                                and isinstance(path[0], int) and path[0] > index):
                            value = dict(value, output_path=[path[0] - 1] + path[1:])
                        elif shapes == {'dict'} and path and path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[index]]),
                                conditions=value.get('conditions', []) +
                                           list(self.conditions))
                        remaining.append(value)
                    env[ref['source']] = remaining
                    if shapes == {'list'}:
                        env[ref['source'] + '$keys'] = [
                            {'kind': 'key', 'source': repr(position), 'key': position}
                            for position in range(len(keys) - 1)]
                    else:
                        markers = []
                        for marker in env.get(ref['source'] + '$keys', []):
                            if marker['key'] == index:
                                continue
                            if marker['key'] == '*':
                                marker = dict(marker, excluded_keys=_unique(
                                    marker.get('excluded_keys', []) + [index]))
                            markers.append(marker)
                        env[ref['source'] + '$keys'] = markers
            if shapes == {'dict'}:
                roots, unknown = self.affected_values(receiver, env)
                mapping_effect = {
                    'operation': 'pop', 'mapping': roots,
                    'element_path': [index],
                    'state_after': ('conditional' if self.conditions
                                    else 'absent' if index != '*' else 'unknown'),
                    'status': 'unknown_key' if index == '*' or unknown else 'bounded',
                    'conditions': list(self.conditions),
                    'evidence': self.evidence(node)}
                self.mapping_effects.append(mapping_effect)
                call.effects.append(dict(mapping_effect, kind='mapping_element'))
            return None
        if method == 'update':
            roots, unknown = self.affected_values(receiver, env)
            paths = []
            inserted = []
            for argument in call.argument_sources:
                slot = argument.get('argument', {})
                explicit_key = (slot.get('keyword')
                                if isinstance(slot, dict) else None)
                for value in argument.get('sources', []):
                    path = ([explicit_key] if explicit_key is not None else
                            value.get('output_path', ['*']))
                    if not path:
                        path = ['*']
                    paths.append(path)
                    inserted.append(dict(value, output_path=path,
                                         conditions=value.get('conditions', []) +
                                                    list(self.conditions)))
            for ref in receiver:
                previous = list(env.get(ref['source'], []))
                for path in paths:
                    if path and path[0] != '*':
                        updated = []
                        for value in previous:
                            old_path = value.get('output_path', [None])
                            if old_path[0] == path[0]:
                                continue
                            if old_path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[path[0]]]))
                            updated.append(value)
                        previous = updated
                env[ref['source']] = _loop_env(
                    {'items': previous + inserted})['items']
                markers = list(env.get(ref['source'] + '$keys', []))
                for path in paths:
                    key = path[0] if path else '*'
                    markers.append({'kind': 'key', 'source': repr(key), 'key': key})
                env[ref['source'] + '$keys'] = _unique(markers)
                call.mutation_flows.extend(
                    dict(value, target_container=ref['source'],
                         effect_summary='mapping_update')
                    for value in inserted)
            mapping_effect = {
                'operation': 'update', 'mapping': roots,
                'element_path': (paths[0] if len(paths) == 1 else ['*']),
                'state_after': ('conditional' if self.conditions else
                                'present' if paths and all(path[0] != '*'
                                                          for path in paths)
                                else 'unknown'),
                'status': 'unknown_source' if unknown or not paths else 'bounded',
                'conditions': list(self.conditions),
                'evidence': self.evidence(node)}
            self.mapping_effects.append(mapping_effect)
            call.effects.append(dict(mapping_effect, kind='mapping_element'))
            return None
        for ref in receiver:
            if method == 'clear':
                if len({v['source'] for v in receiver}) == 1:
                    env[ref['source']] = []
                    env[ref['source'] + '$keys'] = []
                    env.pop(ref['source'] + '$state', None)
            else:
                values = self.marked(call.argument_sources[0]['sources'], node)
                inserted = [dict(v, output_path=['*'] + v.get('output_path', [])) for v in values]
                env[ref['source']] = _loop_env({'items': env.get(ref['source'], []) + inserted})['items']
                env[ref['source'] + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(v, target_container=ref['source']) for v in inserted)
        if method == 'clear':
            roots, unknown = self.mapping_affected_values(receiver, env)
            call.effects.append({'kind': 'container_clear', 'operation': 'clear',
                'mapping': roots, 'element_path': [],
                'object_sources': _unique(value['source'] for value in receiver),
                'completion': 'normal_return', 'status': 'unknown' if unknown else 'exact',
                'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)})
        return None  # Preserve the mutator's call-result endpoint (the runtime value is None).

    ## Apply supported complete helper effects to tracked caller objects.
    ## 将受支持的完整辅助函数效果应用于调用方跟踪对象。
    #
    #  @param definition Source target identity and AST pair.
    #  @param actuals Bound argument source records.
    #  @param captures Captured source records.
    #  @param call Current flow call.
    #  @param env Mutable abstract environment.
    #  @param node Call-site AST node.
    #  @return Whether all relevant effects were completely applied.
    def apply_effects(self, definition, actuals, captures, call, env, node):
        # Apply complete summaries to proven objects on normal completion.
        # Unsupported mapping effects widen exclusions without inventing writes.
        target_ref, target = definition
        effects, cause = self.analyzer._function_effects(definition)
        mapping_candidate = any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
            and child.func.attr == 'pop' or
            isinstance(child, ast.Delete) and any(isinstance(item, ast.Subscript)
                                                 for item in child.targets)
            or isinstance(child, ast.Subscript) and isinstance(child.ctx, ast.Store)
            for child in ast.walk(target))
        affected = [value for inputs in actuals.values() for value in inputs]
        affected_roots, affected_unknown = self.mapping_affected_values(affected, env)
        impact = {'affected_values': affected_roots,
                  'affected_scope': 'unknown' if affected_unknown else
                                    'known' if affected_roots else 'none'}
        if effects is None:
            if cause != 'mapping_effect_budget' and self.mapping_remainder_effect(
                    definition, actuals, call, env, node):
                return False  # Only unaffected keys are complete, never the whole helper.
            ordinary = {argument.arg for argument in target.args.posonlyargs
                        + target.args.args + target.args.kwonlyargs}
            ordinary_actuals = {name: values for name, values in actuals.items() if name in ordinary}
            known_mapping = any(value.get('kind') == 'container' and value.get('container_shape') == 'dict'
                for values in ordinary_actuals.values() for value in self.container_values(values))
            if known_mapping:
                for values in ordinary_actuals.values():
                    self.unknown_container_contents(values, env)
            owner = target_ref.qualname.rpartition('.')[0]
            if (cause != 'mapping_effect_budget' and call.binding_status == 'complete'
                    and not getattr(target, 'decorator_list', []) and not owner
                    and self.analyzer._stable_import_name(target_ref.module + '.' + target_ref.qualname)
                    and (target_ref.module, target_ref.qualname) not in self.modified_return_callables):
                for site in finite_key_delete_sites(target):
                    receivers = self.container_values(actuals.get(site.target, []))
                    arguments = [item for item in call.argument_sources if item.get('parameter') == site.source]
                    literal = arguments[0].get('literal') if len(arguments) == 1 else None
                    if (not receivers or not all(value.get('kind') == 'container'
                            and value.get('container_shape') == 'dict'
                            and value.get('relation') == 'direct' and not value.get('value_incomplete')
                            and not value.get('projection') and not value.get('output_path')
                            for value in receivers) or len({value['source'] for value in receivers}) != 1
                            or literal is None or literal['type'] not in ('tuple', 'list')
                            or not all(isinstance(key, str) for key in literal['value'])):
                        continue
                    keys = _unique(literal['value'])
                    if len(keys) > self.analyzer._effect_fact_steps:
                        self.add_boundary('mapping_effect_budget', node, env, affected, call_id=call.id, **impact)
                        break
                    self.analyzer._effect_fact_steps -= len(keys)
                    roots, _ = self.mapping_affected_values(receivers, env)
                    for key in keys:
                        call.effects.append({'kind': 'mapping_element', 'operation': 'delete',
                            'mapping': roots, 'element_path': [key], 'state_after': 'unknown',
                            'status': 'partial_behavior', 'completion': 'unproven',
                            'reachability': 'not_proven', 'conditions': copy.deepcopy(self.conditions),
                            'sequence_binding': {'parameter': site.source,
                                'argument': arguments[0]['argument'], 'literal': literal,
                                'evidence': arguments[0].get('value_evidence', [])},
                            'operation_conditions': [{'test': self.evidence_at(target_ref, site.membership_test),
                                'branch': True, 'iteration_key': key}],
                            'evidence': [self.evidence_at(target_ref, site.statement)],
                            'loop_evidence': self.evidence_at(target_ref, site.sequence_loop),
                            'call_evidence': self.evidence(node), 'call_id': call.id})
            for values in actuals.values():
                self.invalidate_literals(values, env)
            if mapping_candidate or known_mapping:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                                  call_id=call.id, detail=cause, **impact)
                self.widen_mapping_exclusions(ordinary_actuals, env)
                if cause == 'mapping_effect_budget':
                    self.add_boundary(cause, node, env, affected, call_id=call.id, **impact)
            return False
        expanded, changed_sequences = [], set()
        for effect in effects:
            if effect.kind != 'mapping_delete_keys':
                expanded.append(effect)
                if effect.kind != 'nonlocal_write':
                    changed_sequences.update(value['source'] for value in self.container_values(
                        actuals.get(effect.target, captures.get(effect.target, [])))
                        if value.get('kind') == 'container')
                continue
            sequence_objects = {value['source'] for value in self.container_values(
                actuals.get(effect.source, [])) if value.get('kind') == 'container'}
            if sequence_objects & changed_sequences:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='modified_finite_sequence', **impact)
                for values in actuals.values():
                    self.invalidate_literals(values, env)
                self.widen_mapping_exclusions(actuals, env)
                return False
            arguments = [argument for argument in call.argument_sources
                         if argument.get('parameter') == effect.source]
            literal = arguments[0].get('literal') if len(arguments) == 1 else None
            if (call.binding_status != 'complete' or literal is None
                    or literal['type'] not in ('tuple', 'list')
                    or not all(isinstance(key, str) for key in literal['value'])):
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='unproven_finite_string_sequence', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            keys = _unique(literal['value'])
            if len(keys) > self.analyzer._effect_fact_steps:
                self.add_boundary('mapping_effect_budget', node, env, affected, call_id=call.id, **impact)
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='mapping_effect_budget', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            self.analyzer._effect_fact_steps -= len(keys)
            expanded.extend(FunctionEffect('mapping_delete', effect.target, effect.source,
                effect.statement, 'dict', (key,), None, effect.sequence_loop, effect.membership_test)
                for key in keys)
        effects = tuple(expanded)
        values_by_name = dict(captures)
        values_by_name.update({name: self.container_values(values)
                               for name, values in actuals.items()})
        if effects:
            owner = target_ref.qualname.rpartition('.')[0]
            if (call.binding_status != 'complete' or target.decorator_list
                    or self.analyzer._definition_index.find(target_ref.module, owner, kind='class')
                    or (not owner and not self.analyzer._stable_import_name(
                        target_ref.module + '.' + target_ref.qualname))
                    or (target_ref.module, target_ref.qualname) in self.modified_return_callables):
                self.add_boundary('mapping_effect_unproven' if mapping_candidate else
                                  'container_effect_unknown', node, env, affected,
                                  call_id=call.id, detail='unstable_callable_or_binding', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            ordinary = {argument.arg for argument in
                        target.args.posonlyargs + target.args.args + target.args.kwonlyargs}
            if any(effect.kind != 'nonlocal_write' and effect.target not in ordinary
                   for effect in effects):
                self.add_boundary('container_effect_unknown', node, env, affected,
                                  call_id=call.id, detail='non_ordinary_receiver', **impact)
                return False
        mapping_effects = [effect for effect in effects if effect.receiver_shape == 'dict']
        if mapping_effects:
            cause = None
            for effect in effects:
                receivers = values_by_name.get(effect.target, [])
                shapes = ('dict',) if effect.receiver_shape else (
                    ('list',) if effect.kind == 'container_append' else ('dict', 'list', 'set'))
                if (effect.kind == 'nonlocal_write' or not receivers or not all(
                        value.get('kind') == 'container'
                        and value.get('container_shape') in shapes
                        and value.get('relation') == 'direct'
                        and not value.get('value_incomplete')
                        and not value.get('projection') and not value.get('output_path')
                        and value['source'] in env for value in receivers)
                        or len({value['source'] for value in receivers}) != 1):
                    cause = 'unproven_dict_object'
                    break
            if cause:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                                  call_id=call.id, detail=cause, **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
        complete = True
        for effect in effects:
            kind = effect.kind
            target_name = effect.target
            source_name = effect.source
            if kind == 'nonlocal_write':
                values = values_by_name.get(source_name, [])
                env[target_name] = self.marked(values, node)
                call.effects.append({'kind': 'nonlocal_write', 'target': target_name,
                                     'source': source_name, 'status': 'exact',
                                     'evidence': [self.evidence_at(
                                         target_ref, effect.statement)]})
                call.mutation_flows.extend(dict(value, target_binding=target_name,
                                                effect_summary='nonlocal_write')
                                           for value in self.materialize(values, env))
                continue
            receivers = values_by_name.get(target_name, [])
            self.invalidate_literals(receivers, env)
            expected_shape = 'list' if kind == 'container_append' else None
            if (not receivers or not all(value.get('kind') == 'container'
                    and (expected_shape is None or value.get('container_shape') == expected_shape)
                    for value in receivers)
                    or len({value['source'] for value in receivers}) != 1):
                complete = False
                continue
            if kind in ('mapping_pop', 'mapping_delete'):
                key = effect.element_path[0]
                if isinstance(effect.statement, ast.Return):
                    call.result_sources = self.marked(self.materialize(
                        self.project(receivers, key, env), env), node)
                    for value in call.result_sources:
                        value['evidence'] = _unique(value['evidence'] + [
                            self.evidence_at(target_ref, effect.statement)])
                roots, unknown = self.mapping_affected_values(receivers, env)
                binding = next(item for item in call.parameter_bindings
                               if item.get('parameter') == target_name
                               and item.get('status') == 'exact')
                mapping_effect = {
                    'operation': 'pop' if kind == 'mapping_pop' else 'delete',
                    'mapping': roots, 'element_path': [key],
                    'state_after': 'conditional' if self.conditions else 'absent',
                    'status': 'unknown' if unknown else 'bounded',
                    'completion': 'normal_return', 'may_raise': effect.may_raise,
                    'conditions': _unique(copy.deepcopy(self.conditions) +
                        copy.deepcopy(getattr(target, '_flow_conditions', []))),
                    'call_id': call.id,
                    'binding': copy.deepcopy(binding),
                    'evidence': [self.evidence_at(target_ref, effect.statement)],
                    'call_evidence': self.evidence(node)}
                if effect.sequence_loop is not None:
                    argument = next(item for item in call.argument_sources
                                    if item.get('parameter') == source_name)
                    mapping_effect.update(
                        sequence_binding={'parameter': source_name,
                            'argument': argument['argument'],
                            'literal': copy.deepcopy(argument['literal']),
                            'evidence': copy.deepcopy(argument.get('value_evidence', []))},
                        loop_evidence=self.evidence_at(target_ref, effect.sequence_loop),
                        operation_conditions=[{'test': self.evidence_at(target_ref, effect.membership_test),
                            'branch': True, 'iteration_key': key}])
                self.mapping_effects.append(mapping_effect)
                call.effects.append(dict(mapping_effect, kind='mapping_element'))
                if effect.may_raise:
                    self.add_boundary('mapping_effect_exception_path', node, env, receivers,
                                      call_id=call.id, exception=effect.may_raise,
                                      completion='normal_return',
                                      effect_evidence=mapping_effect['evidence'],
                                      affected_values=roots,
                                      affected_scope='unknown' if unknown else
                                                     'known' if roots else 'none')
                for reference in receivers:
                    remaining = []
                    for value in env.get(reference['source'], []):
                        path = value.get('output_path', [None])
                        if path[0] == key:
                            continue
                        if path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[key]]),
                                evidence=value.get('evidence', []) + mapping_effect['evidence'],
                                conditions=value.get('conditions', []) + list(self.conditions))
                        remaining.append(value)
                    env[reference['source']] = remaining
                    markers = []
                    for marker in env.get(reference['source'] + '$keys', []):
                        if marker['key'] == key:
                            continue
                        if marker['key'] == '*':
                            marker = dict(marker, excluded_keys=_unique(
                                marker.get('excluded_keys', []) + [key]))
                        markers.append(marker)
                    env[reference['source'] + '$keys'] = markers
                continue
            if kind == 'container_clear':
                for reference in receivers:
                    env[reference['source']] = []
                    env[reference['source'] + '$keys'] = []
                    env.pop(reference['source'] + '$state', None)
                call.effects.append({'kind': 'container_clear', 'target': target_name,
                                     'status': 'exact',
                                     'evidence': [self.evidence_at(
                                         target_ref, effect.statement)]})
                continue
            values = values_by_name.get(source_name, [])
            for reference in receivers:
                inserted = [dict(value, output_path=['*'] + value.get('output_path', []))
                            for value in self.marked(values, node)]
                env[reference['source']] = _loop_env({
                    'items': env.get(reference['source'], []) + inserted})['items']
                env[reference['source'] + '$keys'] = [
                    {'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(value, target_container=reference['source'],
                    effect_summary='unconditional_append')
                    for value in self.materialize(inserted, env))
            call.effects.append({'kind': 'container_append', 'target': target_name,
                                 'source': source_name, 'status': 'exact',
                                 'evidence': [self.evidence_at(
                                     target_ref, effect.statement)]})
        return complete

    ## Apply only the unchanged-key part of a bounded fresh-dict helper proof.
    ## 仅应用有界新建字典辅助函数证明中未变键的部分。
    #
    #  @param definition Unique source target, with any proved branch selection.
    #  @param actuals Raw bound values, preserving object identities and literals.
    #  @param call Exact producer edge receiving evidence and assumptions.
    #  @param env Caller state; affected key values remain explicitly incomplete.
    #  @param node Source call for exact evidence and budget diagnostics.
    #  @return True for an admitted remainder, not complete helper effects.
    def mapping_remainder_effect(self, definition, actuals, call, env, node):
        ref, target = definition
        if (call.binding_status != 'complete' or call.target_status != 'resolved'
                or getattr(target, '_flow_branch_budget', None) is not None
                or call.binding_issues or ref.qualname.count('.') or target.decorator_list
                or self.analyzer._captures(*definition)
                or not self.analyzer._stable_import_name(ref.module + '.' + ref.qualname)
                or (ref.module, ref.qualname) in self.modified_return_callables
                or any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(self.node))):
            return False
        ordinary = {a.arg for a in target.args.posonlyargs + target.args.args + target.args.kwonlyargs}
        mappings = [(name, self.exact_container(values, ('dict',), env))
                    for name, values in actuals.items() if name in ordinary]
        mappings = [(name, obj) for name, obj in mappings if obj is not None]
        if len(mappings) != 1:
            return False
        parameter, obj = mappings[0]
        source = obj['source']
        if (not source.startswith(('$parameter:', '$heap:', '$copy:'))
                or any(not marker.get('remainder_preserved')
                       for marker in env.get(source + '$state', []))
                or any(value.get('source') == source for name, values in actuals.items()
                       if name != parameter for value in self.container_values(values))):
            return False
        # References stored in another object, capture or external binding can
        # let an unrelated call mutate this object. Such escapes stay unproved.
        # 保存到其他对象、捕获或外部绑定中的引用可能允许无关调用修改对象。
        for name, values in env.items():
            if name.startswith('$') and any(
                    value.get('kind') == 'container' and value.get('source') == source
                    for value in self.container_values(values, allow_contained=True)):
                return False
        aliases = {name for name, values in env.items() if not name.startswith('$') and any(
            value.get('kind') == 'container' and value.get('source') == source
            for value in self.container_values(values))}
        if any(n is not self.node and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
               and any(isinstance(child, ast.Name) and child.id in aliases
                       for child in ast.walk(n)) for n in ast.walk(self.node)):
            return False
        # Lexical stores outside local names are not a fresh-object proof.
        for statement in ast.walk(self.node):
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                if (statement.value is not None and statement.lineno < node.lineno and any(
                        isinstance(n, (ast.Attribute, ast.Subscript))
                        for t in targets for n in ast.walk(t)) and any(
                        isinstance(n, ast.Name) and n.id in aliases
                        for n in ast.walk(statement.value))):
                    return False
        sequences = {}
        for argument in call.argument_sources:
            literal = argument.get('literal')
            if (literal and literal['type'] in ('list', 'tuple')
                    and all(isinstance(key, str) for key in literal['value'])):
                sequences[argument['parameter']] = frozenset(literal['value'])
        sequence_sources = {}
        for name, values in actuals.items():
            literals = [value.get('literal', {}) for value in values]
            if values and all(literal.get('type') in ('list', 'tuple')
                    and all(isinstance(key, str) for key in literal['value'])
                    and value.get('kind') == 'container' and value.get('relation') == 'direct'
                    and not any(value.get(flag) for flag in ('value_incomplete', 'projection',
                                                            'output_path'))
                    for value, literal in zip(values, literals)):
                keys = frozenset(key for literal in literals for key in literal['value'])
                if len(keys) <= 64:
                    sequences[name] = keys
                    sequence_sources[name] = copy.deepcopy(values)
        count = sum(1 for _ in ast.walk(target))
        if count > 2000 or count > self.analyzer._effect_fact_steps:
            self.add_boundary('mapping_remainder_budget', node, env,
                              actuals[parameter], call_id=call.id)
            return False
        self.analyzer._effect_fact_steps -= count
        try:
            proof = mapping_remainder(target, parameter, sequences,
                lambda name: self.analyzer._builtin_name_status(
                    ref, target, name) == 'confirmed_builtin')
        except _ProofLimit:
            self.add_boundary('mapping_remainder_budget', node, env,
                              actuals[parameter], call_id=call.id)
            return False
        if proof is None:
            return False
        paths = [[key] for key in proof.excluded_keys]
        evidence = _unique([self.evidence_at(ref, statement) for statement in proof.evidence])
        contents = []
        for value in env[source]:
            path = value.get('output_path', [])
            if path and path[0] in proof.excluded_keys:
                continue
            if path[:1] == ['*']:
                value = dict(value, excluded_paths=_unique(value.get('excluded_paths', []) + paths),
                             evidence=_unique(value.get('evidence', []) + evidence))
            contents.append(value)
        # Values at touched keys are unknown, not absent. This marker prevents
        # another consumer from treating the subset as a complete finite dict.
        if paths:
            env[source + '$state'] = [{'contents_unknown': True, 'remainder_preserved': True,
                'affected_paths': _unique(paths + [path for state in env.get(source + '$state', [])
                                                 for path in state.get('affected_paths', [])])}]
        env[source] = contents
        binding = next(b for b in call.parameter_bindings if b.get('parameter') == parameter)
        roots, _ = self.mapping_affected_values(actuals[parameter], env)
        obj_fact = {'source': source, 'container_shape': 'dict', 'identity': 'argument_alias',
            'value_completeness': 'unaffected_keys_only',
            'parameter': parameter, 'parameter_container': obj.get('parameter_container'),
            'function': asdict(ref), 'conditions': copy.deepcopy(self.conditions), 'evidence': evidence}
        effect = {'kind': 'mapping_remainder', 'operation': 'preserve_unaffected_keys',
            'call_id': call.id, 'function': asdict(ref), 'mapping': roots,
            'object_source': source, 'parameter': parameter, 'binding': copy.deepcopy(binding),
            'excluded_paths': paths, 'return_path': (list(proof.return_path)
                if proof.return_path is not None else None),
            'completion': 'normal_return', 'status': 'bounded',
            'value_completeness': 'unaffected_keys_only',
            'conditions': copy.deepcopy(self.conditions), 'evidence': evidence,
            'finite_sequence_sources': sequence_sources,
            'call_evidence': self.evidence(node), 'return_object': obj_fact,
            'assumptions': ['fresh_unescaped_builtin_dict', 'source_snapshot_bindings_hold',
                            'no_external_monkeypatch_or_import_hook', 'no_reflective_frame_access']}
        call.effects.append(effect)
        self.add_boundary('mapping_values_partial', node, env, actuals[parameter],
                          call_id=call.id, affected_paths=paths,
                          value_completeness='unaffected_keys_only')
        if proof.return_path:
            heap = '$remainder_tuple:' + call.id
            env[heap] = [dict(self.container_endpoint(call, node, obj_fact),
                              output_path=list(proof.return_path))]
            env[heap + '$keys'] = [{'kind': 'key', 'source': str(i), 'key': i}
                                  for i in range(proof.return_size)]
            call.result_sources = [{'kind': 'container', 'source': heap, 'container_shape': 'tuple',
                'relation': 'direct', 'evidence': [self.evidence(node)],
                'conditions': copy.deepcopy(self.conditions)}]
        return True

    ## Identify input roots affected through tracked mapping contents.
    ## 识别通过被跟踪映射内容受到影响的输入根。
    #
    #  @param values Mapping source records.
    #  @param env Current abstract environment.
    #  @return Affected roots and unknown-scope flag.
    def mapping_affected_values(self, values, env):
        roots, unknown = self.affected_values(values, env)
        for reference in self.container_values(values):
            name = reference.get('parameter_container')
            if (reference.get('kind') == 'container' and name
                    and not any(root['kind'] == 'parameter' and root['name'] == name
                                for root in roots)):
                roots.append({'kind': 'parameter', 'name': name, 'element_path': []})
        return roots, unknown

    ## Widen mapping exclusions after an unmodeled helper effect.
    ## 在未建模辅助函数效果后放宽映射排除信息。
    #
    #  @param actuals Argument source records.
    #  @param env Mutable abstract environment.
    #  @return None
    def widen_mapping_exclusions(self, actuals, env):
        for inputs in actuals.values():
            for reference in self.container_values(inputs):
                if reference.get('kind') != 'container' or reference.get('container_shape') != 'dict':
                    continue
                source = reference['source']
                env[source] = [dict(value, excluded_paths=[])
                               if value.get('excluded_paths') else value
                               for value in env.get(source, [])]
                env[source + '$keys'] = _unique([
                    dict(marker, excluded_keys=[]) if marker.get('excluded_keys') else marker
                    for marker in env.get(source + '$keys', [])] +
                    [{'kind': 'key', 'source': '*', 'key': '*'}])

    ## Analyze a statement block until its control flow no longer continues.
    ## 分析语句块，直到其控制流不再继续。
    #
    #  @param statements Ordered statement sequence.
    #  @param env Mutable abstract environment.
    #  @return Exit tuples carrying control-flow kind, environment and pending values.
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

    ## Look up a synchronous protocol on a proven source instance's type and MRO.
    ## 在已证明源码实例的类型及 MRO 上查找同步协议。
    #
    #  @param values Raw manager values, not the result of enter.
    #  @param method Special protocol method name.
    #  @return Source method, receiver class and proof issues; no runtime guarantee.
    def context_protocol(self, values, method):
        identities = _unique([value.get('instance_type') for value in values])
        if (not values or len(identities) != 1 or not identities[0]
                or any(value.get('value_incomplete') or value.get('relation') != 'direct'
                       or value.get('projection') or value.get('output_path') for value in values)):
            return None, None, ['receiver_unconfirmed']
        receiver = FunctionRef(**identities[0])
        hierarchy = self.analyzer._class_mro(receiver.module, receiver.qualname)
        if hierarchy is None:
            return None, receiver, ['mro_unavailable']
        if any(cls.decorator_list or cls.keywords or any(
                name in statement_scope_facts(cls.body).bound
                for name in ('__getattribute__', '__getattr__', '__setattr__',
                             '__delattr__', '__init_subclass__'))
                for _, cls in hierarchy):
            return None, receiver, ['lookup_customization']
        pending = [member for _, cls in hierarchy for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and member.name in ('__init__', '__new__', '__enter__')]
        visited, steps = set(), 0
        while pending:
            member = pending.pop()
            if id(member) in visited:
                continue
            visited.add(id(member))
            positional = member.args.posonlyargs + member.args.args
            aliases = {positional[0].arg} if positional else set()
            for child in ast.walk(member):
                steps += 1
                if self.analyzer._analysis_budget is not None:
                    self.analyzer._analysis_budget.checkpoint()
                if steps > _CONTEXT_PROTOCOL_NODE_LIMIT:
                    return None, receiver, ['context_enter_budget']
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.Name):
                    if child.value.id in aliases:
                        aliases.update(target.id for target in child.targets if isinstance(target, ast.Name))
                if (isinstance(child, ast.Attribute) and child.attr == '__class__'
                        and isinstance(child.ctx, (ast.Store, ast.Del))):
                    return None, receiver, ['instance_class_write']
                if isinstance(child, ast.Call) and isinstance(child.func, (ast.Name, ast.Attribute)):
                    mutator = child.func.id if isinstance(child.func, ast.Name) else child.func.attr
                    if mutator in ('setattr', 'delattr', '__setattr__', '__delattr__'):
                        bound = (mutator.startswith('__') and isinstance(child.func, ast.Attribute)
                            and isinstance(child.func.value, ast.Name) and child.func.value.id in aliases)
                        key_index = 0 if bound else 1
                        if len(child.args) <= key_index or (not isinstance(child.args[key_index], ast.Constant)
                                or child.args[key_index].value == '__class__'):
                            return None, receiver, ['instance_class_write_unconfirmed']
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name) and child.func.value.id in aliases):
                    for _, cls in hierarchy:
                        helpers = [statement for statement in cls.body
                                   if child.func.attr in statement_scope_facts([statement]).bound]
                        if helpers:
                            pending.extend(statement for statement in helpers
                                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)))
                            break
        target = None
        for class_ref, cls in hierarchy:
            members = [statement for statement in cls.body
                       if method in statement_scope_facts([statement]).bound]
            if not members:
                continue
            if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
                    or members[0].name != method or members[0].decorator_list
                    or contains_yield(members[0])):
                return None, receiver, ['descriptor_unconfirmed']
            matches = self.analyzer._definition_index.find(class_ref.module,
                class_ref.qualname + '.' + method)
            target = matches[0] if len(matches) == 1 and matches[0][1] is members[0] else None
            break
        if target is None:
            return None, receiver, ['definition_unavailable']
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            return None, receiver, ['class_binding_budget']
        classes = {(ref.module, ref.qualname) for ref, _ in hierarchy}
        if any((ref.module, ref.qualname) in classes and attribute in (
                method, '*', '__bases__', '__class__') for ref, attribute, _, _, _ in writes):
            return None, receiver, ['visible_protocol_write']
        return target, receiver, []

    ## Check whether an implicit context protocol call binds exactly.
    ## 检查隐式上下文协议调用是否能够精确绑定。
    #
    #  @param target Optional source method definition.
    #  @param arguments Number of explicit protocol arguments after the receiver.
    #  @return True only when every argument binds exactly.
    def context_signature_valid(self, target, arguments):
        if target is None:
            return False
        call = ast.Call(func=ast.Name(id='$protocol', ctx=ast.Load()),
                        args=[ast.Constant(value=None) for _ in range(arguments + 1)], keywords=[])
        records, reasons = bind_ast_call(call, FunctionSignature.from_ast(target[1].args))
        return not reasons and all(record['status'] == 'exact' for record in records)

    ## Recognize a source exit method with no modeled effects or suppression.
    ## 识别没有建模效果且不抑制异常的源码退出方法。
    #
    #  @param target Optional source exit method definition.
    #  @return True for the supported no-op shape.
    def context_exit_noop(self, target):
        if not self.context_signature_valid(target, 3):
            return False
        for statement in target[1].body:
            if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)):
                continue
            if isinstance(statement, ast.Return) and (statement.value is None
                    or isinstance(statement.value, ast.Constant)
                    and statement.value.value in (None, False)):
                return True
            return False
        return True

    ## Widen tracked object facts after an unmodeled context-manager effect.
    ## 在未建模上下文管理器效果后放宽跟踪对象事实。
    #
    #  @param env Mutable abstract environment.
    #  @return None
    def unknown_context_effects(self, env):
        self.unknown_container_contents([value for items in env.values() for value in items], env)
        self.invalidate_attributes(env)
        for name, values in env.items():
            env[name] = [dict(value, value_incomplete=True, instance_candidates=[])
                         if value.get('instance_type') or value.get('instance_candidates')
                         or value.get('class_type') or value.get('callable_type') else value
                         for value in values]

    ## Apply or restore proven temporary attributes on the matching fresh receiver.
    ## 为匹配的新建接收者应用或恢复已证明的临时属性。
    #
    #  @param env Mutable abstract environment.
    #  @param effect Temporary receiver attribute evidence.
    #  @param entering Whether entry is being applied rather than cleanup.
    #  @return None
    def apply_temporary_receiver_attributes(self, env, effect, entering):
        receiver = effect['receiver_parameter']
        expected = effect['receiver_origin']
        additions = set(effect['attributes'])
        prior = set(effect['prior_own_attributes'])
        updated = []
        for value in env.get(receiver, []):
            origin = value.get('fresh_receiver_origin')
            if (origin and origin.get('current_function') == expected.get('current_function')
                    and origin.get('allocation') == expected.get('allocation')):
                changed = copy.deepcopy(value)
                new_origin = copy.deepcopy(origin)
                own = set(origin.get('own_attributes', ()))
                new_origin['own_attributes'] = sorted(
                    own | additions if entering else own - additions | prior)
                changed['fresh_receiver_origin'] = new_origin
                updated.append(changed)
            else:
                updated.append(value)
        if updated:
            env[receiver] = _unique(updated)

    ## Evaluate only proven builtin literal truth or exception/None identity tests.
    ## 仅计算已证明的内置字面量真值或异常与 None 的身份测试。
    #
    #  @param node Exit expression; no arbitrary truth protocol is executed.
    #  @param env Current bounded lexical/object facts.
    #  @return True, False or None for an unproved truth value.
    def context_truth(self, node, env):
        literal = self.literal_fact(node, env)
        if literal is not None:
            return bool(literal['value'])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            truth = self.context_truth(node.operand, env)
            return not truth if truth is not None else None
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.Is, ast.IsNot))
                and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value is None and isinstance(node.left, ast.Name)):
            values = env.get(node.left.id, [])
            if values and all(value.get('kind') == 'context_exception' for value in values):
                return isinstance(node.ops[0], ast.IsNot)
            fact = self.literal_fact(node.left, env)
            if fact is not None:
                equal = fact['value'] is None
                return equal if isinstance(node.ops[0], ast.Is) else not equal
        return None

    ## Separate normal constant-key deletion from its pre-operation failure state.
    ## 区分常量键删除的正常完成状态与操作前的失败状态。
    #
    #  @param node Direct dict pop expression or deletion subscript.
    #  @param previous Caller frame before evaluating the operation.
    #  @param env Normal-completion frame after evaluation.
    #  @param exceptional Fallback exceptions for an unproved RHS operation.
    #  @return Exceptional alternatives and whether normal completion is possible.
    def context_operation_exits(self, node, previous, env, exceptional=None):
        receiver, key = None, None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'pop' and len(node.args) == 1):
            receiver, key = node.func.value, node.args[0]
        elif isinstance(node, ast.Subscript):
            receiver, key = node.value, node.slice
        if receiver is None:
            if isinstance(node, ast.Call):
                call = next((call for call in reversed(self.calls)
                             if call.id == _call_key(self.ref.file_path, node)), None)
                if call and call.target_status == 'local_container_protocol':
                    method = node.func.attr
                    if method in ('clear', 'copy', 'update') or (
                            method == 'pop' and len(node.args) == 2):
                        return [], True
            return exceptional or [], True
        reference = (self.exact_container(previous.get(receiver.id, []), ('dict',), previous)
                     if isinstance(receiver, ast.Name) else None)
        literal = self.literal_fact(key, previous)
        if reference is None or literal is None or literal['type'] not in ('str', 'int'):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env, affected_scope='unknown')
            return [('raise', previous, [], None)], True
        state = self.mapping_key_state(reference, literal['value'], previous)
        return ([] if state == 'present' else [('raise', previous, [], 'KeyError')], state != 'absent')

    ## Execute a bounded source exit in an isolated lexical frame sharing heap IDs.
    ## 在共享堆标识的独立词法帧中执行有界源码退出分析。
    #
    #  @param target Saved source descriptor, not a new lookup after the body.
    #  @param call Implicit exit call with actual exception/capture bindings.
    #  @param state Caller state at cleanup, retaining pending-return identities.
    #  @return Source outcomes and their updated caller states, or proof issues.
    def execute_context_exit(self, target, call, state):
        if target is None or call.binding_status != 'complete':
            return None, ['context_exit_binding_unconfirmed']
        ref, method = target
        if ref in self.analyzer._context_exit_stack or len(self.analyzer._context_exit_stack) >= 8:
            return None, ['context_exit_recursion']
        steps = 0
        for _ in ast.walk(method):
            steps += 1
            if self.analyzer._analysis_budget is not None:
                self.analyzer._analysis_budget.checkpoint()
            if steps > min(self.analyzer._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT):
                break
        if self.analyzer._fact_functions <= 0 or steps > min(
                self.analyzer._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT):
            return None, ['context_exit_budget']
        self.analyzer._fact_functions -= 1
        self.analyzer._fact_calls -= steps
        frame = {key: copy.deepcopy(values) for key, values in state.items() if key.startswith('$')}
        parameters = method.args.posonlyargs + method.args.args + method.args.kwonlyargs
        for parameter in parameters:
            sources = [value for argument in call.argument_sources
                       if argument.get('parameter') == parameter.arg for value in argument['sources']]
            literals = [argument.get('literal') for argument in call.argument_sources
                        if argument.get('parameter') == parameter.arg]
            if literals and all(literal is not None and literal == literals[0] for literal in literals):
                sources = [dict(value, literal=copy.deepcopy(literals[0])) for value in sources] or [
                    {'kind': 'context_data', 'source': call.id, 'relation': 'direct',
                     'literal': copy.deepcopy(literals[0]), 'evidence': [], 'conditions': []}]
            frame[parameter.arg] = copy.deepcopy(sources)
        if parameters:
            frame[parameters[0].arg] = copy.deepcopy(call._context_manager_values)
        if method.args.vararg:
            actual = [argument for argument in call.argument_sources
                      if argument.get('parameter') == method.args.vararg.arg]
            heap = '$context_arguments:' + call.id
            frame[heap] = [dict(value, output_path=argument.get('target_path', [])
                               + value.get('output_path', []))
                           for argument in actual for value in argument['sources']]
            frame[heap + '$keys'] = [{'kind': 'key', 'source': index, 'key': index}
                                    for index in range(len(actual))]
            frame[method.args.vararg.arg] = [{'kind': 'container', 'source': heap,
                'container_shape': 'tuple', 'relation': 'direct', 'evidence': [], 'conditions': []}]
        captures = self.analyzer._captures(ref, method)
        for capture in captures:
            frame[capture] = copy.deepcopy(state.get(capture, []))
        for local in self.analyzer._scope_facts(method).bound:
            frame.setdefault(local, [])
        scratch = FlowAnalysis(ref, {})
        child = _Summary(self.analyzer, scratch, ref, method, self.remaining)
        child.context_execution = True
        child.context_cleanup_order = self.context_cleanup_order
        child.conditions = copy.deepcopy(self.conditions)
        self.analyzer._context_exit_stack.append(ref)
        try:
            outcomes = child.block(method.body, frame)
        finally:
            self.analyzer._context_exit_stack.pop()
        self.remaining = min(self.remaining, child.remaining)
        self.calls.extend(child.calls)
        self.mapping_effects.extend(child.mapping_effects)
        self.result.boundaries.extend(scratch.boundaries)
        supported = set()
        for source_call in child.calls:
            if source_call.target_status == 'local_container_protocol':
                supported.add(source_call.id)
            elif (source_call.target_status == 'builtin_boundary'
                    and _exception_class(source_call.callee_name) is not None
                    and self.analyzer._builtin_name_status(ref, method, source_call.callee_name)
                        == 'confirmed_builtin' and all(
                            argument.get('literal') is not None for argument in source_call.argument_sources)):
                supported.add(source_call.id)
        issues = [boundary['reason'] for boundary in scratch.boundaries if not (
            boundary.get('call_id') in supported and boundary['reason'] == 'builtin_boundary')]
        if any(source_call.id not in supported for source_call in child.calls):
            issues.append('context_exit_call_unmodeled')
        if any(kind == 'unknown' for kind, _, _, _ in outcomes):
            issues.append('context_exit_completion_unresolved')
        if issues:
            return None, _unique(issues)
        call.effects = _unique([dict(effect, exit_call_id=call.id,
            completion=effect.get('completion', 'normal_return'),
            conditions=_unique(effect.get('conditions', []) + self.conditions))
            for source_call in child.calls for effect in source_call.effects]
            + [dict(effect, exit_call_id=call.id, completion='normal_return')
               for effect in child.mapping_effects])
        completed = []
        nonlocals = self.analyzer._scope_facts(method).nonlocals
        for kind, frame_state, values, payload in outcomes:
            updated = copy.deepcopy(state)
            updated.update({key: copy.deepcopy(values) for key, values in frame_state.items()
                            if key.startswith('$') or key in nonlocals})
            completed.append((kind, updated, values, payload))
        return completed, []

    ## Bind the cached exit descriptor to the saved manager and pending exception.
    ## 将缓存的退出描述符绑定到保存的管理器和待处理异常。
    #
    #  @param node Owning with statement, used as the implicit call location.
    #  @param record Successful entry facts, not a rebound as/context variable.
    #  @param outcome Pending normal, return, control or exceptional state.
    #  @param origin Body or later entry/expression failure witness.
    #  @return Exact source descriptor candidate and implicit FlowCall.
    def context_exit_call(self, node, record, outcome, origin):
        kind, state, values, exception = outcome
        target_ref = record['exit']['target']
        target = next((item for item in self.analyzer._definition_index.find(
            target_ref['module'], target_ref['qualname']) if asdict(item[0]) == target_ref), None
            ) if target_ref else None
        index = record['item_index']
        order = self.context_cleanup_order[0]
        self.context_cleanup_order[0] += 1
        proof = {'kind': 'context_manager_exit', 'method': '__exit__', 'lookup': 'type_mro',
            'with_id': record['with_id'], 'item_index': index, 'cleanup_order': order,
            'incoming_exit': {'kind': kind, 'exception': exception if kind == 'raise' else None,
                              'origin': origin},
            'basis': 'source_snapshot', 'runtime_target_confirmed': False,
            'assumptions': copy.deepcopy(record['assumptions']),
            'issues': copy.deepcopy(record['exit']['issues']),
            'context_expression': copy.deepcopy(record['context_expression'])}
        if kind == 'return':
            proof['pending_return_sources'] = copy.deepcopy(values)
        if target:
            proof['definition'] = self.evidence_at(*target)
            proof['source_hashes'] = {path: self.analyzer.hashes[path] for path in sorted(
                {self.ref.file_path, target[0].file_path}
                | set(record.get('source_hashes', {}))) if path in self.analyzer.hashes}
        temporary = '$with_exit:%s:%s' % (record['with_id'], order)
        arguments = [temporary + ':exc:%s' % index for index in range(3)]
        state[temporary] = copy.deepcopy(record['manager_sources']) if target else [
            dict(value, value_incomplete=True) for value in record['manager_sources']]
        for index, name in enumerate(arguments):
            state[name] = ([{'kind': 'context_exception', 'source': record['with_id'],
                'component': ('type', 'value', 'traceback')[index], 'exception': exception,
                'relation': 'direct', 'evidence': [], 'conditions': copy.deepcopy(self.conditions)}]
                if kind == 'raise' else [{'kind': 'context_data', 'source': record['with_id'],
                    'literal': {'type': 'NoneType', 'value': None}, 'relation': 'direct',
                    'evidence': [], 'conditions': copy.deepcopy(self.conditions)}])
            if kind == 'unknown':
                state[name] = [{'kind': 'context_data', 'source': record['with_id'],
                    'component': ('type', 'value', 'traceback')[index], 'value_incomplete': True,
                    'relation': 'direct', 'evidence': [], 'conditions': copy.deepcopy(self.conditions)}]
        implicit = ast.Call(func=ast.Attribute(value=ast.Name(id=temporary, ctx=ast.Load()),
            attr='__exit__', ctx=ast.Load()), args=[ast.Name(id=name, ctx=ast.Load()) for name in arguments],
            keywords=[])
        for child in ast.walk(implicit):
            ast.copy_location(child, node)
        implicit._flow_implicit_suffix = ':with_exit:%s:%s' % (record['item_index'], order)
        implicit._flow_implicit_protocol = proof
        implicit._flow_protocol_target = target
        implicit._flow_skip_effects = True
        self.expression(implicit, state)
        for name in [temporary] + arguments:
            state.pop(name, None)
        call = next((call for call in reversed(self.calls) if call.id == _call_key(self.ref.file_path, implicit)), None)
        record['exit'].setdefault('executions', []).append({'call_id': call.id if call else None,
            'cleanup_order': order, 'incoming_exit': copy.deepcopy(proof['incoming_exit'])})
        if call:
            call.callee_name = record['context_expression']['source_text'] + '.__exit__'
            call._context_manager_values = copy.deepcopy(record['manager_sources'])
            for boundary in self.result.boundaries:
                if boundary.get('call_id') == call.id and 'callee_name' in boundary:
                    boundary['callee_name'] = call.callee_name
        return target, call

    ## Clean up successful entries in reverse order, preserving pending objects.
    ## 按相反顺序清理成功进入的管理器，并保留待处理对象。
    #
    #  @param node Owning with statement.
    #  @param outcomes Existing normal/return/control/exception exit tuples.
    #  @param records Managers whose enter completed normally, in entry order.
    #  @param origin Body, context_expression or context_enter failure witness.
    #  @return Updated exit tuples; suppression does not cancel return/control.
    def cleanup_context_exits(self, node, outcomes, records, origin='body'):
        before = copy.deepcopy(self.conditions)
        for record in reversed(records):
            completed = []
            for outcome in outcomes:
                first_outcome = len(completed)
                kind, state, pending, exception = outcome
                self.conditions = _unique(before + record['conditions'])
                temporary_effect = record.get('bounded_temporary_receiver_effects')
                if temporary_effect is not None:
                    self.apply_temporary_receiver_attributes(state, temporary_effect,
                                                              entering=False)
                    record['exit'].setdefault('executions', []).append({
                        'call_id': None, 'cleanup_order': len(record['exit']['executions']),
                        'incoming_exit': {'kind': kind, 'exception': exception if kind == 'raise' else None,
                                          'origin': origin},
                        'status': 'source_modeled', 'issues': [],
                        'evidence': temporary_effect['evidence']})
                    completed.append((kind, state, pending, exception))
                    continue
                target, call = self.context_exit_call(node, record, outcome, origin)
                if call:
                    self.conditions.append({'context_exit': call.id, 'incoming_exit_kind': kind,
                                            'exception': exception if kind == 'raise' else None})
                executed, issues = ((None, ['context_exit_incoming_unresolved']) if kind == 'unknown' else
                    self.execute_context_exit(target, call, state) if call else
                    (None, ['context_exit_budget']))
                if executed is None:
                    self.add_boundary('context_exit_unmodeled', node, state,
                        [value for items in state.values() for value in items],
                        with_id=record['with_id'], item_index=record['item_index'],
                        call_id=call.id if call else None, exit_target=record['exit']['target'],
                        issues=issues, affected_scope='unknown', completion='unconfirmed')
                    for reason in ('context_exit_budget', 'context_exit_recursion'):
                        if reason in issues:
                            self.add_boundary(reason, node, state, call_id=call.id if call else None)
                    self.unknown_context_effects(state)
                    pending = [dict(value, value_incomplete=True, instance_candidates=[])
                               if any(value.get(key) for key in ('instance_type', 'instance_candidates',
                                   'class_type', 'callable_type')) or value.get('kind') == 'callable' else value
                               for value in pending]
                    record['exit']['effects_status'] = 'unmodeled'
                    record['exit']['completion'] = 'unconfirmed'
                    record['exit']['executions'][-1].update(status='unmodeled', issues=issues)
                    completed.extend([(kind, copy.deepcopy(state), copy.deepcopy(pending), exception),
                                      ('raise', copy.deepcopy(state), [], None)])
                    if kind in ('raise', 'unknown'):
                        completed.append(('normal', copy.deepcopy(state), [], None))
                    if call:
                        call.implicit_protocol.update(completion='unconfirmed',
                            exit_outcomes=_unique({'kind': item[0],
                                'exception': item[3] if item[0] == 'raise' else None}
                                for item in completed[first_outcome:]))
                    continue
                record['exit']['executions'][-1]['status'] = 'source_modeled'
                if all(item.get('status') == 'source_modeled' for item in record['exit']['executions']):
                    record['exit']['completion'] = 'source_modeled'
                    if record['exit']['effects_status'] != 'source_noop':
                        record['exit']['effects_status'] = 'source_modeled'
                for exit_kind, updated, values, payload in executed:
                    if exit_kind == 'raise':
                        self.add_boundary('context_exit_exception_path', node, updated,
                            call_id=call.id, exception=payload, completion='exceptional')
                        completed.append(('raise', updated, [], payload))
                        continue
                    if kind == 'raise':
                        truth = payload.get('truth') if exit_kind == 'return' and isinstance(payload, dict) else False
                        if truth is None:
                            self.add_boundary('context_exit_truth_unresolved', node, updated,
                                call_id=call.id, affected_scope='unknown')
                            self.unknown_context_effects(updated)
                            record['exit']['executions'][-1]['status'] = 'truth_unconfirmed'
                            record['exit'].update(effects_status='unmodeled', completion='unconfirmed')
                        if truth is not False:
                            completed.append(('normal', copy.deepcopy(updated), [], None))
                        if truth is not True:
                            completed.append(('raise', copy.deepcopy(updated), [], exception))
                        if truth is None:
                            completed.append(('raise', copy.deepcopy(updated), [], None))
                    else:
                        completed.append((kind, updated, pending, exception))
                call.implicit_protocol.update(completion=(
                    'source_modeled' if record['exit']['executions'][-1]['status'] == 'source_modeled'
                    else 'unconfirmed'),
                    exit_outcomes=_unique({'kind': item[0],
                        'exception': item[3] if item[0] == 'raise' else None}
                        for item in completed[first_outcome:]))
            outcomes = completed
            if (record.get('bounded_temporary_receiver_effects') is not None
                    and record['exit'].get('executions')
                    and all(item.get('status') == 'source_modeled'
                            for item in record['exit']['executions'])):
                record['exit']['completion'] = 'source_modeled'
            if len(outcomes) > _CONTEXT_EXIT_PATH_LIMIT:
                self.add_boundary('context_exit_path_budget', node, _merge_env([item[1] for item in outcomes]),
                                  affected_scope='unknown',
                                  path_limit=_CONTEXT_EXIT_PATH_LIMIT)
                outcomes = []
                for kind in _unique(item[0] for item in completed):
                    paths = [item for item in completed if item[0] == kind]
                    state = _merge_env([item[1] for item in paths])
                    self.unknown_context_effects(state)
                    payloads = _unique(item[3] for item in paths)
                    payload = payloads[0] if len(payloads) == 1 else (
                        {'truth': None} if self.context_execution and kind == 'return' else None)
                    pending = _unique(dict(value, value_incomplete=True, instance_candidates=[])
                        if any(value.get(key) for key in ('instance_type', 'instance_candidates',
                            'class_type', 'callable_type')) or value.get('kind') == 'callable' else value
                        for item in paths for value in item[2])
                    outcomes.append((kind, state, pending, payload))
        self.conditions = before
        return outcomes

    ## Record an implicit enter call for a proven source context manager.
    ## 为已证明的源码上下文管理器记录隐式 enter 调用。
    #
    #  @param item Context-manager item.
    #  @param index Item index in the with statement.
    #  @param node Owning with statement.
    #  @param values Manager source records.
    #  @param target Selected source enter method.
    #  @param env Current abstract environment.
    #  @param proof Protocol lookup evidence.
    #  @return Implicit call record.
    def context_enter_call(self, item, index, node, values, target, env, proof):
        temporary = '$with:%s:%s' % (_call_key(self.ref.file_path, node), index)
        env[temporary] = copy.deepcopy(values) if target else [dict(value, value_incomplete=True)
                                                               for value in values]
        implicit = ast.Call(func=ast.Attribute(value=ast.Name(id=temporary, ctx=ast.Load()),
                             attr='__enter__', ctx=ast.Load()), args=[], keywords=[])
        for child in ast.walk(implicit):
            ast.copy_location(child, item.context_expr)
        implicit._flow_implicit_suffix = ':with_enter:%s' % index
        implicit._flow_implicit_protocol = proof
        implicit._flow_protocol_target = target
        self.expression(implicit, env)
        env.pop(temporary, None)
        call = next((call for call in reversed(self.calls)
                     if call.id == _call_key(self.ref.file_path, implicit)), None)
        if call is not None:
            call.callee_name = ast.unparse(item.context_expr) + '.__enter__'
            for boundary in self.result.boundaries:
                if boundary.get('call_id') == call.id and 'callee_name' in boundary:
                    boundary['callee_name'] = call.callee_name
        return call

    ## Propagate enter results and clean up every modeled body/entry exit path.
    ## 传播 enter 结果，并清理每条已建模的语句体或进入退出路径。
    #
    #  @param node Synchronous ast.With.
    #  @param env Current object contents and lexical bindings.
    #  @return Existing block exit tuples, with explicit protocol boundaries.
    def with_statement(self, node, env):
        before = copy.deepcopy(self.conditions)
        exceptions = []
        exits = []
        for index, item in enumerate(node.items):
            temporary_effect = (bounded_temporary_receiver_attributes(self, item.context_expr, env)
                                if item.optional_vars is None else None)
            if _may_raise(item.context_expr):
                failed = copy.deepcopy(env)
                if exits:
                    self.add_boundary('context_expression_exception_effects_unmodeled', item.context_expr,
                                      failed, affected_scope='unknown')
                    self.unknown_context_effects(failed)
                exceptions.extend(self.cleanup_context_exits(node,
                    [('raise', failed, [], None)], exits, 'context_expression'))
            before_expression = copy.deepcopy(env) if temporary_effect is not None else None
            values = self.marked(self.expression(item.context_expr, env), item.context_expr)
            if temporary_effect is not None:
                env.clear()
                env.update(before_expression)
            target, receiver, issues = self.context_protocol(values, '__enter__')
            exit_target, _, exit_issues = self.context_protocol(values, '__exit__')
            if temporary_effect is not None:
                receiver = FunctionRef(**temporary_effect['receiver_class'])
                issues, exit_issues = [], []
            if exit_target is not None and not self.context_signature_valid(exit_target, 3):
                exit_issues.append('binding_unconfirmed')
            assumptions = ['source_snapshot_bindings_hold', 'standard_type_special_method_lookup',
                           'no_external_monkeypatch_or_import_hook']
            proof = {'kind': 'context_manager_enter', 'method': '__enter__', 'lookup': 'type_mro',
                'with_id': _call_key(self.ref.file_path, node), 'item_index': index,
                'basis': 'source_snapshot', 'runtime_target_confirmed': False,
                'receiver_class': asdict(receiver) if receiver else None,
                'assumptions': assumptions, 'issues': issues,
                'context_expression': self.evidence(item.context_expr)}
            if target is not None:
                proof['definition'] = self.evidence_at(target[0], target[1])
                hierarchy = self.analyzer._class_mro(receiver.module, receiver.qualname)
                proof['source_hashes'] = {path: self.analyzer.hashes[path] for path in sorted(
                    {self.ref.file_path, target[0].file_path, receiver.file_path}
                    | {ref.file_path for ref, _ in hierarchy or ()})
                    if path in self.analyzer.hashes}
            missing_exit = receiver is not None and exit_issues == ['definition_unavailable']
            call = (None if temporary_effect is not None or missing_exit else
                    self.context_enter_call(item, index, node, values, target, env, proof))
            if temporary_effect is not None:
                fact = {'paths': [[]], 'completion': 'normal_possible', 'issues': [],
                        'effects_status': 'source_modeled'}
            elif target and call:
                fact = self.analyzer._context_enter_returns(target, receiver)
            else:
                fact = {'paths': [], 'completion': 'unknown',
                        'issues': ['context_enter_unresolved']}
            if temporary_effect is None and missing_exit:
                fact = {'paths': [], 'completion': 'no_normal_return',
                        'issues': ['context_exit_definition_unavailable'], 'exceptions': ['TypeError']}
            elif temporary_effect is None and target is not None and not self.context_signature_valid(target, 0):
                fact = {'paths': [], 'completion': 'no_normal_return',
                        'issues': ['context_enter_binding_unconfirmed'], 'exceptions': ['TypeError']}
                if call is not None:
                    call.binding_status = 'invalid'
                    call.binding_issues.append({'kind': 'implicit_receiver_binding', 'status': 'invalid'})
            elif temporary_effect is None and call is not None and call.binding_status != 'complete':
                fact = {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_binding_unconfirmed']}
            elif temporary_effect is None and call is None:
                fact = {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_budget']}
            prior_conditions = copy.deepcopy(self.conditions)
            condition = {'context_enter': call.id if call else proof['with_id'] + ':enter:%s' % index,
                         'completion': 'normal_return', 'basis': 'source_snapshot'}
            self.conditions = self.conditions + [condition]
            returned = []
            complete = (temporary_effect is not None
                        or bool(fact['paths']) and not fact['issues'])
            for path in fact['paths']:
                if temporary_effect is not None:
                    break
                known = []
                for value in path:
                    alias = (value.get('kind') == 'parameter'
                        and value.get('source') == fact.get('parameter')
                        and value.get('relation') == 'direct'
                        and not value.get('projection') and not value.get('output_path'))
                    inputs = values if alias else [value] if value.get('instance_type') else []
                    for actual in inputs:
                        if actual.get('value_incomplete') or actual.get('relation') != 'direct':
                            continue
                        evidence = _unique(actual.get('evidence', []) + value.get('evidence', [])
                                           + [self.evidence(item.context_expr)])
                        known.append(dict(actual, kind='call_result', source=call.id,
                            evidence=evidence, conditions=_unique(actual.get('conditions', [])
                                + value.get('conditions', []) + self.conditions),
                            context_manager_return={'enter_call_id': call.id,
                                'identity': 'receiver_alias' if alias else 'return_instance',
                                'object_source': (actual.get('context_manager_return', {}).get(
                                    'object_source', actual['source']) if alias else
                                    '$context_instance:%s:%s' % (call.id, actual['source'])),
                                'return_evidence': value.get('evidence', [])}))
                complete = complete and bool(known)
                returned.extend(known)
            record = {'with_id': proof['with_id'], 'item_index': index,
                'source_hashes': copy.deepcopy(proof.get('source_hashes', {})),
                'context_expression': proof['context_expression'], 'manager_sources': copy.deepcopy(values),
                'as_target': self.evidence(item.optional_vars) if item.optional_vars else None,
                'conditions': copy.deepcopy(self.conditions),
                'enter': {'call_id': call.id if call else None,
                    'target': asdict(target[0]) if target else None, 'issues': _unique(issues + fact['issues']),
                    'return_status': 'source_proven' if complete else 'unconfirmed',
                    'completion': fact['completion'], 'effects_status': fact.get('effects_status', 'unmodeled')},
                'exit': {'target': asdict(exit_target[0]) if exit_target else None,
                    'effects_status': ('source_modeled' if temporary_effect is not None else
                        'source_noop' if self.context_exit_noop(exit_target) else 'unmodeled'),
                    'issues': exit_issues, 'completion': 'deferred'},
                'basis': 'source_snapshot', 'runtime_target_confirmed': False, 'assumptions': assumptions}
            if temporary_effect is not None:
                record['bounded_temporary_receiver_effects'] = temporary_effect
            self.context_managers.append(record)
            self.conditions = prior_conditions
            failed = copy.deepcopy(env)
            if exits and fact.get('exceptions', [None]) and fact.get('effects_status') != 'source_modeled':
                self.add_boundary('context_enter_exception_effects_unmodeled', item.context_expr,
                                  failed, affected_scope='unknown', call_id=call.id if call else None)
                self.unknown_context_effects(failed)
            exceptions.extend(self.cleanup_context_exits(node,
                [('raise', copy.deepcopy(failed), [], exception) for exception in fact.get('exceptions', [None])],
                exits, 'context_enter'))
            self.conditions = prior_conditions + [condition]
            if fact['completion'] == 'no_normal_return':
                self.add_boundary('context_enter_no_normal_return', item.context_expr, env, values,
                                  call_id=call.id if call else None, conditions=copy.deepcopy(self.conditions))
                self.conditions = before
                return exceptions
            exits.append(record)
            if not complete:
                self.add_boundary('context_enter_return_unresolved', item.context_expr, env, values,
                    call_id=call.id if call else None, issues=record['enter']['issues'],
                    conditions=copy.deepcopy(self.conditions))
                returned = [{'kind': 'call_result', 'source': condition['context_enter'],
                    'relation': 'direct', 'evidence': [self.evidence(item.context_expr)],
                    'conditions': copy.deepcopy(self.conditions)}]
            for reason in record['enter']['issues']:
                if reason in ('context_enter_budget', 'context_enter_recursion'):
                    self.add_boundary(reason, item.context_expr, env, values,
                                      call_id=call.id if call else None)
            if temporary_effect is not None:
                self.apply_temporary_receiver_attributes(env, temporary_effect, entering=True)
            elif fact.get('effects_status') != 'source_modeled':
                self.add_boundary('context_enter_effects_unmodeled', item.context_expr, env,
                    [value for items in env.values() for value in items],
                    affected_scope='unknown', call_id=call.id if call else None)
                self.unknown_context_effects(env)
            if call is not None:
                call.result_sources = copy.deepcopy(returned) if complete else []
            if item.optional_vars is not None:
                self.assign_target(item.optional_vars, returned, env, item.optional_vars)
        outcomes = self.block(node.body, env)
        outcomes = self.cleanup_context_exits(node, outcomes, exits)
        self.conditions = before
        return exceptions + outcomes

    ## Analyze one statement into possible control-flow outcomes.
    ## 将单条语句分析为可能的控制流结果。
    #
    #  @param node Statement AST node.
    #  @param env Mutable abstract environment at entry.
    #  @return Outcome tuples including normal and exceptional alternatives.
    def statement(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        ## Construct normal outcomes while retaining earlier exceptional paths.
        ## 构造正常结果，同时保留此前的异常路径。
        #
        #  @param e Current abstract environment.
        #  @return Outcome tuple list.
        def normal(e):
            return [('normal', e, [], None)]
        if self.context_execution:
            if isinstance(node, ast.Nonlocal):
                return normal(env)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Import, ast.ImportFrom, ast.AugAssign)):
                self.add_boundary('context_exit_definition_or_write_unmodeled', node, env,
                                  affected_scope='unknown')
            if isinstance(node, ast.Delete) and len(node.targets) != 1:
                self.add_boundary('context_exit_multiple_delete_unmodeled', node, env,
                                  affected_scope='unknown')
            if (isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    and not all(isinstance(target, ast.Name) for target in (
                        node.targets if isinstance(node, ast.Assign) else [node.target]))):
                self.add_boundary('context_exit_assignment_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, (ast.For, ast.While)):
                self.add_boundary('context_exit_control_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.Try) and any(handler.type is not None and not (
                    isinstance(handler.type, ast.Name) and _exception_class(handler.type.id) is not None
                    and self.analyzer._builtin_name_status(self.ref, self.node, handler.type.id, env)
                        == 'confirmed_builtin') for handler in node.handlers):
                self.add_boundary('context_exit_handler_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.If):
                truth = self.context_truth(node.test, env)
                if truth is not None:
                    before = self.conditions
                    self.conditions = before + [{'test': self.evidence(node.test), 'branch': truth}]
                    outcomes = self.block(node.body if truth else node.orelse, env)
                    self.conditions = before
                    return outcomes
                self.add_boundary('context_exit_guard_unresolved', node.test, env, affected_scope='unknown')
            if isinstance(node, ast.Return):
                truth = self.context_truth(node.value, env) if node.value is not None else False
                previous = copy.deepcopy(env)
                values = self.marked(self.expression(node.value, env), node)
                exceptional, possible = self.context_operation_exits(node.value, previous, env)
                return exceptional + ([('return', env, values, {'truth': truth})] if possible else [])
        previous = copy.deepcopy(env) if self.context_execution else None
        exceptional = []
        # A possible exception uses the environment BEFORE evaluation. Simple
        # name/constant assignments cannot import a later definition into it.
        # 可能异常沿用求值前的环境，不能引入之后才建立的绑定。
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
            target = FunctionRef(self.ref.module, self.ref.qualname + '.' + node.name,
                                 self.ref.file_path, node.lineno)
            env[node.name] = [self.callable_value(target, node, values)]
            return normal(env)
        if isinstance(node, ast.ClassDef):
            env[node.name] = [{
                'kind': 'class',
                'module': self.ref.module,
                'source': self.ref.qualname + '.' + node.name,
                'relation': 'direct',
                'evidence': [self.evidence(node)],
                'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.If):
            self.expression(node.test, env)
            before = list(self.conditions)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            positive = copy.deepcopy(env)
            left = self.block(node.body, positive) if self.refine_guard(node.test, positive) else []
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            negative = copy.deepcopy(env)
            right = (self.block(node.orelse, negative)
                     if self.refine_guard(node.test, negative, positive=False) else [])
            self.conditions = before
            if getattr(self.analyzer, '_conditional_source_state', False):
                normal_left = any(outcome[0] == 'normal' for outcome in left)
                normal_right = any(outcome[0] == 'normal' for outcome in right)
                if normal_left != normal_right:
                    predicate = {'test': self.evidence(node.test), 'branch': normal_left}
                    for kind, state, _, _ in left + right:
                        if kind == 'normal':
                            for name, values in state.items():
                                state[name] = [dict(value, conditions=_unique(
                                    value.get('conditions', []) + [predicate])) for value in values]
            return exceptional + left + right
        if isinstance(node, ast.Try):
            return self.try_statement(node, env)
        if isinstance(node, ast.With):
            return self.with_statement(node, env)
        if isinstance(node, ast.AsyncWith):
            self.add_boundary('async_with_unsupported', node, env, affected_scope='unknown')
            return [('unknown', env, [], None)]
        if isinstance(node, (ast.For, ast.While)):
            before = copy.deepcopy(env)
            head = copy.deepcopy(env)
            exits = []
            if isinstance(node, ast.For):
                iterable = self.marked(self.project(self.expression(node.iter, env), '*', env), node.iter, 'derived')
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
        if isinstance(node, ast.Delete):
            for target in node.targets:
                self.invalidate_class_origins([value for name in _attribute_write_roots(target)
                    for value in env.get(name, [])], env)
                if isinstance(target, ast.Name):
                    values = env.get(target.id, [])
                    self.add_boundary('unsupported_assignment', node, env, values)
                    env[target.id] = []
                    continue
                if isinstance(target, ast.Subscript):
                    receivers = self.container_values(self.expression(target.value, env))
                    self.expression(target.slice, env)
                    if (receivers and all(value.get('kind') == 'container'
                            and value.get('container_shape') == 'dict'
                            for value in receivers)):
                        try:
                            key = ast.literal_eval(target.slice)
                        except (ValueError, TypeError):
                            key = '*'
                        roots, unknown = self.affected_values(receivers, env)
                        if key != '*' and len({value['source']
                                               for value in receivers}) == 1:
                            for reference in receivers:
                                remaining = []
                                for value in env.get(reference['source'], []):
                                    path = value.get('output_path', [])
                                    if path and path[0] == key:
                                        continue
                                    if path and path[0] == '*':
                                        value = dict(value, excluded_paths=_unique(
                                            value.get('excluded_paths', []) + [[key]]),
                                            conditions=value.get('conditions', []) +
                                                       list(self.conditions))
                                    remaining.append(value)
                                env[reference['source']] = remaining
                        self.mapping_effects.append({
                            'operation': 'delete', 'mapping': roots,
                            'element_path': [key],
                            'state_after': ('conditional' if self.conditions
                                            else 'absent' if key != '*' else 'unknown'),
                            'status': 'unknown_key' if key == '*' or unknown else 'bounded',
                            'conditions': list(self.conditions),
                            'evidence': self.evidence(node)})
                        if self.context_execution:
                            if key == '*':
                                self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                                                  affected_scope='unknown')
                            exceptional, possible = self.context_operation_exits(target, previous, env)
                            if not possible:
                                return exceptional
                        continue
                values = []
                if isinstance(target, (ast.Attribute, ast.Subscript)):
                    values = self.expression(target.value, env)
                self.add_boundary('unsupported_assignment', node, env, values)
            return exceptional + normal(env)
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
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            values = self.expression(node.value, env)
            if self.context_execution:
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
                literal = self.literal_fact(node.value, env)
                if literal is not None:
                    values = [dict(value, literal=literal) for value in values] or [
                        {'kind': 'context_data', 'source': self.ref.qualname,
                         'literal': literal, 'relation': 'direct',
                         'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if isinstance(node, ast.AugAssign):
                values = self.marked(self.expression(node.target, env) + values, node, 'derived')
            for target in targets:
                self.assign_target(target, values, env, node)
            return exceptional + normal(env)
        if isinstance(node, ast.Return):
            return exceptional + [('return', env, self.marked(self.expression(node.value, env), node), None)]
        if isinstance(node, ast.Expr):
            self.expression(node.value, env)
            if self.context_execution and isinstance(node.value, ast.Call):
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
            return exceptional + normal(env)
        if isinstance(node, ast.Raise):
            self.expression(node.exc, env)
            expression = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            exception = expression.id if isinstance(expression, ast.Name) else None
            return [('raise', env, [], exception)]
        if isinstance(node, ast.Import):
            for fact in import_facts(node):
                env[fact.python_binding] = [{
                    'kind': 'import',
                    'source': fact.name if fact.asname else fact.python_binding,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.ImportFrom):
            cached = cached_import(self.analyzer, self.ref, node, self.evidence, self.conditions)
            if cached is not None and cached not in self.cached_local_imports:
                self.cached_local_imports.append(cached)
            if node.level:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'relative_local_import', 'evidence': self.evidence(node)})
            for fact in import_facts(node):
                env[fact.python_binding] = ([{'kind': 'import',
                    'source': fact.module + '.' + fact.name,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
                                                  if not node.level else [])
            return normal(env)
        if isinstance(node, ast.Pass):
            return normal(env)
        self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_statement', 'evidence': self.evidence(node)})
        return [('unknown', env, [], None)]

    ## Assign abstract source records to a supported target.
    ## 将抽象来源记录赋给受支持的目标。
    #
    #  @param target Assignment target AST.
    #  @param values Source records being assigned.
    #  @param env Mutable abstract environment.
    #  @param node Statement or expression supplying evidence.
    #  @return None
    def assign_target(self, target, values, env, node):
        attribute = self.attribute_key(target, env)
        self.invalidate_class_origins([value for name in _attribute_write_roots(target)
            for value in env.get(name, [])], env)
        if attribute is not None:
            known = self.class_values(values, allow_incomplete=True, env=env)
            env[attribute[0]] = [dict(value, attribute_provenance=[{
                'receiver_class': attribute[1], 'attribute': target.attr,
                'storage_attribute': attribute[0].rsplit(':', 1)[-1],
                'assignment': self.evidence(node), 'conditions': copy.deepcopy(self.conditions)}])
                for value in self.marked(known, node)]
            if not known:
                self.add_boundary('unsupported_assignment', node, env, values)
            return
        if isinstance(target, ast.Attribute):
            candidates, _ = self.callable_targets(self.expression(target.value, env))
            self.modified_return_callables.update(
                (candidate[0].module, candidate[0].qualname) for candidate in candidates)
        for name in _attribute_write_roots(target):
            root = target
            while isinstance(root, (ast.Attribute, ast.Subscript)):
                root = root.value
            if isinstance(root, ast.Name):
                self.invalidate_literals(self.expression(root, env), env)
                candidates, _ = self.callable_targets(self.expression(root, env))
                self.modified_return_callables.update(
                    (candidate[0].module, candidate[0].qualname) for candidate in candidates)
            imported = env.get(name, [])
            modified = {value['source'] for value in imported
                        if value.get('instance_type') or value.get('class_type') or value.get('instance_candidates')}
            if modified:
                for key, sources in env.items():
                    env[key] = [dict(value, value_incomplete=True, instance_candidates=[])
                                if value.get('source') in modified and (
                                    value.get('instance_type') or value.get('class_type') or value.get('instance_candidates'))
                                else value for value in sources]
            if not imported and name not in env:
                source = self.analyzer.imports.get(self.ref.module, {}).get(name)
                if source:
                    imported = [{'kind': 'import', 'source': source,
                                 'relation': 'direct',
                                 'evidence': [self.evidence(node)],
                                 'conditions': list(self.conditions)}]
            if imported and all(value.get('kind') == 'import' for value in imported):
                env[name] = [dict(value, import_modified=True) for value in imported]
        if isinstance(target, ast.Name):
            env[target.id] = self.marked(values, node)
        elif isinstance(target, (ast.Tuple, ast.List)) and not any(isinstance(t, ast.Starred) for t in target.elts):
            for index, element in enumerate(target.elts):
                projected = self.project(values, index, env)
                self.assign_target(element, projected, env, node)
        elif isinstance(target, ast.Subscript):
            receiver = self.container_values(self.expression(target.value, env))
            if receiver and all(v['kind'] == 'container' and v['container_shape'] == 'dict' for v in receiver):
                index = target.slice.value if isinstance(target.slice, ast.Constant) else '*'
                self.expression(target.slice, env)
                for ref in receiver:
                    previous = env.get(ref['source'], [])
                    if index != '*' and len({v['source'] for v in receiver}) == 1:
                        updated = []
                        for value in previous:
                            path = value.get('output_path', [None])
                            if path[0] == index:
                                continue
                            if path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[index]]))
                            updated.append(value)
                        previous = updated
                    inserted = [dict(v, output_path=[index] + v.get('output_path', []))
                                for v in self.marked(self.materialize(values, env), node)]
                    env[ref['source']] = _loop_env({'items': previous + inserted})['items']
                    keys = env.get(ref['source'] + '$keys', [])
                    for marker in keys:
                        if marker['key'] == '*' and index != '*':
                            marker.setdefault('excluded_keys', []).append(index)
                    env[ref['source'] + '$keys'] = _unique(keys +
                        [{'kind': 'key', 'source': repr(index), 'key': index}])
            else:
                target_values = (env.get(target.value.id, [])
                                 if isinstance(target.value, ast.Name) else [])
                try:
                    affected_key = ast.literal_eval(target.slice)
                except (ValueError, TypeError):
                    affected_key = '*'
                target_values = [dict(value, output_path=[affected_key] +
                                      value.get('output_path', []))
                                 for value in target_values]
                self.add_boundary('unsupported_assignment', node, env,
                                  list(values) + list(target_values))
        else:
            target_values = (env.get(target.value.id, [])
                             if isinstance(target, ast.Attribute)
                             and isinstance(target.value, ast.Name) else [])
            self.add_boundary('unsupported_assignment', node, env,
                              list(values) + list(target_values))

    ## Select a stable plain source function named by a guard operand.
    ## 选择守卫操作数所指向的稳定普通源码函数。
    #
    #  @param node Bare name or source module attribute, never an evaluated call.
    #  @param env Current branch bindings.
    #  @return Unique undecorated module-level source target, or None.
    def guard_callable(self, node, env):
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        if isinstance(node, ast.Attribute):
            bindings = env.get(root.id)
            if bindings is not None:
                if not bindings or any(value.get('kind') != 'import' for value in bindings):
                    return None
            elif root.id not in self.analyzer.imports.get(self.ref.module, {}):
                return None
        candidates, complete = self.callable_targets(self.expression(node, env))
        if not complete or len(candidates) != 1:
            return None
        ref, function = candidates[0]
        if ('.' in ref.qualname or not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                or function.decorator_list):
            return None
        return candidates[0]

    ## Refine facts only on a supported guard branch, preserving dependency roots.
    ## 仅在受支持的守卫分支上细化事实，并保留依赖根。
    #
    #  @param test Already evaluated condition expression.
    #  @param env Independent state for the selected branch.
    #  @param positive Whether this branch requires a truthy condition.
    #  @param allow_callable Disable replay after compound-condition effects.
    #  @return False only for an incompatible closed callable identity.
    def refine_guard(self, test, env, positive=True, allow_callable=True):
        if (getattr(self.analyzer, '_conditional_source_state', False)
                and isinstance(test, ast.Constant) and bool(test.value) != positive):
            return False
        if (getattr(self.analyzer, '_conditional_source_state', False) and allow_callable
                and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)):
            sides = [self.class_values(env.get(value.id, []), env=env)
                     for value in (test.left, test.comparators[0])]
            if all(values and not any(value.get('value_incomplete') for value in values)
                   and len(_unique([value['class_type'] for value in values])) == 1 for values in sides):
                identical = sides[0][0]['class_type'] == sides[1][0]['class_type']
                truth = identical if isinstance(test.ops[0], ast.Is) else not identical
                if truth != positive:
                    return False
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return self.refine_guard(test.operand, env, not positive, allow_callable)
        if isinstance(test, ast.BoolOp) and (positive and isinstance(test.op, ast.And)
                or not positive and isinstance(test.op, ast.Or)):
            # Short-circuit evaluation already refines each operand before the
            # next one runs. Do not replay identities after intervening effects.
            allow_callable = allow_callable and not any(isinstance(node, (
                ast.Call, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom,
                ast.Subscript, ast.BinOp)) or isinstance(node, ast.Compare)
                and not all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
                for node in ast.walk(test))
            for operand in test.values:
                if not self.refine_guard(operand, env, positive, allow_callable):
                    return False
        if (allow_callable and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))):
            equal = positive != isinstance(test.ops[0], ast.IsNot)
            for variable, source in ((test.left, test.comparators[0]),
                                     (test.comparators[0], test.left)):
                if not isinstance(variable, ast.Name) or not env.get(variable.id):
                    continue
                values = env[variable.id]
                if any(value.get('kind') not in ('parameter', 'capture', 'callable')
                       or value.get('relation') != 'direct' or any(value.get(flag) for flag in (
                           'projection', 'output_path', 'value_incomplete')) for value in values):
                    continue
                target = self.guard_callable(source, env)
                if target is None:
                    continue
                if all(value.get('literal') is not None for value in values):
                    return not equal
                candidates, complete = self.callable_targets(values)
                if complete and (all(candidate[0] != target[0] for candidate in candidates) if equal
                        else all(candidate[0] == target[0] for candidate in candidates)):
                    return False
                remaining = []
                for value in values:
                    known, closed = self.callable_targets([value])
                    if closed and len(known) == 1 and (known[0][0] == target[0]) != equal:
                        continue
                    remaining.append(value)
                if not equal:
                    env[variable.id] = remaining
                    return bool(remaining)
                evidence = self.evidence(test)
                env[variable.id] = [dict(value, callable_type=asdict(target[0]),
                    callable_evidence=_unique(value.get('callable_evidence', []) + [evidence]),
                    conditions=_unique(value.get('conditions', []) + list(self.conditions)))
                    for value in remaining]
                return True
        if (allow_callable and isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == 'isinstance' and len(test.args) == 2 and not test.keywords
                and isinstance(test.args[0], ast.Name) and isinstance(test.args[1], ast.Name)
                and test.args[1].id == 'str'
                and all(name not in env and name not in self.analyzer.imports.get(self.ref.module, {})
                        and name not in self.analyzer.module_bindings.get(self.ref.module, set())
                        and self.analyzer._resolve(self.ref, name) is None for name in ('str', 'isinstance'))):
            name = test.args[0].id
            targets, complete = self.callable_targets(env.get(name, []))
            if targets and complete:
                # Closed source function objects are not strings. Do not run
                # an impossible recursive branch and contaminate its sibling.
                return not positive
            if positive:
                env[name] = [dict(v, python_shape='str',
                                  conditions=v.get('conditions', []) + list(self.conditions))
                             for v in env.get(name, [])]
        return True

    ## Analyze supported try, handler and cleanup paths.
    ## 分析受支持的 try、异常处理及清理路径。
    #
    #  @param node Try statement AST.
    #  @param env Abstract environment at entry.
    #  @return Control-flow outcome tuples.
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

    ## Analyze the function body and publish its collected summary facts.
    ## 分析函数体并发布收集到的摘要事实。
    #
    #  @return None
    def run(self):
        if getattr(self.node, '_flow_branch_budget', None) is not None:
            self.result.boundaries.append({'function': asdict(self.ref),
                'reason': 'literal_branch_budget',
                'evidence': self.evidence(self.node._flow_branch_budget)})
        args = self.node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [a for a in (args.vararg, args.kwarg) if a]
        env = {a.arg: [{'kind': 'parameter', 'source': a.arg, 'relation': 'direct',
                        'evidence': [self.evidence(a)], 'conditions': []}] for a in parameters}
        for parameter, facts in self.incoming.items():
            if parameter in env:
                root = env[parameter][0]
                env[parameter] = [dict(root, **fact) for fact in facts]
        if self.receiver_class is not None and parameters:
            env[parameters[0].arg][0]['class_type'] = asdict(self.receiver_class)
        for values in list(env.values()):
            for value in values:
                for effect in value.get('class_lookup_mutations', []):
                    self.register_class_lookup_effect(effect, env)
        for parameter, shape in ((args.vararg, 'tuple'), (args.kwarg, 'dict')):
            if parameter is None:
                continue
            heap = '$parameter:%s:%s:%s' % (
                self.ref.file_path, self.ref.qualname, parameter.arg)
            root = env[parameter.arg][0]
            env[heap] = [dict(root, relation='contained', output_path=['*'])]
            env[heap + '$keys'] = [
                {'kind': 'key', 'source': '*', 'key': '*'}]
            env[parameter.arg] = [{
                'kind': 'container', 'source': heap,
                'container_shape': shape, 'parameter_container': parameter.arg,
                'relation': 'direct', 'evidence': [self.evidence(parameter)],
                'conditions': []}]
        shape_contract = self.analyzer.parameter_shapes.get(
            self.ref.module + '.' + self.ref.qualname, {})
        shapes = shape_contract.get('parameters', {})
        for name, shape in shapes.items():
            if name in env:
                env[name] = [dict(value, python_shape=shape,
                                  shape_provenance=shape_contract['provenance'])
                             for value in env[name]]
        for local in self.analyzer._scope_facts(self.node).bound:
            env.setdefault(local, [])
        capture_objects = {}
        for capture in self.analyzer._captures(self.ref, self.node):
            root = {'kind': 'capture', 'source': capture, 'relation': 'direct',
                    'evidence': [], 'conditions': []}
            facts = self.incoming.get(capture, [])
            binding = facts[0].get('capture_container_binding') if len(facts) == 1 else None
            if binding:
                identity = binding['source'], binding['shape']
                if identity not in capture_objects:
                    heap = '$capture:%s:%s:%s' % (self.ref.file_path, self.ref.qualname, capture)
                    capture_objects[identity] = heap, capture
                    env[heap] = [dict(root, relation='contained', output_path=['*'])]
                    env[heap + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                heap, origin = capture_objects[identity]
                env[capture] = [{'kind': 'container', 'source': heap,
                    'container_shape': binding['shape'], 'parameter_container': origin,
                    'relation': 'direct', 'evidence': copy.deepcopy(binding.get('evidence', [])),
                    'conditions': copy.deepcopy(binding.get('conditions', []))}]
            else:
                env[capture] = [root]
        outcomes = ([('return', env,
                      self.marked(self.expression(self.node.body, env), self.node.body), None)]
                    if isinstance(self.node, ast.Lambda) else self.block(self.node.body, env))
        generator = contains_yield(self.node)
        self.outcomes = outcomes
        self.exit_kinds = {kind for kind, _, _, _ in outcomes}
        for kind, state, values, _ in outcomes:
            if kind == 'return' and not generator:
                returned = self.materialize(values, state)
                self.normal_returns.append(returned)
                self.returns.extend(returned)
            elif kind in ('normal', 'unknown'):
                self.incomplete_return = True
        if generator:
            self.returns.extend(self.yields)
        self.returns = _unique(self.returns)
        merged = {}
        for call in self.calls:
            if call.id not in merged:
                merged[call.id] = call
            else:
                previous = merged[call.id]
                if previous.target != call.target:
                    previous.target = None
                if (previous.target_status != call.target_status
                        and 'local_container_protocol' in (
                            previous.target_status, call.target_status)):
                    previous.target = None
                    previous.target_status = 'receiver_unresolved'
                for attribute in ('parameter_bindings', 'parameter_flows', 'argument_sources', 'argument_flows',
                                   'capture_bindings', 'receiver_sources',
                                   'receiver_type_evidence', 'mutation_flows',
                                   'decorator_identity_evidence',
                                   'return_dependencies', 'effects', 'target_candidates',
                                   'binding_issues'):
                    setattr(previous, attribute, _unique(getattr(previous, attribute) + getattr(call, attribute)))
                previous.callable_sources = _unique(previous.callable_sources + call.callable_sources)
                previous.conditional_returns = _unique(previous.conditional_returns + call.conditional_returns)
                previous.class_method_bindings = _unique(previous.class_method_bindings + call.class_method_bindings)
                previous.class_metadata_bindings = _unique(previous.class_metadata_bindings + call.class_metadata_bindings)
                previous.class_read_bindings = _unique(previous.class_read_bindings + call.class_read_bindings)
                previous.conditional_source_bindings = _unique(
                    previous.conditional_source_bindings + call.conditional_source_bindings)
                previous.candidate_paths = _unique(previous.candidate_paths + call.candidate_paths)
                previous.constructor_bindings = _unique(previous.constructor_bindings + call.constructor_bindings)
                previous.instance_method_bindings = _unique(previous.instance_method_bindings + call.instance_method_bindings)
                previous.result_sources = _merge_result_sources(
                    previous.result_sources, call.result_sources)
                if previous.binding_status != call.binding_status:
                    previous.binding_status = 'uncertain'
        self.calls = list(merged.values())
        partial_effect_calls = {boundary.get('call_id') for boundary in self.result.boundaries
                                if boundary['reason'] == 'mapping_effect_unproven'}
        for call in self.calls:
            if call.id in partial_effect_calls:
                for effect in call.effects:
                    if effect.get('completion') == 'normal_return':
                        effect.update(state_after='conditional', status='partial_context')
        for effect in self.mapping_effects:
            if effect.get('call_id') in partial_effect_calls:
                effect.update(state_after='conditional', status='partial_context')
        ## Collect source nodes for the function summary.
        ## 收集函数摘要使用的源码节点。
        #
        #  @param node AST node to inspect.
        #  @return None
        def collect(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call):
                call_id = _call_key(self.ref.file_path, node)
                if call_id not in merged and self.remaining > 0:
                    self.remaining -= 1
                    call = FlowCall(call_id, self.ref, ast.unparse(node.func), node.lineno, node.col_offset,
                                    node.end_lineno, node.end_col_offset,
                                    analysis_status='not_analyzed', target_status='flow_not_analyzed')
                    self.calls.append(call)
                    merged[call_id] = call
            for child in ast.iter_child_nodes(node):
                collect(child)
        body = [self.node.body] if isinstance(self.node, ast.Lambda) else self.node.body
        for statement in body:
            collect(statement)
        self.calls.sort(key=lambda c: (c.lineno, c.col_offset))
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'fresh_mapping_member_checks': fresh_mapping_member_checks(self),
                                      'keyword_checks': keyword_validation_checks(
                                          self.analyzer, self.ref, self.node),
                                      'capture_rejection_guards': capture_rejection_checks(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_key_accesses': mapping_key_access_footprints(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_attribute_transfers': mapping_attribute_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_return_transfers': mapping_return_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'container_predicates': container_predicate_checks(
                                          self.analyzer, self.ref, self.node),
                                      'parameter_shapes': copy.deepcopy(shapes),
                                      'generator': generator,
                                      'loops': self.loops,
                                      'mapping_effects': self.mapping_effects,
                                      'returns': self.returns,
                                      'decorator_effects': self.analyzer._decoration_facts((self.ref, self.node))})
        if self.context_managers:
            self.result.functions[-1]['context_managers'] = self.context_managers
        fresh = self.analyzer._fresh_decoration_facts((self.ref, self.node))
        if fresh:
            self.result.functions[-1]['fresh_function_decorations'] = fresh
        wrapper = factory_wrapper(self.analyzer, (self.ref, self.node))
        if wrapper is not None and 'forwarding' in wrapper:
            self.result.functions[-1]['source_wrapper_forwarding'] = [wrapper]
        query = metadata_query(self.analyzer, (self.ref, self.node))
        if query is not None:
            self.result.functions[-1]['native_callable_metadata_queries'] = [query]
        observers = observer_effects(self.analyzer, (self.ref, self.node))
        if observers:
            self.result.functions[-1]['native_class_metadata_observers'] = observers
        if self.cached_local_imports:
            self.result.functions[-1]['cached_local_imports'] = self.cached_local_imports
        decorations = self.result.functions[-1]['decorator_effects']
        if decorations and self.analyzer._descriptor_kind((self.ref, self.node)) is None:
            for fact in decorations:
                if fact['body_binding_status'] != 'preserved':
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'decorator_effect_unconfirmed',
                        'identity_status': fact['identity_status'],
                        'body_binding_status': fact['body_binding_status'],
                        'issues': copy.deepcopy(fact['boundaries']),
                        'evidence': copy.deepcopy(fact['expression'])})
        object_fact, _ = self.analyzer._object_returns((self.ref, self.node))
        if object_fact:
            self.result.functions[-1]['return_objects'] = [{
                'parameter': object_fact['parameter'], 'identity': 'argument_alias',
                'evidence': [self.evidence(statement)
                             for statement in object_fact['evidence']]}]
            if object_fact.get('conditions'):
                self.result.functions[-1]['return_objects'][0]['conditions'] = object_fact['conditions']
            if object_fact.get('effects'):
                self.result.functions[-1]['return_objects'][0].update(
                    completion='normal_return', requires_shapes=_unique([
                        {'parameter': effect.target,
                         'shapes': ['dict'] if effect.receiver_shape else ['dict', 'list', 'set']}
                        for effect in object_fact['effects']]))
        guarded = self.analyzer._guarded_object_returns((self.ref, self.node))
        if guarded:
            self.result.functions[-1]['return_objects'] = _unique(
                self.result.functions[-1].get('return_objects', []) + guarded)
        if self.receiver_class is not None:
            self.result.functions[-1]['receiver_contexts'] = [asdict(self.receiver_class)]
        self.result.calls.extend(self.calls)
