## @package pcresolve.flow.proofs.namespaces.metadata._kind_alias_scan
#  Module-local closure checks for inspect.Parameter kind aliases.
#  检查 inspect.Parameter kind 别名在单个模块内是否保持封闭。

import ast


_KIND_MEMBERS = ('POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD', 'VAR_POSITIONAL',
                 'KEYWORD_ONLY', 'VAR_KEYWORD')


## Propagate local enum aliases and identify stable module-level exports.
## 传播局部枚举别名，并标记稳定的模块级导出。
#
#  @param module Source module name.
#  @param nodes AST nodes in module traversal order.
#  @param scopes Lexical scope associated with each node.
#  @param reference Source reference used for canonical import lookup.
#  @param canonical Resolve an expression against source imports and scope.
#  @param stable_module_alias Confirm a module-level alias remains stable.
#  @return Alias names, module-level aliases, or None for an open binding.
def collect_kind_alias_bindings(module, nodes, scopes, reference, *, canonical,
                                stable_module_alias):
    aliases = set()
    module_aliases = set()
    for _ in range(64):
        previous = set(aliases)
        for node in nodes:
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            source = (isinstance(value, ast.Attribute)
                and canonical(reference, scopes[value], value.value) == 'inspect.Parameter'
                and value.attr in _KIND_MEMBERS)
            if not (source or isinstance(value, ast.Name) and value.id in aliases):
                continue
            if isinstance(scopes[node], ast.ClassDef):
                # A class slot is externally retrievable even without a local read.
                return None
            if any(not isinstance(target, ast.Name) for target in node.targets):
                return None
            if scopes[node] is None:
                if (len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name)
                        or not stable_module_alias(module, node.targets[0].id)):
                    return None
                module_aliases.add((module, node.targets[0].id))
            aliases.update(target.id for target in node.targets)
        if aliases == previous:
            return aliases, module_aliases
    return None


## Reject aliases used outside comparisons, replacements, or constructor metadata.
## 拒绝别名被用于比较、元数据替换或构造参数之外的场景。
#
#  @param module Source module name, for diagnostics.
#  @param aliases Propagated local enum aliases.
#  @param nodes AST nodes in module traversal order.
#  @param parents Parent index for the module nodes.
#  @param scopes Lexical scope associated with each node.
#  @param reference Source reference used for canonical import lookup.
#  @param canonical Resolve an expression against source imports and scope.
#  @param identity_operand Accept a native identity-comparison use.
#  @param kind_comparison Accept a proven Parameter-kind comparison.
#  @param kind_replacement Accept a proven metadata replacement use.
#  @param debug_alias_use Optional callback for an unrecognized name use.
#  @return True when all alias reads stay within the supported grammar.
def kind_alias_uses_closed(module, aliases, nodes, parents, scopes, reference, *, canonical,
                           identity_operand, kind_comparison, kind_replacement,
                           debug_alias_use=None):
    for node in nodes:
        if not (isinstance(node, ast.Name) and node.id in aliases
                and isinstance(node.ctx, ast.Load)):
            continue
        parent = parents.get(node)
        if identity_operand(node, parent):
            continue
        if kind_comparison(node, parent, scopes[node]):
            continue
        if kind_replacement(node, parent, scopes[node]):
            continue
        if debug_alias_use is not None:
            debug_alias_use(module, node, parent, scopes[node])
        if isinstance(parent, ast.Assign) and parent.value is node:
            continue
        if (isinstance(parent, ast.Call) and len(parent.args) >= 2
                and parent.args[1] is node
                and canonical(reference, scopes[parent], parent.func) == 'inspect.Parameter'):
            continue
        return False
    return True


## Validate kind references and return module aliases that need import checks.
## 验证 kind 引用，并返回仍需跨模块检查的模块级别名。
#
#  @param module Source module name.
#  @param nodes AST nodes in module traversal order.
#  @param parents Parent index for the module nodes.
#  @param scopes Lexical scope associated with each module node.
#  @param reference Source reference used for canonical import lookup.
#  @param canonical Resolve an expression against source imports and scope.
#  @param identity_operand Accept a native identity-comparison use.
#  @param kind_comparison Accept a proven Parameter-kind comparison.
#  @param kind_replacement Accept a proven metadata replacement use.
#  @param stable_module_alias Confirm a module-level alias remains stable.
#  @return Module-level aliases to check, or None when a use is open.
def inspect_module_kind_aliases(module, nodes, parents, scopes, reference, *, canonical,
                                identity_operand, kind_comparison, kind_replacement,
                                stable_module_alias, debug_alias_use=None):
    for node in nodes:
        if not (isinstance(node, ast.Attribute)
                and canonical(reference, scopes[node], node.value) == 'inspect.Parameter'
                and node.attr in _KIND_MEMBERS):
            continue
        parent = parents.get(node)
        if identity_operand(node, parent):
            continue
        if kind_comparison(node, parent, scopes[node]):
            continue
        if isinstance(parent, ast.Assign) and parent.value is node:
            continue
        if (isinstance(parent, ast.Call) and len(parent.args) >= 2
                and parent.args[1] is node
                and canonical(reference, scopes[parent], parent.func) == 'inspect.Parameter'):
            continue
        return None

    collected = collect_kind_alias_bindings(
        module, nodes, scopes, reference,
        canonical=canonical, stable_module_alias=stable_module_alias)
    if collected is None:
        return None
    aliases, kind_aliases = collected
    if not kind_alias_uses_closed(
            module, aliases, nodes, parents, scopes, reference,
            canonical=canonical, identity_operand=identity_operand,
            kind_comparison=kind_comparison, kind_replacement=kind_replacement,
            debug_alias_use=debug_alias_use):
        return None
    return kind_aliases


## Reject uses of an exported module alias from another source module.
## 拒绝其他源码模块对可导入模块级别名的读取。
#
#  @param module_aliases Stable local aliases discovered by the module scan.
#  @param module_bodies Source module bodies indexed by module name.
#  @param imports Imported local names mapped to their qualified source target.
#  @param identity_operand Identity-comparison use predicate.
#  @return True when no imported alias gains an unsupported use.
def imported_kind_aliases_are_closed(module_aliases, module_bodies, imports,
                                     identity_operand):
    for module, local in module_aliases:
        qualified = module + '.' + local
        for candidate_module, bodies in module_bodies.items():
            for local_name, imported in imports.get(candidate_module, {}).items():
                if imported != qualified:
                    continue
                if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                       and node.id == local_name and not identity_operand(node, None)
                       for _, body in bodies
                       for node in ast.walk(ast.Module(body=body, type_ignores=[]))):
                    return False
    return True
