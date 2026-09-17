## @package pcresolve.import_facts
#  Immutable import-syntax facts and relative-module name resolution.

import ast
from dataclasses import dataclass


## One name declared by an import or from-import statement.
@dataclass(frozen=True)
class ImportFact:
    ## import or from.
    kind: str
    ## Imported alias name exactly as written before an optional as-clause.
    name: str
    ## Explicit as-clause name, or None.
    asname: object = None
    ## Raw from-import module without leading dots.
    module: str = ''
    ## Number of leading dots on a from-import.
    level: int = 0

    ## Return the name bound by Python evaluation rules.
    #  @return Dotted-import root or explicit alias.
    @property
    def python_binding(self):
        if self.asname:
            return self.asname
        return self.name.split('.')[0] if self.kind == 'import' else self.name

    ## Return the full imported name unless an explicit alias replaces it.
    #  @return Full dotted import name or explicit alias.
    @property
    def full_binding(self):
        return self.asname or self.name

    ## Report whether this is a wildcard from-import.
    #  @return True for from X import *.
    @property
    def wildcard(self):
        return self.kind == 'from' and self.name == '*'


## Extract ordered facts from one import statement.
#  @param node ast.Import, ast.ImportFrom, or another AST node.
#  @return Immutable ImportFact tuple; empty for non-import nodes.
def import_facts(node):
    if isinstance(node, ast.Import):
        return tuple(ImportFact('import', alias.name, alias.asname)
                     for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return tuple(ImportFact(
            'from', alias.name, alias.asname, node.module or '', node.level)
            for alias in node.names)
    return ()


## Resolve the module portion of a relative import.
#  @param current_module Dotted name of the file containing the import.
#  @param is_package Whether the containing file is a package initializer.
#  @param imported_module Module after the leading dots, or None.
#  @param level Number of leading dots.
#  @return Absolute dotted module name under the existing ownership policy.
def resolve_relative_module(current_module, is_package, imported_module, level):
    module = imported_module or ''
    if not level or not current_module:
        return module
    parts = current_module.split('.')
    if is_package:
        package_parts = parts
    else:
        if len(parts) < 2:
            return module
        package_parts = parts[:-1]
    strip = level - 1
    if strip >= len(package_parts):
        base = ''
    elif strip == 0:
        base = '.'.join(package_parts)
    else:
        base = '.'.join(package_parts[:-strip])
    if module:
        return base + '.' + module if base else module
    return base
