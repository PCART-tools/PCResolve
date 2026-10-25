## @package pcresolve.star_imports
#  Bounded source-only expansion of literal __all__ imports.

import ast
import os
from dataclasses import dataclass

from .import_facts import import_facts, resolve_relative_module
from .scope_facts import statement_scope_facts


## Source witnesses for unambiguous wildcard bindings.
@dataclass(frozen=True)
class StarImportFacts:
    ## Module to local name to qualified source name.
    aliases: dict
    ## Module to local name to original ImportFrom statement.
    bindings: dict


## Expand literal export lists without importing or evaluating target code.
#  @param module_bodies Module to (source path, top-level statements) sequences.
#  @param max_nodes Maximum inspected AST nodes across this source snapshot.
#  @param max_depth Maximum nested wildcard-import depth.
#  @return Facts; open, conflicting or cyclic namespaces supply no aliases.
def static_star_imports(module_bodies, max_nodes=1000000, max_depth=32):
    # Without a top-level wildcard import there can be no wildcard aliases.
    # Avoid inspecting expression/function bodies merely to return empty facts.
    if not any(isinstance(statement, ast.ImportFrom)
               and any(alias.name == '*' for alias in statement.names)
               for sources in module_bodies.values() if len(sources) == 1
               for _, body in sources for statement in body):
        return StarImportFacts({}, {})
    records = {}
    mutation_nodes = []
    remaining = max_nodes
    for module, sources in module_bodies.items():
        if len(sources) != 1:
            continue
        path, body = sources[0]
        bindings, stars, aliases = {}, [], {}
        exports, all_assignments, unsafe = None, 0, False
        for statement in body:
            nodes = []
            for node in ast.walk(statement):
                remaining -= 1
                if remaining < 0:
                    return StarImportFacts({}, {})
                nodes.append(node)
            if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                   and node.id in ('exec', 'eval', 'globals', 'locals', 'vars', '__import__')
                   for node in nodes):
                unsafe = True
            # A loaded __all__ may escape or be mutated; literal declarations
            # alone are evidence, not general constant propagation.
            if any(isinstance(node, ast.Name) and node.id == '__all__'
                   and isinstance(node.ctx, ast.Load) for node in nodes):
                all_assignments += 2
            if isinstance(statement, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == '__all__'
                    for target in statement.targets):
                all_assignments += 1
                value = statement.value
                if (len(statement.targets) == 1 and isinstance(value, (ast.List, ast.Tuple))
                        and len(value.elts) <= 10000 and all(
                            isinstance(item, ast.Constant) and isinstance(item.value, str)
                            and item.value.isidentifier() for item in value.elts)):
                    exports = tuple(item.value for item in value.elts)
            for name in statement_scope_facts([statement]).bound:
                bindings.setdefault(name, []).append(statement)
            for node in nodes:
                if isinstance(node, (ast.Attribute, ast.Subscript, ast.Call, ast.Assign)):
                    mutation_nodes.append((module, node))
                if isinstance(node, ast.Global):
                    for name in node.names:
                        bindings.setdefault(name, []).append(node)
            for fact in import_facts(statement):
                if fact.kind == 'import':
                    aliases[fact.python_binding] = fact.name if fact.asname else fact.python_binding
                else:
                    base = resolve_relative_module(
                        module, os.path.basename(path).startswith('__init__.'),
                        fact.module, fact.level)
                    if fact.wildcard:
                        stars.append((base, statement))
                    else:
                        aliases[fact.python_binding] = base + '.' + fact.name
        records[module] = (bindings, aliases, stars,
                           exports if all_assignments == 1
                           and len(bindings.get('__all__', [])) == 1 else None, unsafe)

    invalidated = set()

    def imported_name(module, node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        record = records.get(module)
        head = record[1].get(node.id) if record else None
        return head + ''.join('.' + part for part in reversed(parts)) if head else None

    for module, node in mutation_nodes:
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                node.ctx, (ast.Store, ast.Del)):
            selected = node.value if isinstance(node, ast.Subscript) else node
            name = imported_name(module, selected)
            if name:
                invalidated.add(name.split('.__dict__')[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ('setattr', 'delattr'):
                if node.args:
                    name = imported_name(module, node.args[0])
                    if name:
                        invalidated.add(name)
            elif isinstance(node.func, ast.Attribute):
                name = imported_name(module, node.func.value)
                if name and name.endswith('.__all__'):
                    invalidated.add(name)
            for argument in node.args + [keyword.value for keyword in node.keywords]:
                name = imported_name(module, argument)
                if name and (name in records or name.endswith('.__all__')):
                    invalidated.add(name)
        elif isinstance(node, ast.Assign):
            name = imported_name(module, node.value)
            if name and (name in records or name.endswith('.__all__')):
                invalidated.add(name)

    def invalid(name):
        return any(name == prefix or name.startswith(prefix + '.') for prefix in invalidated)

    resolved = {}
    operations = max_nodes

    def expand(module, active):
        nonlocal operations
        operations -= 1
        if operations < 0:
            return None
        if module in resolved:
            return resolved[module]
        if module in active or len(active) >= max_depth or module not in records:
            return None
        bindings, _, stars, _, unsafe = records[module]
        if unsafe:
            return None
        candidates = {}
        for base, statement in stars:
            record = records.get(base)
            if record is None or record[3] is None or invalid(base + '.__all__'):
                return None
            nested = expand(base, active + (module,))
            if nested is None:
                return None
            for name in record[3]:
                operations -= 1
                if operations < 0:
                    return None
                candidates.setdefault(name, []).append((base + '.' + name, statement))
        result = {name: items[0] for name, items in candidates.items()
                  if len(items) == 1 and name not in bindings}
        resolved[module] = result
        return result

    def stable(qualified, seen):
        nonlocal operations
        operations -= 1
        if operations < 0:
            return False
        if qualified in seen or len(seen) >= max_depth:
            return False
        module, _, name = qualified.rpartition('.')
        record = records.get(module)
        if record is None or record[4] or invalid(qualified):
            return False
        expanded = expand(module, ())
        if expanded is None:
            return False
        if name in expanded:
            return stable(expanded[name][0], seen + (qualified,))
        sites = record[0].get(name, [])
        if len(sites) != 1:
            return False
        if isinstance(sites[0], (ast.Import, ast.ImportFrom)):
            target = record[1].get(name)
            return bool(target and stable(target, seen + (qualified,)))
        return isinstance(sites[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))

    aliases, witnesses = {}, {}
    for module in records:
        expanded = expand(module, ())
        if expanded is None:
            continue
        for name, (target, statement) in expanded.items():
            if stable(target, (module + '.' + name,)):
                aliases.setdefault(module, {})[name] = target
                witnesses.setdefault(module, {})[name] = statement
    return StarImportFacts(aliases, witnesses) if operations >= 0 else StarImportFacts({}, {})
