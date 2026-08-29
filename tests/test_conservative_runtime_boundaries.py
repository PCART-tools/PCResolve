## @package tests.test_conservative_runtime_boundaries
#  Regression tests for receiver values supplied by runtime-only boundaries.

import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pcresolve import analyze_project
from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.sources import ContainerItem, ContainerIter


def _analyze(code):
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "main.py")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(code)
        return analyze_project(directory)


def _top(result, expression):
    matches = [
        call.top_library for call in result.all_api_calls
        if call.expression == expression
    ]
    assert len(matches) == 1
    return matches[0]


def test_yield_assignment_result_is_unknown():
    result = _analyze(
        "def coroutine():\n"
        "    value = yield produce()\n"
        "    value.split()\n"
        "def produce():\n"
        "    return 'text'\n"
    )
    assert _top(result, "value.split()") == "unknown"


def test_parameter_runtime_attribute_item_is_unknown():
    result = _analyze(
        "import external\n"
        "def consume(grid):\n"
        "    grid.tags['boundary'].nonzero()\n"
        "consume(external.Grid())\n"
    )
    assert _top(
        result, "grid.tags['boundary'].nonzero()") == "unknown"


def test_parameter_runtime_attribute_item_chain_stays_unknown():
    result = _analyze(
        "import external\n"
        "def consume(frame):\n"
        "    frame.loc[0].product().sum()\n"
        "consume(external.Frame())\n"
    )
    assert _top(result, "frame.loc[0].product().sum()") == "unknown"


def test_forwarded_item_preserves_literal_element_shape():
    result = _analyze(
        "def consume(value):\n"
        "    value.strip()\n"
        "def forward(values):\n"
        "    consume(values[0])\n"
        "forward(['text'])\n"
    )
    assert _top(result, "value.strip()") == "python"


def test_local_list_return_preserves_element_owner():
    result = _analyze(
        "import numpy as np\n"
        "class Producer:\n"
        "    def values(self): return [np.array([1])]\n"
        "for item in Producer().values():\n"
        "    item.reshape(1)\n"
    )
    assert _top(result, "Producer().values()") == "local"
    assert _top(result, "item.reshape(1)") == "numpy"


def test_local_list_return_does_not_promote_local_elements_to_python():
    result = _analyze(
        "class Value:\n"
        "    def lower(self): return self\n"
        "class Producer:\n"
        "    def values(self): return [Value()]\n"
        "for item in Producer().values():\n"
        "    item.lower()\n"
    )
    assert _top(result, "item.lower()") == "local"


def test_local_list_return_keeps_unknown_return_branch():
    result = _analyze(
        "import numpy as np\n"
        "class Producer:\n"
        "    def values(self, other):\n"
        "        if other is not None: return other\n"
        "        return [np.array([1])]\n"
        "for item in Producer().values(external_values):\n"
        "    item.reshape(1)\n"
    )
    assert _top(result, "item.reshape(1)") == "unknown"


def test_forwarded_item_shape_does_not_inherit_container_methods():
    result = _analyze(
        "def consume(value):\n"
        "    value.append('x')\n"
        "def forward(values):\n"
        "    consume(values[0])\n"
        "forward(['text'])\n"
    )
    assert _top(result, "value.append('x')") == "unknown"


def test_imported_runtime_attribute_subscript_does_not_leak_owner():
    result = _analyze(
        "from external import proxy\n"
        "proxy.payload['key']\n"
        "proxy.payload.get('key')\n"
        "proxy.headers.get('key')\n"
    )
    assert _top(result, "proxy.payload.get('key')") == "unknown"
    assert _top(result, "proxy.headers.get('key')") == "external"


def test_compare_result_owner_uses_parameter_call_edge():
    result = _analyze(
        "import numpy as np\n"
        "def positive(values):\n"
        "    flags = values > 0\n"
        "    flags.any()\n"
        "positive(np.array([1]))\n"
    )
    assert _top(result, "flags.any()") == "numpy"


def test_uncalled_parameter_compare_result_is_unknown():
    result = _analyze(
        "def positive(values):\n"
        "    flags = values > 0\n"
        "    flags.any()\n"
    )
    assert _top(result, "flags.any()") == "unknown"


def test_chained_method_uses_verified_result_contract():
    result = _analyze(
        "import numpy as np\n"
        "def multiply(values):\n"
        "    values.dot(values).dot(values)\n"
        "multiply(np.array([1]))\n"
    )
    assert _top(result, "values.dot(values)") == "numpy"
    assert _top(result, "values.dot(values).dot(values)") == "numpy"


def test_imported_call_result_item_does_not_type_parameter():
    result = _analyze(
        "import external\n"
        "def visualize(image):\n"
        "    image.copy()\n"
        "transformed = external.transform()\n"
        "visualize(transformed['image'])\n"
    )
    assert _top(result, "image.copy()") == "unknown"


def test_imported_iterable_element_does_not_type_parameter():
    result = _analyze(
        "import external\n"
        "def label(item):\n"
        "    item.replace('-', ' ')\n"
        "items = external.load()\n"
        "[label(item) for item in items]\n"
    )
    assert _top(result, "item.replace('-', ' ')") == "unknown"


def test_untyped_local_expression_receiver_is_unknown():
    result = _analyze(
        "import json\n"
        "import re\n"
        "def render(line):\n"
        "    content = json.loads(line)\n"
        "    title = content['title']\n"
        "    text = re.sub('x', '', content['text'])\n"
        "    page = 'header' + title + text\n"
        "    page.encode()\n"
        "render(input())\n"
    )
    assert _top(result, "page.encode()") == "unknown"


def test_unproven_local_method_result_is_unknown():
    result = _analyze(
        "import external\n"
        "class Tool:\n"
        "    def __init__(self, worker):\n"
        "        self.worker = worker\n"
        "    def produce(self):\n"
        "        return self.worker.predict()\n"
        "tool = Tool(external.Worker())\n"
        "tool.produce().reshape(2, 2)\n"
    )
    assert _top(result, "tool.produce().reshape(2, 2)") == "unknown"


def test_local_constructor_method_identity_is_local():
    result = _analyze(
        "class Worker:\n"
        "    def run(self):\n"
        "        return None\n"
        "Worker().run()\n"
    )
    assert _top(result, "Worker().run()") == "local"


def test_same_owner_local_operator_result_preserves_library_owner():
    result = _analyze(
        "import numpy as np\n"
        "def prices():\n"
        "    returns = np.zeros((2, 2))\n"
        "    variance = np.zeros((2, 2))\n"
        "    (returns - variance / 2).cumsum(axis=0)\n"
    )
    assert _top(
        result, "(returns - variance / 2).cumsum(axis=0)") == "numpy"


def test_external_attribute_reassignment_does_not_reuse_old_owner():
    result = _analyze(
        "import numpy as np\n"
        "def prices(correlation):\n"
        "    returns = np.zeros((2, 2))\n"
        "    variance = np.zeros((2, 2))\n"
        "    returns = returns @ np.linalg.cholesky(correlation).T\n"
        "    (returns - variance / 2).cumsum(axis=0)\n"
    )
    assert _top(
        result, "(returns - variance / 2).cumsum(axis=0)") == "unknown"


def test_conflicting_local_operator_owners_remain_unknown():
    result = _analyze(
        "import numpy as np\n"
        "import pandas as pd\n"
        "left = np.array([1])\n"
        "right = pd.Series([1])\n"
        "(left + right).reshape(1, 1)\n"
    )
    assert _top(result, "(left + right).reshape(1, 1)") == "unknown"


def test_dotted_import_owner_converges_in_operator_expression():
    result = _analyze(
        "import datetime as dt\n"
        "start = dt.datetime.strptime('2020', '%Y')\n"
        "(start + dt.timedelta(days=1)).strftime('%Y')\n"
    )
    assert _top(
        result, "(start + dt.timedelta(days=1)).strftime('%Y')"
    ) == "datetime"


def test_import_attribute_protocol_evidence_respects_lexical_binding():
    result = _analyze(
        "from external import proxy\n"
        "proxy.payload['key']\n"
        "def collect():\n"
        "    from requests import proxy\n"
        "    proxy.payload.get('key')\n"
        "collect()\n"
    )
    assert _top(result, "proxy.payload.get('key')") == "requests"


def test_recursive_iterator_item_resolution_stops(tmp_path, monkeypatch):
    analyzer = ProjectAnalyzer(str(tmp_path))
    source = ContainerIter("items")
    monkeypatch.setattr(
        analyzer, "_resolve_container_iter",
        lambda *args: ("main", [source]))
    assert analyzer._argument_method_owner_candidates(
        "main", source, "copy", {}) == ["unknown"]


def test_recursive_container_item_resolution_stops(tmp_path, monkeypatch):
    analyzer = ProjectAnalyzer(str(tmp_path))
    source = ContainerItem("items", 0)
    monkeypatch.setattr(
        analyzer, "_resolve_container_item",
        lambda *args: ("main", source))
    assert analyzer._argument_method_owner_candidates(
        "main", source, "copy", {}) == ["unknown"]
