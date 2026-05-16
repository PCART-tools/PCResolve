## @package tests.test_contrucao
#  Test pcresolve against the Contrucao project oracle.
#
#  Contrucao is a TF-IDF + cosine similarity script (1 file).
#  It uses: numpy, requests, bs4, spacy, pandas.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "Contrucao"
)


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


# ── Structural ─────────────────────────────────────────────────────────

def test_one_file_analyzed(result):
    assert len(result.files) == 1
    assert result.files[0].module_name is not None


# ── Correct third-party classifications ─────────────────────────────────

def test_numpy_calls(calls_by_top):
    assert "numpy" in calls_by_top

def test_requests_calls(calls_by_top):
    assert "requests" in calls_by_top

def test_bs4_calls(calls_by_top):
    assert "bs4" in calls_by_top

def test_spacy_calls(calls_by_top):
    assert "spacy" in calls_by_top

def test_pandas_calls(calls_by_top):
    assert "pandas" in calls_by_top


# ── Known issues ───────────────────────────────────────────────────────

def test_np_alias_merged_to_numpy(calls_by_top):
    assert "np" not in calls_by_top


def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["texto", "bagOfWords", "tfidf", "vetor", "matrizCosseno"]
              if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
