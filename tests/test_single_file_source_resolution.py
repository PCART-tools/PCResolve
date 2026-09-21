## @package tests.test_single_file_source_resolution
#  Characterize expression source tracing after extracting the subsystem.

from pcresolve.single_file import analyze_source


def test_source_resolution_preserves_dynamic_import_and_container_item_owners():
    result = analyze_source(
        "import importlib\n"
        "import re\n"
        "module = importlib.import_module('json')\n"
        "patterns = [re.compile('x')]\n"
        "module.loads('{}')\n"
        "patterns[0].match('x')\n"
    )
    owners = {call.expression: call.top_library for call in result.api_calls}

    assert owners["importlib.import_module('json')"] == 'json'
    assert owners["module.loads('{}')"] == 'json'
    assert owners["patterns[0].match('x')"] == 're'
