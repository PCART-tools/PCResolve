## @package tests.test_symbol_table
#  Unit tests for the SymbolTable class.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve.symbol_table import SymbolTable


def test_basic_add_and_trace():
    table = SymbolTable()
    table.add("resp", "requests")
    assert table.direct["resp"] == "requests"
    assert table.get_top("resp") == "requests"
    assert table.get_chain("resp") == ["resp", "requests"]


def test_chained_trace():
    table = SymbolTable()
    table.add("resp", "requests")
    table.add("r", "resp")
    assert table.get_top("r") == "requests"
    assert table.get_chain("r") == ["r", "resp", "requests"]


def test_cycle_detection():
    table = SymbolTable()
    table.add("a", "b")
    table.add("b", "a")
    result = table.trace("a")
    assert len(result) <= 2


def test_local_symbol():
    table = SymbolTable()
    table.add("myfunc", "local")
    assert table.get_top("myfunc") == "local"


def test_none_inputs_ignored():
    table = SymbolTable()
    table.add(None, "requests")
    table.add("x", None)
    assert "x" not in table.direct
    assert None not in table.direct


def test_multi_level_chain():
    table = SymbolTable()
    table.add("pandas", "third_party")
    table.add("pd", "pandas")
    table.add("df", "pd")
    assert table.get_top("df") == "third_party"

    table2 = SymbolTable()
    table2.add("requests", "requests")
    table2.add("resp", "requests")
    assert table2.get_top("resp") == "requests"


if __name__ == "__main__":
    test_basic_add_and_trace()
    test_chained_trace()
    test_cycle_detection()
    test_local_symbol()
    test_none_inputs_ignored()
    test_multi_level_chain()
    print("All SymbolTable tests passed.")
