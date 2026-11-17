## @package tests.test_kind_alias_scan

import ast

from pcresolve.flow.proofs.namespaces.metadata._kind_alias_scan import (
    collect_kind_alias_bindings,
    imported_kind_aliases_are_closed,
    inspect_module_kind_aliases,
    kind_alias_uses_closed,
)


def module_index(source):
    body = ast.parse(source).body
    nodes, parents, scopes = [], {}, {}
    pending = [(node, None) for node in body]
    while pending:
        node, scope = pending.pop()
        nodes.append(node)
        scopes[node] = scope
        for child in ast.iter_child_nodes(node):
            parents[child] = node
            pending.append((child, node if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) else scope))
    return body, nodes, parents, scopes


def canonical(_reference, _scope, node):
    return 'inspect.Parameter' if ast.unparse(node) == 'inspect.Parameter' else ''


def identity_operand(node, parent):
    return (isinstance(parent, ast.Compare)
            and all(isinstance(operator, (ast.Is, ast.IsNot)) for operator in parent.ops)
            and (parent.left is node or any(item is node for item in parent.comparators)))


def kind_comparison(node, parent, _scope):
    if not isinstance(parent, ast.Compare) or not any(
            isinstance(operator, (ast.Eq, ast.NotEq)) for operator in parent.ops):
        return False
    return (parent.left is node and any(ast.unparse(item).endswith('.kind')
                                        for item in parent.comparators)
            or any(item is node for item in parent.comparators)
            and ast.unparse(parent.left).endswith('.kind'))


def inspect_module(source, module='sample'):
    _, nodes, parents, scopes = module_index(source)
    aliases = inspect_module_kind_aliases(
        module, nodes, parents, scopes, object(), canonical=canonical,
        identity_operand=identity_operand, kind_comparison=kind_comparison,
        kind_replacement=lambda *_: False,
        stable_module_alias=lambda *_: True)
    return aliases


def test_local_kind_aliases_allow_only_proven_identity_or_kind_comparisons():
    aliases = inspect_module('''
import inspect
kind = inspect.Parameter.POSITIONAL_ONLY
alias = kind
def valid(parameter):
    return alias is parameter.kind
''')

    assert aliases == {('sample', 'kind'), ('sample', 'alias')}


def test_callback_capable_use_of_a_local_alias_is_rejected():
    aliases = inspect_module('''
import inspect
kind = inspect.Parameter.POSITIONAL_ONLY
def valid():
    callback(kind)
''')

    assert aliases is None


def test_class_slot_alias_is_rejected_even_without_a_local_read():
    aliases = inspect_module('''
import inspect
class Public:
    kind = inspect.Parameter.POSITIONAL_ONLY
''')

    assert aliases is None


def test_assignment_target_escape_is_rejected():
    aliases = inspect_module('''
import inspect
holder.kind = inspect.Parameter.POSITIONAL_ONLY
''')

    assert aliases is None


def test_cross_module_import_use_closes_an_otherwise_local_alias():
    aliases = inspect_module('''
import inspect
kind = inspect.Parameter.POSITIONAL_ONLY
''')
    imported_use = ast.parse('consume(kind)').body[0]
    imported_bodies = {'consumer': [('consumer.py', [imported_use])]}

    assert aliases == {('sample', 'kind')}
    assert imported_kind_aliases_are_closed(
        aliases, imported_bodies, {'consumer': {'kind': 'sample.kind'}}, identity_operand) is False
    assert imported_kind_aliases_are_closed(
        aliases, imported_bodies, {'consumer': {'other': 'sample.kind'}}, identity_operand) is True


def test_alias_propagation_and_use_validation_have_separate_inputs_and_outputs():
    _, nodes, parents, scopes = module_index('''
import inspect
kind = inspect.Parameter.POSITIONAL_ONLY
alias = kind
def valid(parameter):
    return alias is parameter.kind
''')
    collected = collect_kind_alias_bindings(
        'sample', nodes, scopes, object(), canonical=canonical,
        stable_module_alias=lambda *_: True)

    assert collected is not None
    aliases, module_aliases = collected
    assert aliases == {'kind', 'alias'}
    assert module_aliases == {('sample', 'kind'), ('sample', 'alias')}
    assert kind_alias_uses_closed(
        'sample', aliases, nodes, parents, scopes, object(), canonical=canonical,
        identity_operand=identity_operand, kind_comparison=kind_comparison,
        kind_replacement=lambda *_: False)


def test_alias_use_validation_rejects_an_escape_from_a_collected_binding():
    _, nodes, parents, scopes = module_index('''
import inspect
kind = inspect.Parameter.POSITIONAL_ONLY
def escape():
    callback(kind)
''')
    aliases, _ = collect_kind_alias_bindings(
        'sample', nodes, scopes, object(), canonical=canonical,
        stable_module_alias=lambda *_: True)

    assert kind_alias_uses_closed(
        'sample', aliases, nodes, parents, scopes, object(), canonical=canonical,
        identity_operand=identity_operand, kind_comparison=kind_comparison,
        kind_replacement=lambda *_: False) is False
