## @package pcresolve.flow.transfer._summary_support
#  Provide shared value-flow summary helpers.
#
#
#  Supplies call identifiers, environment keys and convergence helpers used by
#  transfer components; it does not construct an analyzer.
#  为传播组件提供调用标识、环境键和收敛辅助函数，不负责构造分析器。



import ast
import builtins
from dataclasses import replace

from pcresolve.facts.program_facts import SourceSpan
from pcresolve.facts.scope_facts import FLOW_SCOPE


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
