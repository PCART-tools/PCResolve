## @package pcresolve.flow.proofs.callables.dispatch.finite_dispatch
#  Expand finite generated dispatch.
#
#
#  Bounded source-only expansion of generated callable tables.
#  对生成的可调用表进行有界、仅基于源码的展开。



import ast


## Generated dispatch expansion exceeded its explicit syntax budget.
## 生成式分派展开超过显式语法预算。
class DispatchLimit(ValueError):
    pass


## Expand one closed module-level comprehension without executing source.
## 不执行源码，展开一个封闭的模块级推导式。
#
#  @param expression Dict comprehension over literal module dict keys.
#  @param body Original module statements, including nested writes and escapes.
#  @param bindings Module binding sites indexed by name.
#  @param stable_function Predicate for a unique stable source function symbol.
#  @return Equivalent finite dict AST, or None outside the supported subset.
def generated_dict(expression, body, bindings, stable_function):
    if (not isinstance(expression, ast.DictComp) or len(expression.generators) != 1
            or 'globals' in bindings):
        return None
    generator = expression.generators[0]
    iterator, value = generator.iter, expression.value
    if (generator.is_async or generator.ifs or not isinstance(generator.target, ast.Name)
            or generator.target.id == 'globals'
            or not isinstance(iterator, ast.Call) or iterator.args or iterator.keywords
            or not isinstance(iterator.func, ast.Attribute) or iterator.func.attr != 'keys'
            or not isinstance(iterator.func.value, ast.Name)
            or not isinstance(value, ast.Subscript) or not isinstance(value.value, ast.Call)
            or not isinstance(value.value.func, ast.Name) or value.value.func.id != 'globals'
            or value.value.args or value.value.keywords
            or not isinstance(value.slice, ast.Name) or value.slice.id != generator.target.id):
        return None
    name = iterator.func.value.id
    assignments = bindings.get(name, [])
    if (len(assignments) != 1 or not isinstance(assignments[0], ast.Assign)
            or assignments[0] not in body or len(assignments[0].targets) != 1
            or not isinstance(assignments[0].value, ast.Dict)
            or assignments[0].lineno >= expression.lineno):
        return None
    source = assignments[0].value
    if len(source.keys) > 64:
        raise DispatchLimit('generated_dispatch_budget')
    if any(not isinstance(key, ast.Constant) or type(key.value) is not str for key in source.keys):
        return None
    try:
        ast.literal_eval(source)
    except (ValueError, TypeError):
        return None

    # Reject reflection and any other use that could mutate or leak the key set.
    # 拒绝反射及其他可能修改或泄露键集合的使用方式。
    count = 0
    for statement in body:
        for parent in ast.walk(statement):
            count += 1
            if count > 20000:
                raise DispatchLimit('generated_dispatch_budget')
            for child in ast.iter_child_nodes(parent):
                if not isinstance(child, ast.Name) or not isinstance(child.ctx, ast.Load):
                    continue
                if child.id in ('globals', 'locals', 'vars', 'exec', 'eval'):
                    if child is not value.value.func:
                        return None
                if child.id == name and child is not iterator.func.value:
                    # No aliases, mutation, escape or unknown use of the key set.
                    return None

    ## Evaluate a bounded string-concatenation key for one literal symbol.
    ## 为单个字面量符号计算有界字符串拼接键。
    #
    #  @param node Key expression AST.
    #  @param symbol Current literal symbol.
    #  @param depth Current recursive expression depth.
    #  @return Concrete key or None for unsupported expressions.
    def key_for(node, symbol, depth=0):
        if depth > 16:
            raise DispatchLimit('generated_dispatch_budget')
        if isinstance(node, ast.Constant) and type(node.value) is str:
            return node.value
        if isinstance(node, ast.Name) and node.id == generator.target.id:
            return symbol
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = key_for(node.left, symbol, depth + 1), key_for(node.right, symbol, depth + 1)
            if left is not None and right is not None and len(left) + len(right) <= 1024:
                return left + right
        return None

    # Every table entry must identify a stable function before expansion succeeds.
    # 展开成功前，每个表项都必须指向稳定函数。
    keys, values = [], []
    for literal in source.keys:
        symbol = literal.value
        key = key_for(expression.key, symbol)
        if key is None or not stable_function(symbol):
            return None
        keys.append(ast.copy_location(ast.Constant(value=key), expression.key))
        values.append(ast.copy_location(ast.Name(id=symbol, ctx=ast.Load()), value))
    return ast.copy_location(ast.Dict(keys=keys, values=values), expression)
