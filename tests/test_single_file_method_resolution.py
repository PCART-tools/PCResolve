## @package tests.test_single_file_method_resolution
#  Characterize receiver-method source collection before extraction.

from pcresolve.cross_file import analyze_project


def test_method_resolution_preserves_receiver_kinds(tmp_path):
    source = tmp_path / "main.py"
    source.write_text(
        "import re\n"
        "class Worker:\n"
        "    def run(self):\n"
        "        return None\n"
        "def clean(value):\n"
        "    return value.strip()\n"
        "' text '.strip()\n"
        "re.compile('a').match('a')\n"
        "Worker().run()\n"
        "clean(' value ')\n",
        encoding="utf-8",
    )

    result = analyze_project(str(tmp_path))
    owners = {call.expression: call.top_library
              for call in result.all_api_calls}

    assert owners["' text '.strip()"] == "python"
    assert owners["re.compile('a').match('a')"] == "re"
    assert owners["Worker().run()"] == "local"
    assert owners["value.strip()"] == "python"
