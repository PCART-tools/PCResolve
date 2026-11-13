## @package pcresolve.scope_facts
#  Immutable lexical-name facts shared by analysis-specific scope policies.
#  供各分析器的作用域策略共享的不可变词法名称事实。

import ast
from dataclasses import dataclass


## Compatibility choices for collecting one lexical body's names.
## 收集单个词法体名称时使用的兼容性选项。
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
## 在指定兼容性策略下观察到的名称。
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


## Collect lexical names while respecting the selected scope boundaries.
## 按选定的作用域边界收集词法名称。
class _ScopeCollector(ast.NodeVisitor):
    ## Initialize the collector and its iterative traversal state.
    ## 初始化收集器及其迭代遍历状态。
    #
    #  @param policy Compatibility choices for this traversal.
    #  @return None
    def __init__(self, policy):
        self.policy = policy
        self.loaded = set()
        self.bound = set()
        self.globals = set()
        self.nonlocals = set()
        self._pending = None

    ## Schedule and visit nodes without recursive visitor calls.
    ## 调度并访问节点，避免访问器递归调用。
    #
    #  @param node AST node to visit.
    #  @return None
    def visit(self, node):
        if self._pending is not None:
            self._pending.append(node)
            return
        self._pending = [node]
        try:
            while self._pending:
                ast.NodeVisitor.visit(self, self._pending.pop())
        finally:
            self._pending = None

    ## Schedule a node's children in source traversal order.
    ## 按源码遍历顺序调度节点的子节点。
    #
    #  @param node AST node whose children are scheduled.
    #  @return None
    def generic_visit(self, node):
        # Handlers keep their scope-specific stopping rules. Descendant syntax
        # is scheduled explicitly rather than consuming a Python call stack.
        # 显式调度后代节点，避免深层源码耗尽 Python 调用栈。
        self._pending.extend(reversed(list(ast.iter_child_nodes(node))))

    ## Record a name as loaded or bound according to its AST context.
    ## 根据 AST 上下文记录名称读取或绑定。
    #
    #  @param node Name node to inspect.
    #  @return None
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.loaded.add(node.id)
        else:
            self.bound.add(node.id)

    ## Bind a nested definition without descending into its named scope.
    ## 绑定嵌套定义的名称，不进入其具名作用域。
    #
    #  @param node Nested function or class definition.
    #  @return None
    def visit_FunctionDef(self, node):
        self.bound.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    ## Traverse a lambda only when the compatibility policy permits it.
    ## 仅在兼容性策略允许时遍历 lambda。
    #
    #  @param node Lambda expression.
    #  @return None
    def visit_Lambda(self, node):
        if self.policy.descend_lambdas:
            self.generic_visit(node)

    ## Record names bound by an import statement.
    ## 记录 import 语句绑定的名称。
    #
    #  @param node Import statement.
    #  @return None
    def visit_Import(self, node):
        self.bound.update(alias.asname or alias.name.split('.')[0]
                          for alias in node.names)

    ## Record from-import bindings under the selected compatibility policy.
    ## 按选定兼容性策略记录 from-import 绑定。
    #
    #  @param node ImportFrom statement.
    #  @return None
    def visit_ImportFrom(self, node):
        if self.policy.import_from_root:
            self.bound.update(alias.asname or alias.name.split('.')[0]
                              for alias in node.names)
        else:
            self.bound.update(alias.asname or alias.name
                              for alias in node.names)

    ## Collect an exception handler and its optional target.
    ## 收集异常处理器及其可选目标名称。
    #
    #  @param node Exception handler.
    #  @return None
    def visit_ExceptHandler(self, node):
        if self.policy.include_except_targets and node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    ## Record names declared global in this body.
    ## 记录当前词法体中声明为 global 的名称。
    #
    #  @param node Global declaration.
    #  @return None
    def visit_Global(self, node):
        self.globals.update(node.names)

    ## Record names declared nonlocal in this body.
    ## 记录当前词法体中声明为 nonlocal 的名称。
    #
    #  @param node Nonlocal declaration.
    #  @return None
    def visit_Nonlocal(self, node):
        self.nonlocals.update(node.names)

    ## Collect comprehension bindings according to the scope policy.
    ## 按作用域策略收集推导式绑定。
    #
    #  @param node Comprehension or generator expression.
    #  @return None
    def _visit_comprehension(self, node):
        if self.policy.include_comprehension_targets:
            self.generic_visit(node)
            return
        # Assignment expressions in a comprehension bind outside its implicit
        # scope. Preserve the mapping adapter's narrow existing treatment.
        # 推导式中的赋值表达式绑定外层作用域，保留映射分析的既有处理。
        for child in ast.walk(node):
            if isinstance(child, ast.NamedExpr):
                self.visit(child.target)

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_DictComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension

    ## Freeze the collected names after applying outer-declaration policy.
    ## 应用外层声明策略后，将收集的名称冻结为事实。
    #
    #  @return Immutable lexical scope facts.
    def facts(self):
        bound = self.bound
        if self.policy.exclude_outer_declarations:
            bound = bound - self.globals - self.nonlocals
        return LexicalScopeFacts(frozenset(self.loaded), frozenset(bound),
                                 frozenset(self.globals), frozenset(self.nonlocals))


## Collect facts for a function or lambda body without entering nested named scopes.
## 收集函数或 lambda 体的事实，不进入嵌套具名作用域。
#
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
## 收集显式语句序列的词法事实。
#
#  @param statements Iterable of statements from one lexical body.
#  @param policy Compatibility policy chosen by the consuming analyzer.
#  @return Immutable lexical-name facts.
def statement_scope_facts(statements, policy=MAPPING_SCOPE):
    collector = _ScopeCollector(policy)
    for statement in statements:
        collector.visit(statement)
    return collector.facts()


## Select names captured from known enclosing lexical bindings.
## 从已知外层词法绑定中选取捕获的名称。
#  Declared nonlocals remain captures even though the compatibility collector
#  also retains their stores in the local bound-name set.
#
#  @param facts LexicalScopeFacts for the nested function or lambda.
#  @param enclosing_bound_names Names bound by its lexical ancestors.
#  @return Sorted immutable tuple of captured names.
def captured_names(facts, enclosing_bound_names):
    nonlocals = facts.nonlocals
    free = (facts.loaded | nonlocals) - (facts.bound - nonlocals)
    return tuple(sorted(free & frozenset(enclosing_bound_names)))


## Select free variables relayed through nested named functions.
## 选取经嵌套具名函数传递的自由变量。
#
#  @param node Source function whose closure cells are being selected.
#  @param enclosing_bound_names Bindings supplied by lexical ancestors.
#  @return Captured names, excluding descendant-local and global bindings.
def transitive_captured_names(node, enclosing_bound_names):
    pending, scopes, children = [node], [], {}
    while pending:
        owner = pending.pop()
        scopes.append(owner)
        nested = []
        body = [owner.body] if isinstance(owner, ast.Lambda) else owner.body
        nodes = list(body)
        while nodes:
            child = nodes.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested.append(child)
            elif not isinstance(child, (ast.ClassDef, ast.Lambda)):
                nodes.extend(ast.iter_child_nodes(child))
        children[id(owner)] = nested
        pending.extend(nested)

    # Process children first so their free names can propagate to each parent.
    # 先处理子作用域，使其自由名称能向父作用域传播。
    free = {}
    for owner in reversed(scopes):
        facts = function_scope_facts(owner)
        local = facts.bound - facts.nonlocals
        names = (facts.loaded | facts.nonlocals) - local - facts.globals
        for child in children[id(owner)]:
            names |= free[id(child)] - local - facts.globals
        free[id(owner)] = names
    return tuple(sorted(free[id(node)] & frozenset(enclosing_bound_names)))
