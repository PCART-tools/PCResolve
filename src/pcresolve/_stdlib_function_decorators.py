## @package pcresolve._stdlib_function_decorators
#  Conditional source models for standard decorators that return plain functions.

import ast

from .class_attribute_effects import _ClassEffectLimit


def _coroutine_imports_stable(analyzer):
    cached = getattr(analyzer, "_coroutine_namespace_premises", None)
    if cached is not None:
        return cached
    paths, inspected = set(), 0
    stable = True
    for module, bodies in analyzer.module_bodies.items():
        if any(
            value == "importlib" or value.startswith("importlib.")
            for value in analyzer.imports.get(module, {}).values()
        ):
            stable = False
        names = {
            name: value
            for name, value in analyzer.imports.get(module, {}).items()
            if value
            in (
                "asyncio",
                "asyncio.coroutines",
                "asyncio.coroutine",
                "asyncio.coroutines.coroutine",
            )
        }
        for path, body in bodies:
            paths.add(path)
            parents = {}
            nodes = []
            for statement in body:
                for node in ast.walk(statement):
                    inspected += 1
                    if inspected > 100000:
                        raise _ClassEffectLimit()
                    nodes.append(node)
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
            for node in nodes:
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    imported = analyzer.imports.get(module, {}).get(node.id, "")
                    if (
                        node.id in ("__import__", "exec", "eval")
                        or imported == "importlib.import_module"
                    ):
                        stable = False
                if not isinstance(node, ast.Name) or node.id not in names:
                    continue
                if not isinstance(node.ctx, ast.Load):
                    stable = False
                    continue
                parent = parents.get(node)
                if names[node.id].endswith(".coroutine"):
                    if not (
                        isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node in parent.decorator_list
                    ):
                        stable = False
                    continue
                if not isinstance(parent, ast.Attribute) or parent.value is not node:
                    stable = False
                    continue
                current = parent
                while isinstance(current, (ast.Attribute, ast.Subscript)):
                    if (
                        isinstance(current.ctx, (ast.Store, ast.Del))
                        or isinstance(current, ast.Attribute)
                        and current.attr == "__dict__"
                    ):
                        stable = False
                    next_node = parents.get(current)
                    if not (
                        isinstance(next_node, (ast.Attribute, ast.Subscript))
                        and next_node.value is current
                    ):
                        break
                    current = next_node
                if isinstance(current, ast.Attribute) and current.attr in (
                    "coroutine",
                    "coroutines",
                ):
                    parent = parents.get(current)
                    if not (
                        isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and current in parent.decorator_list
                    ):
                        stable = False
    cached = stable, tuple(sorted(paths))
    analyzer._coroutine_namespace_premises = cached
    return cached


## Recognize only an imported standard coroutine decorator on a non-entry member.
#  @param analyzer Fixed source/import snapshot, with no local asyncio replacement.
#  @param owner Exact source class identity.
#  @param member Function definition whose defaults/annotations are checked separately.
#  @param shadowed Names already bound in the executing class namespace.
#  @param dependencies Set retaining all inspected import/mutation source files.
#  @return Explicit standard-library premise, or None for unproved names/effects.
def namespace_function_decorator(analyzer, owner, member, shadowed, dependencies=None):
    if (
        member.name in ("__init__", "__new__")
        or len(member.decorator_list) != 1
        or not isinstance(member.decorator_list[0], (ast.Name, ast.Attribute))
        or any(
            name == "asyncio" or name.startswith("asyncio.")
            for name in analyzer.module_bodies
        )
    ):
        return None
    parts = []
    expression = member.decorator_list[0]
    while isinstance(expression, ast.Attribute):
        if len(parts) >= 20:
            raise _ClassEffectLimit()
        parts.append(expression.attr)
        expression = expression.value
    if not isinstance(expression, ast.Name):
        return None
    name = ".".join([expression.id] + list(reversed(parts)))
    head, dot, rest = name.partition(".")
    imported = analyzer.imports.get(owner.module, {}).get(head, "")
    if (
        imported + (dot + rest if dot else "")
        not in ("asyncio.coroutine", "asyncio.coroutines.coroutine")
        or head in shadowed
        or not analyzer._stable_import_name(owner.module + "." + head)
    ):
        return None
    stable, paths = _coroutine_imports_stable(analyzer)
    if not stable:
        return None
    if dependencies is not None:
        dependencies.update(paths)
    # This premise includes the target Python providing the historical symbol.
    # It does not execute the decorator, the method body, or a constructor.
    return "stdlib_asyncio_coroutine_binding"
