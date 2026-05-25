## @package tests.test_sources
#  Unit tests for the typed Source IR and compatibility helpers.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve.sources import (
    ContainerItem, ContainerIter, InstanceMethod, CallResult,
    NameSource, UnknownSource,
    normalize_source, source_to_legacy, source_display, is_structured_source,
)


# ── normalize_source ────────────────────────────────────────────────────

def test_normalize_legacy_container_item():
    result = normalize_source(("container_item", "lst", 0))
    assert isinstance(result, ContainerItem)
    assert result.container == "lst"
    assert result.index == 0


def test_normalize_legacy_instance_method():
    result = normalize_source(("instance_method", "Client", "get"))
    assert isinstance(result, InstanceMethod)
    assert result.receiver == "Client"
    assert result.method == "get"


def test_normalize_legacy_container_iter():
    result = normalize_source(("container_iter", "lst", "*"))
    assert isinstance(result, ContainerIter)
    assert result.container == "lst"


def test_normalize_legacy_call_result():
    result = normalize_source(("call_result", "make", None))
    assert isinstance(result, CallResult)
    assert result.callee == "make"


def test_normalize_passes_string_through():
    assert normalize_source("requests") == "requests"


def test_normalize_passes_dataclass_through():
    cr = CallResult("make")
    assert normalize_source(cr) is cr


# ── source_to_legacy ────────────────────────────────────────────────────

def test_source_to_legacy_container_item():
    ci = ContainerItem("lst", 0)
    assert source_to_legacy(ci) == ("container_item", "lst", 0)


def test_source_to_legacy_instance_method():
    im = InstanceMethod("Client", "get")
    assert source_to_legacy(im) == ("instance_method", "Client", "get")


def test_source_to_legacy_container_iter():
    ci = ContainerIter("lst")
    assert source_to_legacy(ci) == ("container_iter", "lst", "*")


def test_source_to_legacy_call_result():
    cr = CallResult("make")
    assert source_to_legacy(cr) == ("call_result", "make", None)


def test_source_to_legacy_string_passthrough():
    assert source_to_legacy("requests") == "requests"


def test_source_to_legacy_roundtrip():
    """A legacy tuple round-tripped through normalize + to_legacy should match."""
    original = ("container_item", "lst", 0)
    result = source_to_legacy(normalize_source(original))
    assert result == original


# ── source_display ──────────────────────────────────────────────────────

def test_source_display_string():
    assert source_display("requests") == "requests"


def test_source_display_container_item():
    ci = ContainerItem("lst", 0)
    assert source_display(ci) == "lst[0]"


def test_source_display_container_iter():
    ci = ContainerIter("lst")
    assert source_display(ci) == "lst[*]"


def test_source_display_instance_method():
    im = InstanceMethod("Client", "get")
    assert source_display(im) == "Client.get"


def test_source_display_call_result():
    cr = CallResult("make")
    assert source_display(cr) == "make()"


def test_source_display_nested():
    """Nested ContainerItem(ContainerIter(...), ...) should render correctly."""
    nested = ContainerItem(ContainerIter("lst"), "key")
    assert source_display(nested) == "lst[*][key]"


def test_source_display_name_source():
    ns = NameSource("requests")
    assert source_display(ns) == "requests"


def test_source_display_unknown_source():
    us = UnknownSource("???")
    assert source_display(us) == "???"


# ── is_structured_source ────────────────────────────────────────────────

def test_is_structured_source_legacy_tuple():
    assert is_structured_source(("container_item", "a", 0)) is True


def test_is_structured_source_dataclass():
    assert is_structured_source(CallResult("f")) is True
    assert is_structured_source(InstanceMethod("C", "m")) is True


def test_is_structured_source_string():
    assert is_structured_source("requests") is False


def test_is_structured_source_none():
    assert is_structured_source(None) is False
