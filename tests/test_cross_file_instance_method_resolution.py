## @package tests.test_cross_file_instance_method_resolution
#  Characterize instance-method ownership before extracting its resolver.

from pcresolve.cross_file import analyze_project


def test_instance_method_resolution_preserves_receiver_evidence(tmp_path):
    source = tmp_path / "main.py"
    source.write_text(
        "import re\n"
        "class Worker:\n"
        "    def run(self):\n"
        "        return None\n"
        "items = []\n"
        "items.append(1)\n"
        "worker = Worker()\n"
        "worker.run()\n"
        "match = re.match('a', 'a')\n"
        "match.group(0)\n",
        encoding="utf-8",
    )

    result = analyze_project(str(tmp_path))
    owners = {call.expression: call.top_library
              for call in result.all_api_calls}

    assert owners["items.append(1)"] == "python"
    assert owners["worker.run()"] == "local"
    assert owners["match.group(0)"] == "re"
