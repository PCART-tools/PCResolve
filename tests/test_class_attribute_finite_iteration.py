## @package tests.test_class_attribute_finite_iteration

import ast

import pytest

from pcresolve.class_attribute_effects import class_attribute_writes, _ClassEffectLimit


def writes(body, max_nodes=2000, charge=None):
    node = ast.parse('def mutate(cls):\n' + '\n'.join('    ' + line for line in body.splitlines())).body[0]
    return class_attribute_writes(node, 'cls', lambda name: True, lambda node: False,
                                  max_nodes=max_nodes, charge=charge)


def test_nested_literal_loops_bound_every_written_name():
    proof = writes('''for prefix in ["get_", "set_"]:
    for alias in ("lw", "ec"):
        setattr(cls, prefix + alias, True)''')
    assert proof is not None
    assert proof.attributes == ('get_lw', 'get_ec', 'set_lw', 'set_ec')
    assert any(isinstance(node, ast.For) for node in proof.evidence)


def test_empty_loop_skips_unsupported_body_and_runs_else():
    proof = writes('''for name in []:
    opaque(cls)
else:
    cls.cache = 1''')
    assert proof is not None
    assert proof.attributes == ('cache',)


def test_last_iteration_binding_is_available_after_the_loop():
    proof = writes('''for name in ("first", "last"):
    pass
setattr(cls, name, 1)''')
    assert proof is not None
    assert proof.attributes == ('last',)


def test_loop_target_can_overwrite_the_class_alias_without_writing_it():
    proof = writes('''other = cls
for cls in ["cache"]:
    setattr(other, cls, 1)''')
    assert proof is not None
    assert proof.attributes == ('cache',)


@pytest.mark.parametrize('body', [
    'for name in unknown():\n    setattr(cls, name, 1)',
    'for name in [unknown()]:\n    setattr(cls, name, 1)',
    'for name in ["cache"]:\n    opaque(cls)',
    'for name in ["cache"]:\n    break',
    'for name in ["cache"]:\n    continue',
    'for name in ["cache"]:\n    name = unknown()\n    setattr(cls, name, 1)',
    'for name in ["cache"]:\n    cls.__dict__[name] = 1',
    'for name in ["cache"]:\n    setattr(cls, "__bases__", ())',
    'for name in [1]:\n    setattr(cls, name, 1)',
])
def test_dynamic_or_escaping_loop_does_not_prove_a_write_set(body):
    assert writes(body) is None


def test_expansion_is_charged_to_the_same_finite_budget():
    body = '''for left in ["a", "b", "c", "d"]:
    for right in ["w", "x", "y", "z"]:
        setattr(cls, left + right, 1)'''
    charges = []
    with pytest.raises(_ClassEffectLimit):
        writes(body, max_nodes=100, charge=charges.append)
    assert sum(charges) <= 100
    charges.clear()
    proof = writes(body, charge=charges.append)
    assert len(proof.attributes) == 16
    assert proof.nodes == sum(charges)
