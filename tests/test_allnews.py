## @package tests.test_allnews
#  Test pcresolve against the allnews project oracle.
#
#  allnews is an Armenian NLP pipeline with 9 Python files.
#  It uses: gensim, keras, nltk, numpy, pandas, sklearn, pymysql.
#
#  Oracle built by manual code review of all 9 source files.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "allnews"
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


# ── Structural checks ──────────────────────────────────────────────────

def test_all_files_analyzed(result):
    assert len(result.files) == 9, (
        f"Expected 9 files, got {len(result.files)}"
    )


def test_v1_analysis_does_not_recurse_on_builtin_self_rebinding():
    legacy_result = analyze_project(FIXTURE, scope_model="v1")
    assert len(legacy_result.files) == 9


def test_all_files_have_module_name(result):
    for f in result.files:
        assert f.module_name, (
            f"{os.path.basename(f.file_path)} has no module_name"
        )


# ── Correct third-party classification ─────────────────────────────────

def test_gensim_calls(calls_by_top):
    assert "gensim" in calls_by_top, "No gensim calls found"
    gensim_exprs = [c.expression for c in calls_by_top["gensim"]]
    assert any("FastText" in e for e in gensim_exprs)


def test_keras_calls(calls_by_top):
    assert "keras" in calls_by_top
    assert len(calls_by_top["keras"]) >= 15


def test_nltk_calls(calls_by_top):
    assert "nltk" in calls_by_top


def test_sklearn_calls(calls_by_top):
    assert "sklearn" in calls_by_top


def test_pymysql_calls(calls_by_top):
    assert "pymysql" in calls_by_top


def test_pymysql_singleton_receiver_calls(result):
    """Class-qualified singleton fields preserve pymysql receiver ownership."""
    matches = {
        call.expression: call
        for call in result.all_api_calls
        if call.file_path.endswith("allnews_am\\db.py")
    }
    for expression in (
            "self.connection.cursor()",
            "cursor.execute(sql, (offset, limit))",
            "cursor.fetchall()"):
        assert matches[expression].top_library == "pymysql", (
            "%s should resolve through MySQL.__instance.connection" % expression)


def test_tuple_comprehension_regex_receivers_preserve_re(result):
    """Tuple fields from a module-level pattern comprehension keep re owner."""
    calls = [
        call for call in result.all_api_calls
        if call.file_path.endswith("wikiextractor\\WikiExtractor.py")
    ]
    assert any(
        call.lineno == 786
        and call.expression == "pattern.finditer(text)"
        and call.top_library == "re"
        for call in calls
    )
    assert any(
        call.lineno == 787
        and call.expression == "match.group()"
        and call.top_library == "re"
        for call in calls
    )


# ── Local function classification ──────────────────────────────────────

def test_local_classes_are_local(calls_by_top):
    """Locally defined classes should be classified as local."""
    local_exprs = [c.expression for c in calls_by_top.get("local", [])]
    indicators = [
        "MySQL(", "ConllReader(", "Tokenizer(", "Dictionary(",
        "NextFile(", "OutputSplitter(", "Extractor(", "Template(",
    ]
    found = sum(1 for e in local_exprs for ind in indicators if ind in e)
    assert found > 0, "Expected local class instantiations classified as local"


def test_imported_local_class_method_chain_stays_local(result):
    """An imported local class constructor proves its local method chain."""
    matches = [
        call for call in result.all_api_calls
        if call.expression == "t.segmentation().tokenization()"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "local"


def test_local_class_factory_receiver_is_local(result):
    matches = {
        call.expression: call
        for call in result.all_api_calls
        if call.file_path.endswith("WikiExtractor.py")
    }

    assert matches["template.subst(params, self)"].top_library == "local"
    assert matches["extr.expand(ifnex)"].top_library == "unknown"


def test_kwargs_backed_namespace_fields_are_python(result):
    matches = {
        call.expression: call
        for call in result.all_api_calls
        if call.file_path.endswith("WikiExtractor.py")
    }

    for expression in (
            "options.ignored_tag_patterns.append((left, right))",
            "options.knownNamespaces.get(ns, '0')",
            "options.redirects.get(title)",
            "options.filter_category_exclude.add(line.lstrip('^'))",
            "options.filter_category_include.add(line)"):
        assert matches[expression].top_library == "python"


def test_attribute_tuple_container_preserves_regex_receivers(result):
    matches = {
        (call.lineno, call.expression): call
        for call in result.all_api_calls
        if call.file_path.endswith("WikiExtractor.py")
        and call.lineno in (767, 768, 769, 770)
    }

    for key in (
            (767, "left.finditer(text)"),
            (768, "m.start()"),
            (768, "m.end()"),
            (769, "right.finditer(text)"),
            (770, "m.start()"),
            (770, "m.end()")):
        assert matches[key].top_library == "re"


def test_nested_callback_lookup_preserves_local_callable(result):
    matches = [
        call for call in result.all_api_calls
        if call.func_name == "funct"
        and call.expression == "funct(args)"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "local"


# ── Stdlib modules (need import → correctly third-party) ──────────────

def test_stdlib_modules_are_third_party(calls_by_top):
    """Stdlib modules that need import are correctly third-party top_library."""
    for m in ["re", "argparse", "logging", "os", "multiprocessing", "io",
              "fileinput", "timeit", "time", "types", "gzip", "json",
              "urllib", "itertools", "bz2", "codecs", "cgi", "xml"]:
        assert m in calls_by_top, (
            f"{m} should appear as top_library (stdlib, needs import)"
        )

# ── Known issues — documented limitations ──────────────────────────────


def test_missing_imports_not_top(calls_by_top):
    leaked = [v for v in ["get_url", "clean", "compact"] if v in calls_by_top]
    assert not leaked, f"Missing-import names leaked: {leaked}"


def test_scope_pollution_not_top(calls_by_top):
    leaked = [v for v in ["s", "tpl"] if v in calls_by_top]
    assert not leaked, f"Scope-polluted symbols leaked: {leaked}"


def test_local_modules_not_top(calls_by_top):
    leaked = [m for m in ["allnews_am", "allnews_am.processing"]
              if m in calls_by_top]
    assert not leaked, f"Local modules leaked: {leaked}"


def test_builtins_not_top(calls_by_top):
    builtin_leaks = [b for b in ["unichr", "xrange"] if b in calls_by_top]
    assert not builtin_leaks, f"Builtin names leaked: {builtin_leaks}"


def test_no_structured_tuples(calls_by_top):
    structured = [k for k in calls_by_top if isinstance(k, tuple) or str(k).startswith("(")]
    assert not structured, f"Structured tuples leaked: {structured}"
