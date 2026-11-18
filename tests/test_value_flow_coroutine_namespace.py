## @package tests.test_value_flow_coroutine_namespace

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = """{imports}
class Entry:
    def __init__(self, **kwargs):
        pass

    @{decorator}
    def unused(self):
        yield 1
"""


@pytest.mark.parametrize(
    "imports,decorator",
    [
        ("import asyncio", "asyncio.coroutine"),
        ("import asyncio as events", "events.coroutine"),
        ("from asyncio import coroutine", "coroutine"),
        ("from asyncio import coroutine as wrap", "wrap"),
    ],
)
def test_stdlib_coroutine_on_another_method_preserves_constructor_entry(
    tmp_path, imports, decorator
):
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports=imports, decorator=decorator), encoding="utf-8"
    )
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    fact = result.inputs["entry_binding"]
    assert fact["status"] == "source_bound"
    assert fact["target"]["qualname"] == "Entry.__init__"
    assert fact["runtime_target_confirmed"] is False
    assert "stdlib_asyncio_coroutine_binding" in fact["assumptions"]
    assert not fact["issues"]
    with (tmp_path / "sample.py").open("a", encoding="utf-8") as stream:
        stream.write("\ndef call(**kwargs):\n    return Entry(**kwargs)\n")
    nested = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "call"))
    binding = nested.find_calls(callee_name="Entry")[0].constructor_bindings[0]
    assert binding["status"] == "source_bound"
    assert "stdlib_asyncio_coroutine_binding" in binding["assumptions"]


@pytest.mark.parametrize(
    "imports,decorator,extra",
    [
        ("import asyncio\nasyncio = unknown", "asyncio.coroutine", ""),
        ("from asyncio import coroutine\ncoroutine = unknown", "coroutine", ""),
        ("import asyncio", "asyncio.coroutine", "    asyncio = unknown\n"),
        ("from asyncio import coroutine", "coroutine", "    coroutine = unknown\n"),
        ("import asyncio\nasyncio.coroutine = unknown", "asyncio.coroutine", ""),
        (
            "import asyncio\nalias = asyncio\nalias.coroutine = unknown",
            "asyncio.coroutine",
            "",
        ),
        (
            'import asyncio\n__import__("asyncio").coroutine = unknown',
            "asyncio.coroutine",
            "",
        ),
        (
            'import asyncio\nexec("asyncio.coroutine = unknown")',
            "asyncio.coroutine",
            "",
        ),
        ("import asyncio", "asyncio.coroutine()", ""),
        ("from other import coroutine", "coroutine", ""),
    ],
)
def test_unproven_coroutine_names_do_not_establish_a_constructor(
    tmp_path, imports, decorator, extra
):
    source = SOURCE.format(imports=imports, decorator=decorator)
    source = source.replace("class Entry:\n", "class Entry:\n" + extra)
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "unconfirmed"
    assert not result.calls


@pytest.mark.parametrize("body,status", [
    ("    return function\n", "source_bound"),
    ("    opaque(function)\n    return function\n", "unconfirmed"),
])
def test_source_module_named_asyncio_cannot_claim_stdlib_coroutine(tmp_path, body, status):
    (tmp_path / "asyncio.py").write_text(
        "def coroutine(function):\n" + body, encoding="utf-8"
    )
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine"),
        encoding="utf-8",
    )
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    binding = result.inputs["entry_binding"]
    assert binding["status"] == status
    assert "stdlib_asyncio_coroutine_binding" not in binding["assumptions"]
    assert ("source_function_namespace_preservation" in binding["assumptions"]) == (
        status == "source_bound")


@pytest.mark.parametrize("name", ["__init__", "__new__"])
def test_coroutine_cannot_turn_a_deferred_constructor_into_a_synchronous_entry(
    tmp_path, name
):
    (tmp_path / "sample.py").write_text(
        """import asyncio
class Entry:
    @asyncio.coroutine
    def """
        + name
        + """(self, **kwargs):
        yield 1
""",
        encoding="utf-8",
    )
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "unconfirmed"
    assert not result.calls


def test_coroutine_does_not_hide_effectful_method_defaults(tmp_path):
    source = SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine")
    source = source.replace("def unused(self):", "def unused(self, value=install()):")
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "unconfirmed"


def test_visible_coroutine_mutation_in_another_module_invalidates_the_premise(tmp_path):
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine"),
        encoding="utf-8",
    )
    (tmp_path / "patch.py").write_text(
        "import asyncio as events\nevents.coroutine = unknown\n", encoding="utf-8"
    )
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "unconfirmed"


def test_reflective_coroutine_mutation_without_an_import_binding_is_unconfirmed(
    tmp_path,
):
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine"),
        encoding="utf-8",
    )
    (tmp_path / "patch.py").write_text(
        '__import__("asyncio").coroutine = unknown\n', encoding="utf-8"
    )
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "unconfirmed"


def test_standard_decorator_premises_keep_their_inspected_source_dependencies(tmp_path):
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine"),
        encoding="utf-8",
    )
    sibling = tmp_path / "sibling.py"
    sibling.write_text("import asyncio as events\n", encoding="utf-8")
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef("sample", "Entry"))
    assert result.inputs["entry_binding"]["status"] == "source_bound"
    assert str(sibling) in result.inputs["entry_binding"]["source_hashes"]


def test_stdlib_namespace_premises_refresh_when_source_changes(tmp_path):
    (tmp_path / "sample.py").write_text(
        SOURCE.format(imports="import asyncio", decorator="asyncio.coroutine"),
        encoding="utf-8",
    )
    sibling = tmp_path / "sibling.py"
    sibling.write_text("import asyncio as events\n", encoding="utf-8")
    analyzer = FlowAnalyzer(project_root=tmp_path)
    first = analyzer.analyze(FunctionRef("sample", "Entry"))
    snapshot = first.to_dict()
    assert first.inputs["entry_binding"]["status"] == "source_bound"
    sibling.write_text(
        "import asyncio as events\nevents.coroutine = unknown\n", encoding="utf-8"
    )
    second = analyzer.analyze(FunctionRef("sample", "Entry"))
    assert second.inputs["entry_binding"]["status"] == "unconfirmed"
    assert first.to_dict() == snapshot
