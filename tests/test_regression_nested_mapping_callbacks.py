## @package tests.test_regression_nested_mapping_callbacks
#  Literal mapping identities must not outlive their source evidence.

import pytest

from pcresolve import analyze_project


PREFIX = """
def consume(packed_options):
    return packed_options.get('value')

def other(value):
    pass

def external(value):
    pass
"""


def _owner(tmp_path, body):
    (tmp_path / 'main.py').write_text(PREFIX + body, encoding='utf-8')
    result = analyze_project(str(tmp_path))
    calls = [call for call in result.all_api_calls
             if call.expression == "packed_options.get('value')"
             and call.file_path.endswith('main.py')]
    assert len(calls) == 1
    return calls[0].top_library


@pytest.mark.parametrize('selection', [
    "table['module']['run']",
    "table.get('module').get('run')",
    "table['module'].get('run')",
    "table.get('module')['run']",
    "table.get('absent', {'run': consume}).get('run')",
])
def test_nested_selection_propagates_arguments(tmp_path, selection):
    assert _owner(tmp_path, """
table = {'module': {'run': consume}}
callback = %s
callback({})
""" % selection) == 'python'


def test_alias_retains_old_object_after_local_rebind(tmp_path):
    assert _owner(tmp_path, """
def invoke():
    table = {'module': {'run': consume}}
    alias = table
    table = {'module': {'run': other}}
    callback = alias['module']['run']
    callback({})
invoke()
""") == 'python'


def test_dynamic_key_retains_possible_local_targets(tmp_path):
    assert _owner(tmp_path, """
table = {'module': {'run': consume, 'other': other}}
def invoke(key):
    selected = table.get('module')
    callback = selected.get(key)
    if callback:
        callback({})
invoke('run')
""") == 'python'


@pytest.mark.parametrize('body', [
    "return {}",
    "options = {}\n    options['value'] = 1\n    return options",
])
def test_callback_argument_retains_local_factory_dictionary_shape(tmp_path, body):
    assert _owner(tmp_path, """
def build():
    %s
table = {'module': {'run': consume}}
callback = table['module']['run']
callback(build())
""" % body) == 'python'


def test_mixed_factory_shapes_do_not_claim_dictionary_method(tmp_path):
    assert _owner(tmp_path, """
def build(flag):
    if flag:
        return {}
    return 42
table = {'module': {'run': consume}}
callback = table['module']['run']
callback(build(external(None)))
""") == 'unknown'


@pytest.mark.parametrize('body', [
    """
table = {'module': {'run': consume, 'run': other}}
callback = table['module']['run']
callback({})
""",
    """
table = {'module': {'run': consume}}
alias = table['module']
alias['run'] = other
callback = table['module']['run']
callback({})
""",
    """
table = {'module': {'run': consume}}
alias = table
alias.update({'module': {'run': other}})
callback = table.get('module').get('run')
callback({})
""",
    """
table = {'module': {'run': consume}}
external([table])
callback = table['module']['run']
callback({})
""",
    """
table = {'module': {'run': consume}}
def invoke(table):
    callback = table.get('module').get('run')
    callback({})
invoke({})
""",
    """
table = {'module': {'run': consume}}
def invoke():
    callback = table['module']['run']
    callback({})
table = {'module': {'run': other}}
invoke()
""",
    """
def invoke(condition):
    table = {'module': {'run': consume}}
    if condition:
        table = external(None)
    callback = table['module']['run']
    callback({})
invoke(True)
""",
    """
table = {'module': {'run': consume}}
del table['module']['run']
callback = table['module']['run']
callback({})
""",
    """
table = {'module': {'run': consume}}
def invoke():
    callback = table['module']['run']
    callback({})
    table = {}
invoke()
""",
    """
def invoke():
    table = {'module': {'run': consume}}
    def change():
        table['module']['run'] = other
    change()
    callback = table['module']['run']
    callback({})
invoke()
""",
    """
def invoke(condition):
    table = {'module': {'run': other}}
    while condition:
        table = {'module': {'run': consume}}
    callback = table['module']['run']
    callback({})
invoke(False)
""",
    """
def invoke():
    table = {'module': {'run': other}}
    try:
        external(None)
    except Exception:
        table = {'module': {'run': consume}}
    callback = table['module']['run']
    callback({})
invoke()
""",
    """
table = {'module': {'run': consume}, **external(None)}
callback = table['module']['run']
callback({})
""",
    """
key = external(None)
table = {'module': {'run': consume}, key: {'run': other}}
callback = table['module']['run']
callback({})
""",
    """
table = {'module': {'run': consume}}
table |= {'module': {'run': other}}
callback = table['module']['run']
callback({})
""",
])
def test_unproven_or_invalidated_target_does_not_create_edge(tmp_path, body):
    assert _owner(tmp_path, body) != 'python'


def test_mapping_target_does_not_leak_to_same_name_in_another_module(tmp_path):
    (tmp_path / 'unused.py').write_text(PREFIX, encoding='utf-8')
    _owner(tmp_path, """
table = {'module': {'run': consume}}
callback = table['module']['run']
callback({})
""")
    result = analyze_project(str(tmp_path))
    calls = [call for call in result.all_api_calls
             if call.expression == "packed_options.get('value')"]
    owners = {call.file_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]:
              call.top_library for call in calls}
    assert owners == {'main.py': 'python', 'unused.py': 'unknown'}
