## @package pcresolve.flow.transfer.summary_statements
#  Transfer Python statements and control flow.
#
#
#  Processes assignments, guards, exception paths and summary execution.
#  处理赋值、守卫、异常路径以及摘要执行过程。



import ast
import copy
from dataclasses import asdict
from pcresolve.flow.transfer.environment import copy_environment
from pcresolve.facts.effect_facts import contains_yield
from pcresolve.facts.import_facts import import_facts
from pcresolve.flow.model.results import FlowCall, FunctionRef
from pcresolve.flow.proofs.callables._fresh_member_checks import (
    fresh_checks as fresh_mapping_member_checks,
)
from pcresolve.flow.proofs.callables._function_factory import factory_wrapper
from pcresolve.flow.proofs.callables.dispatch.keyword_validation import (
    checks as keyword_validation_checks,
)
from pcresolve.flow.proofs.containers.container_predicates import (
    checks as container_predicate_checks,
)
from pcresolve.flow.proofs.containers.mapping_attribute_transfer import (
    transfers as mapping_attribute_transfers,
)
from pcresolve.flow.proofs.containers.mapping_key_access import (
    footprints as mapping_key_access_footprints,
)
from pcresolve.flow.proofs.containers.mapping_return_transfer import (
    transfers as mapping_return_transfers,
)
from pcresolve.flow.proofs.namespaces.metadata._metadata_observer import (
    observer_effects,
)
from pcresolve.flow.proofs.namespaces.metadata._metadata_queries import metadata_query
from pcresolve.flow.proofs.protocols._cached_imports import cached_import
from pcresolve.flow.proofs.protocols.capture_rejection_guard import (
    checks as capture_rejection_checks,
)
from pcresolve.flow.transfer._summary_support import (
    _attribute_write_roots,
    _call_key,
    _exception_class,
    _loop_env,
    _loop_signature,
    _may_raise,
    _unique,
)
from pcresolve.flow.transfer.environment import (
    guard_surviving_sources,
    merge_environments as _merge_env,
    merge_result_sources as _merge_result_sources,
)


## Check that a value fact refers to the whole original object.
## 检查值事实是否指向完整的原对象。
#
#  @param value Source fact to check.
#  @return True for a complete direct value.
def _direct_guard_value(value):
    return value.get('relation') == 'direct' and not any(
        value.get(flag) for flag in ('value_incomplete', 'projection', 'output_path'))


## Transfer statements and control flow for one function summary.
## 为单个函数摘要转移语句和控制流。
class StatementsMixin:
    _CONTROL_PATH_KEY = '$pcresolve_control_paths'
    _loop_control_depth = 0

    ## Recognize a definitely raising argument after effect-free argument reads.
    ## 识别无副作用实参读取后必然抛错的实参。
    #
    #  @param node Statement whose evaluation order is examined.
    #  @param env Current abstract environment.
    #  @return The raising call and exception name, or None when unproved.
    def definite_argument_raise(self, node, env):
        if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign, ast.Return)):
            outer = node.value
        elif isinstance(node, (ast.If, ast.While)):
            outer = node.test
        elif isinstance(node, ast.For):
            outer = node.iter
        else:
            return None
        if (not isinstance(outer, ast.Call)
                or not isinstance(outer.func, ast.Name) or not outer.args):
            return None
        first = next((argument for argument in outer.args
                      if not isinstance(argument, (ast.Constant, ast.Name))), None)
        if (not isinstance(first, ast.Call) or not isinstance(first.func, ast.Name)
                or first.args or first.keywords or first.func.id in env):
            return None
        target = self.analyzer._resolve(self.ref, first.func.id)
        if (target is None or not self.analyzer._stable_import_name(
                target[0].module + '.' + target[0].qualname)
                or (target[0].module, target[0].qualname) in self.modified_return_callables):
            return None
        function = target[1]
        if (not isinstance(function, ast.FunctionDef) or function.decorator_list
                or function.args.posonlyargs or function.args.args or function.args.kwonlyargs
                or function.args.vararg or function.args.kwarg or len(function.body) != 1
                or not isinstance(function.body[0], ast.Raise)
                or function.body[0].cause is not None):
            return None
        raised = function.body[0].exc
        if isinstance(raised, ast.Name):
            exception_name = raised.id
        elif (isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
                and not raised.keywords
                and all(isinstance(arg, ast.Constant) for arg in raised.args)):
            exception_name = raised.func.id
        else:
            return None
        if (_exception_class(exception_name) is None
                or self.analyzer._builtin_name_status(target[0], function, exception_name)
                != 'confirmed_builtin'):
            return None
        known = {'ValueError', 'RuntimeError', 'TypeError', 'KeyError', 'IndexError',
                 'AssertionError', 'Exception', 'BaseException'}
        return first, exception_name if exception_name in known else None

    ## Canonicalize one evaluated conversion by its root and negation parity.
    ## 将一次求值转换归一到根 token 和取反奇偶性。
    #
    #  @param value Local value fact.
    #  @return Pair of root token and odd/even parity, or None.
    def _canonical_token(self, value):
        token = value.get('truth_token')
        if not token:
            return None
        parents = getattr(self, '_truth_parents', None) or {}
        current = token
        parity = False
        seen = set()
        while current in parents and current not in seen:
            seen.add(current)
            current = parents[current]
            parity = not parity
        return current, parity

    ## Describe a guard operand for comparison across reaching branches.
    ## 描述守卫操作数，用于比较不同抵达分支的后续行为。
    #
    #  @param value Local value fact.
    #  @param conditions Guards selecting the reaching argument binding.
    #  @param seen Calls already expanded along this proof.
    #  @return Value identity or a Boolean base and its complement polarity.
    def _value_signature(self, value, conditions, seen=()):
        source = value.get('source')
        kind = value.get('kind')
        literal = value.get('literal')
        if literal is not None:
            if literal.get('type') == 'bool':
                return ('boolean', ('constant',), literal['value'])
            return ('literal', literal.get('type'), repr(literal.get('value')))

        if kind == 'call_result' and source not in seen:
            proof = self._boolean_bindings([value]).get(source)
            if proof is not None:
                argument, singleton, inverted = proof
                # Only the proved identity test can be identified by its inputs.
                # Ordinary calls may run user code even with identical arguments.
                reaching = [item for item in argument['sources']
                            if self._match_control_path(
                                conditions, item.get('conditions', [])) is not None]
                if len(reaching) == 1 and not any(reaching[0].get(flag) for flag in (
                        'value_incomplete', 'projection', 'output_path')):
                    operand = self._value_signature(reaching[0], conditions, seen + (source,))
                    polarity = bool(inverted) != bool(value.get('boolean_negated'))
                    if operand[0] == 'boolean':
                        return ('boolean', operand[1], operand[2] ^ (not singleton) ^ polarity)
                    return ('boolean', ('identity', operand, singleton), polarity)

        canonical = self._canonical_token(value)
        if canonical is not None:
            root, parity = canonical
            return ('boolean', ('evaluation', root), parity)
        return (kind, source)

    ## Build a branch-binding signature for one guard.
    ## 为一个守卫构造分支绑定签名。
    #
    #  @param values Reaching argument or local binding facts.
    #  @param conditions Ordered guards already observed on the path.
    #  @return Hashable signature used only by redundancy folding.
    def _binding_signature(self, values, conditions=()):
        return tuple(sorted({self._value_signature(value, conditions) for value in values},
                            key=repr))

    ## Resolve calls whose result is the condition being tested.
    ## 查找结果正被用作判断条件的调用。
    #
    #  @param operand Condition operand after unwrapping a unary not.
    #  @return Call identifiers directly represented by the condition.
    def _condition_call_ids(self, operand):
        if not isinstance(operand, ast.Call):
            return []
        call_id = _call_key(self.ref.file_path, operand)
        return [call_id] if any(call.id == call_id for call in self.calls) else []

    ## Prove the Boolean result of an exactly bound source identity predicate.
    ## 证明精确绑定的源码身份判断返回布尔值。
    #
    #  @param call Resolved source call and its argument binding.
    #  @return Parameter, Boolean singleton, and inversion, or None.
    def _boolean_return(self, call):
        cache = getattr(self, '_boolean_return_cache', None)
        if cache is not None and call.id in cache:
            return cache[call.id]
        if (self._loop_control_depth or call.target_status != 'resolved'
                or call.target is None or call.binding_status != 'complete'
                or len(call.argument_sources) != 1):
            return None
        matches = self.analyzer._definition_index.find(call.target.module, call.target.qualname)
        if len(matches) != 1 or matches[0][0] != call.target:
            return None
        function = matches[0][1]
        if (not isinstance(function, ast.FunctionDef) or function.decorator_list
                or len(function.body) != 1 or not isinstance(function.body[0], ast.Return)):
            return None
        expression = function.body[0].value
        if not (isinstance(expression, ast.Compare) and len(expression.ops) == 1
                and isinstance(expression.ops[0], (ast.Is, ast.IsNot))):
            return None
        left, right = expression.left, expression.comparators[0]
        if isinstance(left, ast.Constant):
            left, right = right, left
        argument = call.argument_sources[0]
        if (not argument.get('target_path')
                and isinstance(left, ast.Name) and left.id == argument['parameter']
                and isinstance(right, ast.Constant) and type(right.value) is bool):
            proof = (argument, right.value, isinstance(expression.ops[0], ast.IsNot))
            if cache is None:
                cache = {}
                self._boolean_return_cache = cache
            cache[call.id] = proof
            return proof
        return None

    ## Read the Boolean truth known for one parameter source.
    ## 读取一个参数来源已证明的布尔真值。
    #
    #  @param truths Boolean facts private to this candidate path.
    #  @param source Parameter or capture name.
    #  @return Truthiness, or None when the source has no proved Boolean fact.
    def _source_truthiness(self, truths, source):
        key = '%s is %s' % (source, True)
        if truths.get(key) is True:
            return True
        if truths.get('%s is %s' % (source, False)) is True:
            return False
        if '$truth:%s' % source in truths:
            return bool(truths['$truth:%s' % source])
        if self._source_is_boolean(truths, source):
            if truths.get('%s is %s' % (source, True)) is False:
                return False
            if truths.get('%s is %s' % (source, False)) is False:
                return True
        return None

    ## Check whether one parameter source is proved Boolean.
    ## 检查一个参数来源是否已证明为布尔值。
    #
    #  @param truths Boolean facts private to this candidate path.
    #  @param source Parameter or capture name.
    #  @return True only for an exact singleton fact or an explicit Boolean fact.
    def _source_is_boolean(self, truths, source):
        if truths.get('$bool:%s' % source) is True:
            return True
        return (truths.get('%s is %s' % (source, True)) is True
                or truths.get('%s is %s' % (source, False)) is True)

    ## Store one evaluated Boolean result and its complement chain.
    ## 保存一次已求值的布尔结果及其取反链。
    #
    #  @param truths Boolean facts private to this candidate path.
    #  @param token Truth token for this evaluation.
    #  @param truth Evaluated truth value.
    #  @return None
    def _store_token_truth(self, truths, token, truth):
        parents = getattr(self, '_truth_parents', None) or {}
        children = {}
        for child, parent in parents.items():
            children.setdefault(parent, []).append(child)
        pending = [(token, bool(truth))]
        seen = set()
        while pending:
            current, value = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            key = '$truth:%s' % current
            known = truths.get(key)
            if known is None:
                truths[key] = value
            elif bool(known) != value:
                continue
            parent = parents.get(current)
            if parent is not None:
                pending.append((parent, not value))
            for child in children.get(current, ()):
                pending.append((child, not value))

    ## Read a saved conversion result for this exact evaluated value.
    ## 读取本次求值保存的转换结果。
    #
    #  @param value Local value fact.
    #  @param truths Boolean facts private to this candidate path.
    #  @return Saved truth, or None when this evaluation was not proved.
    def _token_truth(self, value, truths):
        parents = getattr(self, '_truth_parents', None)
        if parents is None:
            parents = {}
            self._truth_parents = parents
        token = value.get('truth_token')
        parent = value.get('truth_parent_token')
        if token and parent:
            parents[token] = parent
        current = token
        parity = False
        seen = set()
        while current and current not in seen:
            seen.add(current)
            truth = truths.get('$truth:%s' % current)
            if truth is not None:
                return (not bool(truth)) if parity else bool(truth)
            current = parents.get(current)
            parity = not parity
        return None

    ## Read one value's truthiness without inventing a singleton identity.
    ## 读取一个值的真值，不把真值强行解释为布尔单例。
    #
    #  @param value Local value fact.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return Truthiness, or None when no complete source proves it.
    def _value_truthiness(self, value, conditions, truths, seen=()):
        if any(value.get(flag) for flag in (
                'value_incomplete', 'projection', 'output_path')):
            return None
        literal = value.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return bool(literal.get('value'))
        converted_truth = self._token_truth(value, truths)
        if converted_truth is not None:
            return converted_truth
        kind = value.get('kind')
        if kind == 'call_result':
            source = value.get('source')
            truth = truths.get(source)
            if truth is None:
                truth = self._source_truthiness(truths, source)
            if truth is None:
                truth = self._resolve_call_result_truth(
                    source, conditions, truths, seen)
        elif kind in ('parameter', 'capture'):
            truth = self._source_truthiness(truths, value.get('source'))
        else:
            return None
        if truth is None:
            return None
        return (not truth) if value.get('boolean_negated') else truth

    ## Check an identity predicate's relation to one value.
    ## 检查一个值对身份谓词单例的关系。
    #
    #  @param value Local value fact.
    #  @param singleton Boolean singleton tested by the source predicate.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return True/False for a proved identity relation, otherwise None.
    def _value_identity_holds(self, value, singleton, conditions, truths, seen=()):
        if any(value.get(flag) for flag in (
                'value_incomplete', 'projection', 'output_path')):
            return None
        literal = value.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return bool(literal.get('value')) is bool(singleton)
        kind = value.get('kind')
        if kind == 'call_result':
            source = value.get('source')
            converted = bool(value.get('truth_converted')
                             or value.get('boolean_negated') is not None)
            if converted:
                truth = self._value_truthiness(value, conditions, truths, seen)
                return None if truth is None else (truth is bool(singleton))
            key = '%s is %s' % (source, singleton)
            known = truths.get(key)
            if known is not None:
                return bool(known)
            truth = self._value_truthiness(value, conditions, truths, seen)
            if truth is not None and truth != bool(singleton):
                return False
            if (truths.get(source) is not None
                    or self._source_is_boolean(truths, source)) and truth is not None:
                return truth is bool(singleton)
            return None
        if kind in ('parameter', 'capture'):
            source = value.get('source')
            converted = bool(value.get('truth_converted')
                             or value.get('boolean_negated') is not None)
            if converted:
                truth = self._value_truthiness(value, conditions, truths, seen)
                return None if truth is None else (truth is bool(singleton))
            key = '%s is %s' % (source, singleton)
            known = truths.get(key)
            if known is not None:
                return bool(known)
            truth = self._value_truthiness(value, conditions, truths, seen)
            if truth is not None and truth != bool(singleton):
                # A value with the opposite truthiness cannot be the singleton.
                # 真值相反的值不可能是该布尔单例。
                return False
            if self._source_is_boolean(truths, source) and truth is not None:
                return truth is bool(singleton)
        return None

    ## Evaluate an identity predicate and retain the selected branch's input fact.
    ## 对身份判断求值，并保存选中分支对实参来源的约束。
    #
    #  @param proof Source predicate and its exact binding.
    #  @param conditions Reaching control path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param selected Predicate result required by this candidate branch.
    #  @return Boolean result if uniquely proved, otherwise None.
    def _path_predicate_truth(self, proof, conditions, truths, selected):
        argument, singleton, inverted = proof
        literal = argument.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return (literal['value'] is singleton) != inverted
        values = self._argument_values(argument, conditions)
        if not values:
            return None
        identities = [self._value_identity_holds(
            value, singleton, conditions, truths) for value in values]
        if all(identity is not None for identity in identities):
            if not all(identity is identities[0] for identity in identities):
                return None
            return identities[0] != inverted
        signatures = {(value.get('kind'), value.get('source'),
                       bool(value.get('boolean_negated')),
                       bool(value.get('truth_converted')),
                       value.get('truth_token')) for value in values}
        if len(signatures) != 1:
            return None
        holds = selected != inverted
        self._apply_identity_to_value(
            values[0], singleton, holds, conditions, truths)
        return None

    ## Find one analyzed call by its exact call identifier.
    ## 按精确调用标识查找一个已分析调用。
    #
    #  @param call_id Call identifier from a local value fact.
    #  @return Matching call, or None when it is absent.
    def _call_by_id(self, call_id):
        index = getattr(self, '_call_index', None)
        count = getattr(self, '_call_index_count', 0)
        if index is None:
            index = {}
            count = 0
        if count != len(self.calls):
            for call in self.calls[count:]:
                index[call.id] = call
            self._call_index = index
            self._call_index_count = len(self.calls)
        return index.get(call_id)

    ## Return argument sources that can reach the current control path.
    ## 返回可抵达当前控制路径的实参来源。
    #
    #  @param argument Recorded predicate argument.
    #  @param conditions Ordered guards already observed on the path.
    #  @return Reaching local source facts.
    def _argument_values(self, argument, conditions):
        return [value for value in argument.get('sources', [])
                if self._match_control_path(
                    conditions, value.get('conditions', [])) is not None
                and not any(value.get(flag) for flag in (
                    'value_incomplete', 'projection', 'output_path'))]

    ## Store a truthiness fact without claiming singleton identity.
    ## 保存真值事实，但不声称布尔单例身份。
    #
    #  @param truths Boolean facts private to this candidate path.
    #  @param source Parameter or capture name.
    #  @param truth Truthiness value.
    #  @return None
    def _set_source_truthiness(self, truths, source, truth):
        truths['$truth:%s' % source] = bool(truth)
        if not self._source_is_boolean(truths, source):
            return
        truths['%s is %s' % (source, truth)] = True
        truths['%s is %s' % (source, not truth)] = False
        truths['$bool:%s' % source] = True

    ## Store an identity/exclusion relation for a parameter source.
    ## 为参数来源保存等于或排除单例的关系。
    #
    #  @param truths Boolean facts private to this candidate path.
    #  @param source Parameter or capture name.
    #  @param singleton Boolean singleton being compared.
    #  @param holds Whether the source is equal to the singleton.
    #  @return None
    def _set_source_identity(self, truths, source, singleton, holds):
        key = '%s is %s' % (source, singleton)
        opposite = '%s is %s' % (source, not singleton)
        known = truths.get(key)
        if known is not None and bool(known) != bool(holds):
            return
        truths[key] = bool(holds)
        if holds:
            truths[opposite] = False
            truths['$bool:%s' % source] = True
            truths['$truth:%s' % source] = bool(singleton)
        elif self._source_is_boolean(truths, source):
            truths[opposite] = True
            truths['$truth:%s' % source] = not bool(singleton)

    ## Apply one proved identity relation to an argument value.
    ## 将一个已证明的身份关系应用到实参值。
    #
    #  @param value Local argument fact.
    #  @param singleton Boolean singleton tested by the predicate.
    #  @param holds Whether the tested argument equals the singleton.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return True when the value's source fact was updated.
    def _apply_identity_to_value(self, value, singleton, holds, conditions, truths, seen=()):
        if any(value.get(flag) for flag in (
                'value_incomplete', 'projection', 'output_path')):
            return False
        kind = value.get('kind')
        if kind == 'call_result':
            source = value.get('source')
            if source is None:
                return False
            # An ordinary call result is not a Boolean value merely because
            # its result is compared with a singleton later.
            # 普通调用结果不会仅因之后与单例比较就成为布尔值。
            if not self._boolean_bindings([value]):
                converted = bool(value.get('truth_converted')
                                 or value.get('boolean_negated') is not None)
                if converted:
                    value_truth = bool(singleton) if holds else not bool(singleton)
                    source_truth = value_truth != bool(value.get('boolean_negated'))
                    token = value.get('truth_token')
                    if token:
                        self._store_token_truth(truths, token, value_truth)
                    self._set_source_identity(
                        truths, source, not source_truth, False)
                else:
                    self._set_source_identity(truths, source, singleton, holds)
                return True
            truth = bool(singleton) if holds else not bool(singleton)
            truth = truth != bool(value.get('boolean_negated'))
            known = truths.get(source)
            if known is not None and bool(known) != truth:
                return False
            truths[source] = truth
            self._propagate_call_result_truth(
                source, truth, conditions, truths, seen)
            return True
        if kind in ('parameter', 'capture'):
            source = value.get('source')
            if source is None:
                return False
            converted = bool(value.get('truth_converted')
                             or value.get('boolean_negated') is not None)
            if converted:
                value_truth = bool(singleton) if holds else not bool(singleton)
                source_truth = value_truth != bool(value.get('boolean_negated'))
                token = value.get('truth_token')
                if token:
                    self._store_token_truth(truths, token, value_truth)
                    if self._source_is_boolean(truths, source):
                        self._set_source_truthiness(truths, source, source_truth)
                else:
                    self._set_source_truthiness(truths, source, source_truth)
                # A truth-converted value excludes the singleton whose
                # truthiness is opposite the source's truthiness. It does not
                # prove the source equals the other singleton.
                # 真值转换结果排除了真值与来源相反的单例，但不能证明原值
                # 等于另一个单例。
                excluded = not source_truth
                self._set_source_identity(
                    truths, source, excluded, False)
            else:
                self._set_source_identity(truths, source, singleton, holds)
            return True
        return False

    ## Evaluate a source predicate from already proved argument facts.
    ## 用已证明的实参事实求值源码谓词。
    #
    #  @param proof Predicate argument, singleton and inversion.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return Predicate truth, or None when an argument remains unknown.
    def _known_predicate_truth(self, proof, conditions, truths, seen=()):
        argument, singleton, inverted = proof
        literal = argument.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return (literal['value'] is singleton) != inverted
        values = self._argument_values(argument, conditions)
        if not values:
            return None
        identities = [self._value_identity_holds(
            value, singleton, conditions, truths, seen) for value in values]
        if any(identity is None for identity in identities):
            return None
        if not all(identity is identities[0] for identity in identities):
            return None
        return identities[0] != inverted

    ## Resolve a call result from its predicate and already proved arguments.
    ## 根据谓词和已证明实参解析一个调用结果。
    #
    #  @param source Call identifier of the result being resolved.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return Boolean result, or None when the source chain is not proved.
    def _resolve_call_result_truth(self, source, conditions, truths, seen=()):
        if truths.get(source) is not None:
            return truths[source]
        if source in seen:
            return None
        call = self._call_by_id(source)
        if call is None:
            return None
        proof = self._boolean_return(call)
        if proof is None:
            return None
        truth = self._known_predicate_truth(
            proof, conditions, truths, tuple(seen) + (source,))
        if truth is not None:
            truths[source] = truth
        return truth

    ## Send a proved call result fact back to its predicate arguments.
    ## 将已证明的调用结果事实传回其谓词实参。
    #
    #  @param source Call identifier whose result is known.
    #  @param truth Result value.
    #  @param conditions Ordered guards already observed on the path.
    #  @param truths Boolean facts private to this candidate path.
    #  @param seen Call identifiers already expanded on this path.
    #  @return None
    def _propagate_call_result_truth(self, source, truth, conditions, truths, seen=()):
        if source in seen:
            return
        call = self._call_by_id(source)
        proof = self._boolean_return(call) if call is not None else None
        if proof is None:
            return
        argument, singleton, inverted = proof
        holds = bool(truth) != inverted
        values = self._argument_values(argument, conditions)
        if len(values) != 1:
            return
        self._apply_identity_to_value(
            values[0], singleton, holds, conditions, truths,
            tuple(seen) + (source,))

    ## Read the Boolean truth carried by one local value fact.
    ## 读取单个局部值事实携带的布尔真值。
    #
    #  @param value Local value fact.
    #  @param truths Boolean facts known on the reaching path.
    #  @return Boolean truth, or None when the value is not proved Boolean.
    def _value_boolean_truth(self, value, truths):
        if any(value.get(flag) for flag in (
                'value_incomplete', 'projection', 'output_path')):
            return None
        literal = value.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return bool(literal.get('value'))
        converted_truth = self._token_truth(value, truths)
        if converted_truth is not None:
            return converted_truth
        negated = bool(value.get('boolean_negated', False))
        kind = value.get('kind')
        if kind == 'call_result':
            truth = truths.get(value.get('source'))
            if truth is None:
                truth = self._source_truthiness(truths, value.get('source'))
        elif kind in ('parameter', 'capture'):
            truth = self._source_truthiness(truths, value.get('source'))
        else:
            return None
        if truth is None:
            return None
        return (not truth) if negated else truth

    ## Check that one local value is proved Boolean for a reaching path.
    ## 检查某个局部值在某条抵达路径上是否已证明为布尔值。
    #
    #  @param value Local value fact.
    #  @param truths Boolean facts known on the reaching path.
    #  @return True only when the value can be evaluated without custom truth.
    def _value_is_boolean(self, value, truths):
        if any(value.get(flag) for flag in (
                'value_incomplete', 'projection', 'output_path')):
            return False
        literal = value.get('literal')
        if literal is not None and literal.get('type') == 'bool':
            return True
        if value.get('truth_converted') or value.get('boolean_negated') is not None:
            return True
        kind = value.get('kind')
        if kind == 'call_result':
            return bool(self._boolean_bindings([value]))
        if kind in ('parameter', 'capture'):
            return self._source_is_boolean(truths, value.get('source'))
        return False

    ## Check whether evaluating an expression is proved not to raise.
    ## 检查表达式是否已证不会抛出异常。
    #
    #  A syntactic negation of a value known to be Boolean cannot run custom
    #  truth conversion. Unknown objects keep the conservative exception path.
    #  已知布尔值的取反不会执行自定义真值转换；未知对象继续保留异常路径。
    #
    #  @param node Expression to inspect.
    #  @param env Current abstract environment.
    #  @return True only for constants and Boolean-valued negations.
    def _expression_cannot_raise(self, node, env):
        if isinstance(node, ast.Constant):
            return type(node.value) is bool
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._expression_cannot_raise(node.operand, env)
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.Is, ast.IsNot))):
            return True
        if not isinstance(node, ast.Name):
            return False
        values = env.get(node.id, [])
        if not values:
            return False
        paths = env.get(self._CONTROL_PATH_KEY) or []
        if not paths:
            return all(self._value_is_boolean(value, {}) for value in values)
        for path in paths:
            truths = path.get('boolean_values', {})
            conditions = path.get('conditions', [])
            reaching = [value for value in values if self._match_control_path(
                conditions, value.get('conditions', [])) is not None]
            if not reaching or not all(self._value_is_boolean(value, truths)
                                       for value in reaching):
                return False
        return True

    ## Resolve direct Boolean call-result identities represented by local bindings.
    ## 查找局部绑定中已证明返回布尔值的直接调用结果。
    #
    #  @param values Reaching local binding alternatives.
    #  @return Boolean call IDs mapped to their agreed input proof, if unique.
    def _boolean_bindings(self, values):
        sources = {value['source'] for value in values if value.get('kind') == 'call_result'
                   and (_direct_guard_value(value) or (
                       value.get('boolean_negated') is not None
                       and not any(value.get(flag) for flag in (
                           'value_incomplete', 'projection', 'output_path'))))}
        if not sources or self._loop_control_depth:
            return {}
        observations = {}
        for call in self.calls:
            if call.id in sources:
                observations.setdefault(call.id, []).append(self._boolean_return(call))
        return {source: proofs[0] if all(proof == proofs[0] for proof in proofs) else None
                for source, proofs in observations.items() if None not in proofs}

    ## Check whether evaluating a proved guard can raise on any reaching binding.
    ## 检查已证明的守卫在可达绑定上是否可能抛出异常。
    #
    #  @param operand Guard expression with logical negations removed.
    #  @param env Reaching bindings.
    #  @param proof Exact source predicate binding, if available.
    #  @param bool_sources Calls proved to return Boolean values.
    #  @return True for a non-raising evaluation in the supported cases.
    def _safe_boolean_guard(self, operand, env, proof, bool_sources):
        if proof is not None:
            arguments = list(operand.args) + [keyword.value for keyword in operand.keywords]
            return all(isinstance(argument, ast.Constant) or (
                isinstance(argument, ast.Name) and env.get(argument.id)
                and all(value.get('kind') in ('parameter', 'literal')
                        and not value.get('value_incomplete') for value in env[argument.id]))
                for argument in arguments)
        if isinstance(operand, ast.Name):
            values = env.get(operand.id, [])
            return bool(values) and all((_direct_guard_value(value) or (
                value.get('boolean_negated') is not None and
                not any(value.get(flag) for flag in ('value_incomplete', 'projection', 'output_path')))) and (
                value.get('literal', {}).get('type') == 'bool' or (
                    value.get('kind') == 'call_result' and value['source'] in bool_sources))
                for value in values)
        return isinstance(operand, ast.Constant) and type(operand.value) is bool

    ## Match a reaching path to the guards required by one local binding.
    ## 将抵达当前判断的路径与某个局部绑定所需的守卫配对。
    #
    #  @param conditions Ordered guards already observed on the path.
    #  @param binding_guards Conditions attached to the source binding.
    #  @return Merged guards, or None when the binding cannot reach this path.
    def _match_control_path(self, conditions, binding_guards):
        merged = list(conditions)
        for inherited in binding_guards:
            test = inherited.get('test')
            branch = inherited.get('branch')
            if not isinstance(test, dict) or branch is None:
                continue
            matches = [guard for guard in merged if guard['test'] == test]
            if any(guard['branch'] != branch for guard in matches):
                return None
            if not matches:
                # A binding guard can precede the first tracked predicate.
                span = (test['lineno'], test['col_offset'])
                index = next((index for index, guard in enumerate(merged)
                              if guard['test']['file_path'] == test['file_path']
                              and (guard['test']['lineno'], guard['test']['col_offset']) > span),
                             len(merged))
                merged.insert(index, {'test': test, 'branch': branch, 'call_ids': []})
        return merged

    ## Add one branch condition to every feasible path in an environment.
    ## 将一个分支条件追加到环境中的每条可行路径。
    #
    #  @param env Environment to update for the selected branch.
    #  @param test Branch condition expression.
    #  @param branch Boolean branch polarity.
    #  @param operand Guard expression with logical negations removed.
    #  @param inverted Whether the test negates the operand.
    #  @param proof Exact source predicate binding, if available.
    #  @param bool_sources Calls proved to return Boolean values.
    #  @return True when the selected branch remains feasible.
    def _extend_control_paths(self, env, test, branch, operand, inverted, proof, bool_sources):
        paths = env.get(self._CONTROL_PATH_KEY)
        call_ids = self._condition_call_ids(operand)
        values = env.get(operand.id, []) if isinstance(operand, ast.Name) else []
        bindings = [value for value in values
                    if value.get('kind') == 'call_result' and value.get('source')]
        has_literal = any(value.get('literal', {}).get('type') == 'bool' for value in values)
        if isinstance(operand, ast.Name):
            tracked = [value for value in values if value.get('kind') in (
                'literal', 'parameter', 'capture', 'call_result')]
            if tracked:
                bindings = tracked
        elif has_literal or bool_sources:
            bindings = values
        constant = (operand.value if isinstance(operand, ast.Constant)
                    and type(operand.value) is bool else None)
        # A literal condition does not need call evidence, but it still selects
        # one branch. Keep it in the ordered path so later return controls can
        # exclude the impossible arm without creating a call record.
        # 字面量条件不需要调用证据，但仍会选择分支；保留在有序路径中，
        # 使后续返回控制能排除不可达分支而不生成调用记录。
        if constant is not None:
            if not paths:
                return True
            selected = branch != inverted
            if constant != selected:
                return False
            guard = {'test': self.evidence(test), 'branch': branch, 'call_ids': [],
                     '_polarity': False, '_binding': ()}
            extended = []
            for path in paths:
                determined = path.get('determined_guards', [])
                updated = dict(path, conditions=_unique(path['conditions'] + [guard]))
                updated['determined_guards'] = _unique(determined + [guard])
                extended.append(updated)
            env[self._CONTROL_PATH_KEY] = _unique(extended)
            return bool(extended)
        if not paths and not call_ids and not bindings and proof is None:
            return True
        paths = paths or [{'kind': 'control_path', 'conditions': [
            dict(guard, call_ids=[]) for guard in self.conditions[:-1]
            if 'test' in guard and 'branch' in guard]}]
        predicate = self.evidence(test)
        extended = []
        for path in paths:
            conditions = path['conditions']
            alternatives = [(matched, value) for value in bindings
                            for matched in (self._match_control_path(
                                conditions, value.get('conditions', [])),)
                            if matched is not None]
            for guards, value in alternatives or [(conditions, {})]:
                sources = [value['source']] if value.get('kind') == 'call_result' else call_ids
                truths = dict(path.get('boolean_values', {}))
                truth, identity = None, None
                selected = branch != inverted
                input_proof = proof
                if not self._loop_control_depth and (_direct_guard_value(value) or (
                        value.get('boolean_negated') is not None and
                        not any(value.get(flag) for flag in ('value_incomplete', 'projection', 'output_path')))):
                    literal = value.get('literal')
                    if literal is not None and literal.get('type') == 'bool':
                        truth = bool(literal.get('value'))
                    elif value.get('kind') == 'call_result' and value['source'] in bool_sources:
                        identity = value['source']
                        negated = value.get('boolean_negated', False)
                        selected = selected != negated
                        truth = truths.get(identity)
                        input_proof = bool_sources[identity]
                    elif value.get('kind') in ('parameter', 'capture'):
                        truth = self._value_boolean_truth(value, truths)
                if input_proof is not None and truth is None:
                    truth = self._path_predicate_truth(input_proof, guards, truths, selected)
                if truth is not None and truth != selected:
                    continue
                if identity is not None:
                    truths[identity] = selected
                    self._propagate_call_result_truth(
                        identity, selected, guards, truths)
                # Keep operand polarity private. The public path keeps only
                # test/branch/call_ids, while redundancy folding must distinguish
                # `b = not a` from `b = a` on the same call.
                # 将操作数极性保存在内部。公共路径只保留 test/branch/call_ids；
                # 冗余折叠需要区分同一调用上的 `b = not a` 与 `b = a`。
                binding_values = [value] if value else (
                    self._argument_values(proof[0], guards) if proof is not None else [])
                guard = {'test': predicate, 'branch': branch, 'call_ids': sources,
                         '_polarity': bool(value.get('boolean_negated', False)),
                         '_binding': self._binding_signature(binding_values, guards)}
                determined = path.get('determined_guards', [])
                if truth is not None:
                    determined = _unique(determined + [guard])
                updated = dict(path, conditions=_unique(guards + [guard]))
                if truths:
                    updated['boolean_values'] = truths
                if determined:
                    updated['determined_guards'] = determined
                extended.append(updated)
        env[self._CONTROL_PATH_KEY] = _unique(extended)
        return bool(extended)

    ## Fold complementary guards when their downstream outcomes agree.
    ## 当守卫的真假两支具有相同后续结果时，合并这两条路径。
    #
    #  @param exits Outcomes with their remaining ordered guards.
    #  @return Comparable continuation with equivalent branches joined.
    def _joined_control_continuation(self, exits):
        nodes = [({}, set())]
        for kind, destination, guards in exits:
            node = 0
            for span, branch, sources, polarity, binding in guards:
                tests, _ = nodes[node]
                branches = tests.setdefault((span, sources, polarity, binding), {})
                if branch not in branches:
                    branches[branch] = len(nodes)
                    nodes.append(({}, set()))
                node = branches[branch]
            nodes[node][1].add((None, (kind, destination)))
        # Children are allocated after their parents. Fold the leaves first.
        # 子节点晚于父节点创建，从叶节点开始归并。
        continuations = {}
        for index in range(len(nodes) - 1, -1, -1):
            tests, completed = nodes[index]
            for test, branches in tests.items():
                outcomes = {branch: continuations[child] for branch, child in branches.items()}
                if len(outcomes) == 2 and outcomes[True] == outcomes[False]:
                    completed.update(outcomes[True])
                else:
                    completed.update(((test, branch), result)
                                     for branch, result in outcomes.items())
            continuations[index] = frozenset(completed)
        return continuations[0]

    ## Collect return controls from the completed paths and their actual exits.
    ## 根据已完成路径及其实际出口收集返回控制关系。
    #
    #  @param outcomes Final outcomes of the function body.
    #  @return Return control records grouped by call identifier.
    def _return_control_flows(self, outcomes):
        span_fields = ('file_path', 'lineno', 'col_offset', 'end_lineno', 'end_col_offset')
        continuations = {}
        records = []
        for kind, state, _, detail in outcomes:
            paths = state.get(self._CONTROL_PATH_KEY, [])
            if not paths:
                continue
            returned = (detail or {}).get('return') if kind == 'return' else None
            destination = tuple(returned[field] for field in span_fields) if returned else None
            for path in paths:
                conditions = path['conditions']
                determined = path.get('determined_guards', [])
                guards = tuple((tuple(condition['test'][field] for field in span_fields),
                                condition['branch'], tuple(condition.get('call_ids', ())),
                                bool(condition.get('_polarity', False)),
                                condition.get('_binding', ()))
                               for condition in conditions)
                for index, (span, branch, sources, polarity, binding) in enumerate(guards):
                    if conditions[index] in determined:
                        continue
                    for call_id in sources:
                        key = (call_id, span, guards[:index])
                        exits = continuations.setdefault(key, {True: set(), False: set()})
                        # Compare the value tested at each subsequent guard. Keep
                        # observation IDs on the original path for public evidence.
                        continuation = tuple(
                            (span_, taken, () if binding_ else ids,
                             False if binding_ else polarity_, binding_)
                            for (span_, taken, ids, polarity_, binding_), condition
                            in zip(guards[index + 1:], conditions[index + 1:])
                            if condition not in determined)
                        exits[branch].add((kind, destination, continuation))
                        if returned:
                            # Internal polarity is not part of flow-0.2.
                            # 内部极性不属于 flow-0.2 公共字段。
                            records.append((key, {
                                'call_id': call_id,
                                'predicate': conditions[index]['test'],
                                'branch': branch,
                                'path': [{key: value for key, value in condition.items()
                                          if not key.startswith('_')}
                                         for condition in conditions],
                                'return': returned,
                            }))
        redundant = set()
        for key, exits in continuations.items():
            positive, negative = exits[True], exits[False]
            if not positive or not negative:
                continue
            # A branch can skip inner tests and still reach the same return.
            # 两支可以执行不同的内层判断，最后仍到达同一处返回。
            combined = positive | negative
            destinations = {destination for _, destination, _ in combined}
            single_return = len(destinations) == 1 and None not in destinations
            known_exits = all(kind in ('return', 'raise', 'normal') for kind, _, _ in combined)
            same_continuation = (known_exits and (positive == negative or (
                {(kind, destination) for kind, destination, _ in positive}
                == {(kind, destination) for kind, destination, _ in negative}
                and self._joined_control_continuation(positive)
                == self._joined_control_continuation(negative))))
            if single_return or same_continuation:
                redundant.add(key)
        controls = {}
        for key, record in records:
            if key not in redundant:
                controls.setdefault(record['call_id'], []).append(record)
        return controls

    ## Preserve known field writes on possible call-exception paths.
    ## 在可能的调用异常路径上保留已知字段写入候选。
    #  The pre-call state remains alongside these writes because completion is unknown.
    #
    #  @param outcomes Possible exceptional outcomes created before expression evaluation.
    #  @param call_start Index of the first call evaluated by the current statement.
    #  @return The same outcomes with bounded field-write candidates added.
    def preserve_call_field_writes_on_exception(self, outcomes, call_start):
        if not outcomes:
            return outcomes
        calls = self.calls[call_start:]
        for call in calls:
            for value in call.mutation_flows:
                field_key = value.get('target_field_key')
                if not field_key:
                    continue
                for kind, state, values, exception in outcomes:
                    if kind != 'raise':
                        continue
                    if not state.get(field_key):
                        state[field_key] = [{
                            'kind': 'instance_field',
                            'source': field_key,
                            'field': value.get('target_field'),
                            'receiver': value.get('target_receiver'),
                            'relation': 'direct',
                            'evidence': list(value.get('evidence', [])),
                            'conditions': []}]
                    candidate = dict(value,
                        value_incomplete=True,
                        exception_write_candidate=True)
                    state[field_key] = _unique(state[field_key] + [candidate])
        return outcomes

    ## Evaluate one statement and return the outcome tuples it produces.
    ## 求值单条语句并返回其产生的结果元组。
    #
    #  @param node Statement node to evaluate.
    #  @param env Abstract environment read and updated in place.
    #  @return Outcome tuples tagged normal, return, raise, break, continue or unknown.
    def statement(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        call_start = len(self.calls)
        ## Construct normal outcomes while retaining earlier exceptional paths.
        ## 构造正常结果，同时保留此前的异常路径。
        #
        #  @param e Current abstract environment.
        #  @return Outcome tuple list.
        def normal(e):
            return [('normal', e, [], None)]
        if self.context_execution:
            if isinstance(node, ast.Nonlocal):
                return normal(env)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Import, ast.ImportFrom, ast.AugAssign)):
                self.add_boundary('context_exit_definition_or_write_unmodeled', node, env,
                                  affected_scope='unknown')
            if isinstance(node, ast.Delete) and len(node.targets) != 1:
                self.add_boundary('context_exit_multiple_delete_unmodeled', node, env,
                                  affected_scope='unknown')
            if (isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    and not all(isinstance(target, ast.Name) for target in (
                        node.targets if isinstance(node, ast.Assign) else [node.target]))):
                self.add_boundary('context_exit_assignment_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, (ast.For, ast.While)):
                self.add_boundary('context_exit_control_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.Try) and any(handler.type is not None and not (
                    isinstance(handler.type, ast.Name) and _exception_class(handler.type.id) is not None
                    and self.analyzer._builtin_name_status(self.ref, self.node, handler.type.id, env)
                        == 'confirmed_builtin') for handler in node.handlers):
                self.add_boundary('context_exit_handler_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.If):
                truth = self.context_truth(node.test, env)
                if truth is not None:
                    before = self.conditions
                    self.conditions = before + [{'test': self.evidence(node.test), 'branch': truth}]
                    outcomes = self.block(node.body if truth else node.orelse, env)
                    self.conditions = before
                    return outcomes
                self.add_boundary('context_exit_guard_unresolved', node.test, env, affected_scope='unknown')
            if isinstance(node, ast.Return):
                truth = self.context_truth(node.value, env) if node.value is not None else False
                previous = copy_environment(env)
                values = self.marked(self.expression(node.value, env), node)
                exceptional, possible = self.context_operation_exits(node.value, previous, env)
                return exceptional + ([('return', env, values, {'truth': truth})] if possible else [])
        previous = copy_environment(env) if self.context_execution else None
        exceptional = []
        # A possible exception uses the environment BEFORE evaluation. Simple
        # name/constant assignments cannot import a later definition into it.
        # 可能异常沿用求值前的环境，不能引入之后才建立的绑定。
        expressions = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Expr)):
            expressions = [node.value]
        elif isinstance(node, ast.If):
            expressions = [node.test]
        if any(_may_raise(e) for e in expressions if e is not None) and not all(
                self._expression_cannot_raise(e, env) for e in expressions if e is not None):
            exceptional = [('raise', copy_environment(env), [], None)]
        definite_raise = self.definite_argument_raise(node, env)
        if definite_raise is not None:
            first, exception = definite_raise
            self.expression(first, env)
            if not exceptional:
                exceptional = [('raise', copy_environment(env), [], None)]
            return exceptional + [('raise', env, [], exception)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults))
            defaults += [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]
            values = {a.arg: self.expression(d, env) for a, d in defaults}
            target = FunctionRef(self.ref.module, self.ref.qualname + '.' + node.name,
                                 self.ref.file_path, node.lineno)
            env[node.name] = [self.callable_value(target, node, values)]
            return normal(env)
        if isinstance(node, ast.ClassDef):
            env[node.name] = [{
                'kind': 'class',
                'module': self.ref.module,
                'source': self.ref.qualname + '.' + node.name,
                'relation': 'direct',
                'evidence': [self.evidence(node)],
                'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.If):
            start = len(self.calls)
            self.expression(node.test, env)
            exceptional = self.preserve_call_field_writes_on_exception(
                exceptional, call_start)
            operand, inverted = node.test, False
            while isinstance(operand, ast.UnaryOp) and isinstance(operand.op, ast.Not):
                operand, inverted = operand.operand, not inverted
            proof = None
            if isinstance(operand, ast.Call):
                call_id = _call_key(self.ref.file_path, operand)
                call = next((item for item in self.calls[start:] if item.id == call_id), None)
                if call is not None:
                    proof = self._boolean_return(call)
            elif (isinstance(operand, ast.Compare) and len(operand.ops) == 1
                  and isinstance(operand.ops[0], (ast.Is, ast.IsNot))):
                left, right = operand.left, operand.comparators[0]
                if isinstance(left, ast.Constant) and type(left.value) is bool:
                    left, right = right, left
                if (isinstance(left, ast.Name) and isinstance(right, ast.Constant)
                        and type(right.value) is bool):
                    proof = ({'sources': env.get(left.id, [])},
                             right.value, isinstance(operand.ops[0], ast.IsNot))
            values = env.get(operand.id, []) if isinstance(operand, ast.Name) else []
            bool_sources = self._boolean_bindings(values)
            if exceptional and self._safe_boolean_guard(operand, env, proof, bool_sources):
                exceptional = []
            before = list(self.conditions)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            positive = copy_environment(env)
            feasible = self._extend_control_paths(
                positive, node.test, True, operand, inverted, proof, bool_sources)
            left = (self.block(node.body, positive)
                    if feasible and self.refine_guard(node.test, positive) else [])
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            negative = copy_environment(env)
            feasible = self._extend_control_paths(
                negative, node.test, False, operand, inverted, proof, bool_sources)
            right = (self.block(node.orelse, negative)
                     if feasible and self.refine_guard(node.test, negative, positive=False) else [])
            self.conditions = before
            normal_left = [state for kind, state, _, _ in left if kind == 'normal']
            normal_right = [state for kind, state, _, _ in right if kind == 'normal']
            test_evidence = self.evidence(node.test)
            guard_surviving_sources(env, normal_left, normal_right, test_evidence)
            if any(self._CONTROL_PATH_KEY in state for state in normal_left + normal_right):
                # A sibling can start tracking inside its suite. Retain the
                # other suite's path when only one of them began tracking.
                for states, branch in ((normal_left, True), (normal_right, False)):
                    for state in states:
                        if self._CONTROL_PATH_KEY not in state:
                            conditions = [dict(guard, call_ids=[]) for guard in before
                                          if 'test' in guard and 'branch' in guard]
                            conditions.append({'test': test_evidence, 'branch': branch,
                                               'call_ids': []})
                            state[self._CONTROL_PATH_KEY] = [
                                {'kind': 'control_path', 'conditions': conditions}]
            if getattr(self.analyzer, '_conditional_source_state', False):
                if bool(normal_left) != bool(normal_right):
                    predicate = {'test': test_evidence, 'branch': bool(normal_left)}
                    for kind, state, _, _ in left + right:
                        if kind == 'normal':
                            for name, values in state.items():
                                state[name] = [dict(value, conditions=_unique(
                                    value.get('conditions', []) + [predicate])) for value in values]
            return exceptional + left + right
        if isinstance(node, ast.Try):
            return self.try_statement(node, env)
        if isinstance(node, ast.With):
            return self.with_statement(node, env)
        if isinstance(node, ast.AsyncWith):
            self.add_boundary('async_with_unsupported', node, env, affected_scope='unknown')
            return [('unknown', env, [], None)]
        if isinstance(node, (ast.For, ast.While)):
            before = copy_environment(env)
            head = copy_environment(env)
            exits = []
            if isinstance(node, ast.For):
                loop_exception = []
                if (_may_raise(node.iter)
                        and not self._expression_cannot_raise(node.iter, env)):
                    loop_exception = [('raise', copy_environment(env), [], None)]
                iterable = self.marked(self.project(self.expression(node.iter, env), '*', env), node.iter, 'derived')
                exits.extend(self.preserve_call_field_writes_on_exception(
                    loop_exception, call_start))
            converged = False
            for iteration in range(16):
                body_env = copy.deepcopy(head)
                if isinstance(node, ast.For):
                    self.assign_target(node.target, iterable, body_env, node)
                else:
                    loop_exception = []
                    if (_may_raise(node.test)
                            and not self._expression_cannot_raise(node.test, body_env)):
                        loop_exception = [('raise', copy.deepcopy(body_env), [], None)]
                    guard_call_start = len(self.calls)
                    self.expression(node.test, body_env)
                    exits.extend(self.preserve_call_field_writes_on_exception(
                        loop_exception, guard_call_start))
                self._loop_control_depth += 1
                try:
                    outcomes = self.block(node.body, body_env)
                finally:
                    self._loop_control_depth -= 1
                exits.extend(o for o in outcomes if o[0] not in ('normal', 'continue'))
                continuing = [before] + [e for k, e, _, _ in outcomes if k in ('normal', 'continue')]
                updated = _loop_env(_merge_env(continuing))
                if _loop_signature(updated) == _loop_signature(head):
                    head = updated
                    converged = True
                    break
                head = updated
            else:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'loop_iteration_limit',
                                               'evidence': self.evidence(node)})
            self.loops.append({'lineno': node.lineno, 'col_offset': node.col_offset,
                               'iterations': iteration + 1,
                               'status': 'converged' if converged else 'bounded',
                               'semantics': 'may-flow; one witness per dependency'})
            completed = self.block(node.orelse, head)
            completed += [('normal', e, [], None) for k, e, _, _ in exits if k == 'break']
            completed += [o for o in exits if o[0] != 'break']
            return completed
        if isinstance(node, (ast.Break, ast.Continue)):
            return [('break' if isinstance(node, ast.Break) else 'continue', env, [], None)]
        if isinstance(node, ast.Delete):
            for target in node.targets:
                self.invalidate_class_origins([value for name in _attribute_write_roots(target)
                    for value in env.get(name, [])], env)
                if isinstance(target, ast.Name):
                    values = env.get(target.id, [])
                    self.add_boundary('unsupported_assignment', node, env, values)
                    env[target.id] = []
                    continue
                if isinstance(target, ast.Subscript):
                    receivers = self.container_values(self.expression(target.value, env))
                    self.expression(target.slice, env)
                    if (receivers and all(value.get('kind') == 'container'
                            and value.get('container_shape') == 'dict'
                            for value in receivers)):
                        try:
                            key = ast.literal_eval(target.slice)
                        except (ValueError, TypeError):
                            key = '*'
                        roots, unknown = self.affected_values(receivers, env)
                        if key != '*' and len({value['source']
                                               for value in receivers}) == 1:
                            for reference in receivers:
                                remaining = []
                                for value in env.get(reference['source'], []):
                                    path = value.get('output_path', [])
                                    if path and path[0] == key:
                                        continue
                                    if path and path[0] == '*':
                                        value = dict(value, excluded_paths=_unique(
                                            value.get('excluded_paths', []) + [[key]]),
                                            conditions=value.get('conditions', []) +
                                                       list(self.conditions))
                                    remaining.append(value)
                                env[reference['source']] = remaining
                        self.mapping_effects.append({
                            'operation': 'delete', 'mapping': roots,
                            'element_path': [key],
                            'state_after': ('conditional' if self.conditions
                                            else 'absent' if key != '*' else 'unknown'),
                            'status': 'unknown_key' if key == '*' or unknown else 'bounded',
                            'conditions': list(self.conditions),
                            'evidence': self.evidence(node)})
                        if self.context_execution:
                            if key == '*':
                                self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                                                  affected_scope='unknown')
                            exceptional, possible = self.context_operation_exits(target, previous, env)
                            if not possible:
                                return exceptional
                        continue
                values = []
                if isinstance(target, (ast.Attribute, ast.Subscript)):
                    values = self.expression(target.value, env)
                self.add_boundary('unsupported_assignment', node, env, values)
            return exceptional + normal(env)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], (ast.Tuple, ast.List))
                    and isinstance(node.value, (ast.Tuple, ast.List))
                    and len(node.targets[0].elts) == len(node.value.elts)
                    and not any(isinstance(n, ast.Starred) for n in node.targets[0].elts + node.value.elts)):
                elements = [self.expression(v, env) for v in node.value.elts]
                exceptional = self.preserve_call_field_writes_on_exception(
                    exceptional, call_start)
                for target, values in zip(node.targets[0].elts, elements):
                    self.assign_target(target, values, env, node)
                return exceptional + normal(env)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            values = self.expression(node.value, env)
            exceptional = self.preserve_call_field_writes_on_exception(
                exceptional, call_start)
            if (not self.context_execution and not isinstance(node, ast.AugAssign)
                    and isinstance(node.value, ast.Constant) and type(node.value.value) is bool
                    and all(isinstance(target, ast.Name) for target in targets)):
                values = [{'kind': 'literal', 'source': repr(node.value.value),
                           'literal': self.literal_fact(node.value, env), 'relation': 'direct',
                           'evidence': [self.evidence(node.value)], 'conditions': []}]
            if self.context_execution:
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
                literal = self.literal_fact(node.value, env)
                if literal is not None:
                    values = [dict(value, literal=literal) for value in values] or [
                        {'kind': 'context_data', 'source': self.ref.qualname,
                         'literal': literal, 'relation': 'direct',
                         'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if isinstance(node, ast.AugAssign):
                values = self.marked(self.expression(node.target, env) + values, node, 'derived')
            for target in targets:
                self.assign_target(target, values, env, node)
            return exceptional + normal(env)
        if isinstance(node, ast.Return):
            values = self.marked(self.expression(node.value, env), node)
            exceptional = self.preserve_call_field_writes_on_exception(
                exceptional, call_start)
            return exceptional + [('return', env, values,
                                   {'return': self.evidence(node)})]
        if isinstance(node, ast.Expr):
            self.expression(node.value, env)
            exceptional = self.preserve_call_field_writes_on_exception(
                exceptional, call_start)
            if self.context_execution and isinstance(node.value, ast.Call):
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
            return exceptional + normal(env)
        if isinstance(node, ast.Raise):
            self.expression(node.exc, env)
            expression = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            exception = expression.id if isinstance(expression, ast.Name) else None
            return [('raise', env, [], exception)]
        if isinstance(node, ast.Import):
            for fact in import_facts(node):
                env[fact.python_binding] = [{
                    'kind': 'import',
                    'source': fact.name if fact.asname else fact.python_binding,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.ImportFrom):
            cached = cached_import(self.analyzer, self.ref, node, self.evidence, self.conditions)
            if cached is not None and cached not in self.cached_local_imports:
                self.cached_local_imports.append(cached)
            if node.level:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'relative_local_import', 'evidence': self.evidence(node)})
            for fact in import_facts(node):
                env[fact.python_binding] = ([{'kind': 'import',
                    'source': fact.module + '.' + fact.name,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
                                                  if not node.level else [])
            return normal(env)
        if isinstance(node, ast.Pass):
            return normal(env)
        self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_statement', 'evidence': self.evidence(node)})
        return [('unknown', env, [], None)]

    ## Bind value facts to one assignment target in the environment.
    ## 将一个赋值目标的值事实绑定到环境中。
    #
    #  @param target Assignment target node to bind.
    #  @param values Value facts assigned to the target.
    #  @param env Environment receiving the new bindings.
    #  @param node Source statement providing assignment evidence.
    #  @return None
    def assign_target(self, target, values, env, node):
        attribute = self.attribute_key(target, env)
        self.invalidate_class_origins([value for name in _attribute_write_roots(target)
            for value in env.get(name, [])], env)
        if attribute is not None:
            known = self.class_values(values, allow_incomplete=True, env=env)
            env[attribute[0]] = [dict(value, attribute_provenance=[{
                'receiver_class': attribute[1], 'attribute': target.attr,
                'storage_attribute': attribute[0].rsplit(':', 1)[-1],
                'assignment': self.evidence(node), 'conditions': copy.deepcopy(self.conditions)}])
                for value in self.marked(known, node)]
            if not known:
                self.add_boundary('unsupported_assignment', node, env, values)
            return
        if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                and self.ref.qualname.rpartition('.')[0]
                and isinstance(self.node, (ast.FunctionDef, ast.AsyncFunctionDef))):
            parameters = self.node.args.posonlyargs + self.node.args.args
            if parameters and target.value.id == parameters[0].arg:
                receivers = self.expression(target.value, env)
                field_keys = ([] if self.class_values(receivers, allow_incomplete=True, env=env)
                              else self.instance_field_keys(receivers, target.attr))
                if len(field_keys) == 1:
                    field_key = field_keys[0]
                    previous = env.get(field_key) or [{
                        'kind': 'instance_field', 'source': field_key,
                        'field': target.attr, 'receiver': copy.deepcopy(receivers[0]),
                        'relation': 'direct', 'evidence': [self.evidence(target)],
                        'conditions': []}]
                    env[field_key] = _unique(copy.deepcopy(previous) + [
                        dict(value, value_incomplete=True)
                        for value in self.marked(values, node)])
                    # Attribute assignment may invoke a descriptor or shadow a method.
                    # Retain receiver identity but require a fresh lookup proof afterwards.
                    identities = {value.get('source') for value in receivers
                                  if value.get('instance_type')}
                    if identities:
                        for name, sources in env.items():
                            env[name] = [dict(value, value_incomplete=True)
                                         if value.get('source') in identities
                                         and value.get('instance_type') else value
                                         for value in sources]
                    self.add_boundary('unsupported_assignment', node, env,
                                      list(values) + list(receivers),
                                      partial_support='instance_field_state')
                    return
        if isinstance(target, ast.Attribute):
            candidates, _ = self.callable_targets(self.expression(target.value, env))
            self.modified_return_callables.update(
                (candidate[0].module, candidate[0].qualname) for candidate in candidates)
        for name in _attribute_write_roots(target):
            root = target
            while isinstance(root, (ast.Attribute, ast.Subscript)):
                root = root.value
            if isinstance(root, ast.Name):
                self.invalidate_literals(self.expression(root, env), env)
                candidates, _ = self.callable_targets(self.expression(root, env))
                self.modified_return_callables.update(
                    (candidate[0].module, candidate[0].qualname) for candidate in candidates)
            imported = env.get(name, [])
            modified = {value['source'] for value in imported
                        if value.get('instance_type') or value.get('class_type') or value.get('instance_candidates')}
            if modified:
                for key, sources in env.items():
                    env[key] = [dict(value, value_incomplete=True, instance_candidates=[])
                                if value.get('source') in modified and (
                                    value.get('instance_type') or value.get('class_type') or value.get('instance_candidates'))
                                else value for value in sources]
            if not imported and name not in env:
                source = self.analyzer.imports.get(self.ref.module, {}).get(name)
                if source:
                    imported = [{'kind': 'import', 'source': source,
                                 'relation': 'direct',
                                 'evidence': [self.evidence(node)],
                                 'conditions': list(self.conditions)}]
            if imported and all(value.get('kind') == 'import' for value in imported):
                env[name] = [dict(value, import_modified=True) for value in imported]
        if isinstance(target, ast.Name):
            env[target.id] = self.marked(values, node)
        elif isinstance(target, (ast.Tuple, ast.List)) and not any(isinstance(t, ast.Starred) for t in target.elts):
            for index, element in enumerate(target.elts):
                projected = self.project(values, index, env)
                self.assign_target(element, projected, env, node)
        elif isinstance(target, ast.Subscript):
            receiver = self.container_values(self.expression(target.value, env))
            if receiver and all(v['kind'] == 'container' and v['container_shape'] == 'dict' for v in receiver):
                index = target.slice.value if isinstance(target.slice, ast.Constant) else '*'
                self.expression(target.slice, env)
                for ref in receiver:
                    previous = env.get(ref['source'], [])
                    if index != '*' and len({v['source'] for v in receiver}) == 1:
                        updated = []
                        for value in previous:
                            path = value.get('output_path', [None])
                            if path[0] == index:
                                continue
                            if path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[index]]))
                            updated.append(value)
                        previous = updated
                    inserted = [dict(v, output_path=[index] + v.get('output_path', []))
                                for v in self.marked(self.materialize(values, env), node)]
                    env[ref['source']] = _loop_env({'items': previous + inserted})['items']
                    keys = env.get(ref['source'] + '$keys', [])
                    for marker in keys:
                        if marker['key'] == '*' and index != '*':
                            marker.setdefault('excluded_keys', []).append(index)
                    env[ref['source'] + '$keys'] = _unique(keys +
                        [{'kind': 'key', 'source': repr(index), 'key': index}])
            else:
                target_values = (env.get(target.value.id, [])
                                 if isinstance(target.value, ast.Name) else [])
                try:
                    affected_key = ast.literal_eval(target.slice)
                except (ValueError, TypeError):
                    affected_key = '*'
                target_values = [dict(value, output_path=[affected_key] +
                                      value.get('output_path', []))
                                 for value in target_values]
                self.add_boundary('unsupported_assignment', node, env,
                                  list(values) + list(target_values))
        else:
            target_values = (env.get(target.value.id, [])
                             if isinstance(target, ast.Attribute)
                             and isinstance(target.value, ast.Name) else [])
            self.add_boundary('unsupported_assignment', node, env,
                              list(values) + list(target_values))

    ## Resolve a single stable source function used as a guard operand.
    ## 解析守卫操作数中使用的唯一稳定源码函数。
    #
    #  @param node Guard operand expression to resolve.
    #  @param env Environment holding the receiver bindings.
    #  @return Sole stable function candidate, or None when unresolved or unstable.
    def guard_callable(self, node, env):
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        if isinstance(node, ast.Attribute):
            bindings = env.get(root.id)
            if bindings is not None:
                if not bindings or any(value.get('kind') != 'import' for value in bindings):
                    return None
            elif root.id not in self.analyzer.imports.get(self.ref.module, {}):
                return None
        candidates, complete = self.callable_targets(self.expression(node, env))
        if not complete or len(candidates) != 1:
            return None
        ref, function = candidates[0]
        if ('.' in ref.qualname or not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                or function.decorator_list):
            return None
        return candidates[0]

    ## Refine environment facts under a guard branch and report its feasibility.
    ## 在守卫分支下收紧环境事实并报告该分支是否可行。
    #
    #  @param test Guard test expression being evaluated.
    #  @param env Environment refined for the selected branch.
    #  @param positive True when refining the branch where the test holds.
    #  @param allow_callable Whether callable identity facts may be used.
    #  @return False when known facts contradict the branch, otherwise True.
    def refine_guard(self, test, env, positive=True, allow_callable=True):
        if (getattr(self.analyzer, '_conditional_source_state', False)
                and isinstance(test, ast.Constant) and bool(test.value) != positive):
            return False
        if (getattr(self.analyzer, '_conditional_source_state', False) and allow_callable
                and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)):
            sides = [self.class_values(env.get(value.id, []), env=env)
                     for value in (test.left, test.comparators[0])]
            if all(values and not any(value.get('value_incomplete') for value in values)
                   and len(_unique([value['class_type'] for value in values])) == 1 for values in sides):
                identical = sides[0][0]['class_type'] == sides[1][0]['class_type']
                truth = identical if isinstance(test.ops[0], ast.Is) else not identical
                if truth != positive:
                    return False
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return self.refine_guard(test.operand, env, not positive, allow_callable)
        if isinstance(test, ast.BoolOp) and (positive and isinstance(test.op, ast.And)
                or not positive and isinstance(test.op, ast.Or)):
            # Short-circuit evaluation already refines each operand before the
            # next one runs. Do not replay identities after intervening effects.
            allow_callable = allow_callable and not any(isinstance(node, (
                ast.Call, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom,
                ast.Subscript, ast.BinOp)) or isinstance(node, ast.Compare)
                and not all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
                for node in ast.walk(test))
            for operand in test.values:
                if not self.refine_guard(operand, env, positive, allow_callable):
                    return False
        if (allow_callable and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))):
            equal = positive != isinstance(test.ops[0], ast.IsNot)
            for variable, source in ((test.left, test.comparators[0]),
                                     (test.comparators[0], test.left)):
                if not isinstance(variable, ast.Name) or not env.get(variable.id):
                    continue
                values = env[variable.id]
                if any(value.get('kind') not in ('parameter', 'capture', 'callable')
                       or value.get('relation') != 'direct' or any(value.get(flag) for flag in (
                           'projection', 'output_path', 'value_incomplete')) for value in values):
                    continue
                target = self.guard_callable(source, env)
                if target is None:
                    continue
                if all(value.get('literal') is not None for value in values):
                    return not equal
                candidates, complete = self.callable_targets(values)
                if complete and (all(candidate[0] != target[0] for candidate in candidates) if equal
                        else all(candidate[0] == target[0] for candidate in candidates)):
                    return False
                remaining = []
                for value in values:
                    known, closed = self.callable_targets([value])
                    if closed and len(known) == 1 and (known[0][0] == target[0]) != equal:
                        continue
                    remaining.append(value)
                if not equal:
                    env[variable.id] = remaining
                    return bool(remaining)
                evidence = self.evidence(test)
                env[variable.id] = [dict(value, callable_type=asdict(target[0]),
                    callable_evidence=_unique(value.get('callable_evidence', []) + [evidence]),
                    conditions=_unique(value.get('conditions', []) + list(self.conditions)))
                    for value in remaining]
                return True
        if (allow_callable and isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == 'isinstance' and len(test.args) == 2 and not test.keywords
                and isinstance(test.args[0], ast.Name) and isinstance(test.args[1], ast.Name)
                and test.args[1].id == 'str'
                and all(name not in env and name not in self.analyzer.imports.get(self.ref.module, {})
                        and name not in self.analyzer.module_bindings.get(self.ref.module, set())
                        and self.analyzer._resolve(self.ref, name) is None for name in ('str', 'isinstance'))):
            name = test.args[0].id
            targets, complete = self.callable_targets(env.get(name, []))
            if targets and complete:
                # Closed source function objects are not strings. Do not run
                # an impossible recursive branch and contaminate its sibling.
                return not positive
            if positive:
                env[name] = [dict(v, python_shape='str',
                                  conditions=v.get('conditions', []) + list(self.conditions))
                             for v in env.get(name, [])]
        return True

    ## Evaluate a try statement including its handlers and final body.
    ## 求值 try 语句，包括异常处理器和 finally 代码块。
    #
    #  @param node Try statement node to evaluate.
    #  @param env Environment entering the try statement.
    #  @return Outcome tuples for normal completions, handled exceptions and escapes.
    def try_statement(self, node, env):
        outcomes = self.block(node.body, copy_environment(env))
        completed = []
        # Merge exception prefixes by known exception spelling. This bounds
        # repeated handler analysis and preserves definitions at raise sites.
        raised = {}
        for kind, state, values, exception in outcomes:
            if kind == 'normal':
                completed.extend(self.block(node.orelse, state))
            elif kind == 'raise':
                raised.setdefault(exception, []).append(state)
            else:
                completed.append((kind, state, values, exception))
        for exception, states in raised.items():
            state = _merge_env(states)
            caught = False
            for handler in node.handlers:
                names = ([n.id for n in handler.type.elts if isinstance(n, ast.Name)]
                         if isinstance(handler.type, ast.Tuple)
                         else [handler.type.id] if isinstance(handler.type, ast.Name) else [])
                exact = handler.type is None
                raised_class = _exception_class(exception)
                handler_classes = [_exception_class(n) for n in names]
                # Unknown/custom inheritance cannot safely exclude a handler.
                if raised_class and handler_classes and all(handler_classes):
                    if not any(issubclass(raised_class, cls) for cls in handler_classes):
                        continue
                    exact = True
                before = list(self.conditions)
                self.conditions = before + [{'handler': self.evidence(handler), 'exception': exception or 'unknown'}]
                handled = copy_environment(state)
                if handler.name:
                    handled[handler.name] = []
                handler_exits = self.block(handler.body, handled)
                for item in handler_exits:
                    if handler.name:
                        item[1].pop(handler.name, None)
                completed.extend(handler_exits)
                self.conditions = before
                if exact:
                    caught = True
                    break
            if not caught:
                completed.append(('raise', state, [], exception))
        if not node.finalbody:
            return completed
        finalized = []
        for kind, state, values, exception in completed:
            for final_kind, final_env, final_values, final_exc in self.block(
                    node.finalbody, copy_environment(state)):
                if final_kind == 'normal':
                    finalized.append((kind, final_env, values, exception))
                else:
                    finalized.append((final_kind, final_env, final_values, final_exc))
        return finalized

    ## Execute the summarized function and populate its analysis result.
    ## 执行被摘要的函数并填充其分析结果。
    #
    #  @return None
    def run(self):
        if getattr(self.node, '_flow_branch_budget', None) is not None:
            self.result.boundaries.append({'function': asdict(self.ref),
                'reason': 'literal_branch_budget',
                'evidence': self.evidence(self.node._flow_branch_budget)})
        args = self.node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [a for a in (args.vararg, args.kwarg) if a]
        env = {a.arg: [{'kind': 'parameter', 'source': a.arg, 'relation': 'direct',
                        'evidence': [self.evidence(a)], 'conditions': []}] for a in parameters}
        for parameter, facts in self.incoming.items():
            if parameter in env:
                root = env[parameter][0]
                env[parameter] = [dict(root, **fact) for fact in facts]
        if self.receiver_class is not None and parameters:
            env[parameters[0].arg][0]['class_type'] = asdict(self.receiver_class)
        for values in list(env.values()):
            for value in values:
                for effect in value.get('class_lookup_mutations', []):
                    self.register_class_lookup_effect(effect, env)
        for parameter, shape in ((args.vararg, 'tuple'), (args.kwarg, 'dict')):
            if parameter is None:
                continue
            heap = '$parameter:%s:%s:%s' % (
                self.ref.file_path, self.ref.qualname, parameter.arg)
            root = env[parameter.arg][0]
            env[heap] = [dict(root, relation='contained', output_path=['*'])]
            env[heap + '$keys'] = [
                {'kind': 'key', 'source': '*', 'key': '*'}]
            env[parameter.arg] = [{
                'kind': 'container', 'source': heap,
                'container_shape': shape, 'parameter_container': parameter.arg,
                'relation': 'direct', 'evidence': [self.evidence(parameter)],
                'conditions': []}]
        shape_contract = self.analyzer.parameter_shapes.get(
            self.ref.module + '.' + self.ref.qualname, {})
        shapes = shape_contract.get('parameters', {})
        for name, shape in shapes.items():
            if name in env:
                env[name] = [dict(value, python_shape=shape,
                                  shape_provenance=shape_contract['provenance'])
                             for value in env[name]]
        for local in self.analyzer._scope_facts(self.node).bound:
            env.setdefault(local, [])
        capture_objects = {}
        for capture in self.analyzer._captures(self.ref, self.node):
            root = {'kind': 'capture', 'source': capture, 'relation': 'direct',
                    'evidence': [], 'conditions': []}
            facts = self.incoming.get(capture, [])
            binding = facts[0].get('capture_container_binding') if len(facts) == 1 else None
            if binding:
                identity = binding['source'], binding['shape']
                if identity not in capture_objects:
                    heap = '$capture:%s:%s:%s' % (self.ref.file_path, self.ref.qualname, capture)
                    capture_objects[identity] = heap, capture
                    env[heap] = [dict(root, relation='contained', output_path=['*'])]
                    env[heap + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                heap, origin = capture_objects[identity]
                env[capture] = [{'kind': 'container', 'source': heap,
                    'container_shape': binding['shape'], 'parameter_container': origin,
                    'relation': 'direct', 'evidence': copy.deepcopy(binding.get('evidence', [])),
                    'conditions': copy.deepcopy(binding.get('conditions', []))}]
            else:
                env[capture] = [root]
        outcomes = ([('return', env,
                      self.marked(self.expression(self.node.body, env), self.node.body), None)]
                    if isinstance(self.node, ast.Lambda) else self.block(self.node.body, env))
        generator = contains_yield(self.node)
        self.outcomes = outcomes
        self.exit_kinds = {kind for kind, _, _, _ in outcomes}
        for kind, state, values, _ in outcomes:
            if kind == 'return' and not generator:
                returned = self.materialize(values, state)
                self.normal_returns.append(returned)
                self.returns.extend(returned)
            elif kind in ('normal', 'unknown'):
                self.incomplete_return = True
        if generator:
            self.returns.extend(self.yields)
        self.returns = _unique(self.returns)
        merged = {}
        for call in self.calls:
            if call.id not in merged:
                merged[call.id] = call
            else:
                previous = merged[call.id]
                if previous.target != call.target:
                    previous.target = None
                if (previous.target_status != call.target_status
                        and 'local_container_protocol' in (
                            previous.target_status, call.target_status)):
                    previous.target = None
                    previous.target_status = 'receiver_unresolved'
                for attribute in ('parameter_bindings', 'parameter_flows', 'argument_sources', 'argument_flows',
                                   'control_flows',
                                   'capture_bindings', 'receiver_sources',
                                   'receiver_type_evidence', 'mutation_flows',
                                   'decorator_identity_evidence',
                                   'return_dependencies', 'effects', 'target_candidates',
                                   'binding_issues'):
                    setattr(previous, attribute, _unique(getattr(previous, attribute) + getattr(call, attribute)))
                previous.callable_sources = _unique(previous.callable_sources + call.callable_sources)
                previous.conditional_returns = _unique(previous.conditional_returns + call.conditional_returns)
                previous.class_method_bindings = _unique(previous.class_method_bindings + call.class_method_bindings)
                previous.class_metadata_bindings = _unique(previous.class_metadata_bindings + call.class_metadata_bindings)
                previous.class_read_bindings = _unique(previous.class_read_bindings + call.class_read_bindings)
                previous.conditional_source_bindings = _unique(
                    previous.conditional_source_bindings + call.conditional_source_bindings)
                previous.candidate_paths = _unique(previous.candidate_paths + call.candidate_paths)
                previous.constructor_bindings = _unique(previous.constructor_bindings + call.constructor_bindings)
                previous.instance_method_bindings = _unique(previous.instance_method_bindings + call.instance_method_bindings)
                previous.result_sources = _merge_result_sources(
                    previous.result_sources, call.result_sources)
                if previous.binding_status != call.binding_status:
                    previous.binding_status = 'uncertain'
        self.calls = list(merged.values())
        controls = self._return_control_flows(outcomes)
        for call in self.calls:
            call.control_flows = _unique(call.control_flows + controls.get(call.id, []))
        partial_effect_calls = {boundary.get('call_id') for boundary in self.result.boundaries
                                if boundary['reason'] == 'mapping_effect_unproven'}
        for call in self.calls:
            if call.id in partial_effect_calls:
                for effect in call.effects:
                    if effect.get('completion') == 'normal_return':
                        effect.update(state_after='conditional', status='partial_context')
        for effect in self.mapping_effects:
            if effect.get('call_id') in partial_effect_calls:
                effect.update(state_after='conditional', status='partial_context')
        ## Collect source nodes for the function summary.
        ## 收集函数摘要使用的源码节点。
        #
        #  @param node AST node to inspect.
        #  @return None
        def collect(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call):
                call_id = _call_key(self.ref.file_path, node)
                if call_id not in merged and self.remaining > 0:
                    self.remaining -= 1
                    call = FlowCall(call_id, self.ref, ast.unparse(node.func), node.lineno, node.col_offset,
                                    node.end_lineno, node.end_col_offset,
                                    analysis_status='not_analyzed', target_status='flow_not_analyzed')
                    self.calls.append(call)
                    merged[call_id] = call
            for child in ast.iter_child_nodes(node):
                collect(child)
        body = [self.node.body] if isinstance(self.node, ast.Lambda) else self.node.body
        for statement in body:
            collect(statement)
        self.calls.sort(key=lambda c: (c.lineno, c.col_offset))
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'fresh_mapping_member_checks': fresh_mapping_member_checks(self),
                                      'keyword_checks': keyword_validation_checks(
                                          self.analyzer, self.ref, self.node),
                                      'capture_rejection_guards': capture_rejection_checks(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_key_accesses': mapping_key_access_footprints(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_attribute_transfers': mapping_attribute_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_return_transfers': mapping_return_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'container_predicates': container_predicate_checks(
                                          self.analyzer, self.ref, self.node),
                                      'parameter_shapes': copy.deepcopy(shapes),
                                      'generator': generator,
                                      'loops': self.loops,
                                      'mapping_effects': self.mapping_effects,
                                      'returns': self.returns,
                                      'decorator_effects': self.analyzer._decoration_facts((self.ref, self.node))})
        if self.context_managers:
            self.result.functions[-1]['context_managers'] = self.context_managers
        fresh = self.analyzer._fresh_decoration_facts((self.ref, self.node))
        if fresh:
            self.result.functions[-1]['fresh_function_decorations'] = fresh
        wrapper = factory_wrapper(self.analyzer, (self.ref, self.node))
        if wrapper is not None and 'forwarding' in wrapper:
            self.result.functions[-1]['source_wrapper_forwarding'] = [wrapper]
        query = metadata_query(self.analyzer, (self.ref, self.node))
        if query is not None:
            self.result.functions[-1]['native_callable_metadata_queries'] = [query]
        observers = observer_effects(self.analyzer, (self.ref, self.node))
        if observers:
            self.result.functions[-1]['native_class_metadata_observers'] = observers
        if self.cached_local_imports:
            self.result.functions[-1]['cached_local_imports'] = self.cached_local_imports
        decorations = self.result.functions[-1]['decorator_effects']
        if decorations and self.analyzer._descriptor_kind((self.ref, self.node)) is None:
            for fact in decorations:
                if fact['body_binding_status'] != 'preserved':
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'decorator_effect_unconfirmed',
                        'identity_status': fact['identity_status'],
                        'body_binding_status': fact['body_binding_status'],
                        'issues': copy.deepcopy(fact['boundaries']),
                        'evidence': copy.deepcopy(fact['expression'])})
        object_fact, _ = self.analyzer._object_returns((self.ref, self.node))
        if object_fact:
            self.result.functions[-1]['return_objects'] = [{
                'parameter': object_fact['parameter'], 'identity': 'argument_alias',
                'evidence': [self.evidence(statement)
                             for statement in object_fact['evidence']]}]
            if object_fact.get('conditions'):
                self.result.functions[-1]['return_objects'][0]['conditions'] = object_fact['conditions']
            if object_fact.get('effects'):
                self.result.functions[-1]['return_objects'][0].update(
                    completion='normal_return', requires_shapes=_unique([
                        {'parameter': effect.target,
                         'shapes': ['dict'] if effect.receiver_shape else ['dict', 'list', 'set']}
                        for effect in object_fact['effects']]))
        guarded = self.analyzer._guarded_object_returns((self.ref, self.node))
        if guarded:
            self.result.functions[-1]['return_objects'] = _unique(
                self.result.functions[-1].get('return_objects', []) + guarded)
        if self.receiver_class is not None:
            self.result.functions[-1]['receiver_contexts'] = [asdict(self.receiver_class)]
        self.result.calls.extend(self.calls)
