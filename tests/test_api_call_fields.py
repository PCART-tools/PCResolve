## @package tests.test_api_call_fields
#  Verify new ApiCall fields (location, func_name, parameters) are populated.

import os
from pcresolve.cross_file import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'api_call_fields')


def test_source_location():
    result = analyze_project(FIXTURE)
    calls = {c.expression: c for c in result.all_api_calls}
    c = calls["requests.get('https://example.com')"]
    assert c.lineno == 2
    assert c.col_offset == 0
    assert c.file_path.endswith('main.py')


def test_end_location():
    result = analyze_project(FIXTURE)
    calls = {c.expression: c for c in result.all_api_calls}
    c = calls["requests.get('https://example.com')"]
    assert c.end_lineno == 2
    assert c.end_col_offset > 0


def test_func_parameters_split():
    result = analyze_project(FIXTURE)
    calls = {c.expression: c for c in result.all_api_calls}
    c = calls["requests.get('https://example.com')"]
    assert c.func_name == "requests.get"
    assert c.parameters == "'https://example.com'"
