## @package tests.test_semantic_result_contracts
#  Verify evidence-backed result contracts and conservative fallbacks.

import os
import tempfile

from pcresolve import analyze_project


def _analyze(code):
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "main.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(code)
        return analyze_project(directory)


def _call(result, expression):
    matches = [
        call for call in result.all_api_calls
        if call.expression == expression
    ]
    assert len(matches) == 1, (expression, [
        call.expression for call in result.all_api_calls
    ])
    return matches[0]


def test_function_local_import_is_direct_ownership_evidence():
    result = _analyze(
        "def render():\n"
        "    import matplotlib.pyplot as plt\n"
        "    plt.title('result')\n"
        "    plt.gcf().savefig('result.png')\n"
    )

    assert _call(result, "plt.title('result')").top_library == "matplotlib"
    assert _call(result, "plt.gcf()").top_library == "matplotlib"
    assert _call(
        result, "plt.gcf().savefig('result.png')"
    ).top_library == "matplotlib"


def test_function_local_import_from_is_direct_ownership_evidence():
    result = _analyze(
        "def render():\n"
        "    from matplotlib import pyplot as plt\n"
        "    plt.gcf().add_subplot(111)\n"
    )

    gcf_call = _call(result, "plt.gcf()")
    assert gcf_call.top_library == "matplotlib"
    assert gcf_call.resolved_func == "matplotlib.pyplot.gcf"
    assert _call(
        result, "plt.gcf().add_subplot(111)"
    ).top_library == "matplotlib"


def test_function_local_import_aliases_are_lexically_isolated():
    result = _analyze(
        "def decode():\n"
        "    import json as lib\n"
        "    lib.loads('{}')\n"
        "def compile_pattern():\n"
        "    import re as lib\n"
        "    lib.compile('x')\n"
    )

    loads_call = _call(result, "lib.loads('{}')")
    compile_call = _call(result, "lib.compile('x')")
    assert loads_call.top_library == "json"
    assert loads_call.resolved_func == "json.loads"
    assert compile_call.top_library == "re"
    assert compile_call.resolved_func == "re.compile"


def test_python_result_contract_overrides_callable_owner():
    result = _analyze(
        "def encode():\n"
        "    import json\n"
        "    json.dumps({'key': 'value'}).strip()\n"
    )

    assert _call(
        result, "json.dumps({'key': 'value'})"
    ).top_library == "json"
    assert _call(
        result, "json.dumps({'key': 'value'}).strip()"
    ).top_library == "python"


def test_torchvision_to_tensor_result_is_torch_owned():
    result = _analyze(
        "import torchvision.transforms.functional as FT\n"
        "def inspect_image(image):\n"
        "    image.size(1)\n"
        "def run(raw):\n"
        "    image = FT.to_tensor(raw)\n"
        "    inspect_image(image)\n"
    )

    assert _call(result, "FT.to_tensor(raw)").top_library == "torchvision"
    assert _call(result, "image.size(1)").top_library == "torch"


def test_scipy_bisplev_result_is_numpy_owned():
    result = _analyze(
        "from scipy.interpolate import bisplev\n"
        "value = bisplev(1.0, 2.0, tck).item()\n"
    )

    assert _call(
        result, "bisplev(1.0, 2.0, tck)"
    ).top_library == "scipy"
    assert _call(
        result, "bisplev(1.0, 2.0, tck).item()"
    ).top_library == "numpy"


def test_stdlib_path_iterators_yield_python_strings():
    result = _analyze(
        "import glob\n"
        "import os\n"
        "for filename in os.listdir('.'):\n"
        "    filename.endswith('.py')\n"
        "for path in glob.glob('*.py'):\n"
        "    path.split('/')\n"
        "    path.append('invalid')\n"
    )

    assert _call(
        result, "filename.endswith('.py')"
    ).top_library == "python"
    assert _call(result, "path.split('/')").top_library == "python"
    assert _call(
        result, "path.append('invalid')"
    ).top_library == "unknown"


def test_stdlib_regex_result_objects_keep_re_owner():
    result = _analyze(
        "import re\n"
        "pattern = re.compile('a')\n"
        "match = re.match('a', 'a')\n"
        "pattern.finditer('a')\n"
        "group_text = match.group(0)\n"
        "group_text.append('invalid')\n"
    )

    assert _call(result, "pattern.finditer('a')").top_library == "re"
    assert _call(result, "match.group(0)").top_library == "re"
    assert _call(
        result, "group_text.append('invalid')"
    ).top_library == "unknown"


def test_stdlib_regex_callback_receives_re_match():
    result = _analyze(
        "import re\n"
        "def replace(match):\n"
        "    return match.group(0)\n"
        "re.sub('a', replace, 'a')\n"
    )

    assert _call(result, "match.group(0)").top_library == "re"


def test_stdlib_regex_split_items_are_python_strings():
    result = _analyze(
        "import re\n"
        "prefix, value = re.split(':', 'key:value')\n"
        "prefix.strip()\n"
        "value.startswith('v')\n"
    )

    assert _call(result, "prefix.strip()").top_library == "python"
    assert _call(result, "value.startswith('v')").top_library == "python"


def test_argparse_namespace_builtin_values_are_python_owned():
    result = _analyze(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--method', default='fast')\n"
        "parser.add_argument('--count', type=int)\n"
        "args = parser.parse_args()\n"
        "args.method.startswith('f')\n"
        "str(args.count).strip()\n"
    )

    assert _call(
        result, "args.method.startswith('f')"
    ).top_library == "python"


def test_argparse_argument_group_preserves_namespace_value_shapes():
    result = _analyze(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "group = parser.add_argument_group('options')\n"
        "group.add_argument('--name', default='fast')\n"
        "group.add_argument('--bytes', default='1M')\n"
        "args = parser.parse_args()\n"
        "args.name.strip()\n"
        "args.bytes[-1].lower()\n"
    )

    assert _call(result, "args.name.strip()").top_library == "python"
    assert _call(result, "args.bytes[-1].lower()").top_library == "python"


def test_local_kwargs_constructor_preserves_field_shapes():
    result = _analyze(
        "class Namespace:\n"
        "    def __init__(self, **kwargs):\n"
        "        self.__dict__.update(kwargs)\n"
        "options = Namespace(names=[], values={}, flags=set())\n"
        "options.names.append('value')\n"
        "options.values.get('key')\n"
        "options.flags.add('flag')\n"
    )

    assert _call(result, "options.names.append('value')").top_library == "python"
    assert _call(result, "options.values.get('key')").top_library == "python"
    assert _call(result, "options.flags.add('flag')").top_library == "python"
    assert _call(result, "self.__dict__.update(kwargs)").top_library == "python"


def test_local_kwargs_constructor_fields_do_not_survive_rebinding():
    result = _analyze(
        "class Namespace:\n"
        "    def __init__(self, **kwargs):\n"
        "        self.__dict__.update(kwargs)\n"
        "options = Namespace(names=[])\n"
        "options = make_options()\n"
        "options.names.append('value')\n"
    )

    assert _call(result, "options.names.append('value')").top_library != "python"


def test_local_kwargs_constructor_fields_do_not_cross_function_scopes():
    result = _analyze(
        "class Namespace:\n"
        "    def __init__(self, **kwargs):\n"
        "        self.__dict__.update(kwargs)\n"
        "def build():\n"
        "    options = Namespace(names=[])\n"
        "    options.names.append('value')\n"
        "def consume():\n"
        "    options.names.append('value')\n"
    )

    matches = [
        call for call in result.all_api_calls
        if call.expression == "options.names.append('value')"
    ]
    assert [call.top_library for call in matches] == ["python", "unknown"]


def test_local_kwargs_constructor_fields_do_not_cross_class_scope():
    result = _analyze(
        "class Namespace:\n"
        "    def __init__(self, **kwargs):\n"
        "        self.__dict__.update(kwargs)\n"
        "class Holder:\n"
        "    options = Namespace(names=[])\n"
        "    def consume(self):\n"
        "        options.names.append('value')\n"
    )

    assert _call(result, "options.names.append('value')").top_library != "python"


def test_stdlib_element_text_attribute_is_python_owned():
    result = _analyze(
        "import xml.etree.ElementTree as ET\n"
        "root = ET.parse('input.xml').getroot()\n"
        "value = root.find('name').text.lower().strip()\n"
    )

    assert _call(
        result, "root.find('name').text.lower()"
    ).top_library == "python"
    assert _call(
        result, "root.find('name').text.lower().strip()"
    ).top_library == "python"


def test_stdlib_element_text_shape_survives_function_local_iteration():
    result = _analyze(
        "import xml.etree.ElementTree as ET\n"
        "def labels(path):\n"
        "    root = ET.parse(path).getroot()\n"
        "    for item in root.iter('item'):\n"
        "        item.find('name').text.lower().strip()\n"
    )

    assert _call(
        result, "item.find('name').text.lower()"
    ).top_library == "python"
    assert _call(
        result, "item.find('name').text.lower().strip()"
    ).top_library == "python"


def test_local_text_attribute_chain_does_not_gain_stdlib_shape():
    result = _analyze(
        "class Value:\n"
        "    text = None\n"
        "class Root:\n"
        "    def iter(self): return [self]\n"
        "    def find(self, name): return Value()\n"
        "def labels():\n"
        "    for item in Root().iter():\n"
        "        item.find('name').text.lower()\n"
        "labels()\n"
    )

    assert _call(
        result, "item.find('name').text.lower()"
    ).top_library == "local"


def test_gpy_predict_unpacked_results_are_numpy_owned():
    result = _analyze(
        "from GPy.models import GPRegression\n"
        "model = GPRegression(X, y)\n"
        "predictions, variance = model.predict(X)\n"
        "predictions.ravel()\n"
        "variance.ravel()\n"
    )

    assert _call(result, "model.predict(X)").top_library == "GPy"
    assert _call(result, "predictions.ravel()").top_library == "numpy"
    assert _call(result, "variance.ravel()").top_library == "numpy"


def test_gpy_predict_indexed_result_is_numpy_owned():
    result = _analyze(
        "from GPy.models import GPRegression\n"
        "class Model:\n"
        "    def fit(self, X, y):\n"
        "        self.model = GPRegression(X, y)\n"
        "    def predict(self, X):\n"
        "        predictions = self.model.predict(X)[0]\n"
        "        predictions.reshape(2, 2)\n"
    )

    assert _call(result, "self.model.predict(X)").top_library == "GPy"
    assert _call(result, "predictions.reshape(2, 2)").top_library == "numpy"


def test_skimage_downscale_result_is_numpy_owned():
    result = _analyze(
        "import skimage.transform\n"
        "reduced = skimage.transform.downscale_local_mean(data, (2, 2))\n"
        "reduced.astype('float32')\n"
    )

    assert _call(
        result, "skimage.transform.downscale_local_mean(data, (2, 2))"
    ).top_library == "skimage"
    assert _call(
        result, "reduced.astype('float32')"
    ).top_library == "numpy"


def test_scipy_issparse_narrows_only_the_true_branch():
    result = _analyze(
        "from scipy.sparse import issparse\n"
        "def normalize(value):\n"
        "    return value.todense() if issparse(value) else value.copy()\n"
        "def unchecked(value):\n"
        "    return value.todense()\n"
    )

    guarded = [
        call for call in result.all_api_calls
        if call.expression == "value.todense()" and call.lineno == 3
    ]
    assert len(guarded) == 1
    assert guarded[0].top_library == "scipy"
    unchecked = [
        call for call in result.all_api_calls
        if call.expression == "value.todense()" and call.lineno == 5
    ]
    assert len(unchecked) == 1
    assert unchecked[0].top_library == "unknown"


def test_scipy_issparse_statement_guard_is_branch_local():
    result = _analyze(
        "from scipy.sparse import issparse\n"
        "def normalize(value):\n"
        "    if issparse(value):\n"
        "        value.todense()\n"
        "    value.copy()\n"
    )

    assert _call(result, "value.todense()").top_library == "scipy"
    assert _call(result, "value.copy()").top_library == "unknown"
