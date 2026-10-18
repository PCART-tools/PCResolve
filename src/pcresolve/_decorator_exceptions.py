## @package pcresolve._decorator_exceptions
#  Exception-only translations inside a bounded decoration proof.

import ast
import copy
from dataclasses import asdict

from .effect_facts import builtin_exception_translation
from .scope_facts import statement_scope_facts


def builtin_raise(proof, statement, env, target, initializing, shapes_of, translation=None):
    ref, definition = target
    raised = statement.exc
    cause = (statement.cause is None or isinstance(statement.cause, ast.Constant)
             and statement.cause.value is None
             or translation is not None and translation['cause_kind'] == 'caught_exception'
             and isinstance(statement.cause, ast.Name)
             and statement.cause.id == translation['exception_name'])
    if (isinstance(raised, ast.Call) and isinstance(raised.func, ast.Name)
            and raised.func.id in ('KeyError', 'TypeError', 'ValueError', 'AttributeError')
            and not raised.keywords and not any(isinstance(arg, ast.Starred) for arg in raised.args)
            and cause and proof.analyzer._builtin_name_status(ref, definition, raised.func.id)
                == 'confirmed_builtin' and proof.scalar_builtin_namespace(ref, statement)):
        values = [proof.expression(arg, env, target, initializing) for arg in raised.args]
        scalar = {'str', 'int', 'bool', 'float', 'NoneType'}
        shapes = [sorted(shapes_of(value)) for value in values]
        if all(shape and set(shape) <= scalar for shape in shapes):
            proof.effects.append({'operation': 'raise', 'target': raised.func.id,
                'impact': 'control_only', 'element_path': [],
                'protocol': 'builtin_exception_raise', 'argument_shapes': shapes,
                'completion': 'exceptional_exit', 'function': asdict(ref),
                'evidence': proof.evidence_at(ref, statement),
                'conditions': copy.deepcopy(proof.conditions),
                **({'exception_translation': translation} if translation is not None else {})})
            return True
    proof.issue('decorator_raise_protocol_unproven', ref, statement)
    return False


def translate(proof, statement, env, target, initializing, shapes_of):
    if statement.orelse or statement.finalbody or not 1 <= len(statement.handlers) <= 4:
        return None
    ref, definition = target
    shapes = [builtin_exception_translation(handler) for handler in statement.handlers]
    if any(shape is None for shape in shapes):
        return None
    proof.extra_assumptions.append('builtin_exception_handler_semantics')
    # The handler can run after any body prefix. Only immutable local inputs
    # untouched throughout the try body can be reused from its entry state.
    written = statement_scope_facts(statement.body).bound
    for handler, shape in zip(statement.handlers, shapes):
        if set(shape['argument_names']) & written:
            proof.issue('decorator_exception_translation_unproven', ref, handler)
            return None
        if not all(proof.analyzer._builtin_name_status(ref, definition, name)
                   == 'confirmed_builtin' for name in shape['caught_types']):
            proof.issue('decorator_exception_translation_unproven', ref, handler)
            return None
        translation = {**shape, 'handler': proof.evidence_at(ref, handler),
            'try': proof.evidence_at(ref, statement),
            'completion': 'exceptional_exit_only', 'runtime_exception_observed': False}
        local = dict(env)
        if handler.name is not None:
            local[handler.name] = {'kind': 'data'}
        proof.evidence.append(proof.evidence_at(ref, handler))
        proof.conditions.append({'exception_handler': proof.evidence_at(ref, handler),
                                 'caught_types': list(shape['caught_types'])})
        try:
            builtin_raise(proof, handler.body[0], local, target, initializing, shapes_of, translation)
        finally:
            proof.conditions.pop()
    # All supported handlers terminate exceptionally. They cannot supply a
    # return value, restore a modified binding, or continue after the try.
    return proof.statements(statement.body, env, target, initializing)
