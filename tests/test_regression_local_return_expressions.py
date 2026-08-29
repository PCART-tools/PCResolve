## @package tests.test_regression_local_return_expressions
#  Local return operators retain both operand dependencies.

import pytest

from pcresolve import analyze_project


def _calls(tmp_path, source):
    (tmp_path / 'main.py').write_text(source, encoding='utf-8')
    return {call.expression: call.top_library
            for call in analyze_project(str(tmp_path)).all_api_calls}


def test_return_of_two_locally_bound_arrays(tmp_path):
    calls = _calls(tmp_path, '''
import numpy as np
def build():
    first = np.reshape([1, 2, 3], (3,))
    second = np.reshape([4, 5, 6], (3,))
    return first + second
result = build()
result.reshape(1, -1)
''')
    assert calls['result.reshape(1, -1)'] == 'numpy'


def test_return_arithmetic_preserves_existing_conversion(tmp_path):
    calls = _calls(tmp_path, '''
from scipy.spatial.distance import cdist
def build(a, b):
    return 1 - cdist(a, b)
result = build([], [])
result.reshape(1, -1)
''')
    assert calls['result.reshape(1, -1)'] == 'numpy'
    assert calls['cdist(a, b)'] == 'scipy'


@pytest.mark.parametrize('other', ['unbound', 'opaque()', 'None'])
def test_return_expression_keeps_unknown_or_invalid_operand(tmp_path, other):
    calls = _calls(tmp_path, '''
import numpy as np
from dependency import opaque
def build():
    first = np.reshape([1, 2, 3], (3,))
    return first + %s
result = build()
result.reshape(1, -1)
''' % other)
    assert calls['result.reshape(1, -1)'] != 'numpy'


def test_return_expression_uses_values_before_later_rebinding(tmp_path):
    calls = _calls(tmp_path, '''
import numpy as np
def build():
    first = np.reshape([1, 2, 3], (3,))
    second = np.reshape([4, 5, 6], (3,))
    return first + second
first = None
second = None
result = build()
result.reshape(1, -1)
''')
    assert calls['result.reshape(1, -1)'] == 'numpy'


def test_scalar_default_in_parameter_expression(tmp_path):
    calls = _calls(tmp_path, '''
import numpy as np
def consume(value, scale=2):
    (value * scale).sum()
consume(np.reshape([1, 2, 3], (3,)))
''')
    assert calls['(value * scale).sum()'] == 'numpy'


def test_scalar_binding_in_parameter_expression(tmp_path):
    calls = _calls(tmp_path, '''
import numpy as np
def consume(value, scale):
    (value * scale).sum()
weight = 0.5
alias = weight
consume(np.reshape([1, 2, 3], (3,)), alias)
''')
    assert calls['(value * scale).sum()'] == 'numpy'


def test_scalar_rebinding_cannot_supply_stale_shape(tmp_path):
    calls = _calls(tmp_path, '''
import numpy as np
from dependency import opaque
def consume(value, scale):
    (value * scale).sum()
weight = 0.5
weight = opaque()
consume(np.reshape([1, 2, 3], (3,)), weight)
''')
    assert calls['(value * scale).sum()'] == 'unknown'


def test_resolved_return_owner_is_not_looked_up_through_star_import(tmp_path):
    (tmp_path / 'factory.py').write_text('''
import pandas as pd
def build():
    return pd.read_csv('input.csv')
''', encoding='utf-8')
    calls = _calls(tmp_path, '''
from factory import *
result = build()
result.head()
''')
    assert calls['result.head()'] == 'pandas'
