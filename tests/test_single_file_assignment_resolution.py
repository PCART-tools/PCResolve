## @package tests.test_single_file_assignment_resolution
#  Characterize assignment facts before extracting the visitor stage.

from pcresolve.cross_file import analyze_project


def test_assignments_preserve_direct_container_and_unpack_sources(tmp_path):
    source = tmp_path / "main.py"
    source.write_text(
        "import re\n"
        "pattern = re.compile('a')\n"
        "pattern.match('a')\n"
        "patterns = [re.compile('b')]\n"
        "patterns[0].match('b')\n"
        "left, right = (re.compile('c'), re.compile('d'))\n"
        "right.match('d')\n",
        encoding="utf-8",
    )

    result = analyze_project(str(tmp_path))
    owners = {call.expression: call.top_library
              for call in result.all_api_calls}

    assert owners["pattern.match('a')"] == "re"
    assert owners["patterns[0].match('b')"] == "re"
    assert owners["right.match('d')"] == "re"
