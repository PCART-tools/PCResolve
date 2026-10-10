## @package tests.test_indexed_parameter_sources
#  Parameter provenance preserves signature order without exhaustive rescans.

import ast

from pcresolve import ProjectAnalyzer
from pcresolve.single_file import SingleFileAnalyzer


def _tracer(source):
    tracer = SingleFileAnalyzer(module_name='main')
    tracer.visit(ast.parse(source))
    return tracer


def test_parameter_trace_skips_unrelated_signatures(tmp_path, monkeypatch):
    tracer = _tracer('def forward(api): pass\n' + ''.join(
        'def unused_%s(other): pass\n' % index for index in range(200)))
    scanned = []

    class ObservedParameters(list):
        def index(self, value, *args):
            scanned.append(value)
            return super().index(value, *args)

    tracer.function_params = {name: ObservedParameters(params)
                              for name, params in tracer.function_params.items()}
    analyzer = ProjectAnalyzer(str(tmp_path))
    tracer.call_sites['forward'] = [{'module': 'main', 'args': ['json']}]
    monkeypatch.setattr(analyzer, 'trace_symbol', lambda *args, **kwargs: ['json'])
    for _ in range(3):
        assert analyzer._trace_parameter_source(
            'main', 'api', 'api', tracer, {'main': tracer}, set()) == ['api', 'json']
        assert analyzer._trace_parameter_source(
            'main', 'missing', 'missing', tracer, {'main': tracer}, set()) is None
    assert scanned == []


def test_parameter_trace_preserves_overwritten_alias_order(tmp_path, monkeypatch):
    tracer = _tracer('''
class First:
    def method(self, value): pass
class Second:
    def method(self, other): pass
callback = lambda value: value
''')
    # The simple method alias is overwritten; qualified aliases retain both
    # signatures. Trace the first successful call in legacy dictionary order.
    for name in tracer.function_params:
        tracer.call_sites[name] = [{'module': 'main', 'args': [name]}]
    analyzer = ProjectAnalyzer(str(tmp_path))
    monkeypatch.setattr(analyzer, 'trace_symbol',
                        lambda module, source, *args, **kwargs: [source])
    assert analyzer._trace_parameter_source(
        'main', 'value', 'value', tracer, {'main': tracer}, set()) == [
            'value', 'First.method']
    # Visiting new definitions invalidates cached signatures, while changed
    # call-site evidence must be visible without rebuilding signature facts.
    tracer.visit(ast.parse('def later(new_parameter): pass'))
    tracer.call_sites['later'] = [{'module': 'main', 'args': ['json']}]
    assert analyzer._trace_parameter_source(
        'main', 'new_parameter', 'value', tracer, {'main': tracer}, set()) == [
            'value', 'json']
    tracer.call_sites['later'][0]['args'] = ['csv']
    assert analyzer._trace_parameter_source(
        'main', 'new_parameter', 'value', tracer, {'main': tracer}, set()) == [
            'value', 'csv']
