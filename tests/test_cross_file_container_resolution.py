## @package tests.test_cross_file_container_resolution
#  Characterize container item and iteration ownership before extraction.

from pcresolve.cross_file import analyze_project


def test_container_resolution_preserves_item_and_iteration_sources(tmp_path):
    source = tmp_path / "main.py"
    source.write_text(
        "import re\n"
        "patterns = (re.compile('a'), re.compile('b'))\n"
        "patterns[0].match('a')\n"
        "patterns[-1].match('b')\n"
        "for pattern in patterns:\n"
        "    pattern.match('text')\n"
        "words = ['alpha']\n"
        "for word in words:\n"
        "    word.strip()\n",
        encoding="utf-8",
    )

    result = analyze_project(str(tmp_path))
    owners = {call.expression: call.top_library
              for call in result.all_api_calls}

    assert owners["patterns[0].match('a')"] == "re"
    assert owners["patterns[-1].match('b')"] == "re"
    assert owners["pattern.match('text')"] == "re"
    assert owners["word.strip()"] == "python"
