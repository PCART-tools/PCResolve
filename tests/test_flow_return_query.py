## @package tests.test_flow_return_query
#  Return path queries consume result records without the analyzer.
import pytest
from pcresolve.flow.model import FlowAnalysis, FunctionRef
from pcresolve.flow.query.return_paths import trace_parameter


def test_return_query_rejects_unknown_parameter_without_mutation():
    entry = FunctionRef(module='main', qualname='entry', file_path='main.py', lineno=1)
    result = FlowAnalysis(entry, {}, functions=[{'function': entry, 'parameters': ['value'], 'returns': []}])
    before = result.to_dict()
    with pytest.raises(ValueError, match='Unknown entry parameter'):
        trace_parameter(result, 'missing')
    assert result.to_dict() == before
