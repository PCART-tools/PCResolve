## @package pcresolve.flow.proofs.callables._constructor_retention_values
#  Literal and branch-condition reasoning for receiver retention proofs.
#  接收者存储保留证明中的字面量与分支条件推理。

import ast


## Resolve a supported literal, local, or receiver attribute value.
## 解析受支持的字面量、局部变量或接收者属性值。
#
#  @param node Expression whose value is requested.
#  @param locals_ Known local literal values.
#  @param receiver Receiver parameter name.
#  @param receiver_values Known receiver attribute values.
#  @param unknown Per-proof unknown sentinel.
#  @return Known value or the unknown sentinel.
def known_receiver_value(node, locals_, receiver, receiver_values, unknown):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return locals_.get(node.id, unknown)
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == receiver):
        return receiver_values.get(node.attr, unknown)
    return unknown


## Evaluate only conditions whose value dependencies are statically known.
## 仅计算依赖值均可静态确定的条件。
#
#  @param node Condition expression.
#  @param locals_ Known local literal values.
#  @param receiver Receiver parameter name.
#  @param owner Source reference owning the current method.
#  @param method Method AST node used for builtin resolution.
#  @param unknown Per-proof unknown sentinel.
#  @param known_value Resolve a supported literal or local value.
#  @param builtin_name_status Query the source binding of a builtin name.
#  @return Boolean result or the unknown sentinel.
def known_receiver_condition(node, locals_, receiver, owner, method, unknown, *,
                             known_value, builtin_name_status):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'len' and len(node.args) == 1 and not node.keywords
            and builtin_name_status(owner, method, 'len') == 'confirmed_builtin'):
        value = known_value(node.args[0], locals_, receiver)
        if type(value) in (tuple, list, dict, str, bytes):
            return bool(len(value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = known_receiver_condition(
            node.operand, locals_, receiver, owner, method, unknown,
            known_value=known_value, builtin_name_status=builtin_name_status)
        return unknown if value is unknown else not value
    if isinstance(node, ast.BoolOp):
        values = [known_receiver_condition(
            value, locals_, receiver, owner, method, unknown,
            known_value=known_value, builtin_name_status=builtin_name_status)
            for value in node.values]
        if isinstance(node.op, ast.And):
            if False in values:
                return False
            return all(values) if unknown not in values else unknown
        if True in values:
            return True
        return all(not value for value in values) if unknown not in values else unknown
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        left = known_value(node.left, locals_, receiver)
        right = known_value(node.comparators[0], locals_, receiver)
        if left is unknown or right is unknown:
            return unknown
        if isinstance(node.ops[0], ast.Is):
            return left is right
        if isinstance(node.ops[0], ast.IsNot):
            return left is not right
    value = known_value(node, locals_, receiver)
    return unknown if value is unknown else bool(value)
