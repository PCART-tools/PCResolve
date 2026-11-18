## @package pcresolve.flow.proofs.classes.deferred._class_deferred_expression
#  Rewrite deferred class-effect expressions.
#
#
#  Bounded expression rewriting for declaration-time class-effect proofs.
#  为类声明阶段效果证明执行有界表达式改写。



import ast
import copy

from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call


## Replace safe class observations and inline exact fresh helper calls.
## 改写安全的类命名空间观察，并内联精确的新鲜辅助函数调用。
#
#  @param node Expression to validate and rewrite.
#  @param bindings Current local helper/function bindings.
#  @param values Known local literal strings.
#  @param parameter Protected class parameter name.
#  @param string_value Bounded literal-string query.
#  @param source_span Source evidence location query.
#  @param builtin_name_status Query confirming a source name is a builtin.
#  @param native_namespace Query confirming relevant builtins remain stable.
#  @param namespace_read Query for a protected class namespace fact.
#  @param consume_helper_budget Charge the bounded helper expansion budget.
#  @return Rewritten expression, namespace facts, and inlined-call evidence.
def rewrite_deferred_expression(node, bindings, values, parameter, *, string_value,
                                source_span, builtin_name_status, native_namespace,
                                namespace_read, consume_helper_budget):
    if node is None:
        return None, [], []

    namespace_queries = []
    helper_calls = []

    ## Rewrite only class-safe observations and immediately invoked helpers.
    ## 仅改写类安全观察及立即调用的辅助函数。
    class Inline(ast.NodeTransformer):
        def __init__(self):
            self.active = set()

        ## Keep deferred callable bodies opaque during expression rewriting.
        ## 表达式改写期间保持延后执行的可调用函数体不透明。
        def visit_Lambda(self, item):
            return item

        visit_GeneratorExp = visit_Lambda
        visit_ListComp = visit_Lambda
        visit_SetComp = visit_Lambda
        visit_DictComp = visit_Lambda

        ## Rewrite a guarded native vars(class) membership check.
        ## 改写受保护的原生 vars(class) 成员检查。
        def visit_Compare(self, item):
            if (len(item.ops) == 1 and isinstance(item.ops[0], (ast.In, ast.NotIn))
                    and len(item.comparators) == 1
                    and string_value(item.left, values) is not None):
                right = item.comparators[0]
                if (isinstance(right, ast.Call) and isinstance(right.func, ast.Name)
                        and right.func.id == 'vars' and len(right.args) == 1
                        and not right.keywords and isinstance(right.args[0], ast.Name)
                        and right.args[0].id == parameter
                        and builtin_name_status('vars') and native_namespace()):
                    premise = namespace_read()
                    if premise is not None:
                        premise['lookup_evidence'] = source_span(item)
                        namespace_queries.append(premise)
                        return ast.copy_location(ast.Name(
                            id='$native_class_namespace_membership', ctx=ast.Load()), item)
            return self.generic_visit(item)

        ## Validate native lookups and inline one exact private helper call.
        ## 校验原生查找并内联一个精确的私有辅助函数调用。
        def visit_Call(self, call):
            if (isinstance(call.func, ast.Name) and call.func.id == 'getattr'
                    and len(call.args) == 3 and not call.keywords
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == parameter
                    and builtin_name_status('getattr') and native_namespace()):
                name = string_value(call.args[1], values)
                fallback = call.args[2]
                try:
                    if any(isinstance(item, ast.Call) for item in ast.walk(fallback)):
                        raise ValueError()
                    ast.literal_eval(fallback)
                    premise = namespace_read(absent=name) if name else None
                except (ValueError, TypeError, RecursionError):
                    premise = None
                if premise is not None:
                    premise['lookup_evidence'] = source_span(call)
                    namespace_queries.append(premise)
                    return copy.deepcopy(fallback)

            if not isinstance(call.func, ast.Name) or call.func.id not in bindings:
                return self.generic_visit(call)
            name = call.func.id
            kind, helper = bindings[name][:2]
            body = _body(helper) if kind == 'helper' else []
            if (name in self.active or len(self.active) >= 16 or kind != 'helper'
                    or not _declaration(helper) or len(body) != 1
                    or not isinstance(body[0], ast.Return) or body[0].value is None
                    or helper.args.vararg or helper.args.kwarg
                    or any(isinstance(item, (ast.Lambda, ast.Yield, ast.YieldFrom,
                                             ast.Await, ast.NamedExpr))
                           for item in ast.walk(body[0]))):
                raise ValueError()
            records, reasons = bind_ast_call(call, FunctionSignature.from_ast(helper.args))
            if reasons or any(record['status'] != 'exact' for record in records):
                raise ValueError()
            consume_helper_budget(helper)
            self.active.add(name)
            # An immediate lambda preserves argument snapshots, lexical
            # parameter binding and comprehension scope. Its full body is
            # still checked by the class-effect validator below.
            replacement = copy.copy(call)
            replacement.func = ast.copy_location(ast.Lambda(
                args=copy.deepcopy(helper.args), body=copy.deepcopy(body[0].value)), call)
            # Keep helper parameters scoped; unresolved nested helper uses are
            # rejected by the final binding scan.
            replacement.args = [self.visit(argument) for argument in replacement.args]
            replacement.keywords = [ast.keyword(arg=item.arg, value=self.visit(item.value))
                                    for item in replacement.keywords]
            self.active.remove(name)
            helper_calls.append({'call_evidence': source_span(call),
                'helper_evidence': source_span(helper),
                'effects': 'source_body_requires_validation',
                'runtime_helper_executed': False})
            return replacement

    rewritten = Inline().visit(copy.deepcopy(node))
    if any(isinstance(item, ast.Name) and item.id in bindings for item in ast.walk(rewritten)):
        raise ValueError()
    return rewritten, namespace_queries, helper_calls


## Return function statements other than an inert leading docstring.
## 返回函数体语句并移除惰性的首个文档字符串。
def _body(node):
    return [statement for statement in node.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]


## Check that a helper declaration has the restricted supported shape.
## 检查辅助函数声明是否符合受限的支持形态。
def _declaration(node):
    if not isinstance(node, ast.FunctionDef):
        return False
    args = node.args
    arguments = args.posonlyargs + args.args + args.kwonlyargs
    arguments += [arg for arg in (args.vararg, args.kwarg) if arg]
    return (not node.decorator_list and not args.defaults
            and not any(value is not None for value in args.kw_defaults)
            and not any(arg.annotation is not None for arg in arguments)
            and node.returns is None)
