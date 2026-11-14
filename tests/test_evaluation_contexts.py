## @package tests.test_evaluation_contexts

import ast

from pcresolve.facts.effect_facts import evaluation_contexts


def contexts(source):
    tree = ast.parse(source)
    return {node.func.id: tuple((kind, getattr(scope, 'name', type(scope).__name__))
            for kind, scope in requirements)
            for node, requirements in evaluation_contexts(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def test_function_declaration_inputs_are_in_the_enclosing_phase():
    result = contexts('''@decorate(factory())
def work(value=default(), item: annotation() = None) -> result_type():
    body()
''')
    for name in ('decorate', 'factory', 'default', 'annotation', 'result_type'):
        assert result[name] == ()
    assert result['body'] == (('function_invocation', 'work'),)


def test_nested_class_defaults_retain_the_enclosing_invocation():
    result = contexts('''def outer():
    class Inner(base(), metaclass=meta()):
        field = initializer()
        def method(self, value=default()): body()
''')
    for name in ('base', 'meta', 'initializer', 'default'):
        assert result[name] == (('function_invocation', 'outer'),)
    assert result['body'] == (('function_invocation', 'outer'), ('function_invocation', 'method'))


def test_lambda_defaults_and_generator_outer_iterator_execute_before_resumption():
    result = contexts('''value = lambda arg=default(): body()
items = (element(item) for item in outer_iter() if predicate(item))
''')
    assert result['default'] == ()
    assert result['body'] == (('function_invocation', 'Lambda'),)
    assert result['outer_iter'] == ()
    assert result['element'] == result['predicate'] == (('generator_resumption', 'GeneratorExp'),)


def test_generator_function_body_requires_resumption_in_addition_to_call():
    result = contexts('''def generate(value=default()):
    yield body()
''')
    assert result['default'] == ()
    assert result['body'] == (('function_invocation', 'generate'), ('generator_resumption', 'generate'))


def test_coroutine_and_async_generator_bodies_need_distinct_resumption():
    result = contexts('''async def coroutine(value=default()):
    body()
async def stream():
    yield element()
''')
    assert result['default'] == ()
    assert result['body'] == (('function_invocation', 'coroutine'), ('coroutine_resumption', 'coroutine'))
    assert result['element'] == (('function_invocation', 'stream'), ('async_generator_resumption', 'stream'))


def test_a_nested_generator_does_not_make_its_outer_function_a_generator():
    result = contexts('''def outer():
    def inner(): yield element()
    body()
''')
    assert result['body'] == (('function_invocation', 'outer'),)
    assert result['element'] == (('function_invocation', 'outer'), ('function_invocation', 'inner'),
                                 ('generator_resumption', 'inner'))


def test_later_generator_iterators_are_deferred_but_list_comprehensions_are_eager():
    result = contexts('''items = (element(x, y) for x in first() for y in later(x))
values = [eager(x) for x in eager_iter()]
''')
    assert result['first'] == ()
    assert result['later'] == result['element'] == (('generator_resumption', 'GeneratorExp'),)
    assert result['eager'] == result['eager_iter'] == ()
