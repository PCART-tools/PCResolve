## @package tests.test_source_fact_cache_schema
#  Cached single-file visitor state has a declared fact schema.

import ast
from dataclasses import fields, is_dataclass
from pathlib import Path

from pcresolve.ownership import source_fact_cache


def test_visitor_fact_payload_is_a_declared_record():
    record = source_fact_cache.SingleFileVisitorFacts
    assert is_dataclass(record)
    names = {item.name for item in fields(record)}
    assert {
        'return_sources', 'symbols', 'module_cg', 'scope_stack',
        'mapping_facts_literals', '_mapping_edges',
    } <= names


def test_cache_capture_and_clone_do_not_copy_visitor_dictionary_state():
    source = Path(source_fact_cache.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    forbidden = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == '__dict__'
                and isinstance(node.value, ast.Name)
                and node.value.id in {'tracer', 'copied'}):
            forbidden.append(node)
        if (isinstance(node, ast.Name) and node.id == '_RUN_STATE'):
            forbidden.append(node)
    assert not forbidden
