## @package tests.test_public_source_call_protocol

import ast

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, SourceSpan


PREDICATE = '''def accepts_iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
'''


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_public_source_call_protocol_is_exact_and_versioned(tmp_path):
    helper = put(tmp_path, 'helpers.py', PREDICATE)
    caller = put(tmp_path, 'library.py',
                 'from helpers import accepts_iterable\n'
                 'def entry(value):\n'
                 '    return accepts_iterable(value)\n')
    tree = ast.parse(caller.read_text(encoding='utf-8'))
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call))
    analyzer = FlowAnalyzer(source_files=[str(caller)], import_roots=[str(tmp_path)],
                            support_source_protocols=True)

    fact = analyzer.source_call_protocol(
        FunctionRef('library', 'entry', str(caller), 2),
        SourceSpan.from_ast(str(caller), call))

    assert fact['schema_version'] == 'source-call-protocol-0.1'
    assert fact['status'] == 'source_bound'
    assert fact['protocol'] == 'iterability'
    assert fact['target'] == 'helpers.accepts_iterable'
    assert fact['fact']['kind'] == 'source_native_type_iterability_predicate'
    assert fact['fact']['source_hashes'][str(helper)]
    assert fact['call_syntax'] == ast.dump(call, include_attributes=False)


def test_public_source_call_protocol_requires_one_exact_callsite(tmp_path):
    caller = put(tmp_path, 'library.py',
                 'def entry(value):\n'
                 '    return opaque(value)\n')
    analyzer = FlowAnalyzer(source_files=[str(caller)], import_roots=[str(tmp_path)])
    span = SourceSpan(str(caller), 2, 11, 2, 24)

    assert analyzer.source_call_protocol(
        FunctionRef('library', 'entry', str(caller), 1), span) is None
    with pytest.raises(ValueError, match='Unsupported source call protocol'):
        analyzer.source_call_protocol(FunctionRef('library', 'entry', str(caller), 1),
                                      span, protocol='unknown')


def test_public_caller_input_contract_has_a_schema_version(tmp_path):
    caller = put(tmp_path, 'client.py',
                 'from sample import target\n'
                 'target(value=7)\n')
    tree = ast.parse(caller.read_text(encoding='utf-8'))
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call))
    analyzer = FlowAnalyzer(source_files=[str(caller)], import_roots=[str(tmp_path)])

    fact = analyzer.caller_inputs(SourceSpan.from_ast(str(caller), call))

    assert fact['schema_version'] == 'caller-inputs-0.1'
    assert fact['status'] == 'source_bound'
    assert fact['arguments'][0]['value']['value'] == 7


def test_public_source_call_protocol_rejects_changed_dependency_source(tmp_path):
    helper = put(tmp_path, 'helpers.py', PREDICATE)
    caller = put(tmp_path, 'library.py',
                 'from helpers import accepts_iterable\n'
                 'def entry(value):\n'
                 '    return accepts_iterable(value)\n')
    call = next(node for node in ast.walk(ast.parse(caller.read_text(encoding='utf-8')))
                if isinstance(node, ast.Call))
    analyzer = FlowAnalyzer(source_files=[str(caller)], import_roots=[str(tmp_path)],
                            support_source_protocols=True)
    entry = FunctionRef('library', 'entry', str(caller), 2)
    span = SourceSpan.from_ast(str(caller), call)
    assert analyzer.source_call_protocol(entry, span) is not None
    helper.write_text('def accepts_iterable(value):\n    return False\n', encoding='utf-8')

    with pytest.raises(ValueError, match='Source protocol sources changed'):
        analyzer.source_call_protocol(entry, span)

