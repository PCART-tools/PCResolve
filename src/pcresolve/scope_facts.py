## @package pcresolve.scope_facts
#  Immutable lexical-name facts shared by analysis-specific scope policies.

import ast
from dataclasses import dataclass


## Compatibility choices for collecting one lexical body's names.
#  The policies retain existing analyzer behavior during extraction; they do
#  not claim complete Python compiler symbol-table semantics.
@dataclass(frozen=True)
class ScopeFactPolicy:
    ## Include the root function or lambda's declared parameters as bindings.
    include_parameters: bool
    ## Descend into lambda defaults and bodies encountered in this body.
    descend_lambdas: bool
    ## Treat ordinary comprehension targets as bindings in the current body.
    include_comprehension_targets: bool
    ## Include an except-handler's string target as a binding.
    include_except_targets: bool
    ## Remove names declared global or nonlocal from current-body bindings.
    exclude_outer_declarations: bool
    ## Reduce unaliased from-import names to their first dotted component.
    import_from_root: bool


## Names observed under one explicit compatibility policy.
@dataclass(frozen=True)
class LexicalScopeFacts:
    ## Names read by expressions traversed under the policy.
    loaded: frozenset
    ## Names assigned, imported, declared, or parameter-bound in this body.
    bound: frozenset
    ## Names declared global in this body.
    globals: frozenset
    ## Names declared nonlocal in this body.
    nonlocals: frozenset


# Flow historically includes comprehension targets and nested lambda bodies,
# but not except-handler string targets. Global/nonlocal stores remain in its
# bound set; capture selection handles nonlocals separately.
FLOW_SCOPE = ScopeFactPolicy(True, True, True, False, False, True)

# Mapping stability treats comprehensions and lambdas as nested scopes, while
# named-expression targets in comprehensions still bind the surrounding scope.
MAPPING_SCOPE = ScopeFactPolicy(False, False, False, True, True, False)


class _ScopeCollector(ast.NodeVisitor):
    def __init__(self, policy):
        self.policy = policy
        self.loaded = set()
        self.bound = set()
        self.globals = set()
        self.nonlocals = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.loaded.add(node.id)
        else:
            self.bound.add(node.id)

    def visit_FunctionDef(self, node):
        self.bound.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    def visit_Lambda(self, node):
        if self.policy.descend_lambdas:
            self.generic_visit(node)

    def visit_Import(self, node):
        self.bound.update(alias.asname or alias.name.split('.')[0]
                          for alias in node.names)

    def visit_ImportFrom(self, node):
        if self.policy.import_from_root:
            self.bound.update(alias.asname or alias.name.split('.')[0]
                              for alias in node.names)
        else:
            self.bound.update(alias.asname or alias.name
                              for alias in node.names)

    def visit_ExceptHandler(self, node):
        if self.policy.include_except_targets and node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.globals.update(node.names)

    def visit_Nonlocal(self, node):
        self.nonlocals.update(node.names)

    def _visit_comprehension(self, node):
        if self.policy.include_comprehension_targets:
            self.generic_visit(node)
            return
        # Assignment expressions in a comprehension bind outside its implicit
        # scope. Preserve the mapping adapter's narrow existing treatment.
        for child in ast.walk(node):
            if isinstance(child, ast.NamedExpr):
                self.visit(child.target)

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_DictComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension

    def facts(self):
        bound = self.bound
        if self.policy.exclude_outer_declarations:
            bound = bound - self.globals - self.nonlocals
        return LexicalScopeFacts(frozenset(self.loaded), frozenset(bound),
                                 frozenset(self.globals), frozenset(self.nonlocals))


## Collect facts for a function or lambda body without entering nested named scopes.
#  @param node ast.FunctionDef, ast.AsyncFunctionDef, or ast.Lambda.
#  @param policy Compatibility policy chosen by the consuming analyzer.
#  @return Immutable lexical-name facts.
def function_scope_facts(node, policy=FLOW_SCOPE):
    collector = _ScopeCollector(policy)
    if policy.include_parameters:
        arguments = node.args
        collector.bound.update(argument.arg for argument in
                               arguments.posonlyargs + arguments.args + arguments.kwonlyargs)
        collector.bound.update(argument.arg for argument in
                               (arguments.vararg, arguments.kwarg) if argument)
    body = [node.body] if isinstance(node, ast.Lambda) else node.body
    for statement in body:
        collector.visit(statement)
    return collector.facts()


## Collect facts for an explicit statement sequence.
#  @param statements Iterable of statements from one lexical body.
#  @param policy Compatibility policy chosen by the consuming analyzer.
#  @return Immutable lexical-name facts.
def statement_scope_facts(statements, policy=MAPPING_SCOPE):
    collector = _ScopeCollector(policy)
    for statement in statements:
        collector.visit(statement)
    return collector.facts()
