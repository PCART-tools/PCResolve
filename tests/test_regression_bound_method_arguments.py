## @package tests.test_regression_bound_method_arguments
#  Implicit method receivers must not shift explicit call arguments.

import pytest

from pcresolve import analyze_project


@pytest.mark.parametrize('declaration,invocation', [
    ('@classmethod\n    def consume(cls, text):', "Worker.consume('abc')"),
    ('@classmethod\n    def consume(klass, text):', "Worker.consume('abc')"),
    ('def consume(instance, text):', "Worker().consume('abc')"),
    ('@staticmethod\n    def consume(self, text):', "Worker.consume(42, 'abc')"),
])
def test_bound_receiver_is_not_an_explicit_argument(tmp_path, declaration, invocation):
    (tmp_path / 'main.py').write_text('''
class Worker:
    %s
        text.upper()
%s
''' % (declaration, invocation), encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'text.upper')
    assert call.top_library == 'python'


def test_ordinary_function_parameter_named_self_is_not_skipped(tmp_path):
    (tmp_path / 'main.py').write_text('''
def consume(self, text):
    text.upper()
consume('abc', 42)
''', encoding='utf-8')
    call = next(c for c in analyze_project(str(tmp_path)).all_api_calls
                if c.func_name == 'text.upper')
    assert call.top_library == 'unknown'
