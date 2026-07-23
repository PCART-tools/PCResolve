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
