## @package tests.test_diff_taxonomy
#  CLI tests for diff_v1_v2 --taxonomy classification accuracy.

import os
import subprocess
import sys
import tempfile

from scripts.diff_v1_v2 import _classify_expr

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "diff_v1_v2.py")


def _run_taxonomy(code):
    """Create a temp project, analyse it with --taxonomy, return stdout."""
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write(code)
        r = subprocess.run(
            [sys.executable, SCRIPT, "--taxonomy", td],
            capture_output=True, text=True)
        return r.stdout, r.returncode


def test_binop_with_subscript_is_container():
    """(arr[i] + offset).reshape() receiver contains Subscript → container."""
    # Use a function scope to trigger local-variable regression in v2
    code = ("import numpy as np\n"
            "def f(arr):\n"
            "    return (arr[0] + 1).reshape(1)\n"
            "f(np.array([1,2]))\n")
    out, rc = _run_taxonomy(code)
    assert rc == 0
    assert "container/subscript" in out, (
        "BinOp receiver with Subscript should be container/subscript\n%s" % out)


def test_df_subscript_astype_is_container():
    """df['x'].astype() → container/subscript."""
    code = ("import pandas as pd\n"
            "def f(df):\n"
            "    return df['x'].astype('str')\n"
            "f(pd.DataFrame())\n")
    out, rc = _run_taxonomy(code)
    assert rc == 0
    assert "container/subscript" in out, (
        "df['x'].astype() should be container/subscript\n%s" % out)


def test_plain_attribute_method_is_not_misclassified():
    """v.mean() → attribute_method, not bare_call."""
    assert _classify_expr("v.mean()") == "attribute_method"


def test_taxonomy_preserves_baseline_gate():
    """--taxonomy must not break normal gate output."""
    code = "import requests\nrequests.get('x')\n"
    out, rc = _run_taxonomy(code)
    assert rc == 0
    assert "Regressions (" not in out or "TOTAL regressions: 0" in out
