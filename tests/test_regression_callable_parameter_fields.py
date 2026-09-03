## @package tests.test_regression_callable_parameter_fields
#  Constructor-injected callable fields retain exact local dispatch identity.

import pytest

from pcresolve import analyze_project


@pytest.mark.parametrize('setup,owner', [
    ('use(Holder(Cost()))', 'numpy'),
    ('other = Holder(Other()); use(Holder(Cost()))', 'numpy'),
    ('use(Holder(Other()))', 'unknown'),
    ('use(Holder(Cost())); use(Holder(Other()))', 'unknown'),
    ('holder = Holder(Cost()); holder.callback = Other(); use(holder)', 'unknown'),
    ('from dependency import mutate\nholder = Holder(Cost()); mutate(holder); use(holder)', 'unknown'),
    ('from dependency import mutate\nholder = Holder(Cost()); mutate([holder]); use(holder)', 'unknown'),
    ('from dependency import opaque, flag\nuse(Holder(Cost() if flag else opaque()))', 'unknown'),
])
def test_callable_field_uses_actual_constructor_argument(tmp_path, setup, owner):
    (tmp_path / 'main.py').write_text('''
import numpy as np
class Cost:
    def __call__(self, values):
        return np.reshape(values, (-1,))
class Other:
    def __call__(self, values):
        return None
class Holder:
    def __init__(self, callback):
        self.callback = callback
def use(holder):
    result = holder.callback([1, 2])
    result.reshape(-1, 1)
%s
''' % setup, encoding='utf-8')
    calls = analyze_project(str(tmp_path)).all_api_calls
    result = next(call for call in calls if call.func_name == 'result.reshape')
    assert result.top_library == owner


def test_parameter_receiver_must_not_escape_before_field_call(tmp_path):
    (tmp_path / 'main.py').write_text('''
import numpy as np
from dependency import mutate
class Cost:
    def __call__(self, value):
        return np.reshape(value, (-1,))
class Holder:
    def __init__(self, callback):
        self.callback = callback
def use(holder):
    mutate(holder)
    result = holder.callback([1])
    result.reshape(-1, 1)
use(Holder(Cost()))
''', encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'result.reshape')
    assert call.top_library == 'unknown'


def test_external_receiver_method_can_replace_injected_callable(tmp_path):
    (tmp_path / 'main.py').write_text('''
import numpy as np
from dependency import Base
class Cost:
    def __call__(self, value):
        return np.reshape(value, (-1,))
class Holder(Base):
    def __init__(self, callback):
        self.callback = callback
def use(holder):
    holder.reconfigure()
    result = holder.callback([1])
    result.reshape(-1, 1)
use(Holder(Cost()))
''', encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'result.reshape')
    assert call.top_library == 'unknown'


@pytest.mark.parametrize('method_body,owner', [
    ('return self.callback', 'numpy'),
    ('mutate(self)', 'unknown'),
])
def test_local_receiver_method_requires_non_escaping_body(tmp_path, method_body, owner):
    (tmp_path / 'main.py').write_text('''
import numpy as np
from dependency import mutate
class Cost:
    def __call__(self, value):
        return np.reshape(value, (-1,))
class Holder:
    def __init__(self, callback):
        self.callback = callback
    def prepare(self):
        %s
def use(holder):
    result = holder.callback([1])
    result.reshape(-1, 1)
holder = Holder(Cost())
holder.prepare()
use(holder)
''' % method_body, encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'result.reshape')
    assert call.top_library == owner


def test_constructor_must_not_publish_field_owner(tmp_path):
    (tmp_path / 'main.py').write_text('''
import numpy as np
from dependency import register
class Cost:
    def __call__(self, value):
        return np.reshape(value, (-1,))
class Holder:
    def __init__(self, callback):
        self.callback = callback
        register(self)
def use(holder):
    result = holder.callback([1])
    result.reshape(-1, 1)
use(Holder(Cost()))
''', encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'result.reshape')
    assert call.top_library == 'unknown'
