## @package tests.test_single_file_call_collection
#  Characterize single-file call collection before extracting the stage.

from pcresolve.single_file import analyze_source


def test_call_collection_preserves_builtin_import_and_local_owners():
    result = analyze_source(
        "import json\n"
        "def helper():\n"
        "    return None\n"
        "json.loads('{}')\n"
        "len([])\n"
        "helper()\n"
    )
    owners = {call.expression: call.top_library for call in result.api_calls}

    assert owners["json.loads('{}')"] == "json"
    assert owners["len([])"] == "python"
    assert owners["helper()"] == "local"
