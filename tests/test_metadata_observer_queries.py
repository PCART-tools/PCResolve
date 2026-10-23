## @package tests.test_metadata_observer_queries

import ast
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve._metadata_observer import observer_query


SOURCE = '''import inspect
import re
from functools import lru_cache
def iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
class Root: pass
class Observer:
    def __init__(self, obj):
        if not isinstance(obj, Root):
            if iterable(obj):
                obj = list(obj)
                if len(obj): obj = obj[0]
        self.original = obj
        if not isinstance(obj, type): obj = type(obj)
        self.o = obj
        self.aliases = self.get_aliases()
    @staticmethod
    @lru_cache(maxsize=None)
    def count(fn):
        return len(inspect.signature(fn).parameters)
    @staticmethod
    @lru_cache(maxsize=None)
    def is_alias(fn):
        text = inspect.getdoc(fn)
        if text is None: return False
        return text.startswith('Alias ')
    def get_aliases(self):
        names = [name for name in dir(self.o)
                 if name.startswith(('set_', 'get_')) and callable(getattr(self.o, name))]
        aliases = {}
        for name in names:
            fn = getattr(self.o, name)
            if not self.is_alias(fn): continue
            propname = re.search('`({}.*)`'.format(name[:4]), inspect.getdoc(fn)).group(1)
            aliases.setdefault(propname[4:], set()).add(name[4:])
        return aliases
    def get_setters(self):
        setters = []
        for name in dir(self.o):
            if not name.startswith('set_'): continue
            fn = getattr(self.o, name)
            if not callable(fn) or self.count(fn) < 2 or self.is_alias(fn): continue
            setters.append(name[4:])
        return setters
'''


def prepare(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Observer', kind='class')[0]
    return analyzer, target, path


LOOP_ELSE_QUERY = '''
    def describe(self):
        result = []
        for name in ['candidate']:
            if name.startswith('candidate'):
                result.append(name)
                break
        else:
            result.append('fallback')
        return result
'''


MRO_QUERY = '''
    def describe(self):
        result = []
        for prop in self.get_setters():
            for cls in self.o.__mro__:
                method = getattr(cls, f"set_{prop}", None)
                if method and method.__doc__ is not None:
                    break
            else:
                method = getattr(self.o, f"set_{prop}")
            result.append(f"{method.__module__}.{method.__qualname__}")
        return result
'''


ROW_QUERY = '''
    def describe(self):
        rows = [(prop, f"prefix{prop}") for prop in self.get_setters()]
        return [target.replace('prefix', '') for prop, target in rows]
'''


LINK_QUERY = ROW_QUERY.replace("target.replace('prefix', '')", 'self.link(prop, target)') + '''
    _unlinked = {'native.name', 'other.name'}
    def link(self, prop, target):
        if target in self._unlinked:
            return f"``{prop}``"
        return ':meth:`%s <%s>`' % (prop, target)
'''


TABLE_QUERY = '''
    def describe(self):
        names = self.get_setters()
        labels = [f"label_{name}" for name in names]
        width = max(len(name) for name in names)
        return ['header', *[name.ljust(width) + label for name, label in zip(names, labels)], 'footer']
'''


NULLABLE_TABLE_QUERY = '''
    def optional(self, value):
        if value.startswith('absent'): return None
        return value
    def describe(self):
        values = [self.optional(name) for name in self.get_setters()]
        width = max(len(value) for value in values)
        return [value.ljust(width) for value in values]
'''


def test_nullable_native_text_operations_only_describe_normal_return(tmp_path):
    analyzer, target, _ = prepare(tmp_path, SOURCE + NULLABLE_TABLE_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    assert proof['completion'] == 'normal_return_only'


def test_nullable_text_operations_do_not_discard_later_exposures(tmp_path):
    query = NULLABLE_TABLE_QUERY.replace('return [value.ljust(width) for value in values]',
        'opaque(self.o)\n        return [value.ljust(width) for value in values]')
    analyzer, target, _ = prepare(tmp_path, SOURCE + query)
    assert observer_query(analyzer, target, 'describe') is None


def test_private_native_table_formatting_consumes_generators_immediately(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + TABLE_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    assert proof['completion'] == 'normal_return_only'
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Value documentation."""
    assert namespace['Observer'](Example).describe() == ['header', 'valuelabel_value', 'footer']


@pytest.mark.parametrize('old,new', [
    ('len(name) for name in names', 'opaque(self.o) for name in names'),
    ('max(len(name) for name in names)', 'max((len(name) for name in names), key=opaque)'),
    ('name.ljust(width)', 'name.ljust(opaque(self.o))'),
    ('zip(names, labels)', 'zip(names, opaque(self.o))'),
    ('zip(names, labels)', 'zip(names, labels, strict=opaque())'),
    ("'header', *[", 'self.o, *['),
])
def test_table_formatting_does_not_hide_callbacks_or_class_data(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + TABLE_QUERY.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


def test_source_literal_string_set_membership_retains_binding_obligation(tmp_path):
    analyzer, target, _ = prepare(tmp_path, SOURCE + LINK_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    creation = next(item for item in proof['native_data_members'] if item['attribute'] == '_unlinked')
    assert creation['creation']['result_kind'] == 'native_string_set'
    assert creation['runtime_value_confirmed'] is False
    assert proof['input_preconditions']['observer_data_members'] == 'source_creation_values_preserved'


@pytest.mark.parametrize('old,new', [
    ("{'native.name', 'other.name'}", '{opaque()}'),
    ("{'native.name', 'other.name'}", '{1, 2}'),
    ("{'native.name', 'other.name'}", 'opaque()'),
    ('target in self._unlinked', 'self.o in self._unlinked'),
    ('return f"``{prop}``"', 'return opaque(self.o)'),
])
def test_literal_set_queries_reject_open_elements_and_class_capabilities(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + LINK_QUERY.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


def test_private_native_tuple_rows_can_be_unpacked_without_callbacks(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + ROW_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    assert proof['result_shape'] == 'native_string_list'
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Value documentation."""
    assert namespace['Observer'](Example).describe() == ['value']


@pytest.mark.parametrize('old,new', [
    ('prop, target in rows', 'prop, target, extra in rows'),
    ('prop, target in rows', 'prop, *target in rows'),
    ('prop, target in rows', 'prop, self.changed in rows'),
    ('for prop, target in rows]', 'for prop, target in rows if opaque(self.o)]'),
    ("target.replace('prefix', '')", "target.replace('prefix', opaque(self.o))"),
    ('(prop, f"prefix{prop}")', '(prop, self.o)'),
])
def test_tuple_row_unpacking_keeps_open_bindings_and_effects_unresolved(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + ROW_QUERY.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


def test_private_query_mro_retains_ancestor_lookup_obligations(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + MRO_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    assert proof['result_shape'] == 'native_string_list'
    assert proof['input_preconditions']['ancestry'] == 'native_type_mro_with_unchanged_member_namespaces'
    ancestor = [item for item in proof['native_member_lookups']
                if item.get('receiver_scope') == 'input_class_mro']
    assert ancestor
    assert all(item['presence'] == 'unresolved' for item in ancestor)
    assert proof['native_mro_queries'][0]['runtime_lookup_confirmed'] is False
    namespace = runpy.run_path(str(path))
    class Parent:
        def set_value(self, value):
            """A documented setter."""
    class Child(Parent):
        pass
    assert namespace['Observer'](Child).describe() == [Parent.set_value.__module__ + '.'
                                                     + Parent.set_value.__qualname__]


@pytest.mark.parametrize('old,new', [
    ('result.append(f"{method.__module__}.{method.__qualname__}")', 'result.append(cls)'),
    ('method = getattr(cls,', 'cls.changed = True\n                method = getattr(cls,'),
    ('if method and', 'opaque(cls)\n                if method and'),
    ('if method and', 'method()\n                if method and'),
    ('f"set_{prop}", None', 'f"set_{prop}", opaque(self.o)'),
    ('f"set_{prop}"', 'f"other_{prop}"'),
])
def test_mro_queries_do_not_authorize_class_escapes_or_calls(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + MRO_QUERY.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


@pytest.mark.parametrize('condition', ['not method', 'not hasattr(cls, f"set_{prop}")'])
def test_ancestor_presence_is_not_inferred_from_child_directory(tmp_path, condition):
    query = MRO_QUERY.replace('if method and method.__doc__ is not None:',
        'if ' + condition + ':\n                    opaque(self.o)\n                if method:')
    analyzer, target, _ = prepare(tmp_path, SOURCE + query)
    assert observer_query(analyzer, target, 'describe') is None


def test_native_mro_capability_cannot_be_returned_as_data(tmp_path):
    query = '''
    def describe(self):
        return self.o.__mro__
'''
    analyzer, target, _ = prepare(tmp_path, SOURCE + query)
    assert observer_query(analyzer, target, 'describe') is None


def test_private_query_for_else_keeps_break_and_exhaustion_paths(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + LOOP_ELSE_QUERY)
    proof = observer_query(analyzer, target, 'describe')
    assert proof is not None
    assert proof['result_shape'] == 'native_string_list'
    namespace = runpy.run_path(str(path))
    assert namespace['Observer'](namespace['Root']).describe() == ['candidate']


@pytest.mark.parametrize('old,new', [
    ("result.append('fallback')", 'opaque(self.o)'),
    ('result.append(name)', 'opaque(self.o)'),
    ('return result', 'opaque(self.o)\n        return result'),
])
def test_private_query_for_else_never_discards_path_exposures(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + LOOP_ELSE_QUERY.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


@pytest.mark.parametrize('body', [
    'continue',
    "for inner in ['inner']:\n                break",
])
def test_continue_and_nested_break_do_not_skip_outer_else(tmp_path, body):
    query = '''
    def describe(self):
        for name in ['outer']:
            BODY
        else:
            opaque(self.o)
        return ['text']
'''.replace('BODY', body)
    analyzer, target, _ = prepare(tmp_path, SOURCE + query)
    assert observer_query(analyzer, target, 'describe') is None


FORMATTER = '''
    def describe(self, prop=None, leadingspace=2):
        return self.render(prop, leadingspace=leadingspace)
    def render(self, prop=None, *, leadingspace=2):
        if prop is not None:
            return [prop]
        if leadingspace:
            return self.get_setters()
        return ['compact']
'''


@pytest.mark.parametrize('keywords,expected', [
    ({}, ['value']), ({'leadingspace': 4}, ['value']),
    ({'leadingspace': 0}, ['compact']), ({'prop': 'chosen'}, ['chosen']),
])
def test_observer_binds_literal_formatting_arguments_and_defaults(tmp_path, keywords, expected):
    analyzer, target, path = prepare(tmp_path, SOURCE + FORMATTER)
    fact = observer_query(analyzer, target, 'describe', keyword_literals=keywords)
    assert fact is not None and fact['status'] == 'requires_native_class_metadata'
    assert fact['result_shape'] == 'native_string_list'
    assert fact['query_arguments']['positional'] == []
    assert fact['query_arguments']['keywords'] == keywords
    assert fact['query_arguments']['binding'] == 'exact_source_signature'
    assert fact['query_arguments']['defaults'] == {
        key: value for key, value in {'prop': None, 'leadingspace': 2}.items()
        if key not in keywords}
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Value documentation."""
    assert namespace['Observer'](Example).describe(**keywords) == expected


@pytest.mark.parametrize('positional,keywords', [
    (('chosen',), {}), (('chosen', 4), {}),
    (('chosen',), {'leadingspace': 0}),
])
def test_observer_keeps_explicit_positional_argument_obligations(tmp_path, positional, keywords):
    analyzer, target, _ = prepare(tmp_path, SOURCE + FORMATTER)
    fact = observer_query(analyzer, target, 'describe',
                          positional_literals=positional, keyword_literals=keywords)
    assert fact is not None
    assert fact['query_arguments']['positional'] == list(positional)
    assert fact['query_arguments']['keywords'] == keywords


@pytest.mark.parametrize('positional,keywords', [
    (('chosen',), {'prop': 'duplicate'}), ((None, 2, 3), {}),
    ((), {'unknown': 4}), ((), {'leadingspace': object()}),
    ((), {'leadingspace': []}), ((), {4: 2}),
])
def test_observer_invalid_bindings_and_nonliteral_inputs_stay_open(tmp_path, positional, keywords):
    analyzer, target, _ = prepare(tmp_path, SOURCE + FORMATTER)
    assert observer_query(analyzer, target, 'describe',
        positional_literals=positional, keyword_literals=keywords) is None


def test_observer_argument_profiles_do_not_share_conditional_results(tmp_path):
    analyzer, target, _ = prepare(tmp_path, SOURCE + FORMATTER)
    compact = observer_query(analyzer, target, 'describe', keyword_literals={'leadingspace': 0})
    padded = observer_query(analyzer, target, 'describe', keyword_literals={'leadingspace': 4})
    assert compact is not None and padded is not None
    assert compact['query_arguments'] != padded['query_arguments']
    compact['query_arguments']['keywords']['leadingspace'] = 999
    again = observer_query(analyzer, target, 'describe', keyword_literals={'leadingspace': 0})
    assert again['query_arguments']['keywords'] == {'leadingspace': 0}


@pytest.mark.parametrize('old,new', [
    ('leadingspace=2', 'leadingspace=opaque()'),
    ('return self.render(prop, leadingspace=leadingspace)',
     'return self.render(prop, wrong=leadingspace)'),
    ('return self.render(prop, leadingspace=leadingspace)',
     'return self.render(prop, **opaque)'),
    ('return [prop]', 'opaque(self.o)\n            return [prop]'),
])
def test_observer_argument_binding_does_not_hide_evaluation_or_class_escape(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE + FORMATTER.replace(old, new))
    assert observer_query(analyzer, target, 'describe', keyword_literals={'prop': 'chosen'}) is None


TEXT_FORMATTER = '''
    def describe(self, prop=None, leadingspace=2):
        pad = ' ' * leadingspace
        if prop is not None:
            return [pad + '%s: %s' % (prop, None)]
        lines = []
        for prop in sorted(self.get_setters()):
            lines.append('%s%s: %s' % (pad, prop, 'native text'))
        return lines
'''


MEMBER_FORMATTER = '''
    def describe(self):
        lines = []
        for prop in self.get_setters():
            lines.append(self.describe_property(prop))
        return lines
    def describe_property(self, prop):
        name = 'set_%s' % prop
        if not hasattr(self.o, name):
            raise AttributeError('%s has no function %s' % (self.o, name))
        fn = getattr(self.o, name)
        return 'Property %s' % prop
'''


@pytest.mark.parametrize('prefix', ['set_', 'emit_'])
def test_directory_member_name_survives_exact_prefix_removal_and_restoration(tmp_path, prefix):
    source = SOURCE.replace("startswith('set_')", f"startswith('{prefix}')")
    source = source.replace('setters.append(name[4:])', f'setters.append(name[{len(prefix)}:])')
    source += MEMBER_FORMATTER.replace("'set_%s'", repr(prefix + '%s'))
    analyzer, target, path = prepare(tmp_path, source)
    result = observer_query(analyzer, target, 'describe')
    assert result is not None
    assert result['status'] == 'requires_native_class_metadata'
    assert result['result_shape'] == 'native_string_list'
    assert result['input_preconditions']['member_namespace'] == 'unchanged_during_query'
    checks = [item for item in result['native_member_lookups'] if item['operation'] == 'hasattr']
    assert checks and all(item['result'] is True for item in checks)
    assert all(item['name_source'] == 'input_class_directory' for item in checks)
    assert all(item['member_prefixes'] == [prefix] for item in checks)
    assert all({step['operation'] for step in item['name_evidence']} >= {
        'directory', 'remove_prefix', 'restore_prefix'} for item in checks)
    assert all(item['runtime_lookup_confirmed'] is False for item in checks)
    namespace = runpy.run_path(str(path))
    def method(self, value):
        """Native documentation."""
    example = type('Example', (), {prefix + 'value': method})
    assert namespace['Observer'](example).describe() == ['Property value']


@pytest.mark.parametrize('old,new', [
    ("'set_%s' % prop", "'get_%s' % prop"),
    ("'set_%s' % prop", "'set_%r' % prop"),
    ("'set_%s' % prop", "'set_%s_extra' % prop"),
    ('setters.append(name[4:])', 'setters.append(name[3:])'),
    ('setters.append(name[4:])', 'setters.append(name[5:])'),
    ('setters.append(name[4:])', 'setters.append(name[4::2])'),
    ('setters.append(name[4:])', 'setters.append(name[4:-1])'),
    ("name = 'set_%s' % prop", "prop = 'invented'\n        name = 'set_%s' % prop"),
    ("name = 'set_%s' % prop", "self.o = 'foreign'\n        name = 'set_%s' % prop"),
    ('setters.append(name[4:])', "setters.append('invented')"),
    ('setters.append(name[4:])', "setters.append(name[4:])\n            setters.append('invented')"),
    ('if not hasattr(self.o, name):',
     'hasattr = opaque\n        if not hasattr(self.o, name):'),
])
def test_changed_names_or_receivers_cannot_inherit_directory_membership(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, (SOURCE + MEMBER_FORMATTER).replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


DOCUMENTATION_FORMATTER = MEMBER_FORMATTER.replace(
    "        return 'Property %s' % prop", '''        text = inspect.getdoc(fn)
        if text is None:
            return 'unknown'
        if text.startswith('Alias for '):
            return None
        match = self._values_pattern.search(text)
        if match is not None:
            return re.sub('\\n *', ' ', match.group(1))
        param_name = fn.__code__.co_varnames[1]
        match = re.search(r'(?m)^ *\\*?{} : (.+)'.format(param_name), text)
        if match:
            return match.group(1)
        return 'unknown'
    _values_pattern = re.compile(r'\\n\\s*ACCEPTS: ([^\\n]+)')''').replace(
        'lines.append(self.describe_property(prop))',
        "lines.append('%s' % self.describe_property(prop))")


def test_source_regex_and_function_code_metadata_stay_conditional_native_data(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + DOCUMENTATION_FORMATTER)
    result = observer_query(analyzer, target, 'describe')
    assert result is not None and result['result_shape'] == 'native_string_list'
    members = result['native_data_members']
    assert len(members) == 1 and members[0]['attribute'] == '_values_pattern'
    assert members[0]['creation']['result_kind'] == 'native_regex_pattern'
    assert members[0]['creation']['source_hashes'] == analyzer.hashes
    assert members[0]['runtime_value_confirmed'] is False
    assert result['input_preconditions']['observer_data_members'] == 'source_creation_values_preserved'
    assert result['input_preconditions']['metadata_results']['code'] == 'native_code_with_native_string_varnames'
    assert 'native_python_code_metadata_without_user_callbacks' in result[
        'input_preconditions']['native_function_metadata_protocols']
    namespace = runpy.run_path(str(path))
    class Example:
        def set_first(self, value):
            """Set value.

            ACCEPTS: native-text
            """
        def set_second(self, value):
            """Set value.

            value : source-text
            """
    assert namespace['Observer'](Example).describe() == ['native-text', 'source-text']


@pytest.mark.parametrize('old,new', [
    ('fn.__code__.co_varnames[1]', 'fn.__code__.co_consts[1]'),
    ('fn.__code__.co_varnames[1]', 'fn.__code__.co_varnames[opaque()]'),
    ('param_name = fn.__code__.co_varnames[1]',
     'opaque(fn.__code__)\n        param_name = fn.__code__.co_varnames[1]'),
    ("re.sub('\\n *', ' ', match.group(1))", "re.sub('\\n *', opaque, match.group(1))"),
    ("_values_pattern = re.compile(r'\\n\\s*ACCEPTS: ([^\\n]+)')", '_values_pattern = opaque'),
    ('text = inspect.getdoc(fn)', 'self._values_pattern = opaque\n        text = inspect.getdoc(fn)'),
])
def test_regex_and_code_metadata_do_not_admit_callbacks_or_opaque_state(tmp_path, old, new):
    source = SOURCE + DOCUMENTATION_FORMATTER
    assert old in source
    analyzer, target, _ = prepare(tmp_path, source.replace(old, new))
    assert observer_query(analyzer, target, 'describe') is None


def test_an_optional_regex_capture_cannot_hide_a_class_escape(tmp_path):
    source = SOURCE + '''
    def describe(self):
        value = re.search('(value)?', 'other').group(1)
        if value is None:
            opaque(self.o)
        return ['safe']
'''
    analyzer, target, _ = prepare(tmp_path, source)
    assert observer_query(analyzer, target, 'describe') is None


def test_optional_regex_capture_is_not_claimed_to_be_a_string(tmp_path):
    source = SOURCE + '''
    def describe(self):
        return [re.search('(value)?', 'other').group(1)]
'''
    analyzer, target, _ = prepare(tmp_path, source)
    assert observer_query(analyzer, target, 'describe') is None


ALIASED_FORMATTER = DOCUMENTATION_FORMATTER.replace(
    "lines.append('%s' % self.describe_property(prop))",
    "lines.append('%s: %s' % (self.label(prop), self.describe_property(prop)))") + '''
    def label(self, prop):
        aliases = ''.join(' or %s' % name for name in sorted(self.aliases.get(prop, [])))
        return prop + aliases
'''


def test_readonly_alias_collections_and_consumed_string_generator(tmp_path):
    analyzer, target, path = prepare(tmp_path, SOURCE + ALIASED_FORMATTER)
    result = observer_query(analyzer, target, 'describe')
    assert result is not None and result['result_shape'] == 'native_string_list'
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Set value.

            value : source-text
            """
        def set_short(self, value):
            """Alias for `set_value`."""
    assert namespace['Observer'](Example).describe() == ['value or short: source-text']


@pytest.mark.parametrize('expression', [
    '[self.change() for name in ["x"]]',
    '"".join(self.change() for name in ["x"])',
])
def test_discarded_comprehension_state_cannot_hide_a_class_escape(tmp_path, expression):
    source = SOURCE.replace('self.aliases = self.get_aliases()',
                            'self.flag = False\n        self.aliases = self.get_aliases()') + f'''
    def change(self):
        self.flag = True
        return 'text'
    def describe(self):
        values = {expression}
        if self.flag:
            opaque(self.o)
        return ['text']
'''
    analyzer, target, _ = prepare(tmp_path, source)
    assert observer_query(analyzer, target, 'describe') is None


@pytest.mark.parametrize('keywords,expected', [
    ({'leadingspace': 4}, ['    value: native text']),
    ({'leadingspace': 0}, ['value: native text']),
    ({'prop': 'chosen'}, ['  chosen: None']),
])
def test_native_text_formatting_has_no_class_input_callback(tmp_path, keywords, expected):
    analyzer, target, path = prepare(tmp_path, SOURCE + TEXT_FORMATTER)
    fact = observer_query(analyzer, target, 'describe', keyword_literals=keywords)
    assert fact is not None and fact['result_shape'] == 'native_string_list'
    assert fact['input_effects']['source_writes'] == []
    assert fact['input_effects']['source_exposures'] == []
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Value documentation."""
    assert namespace['Observer'](Example).describe(**keywords) == expected


@pytest.mark.parametrize('old,new,keywords', [
    ("' ' * leadingspace", "' ' * self.o", {'prop': 'chosen'}),
    ("(prop, None)", "(prop, self.o)", {'prop': 'chosen'}),
    ('sorted(self.get_setters())', 'sorted(self.get_setters(), key=opaque)', {}),
])
def test_native_text_formatting_cannot_hide_class_capabilities_or_callbacks(tmp_path, old, new, keywords):
    analyzer, target, _ = prepare(tmp_path, SOURCE + TEXT_FORMATTER.replace(old, new))
    assert observer_query(analyzer, target, 'describe', keyword_literals=keywords) is None


@pytest.mark.parametrize('method,shape', [
    ('get_setters', 'native_string_list'), ('get_aliases', 'native_string_set_mapping'),
])
def test_whole_observer_query_keeps_class_retention_and_metadata_premises_explicit(
        tmp_path, method, shape):
    analyzer, target, _ = prepare(tmp_path)
    result = observer_query(analyzer, target, method)
    assert result is not None
    assert result['status'] == 'requires_native_class_metadata'
    assert result['result_shape'] == shape
    assert result['completion'] == 'normal_return_only'
    assert result['runtime_execution_confirmed'] is False
    assert result['input_effects']['source_writes'] == []
    assert result['input_effects']['source_exposures'] == []
    assert result['input_effects']['private_receiver_fields'] == ['o', 'original']
    assert result['input_effects']['native_cache_retention'] is True
    assert result['input_preconditions']['exact_metaclass'] == 'type'
    assert result['input_preconditions']['member_prefixes'] == ['get_', 'set_']
    assert result['native_iterability_queries'][0]['source_protocol']['result'] is False
    assert result['source_hashes'] == analyzer.hashes


def test_an_uncached_instance_helper_and_inline_signature_query_share_the_same_proof(tmp_path):
    source = SOURCE.replace('    @staticmethod\n    @lru_cache(maxsize=None)\n    def is_alias(fn):',
                            '    def is_alias(self, fn):')
    source = source.replace('self.count(fn)', 'len(inspect.signature(fn).parameters)')
    analyzer, target, _ = prepare(tmp_path, source)
    result = observer_query(analyzer, target, 'get_setters')
    assert result is not None
    assert result['result_shape'] == 'native_string_list'
    assert result['input_effects']['native_cache_retention'] is False


def test_whole_query_has_an_independent_runtime_control(tmp_path):
    analyzer, target, path = prepare(tmp_path)
    assert observer_query(analyzer, target, 'get_setters') is not None
    namespace = runpy.run_path(str(path))
    class Example:
        def set_value(self, value):
            """Value documentation."""
        def set_short(self, value):
            """Alias for `set_value`."""
    observer = namespace['Observer'](Example)
    assert observer.get_setters() == ['value']
    assert observer.get_aliases() == {'value': {'short'}}


@pytest.mark.parametrize('old,new', [
    ('self.o = obj', 'self.o = obj\n        obj.changed = True'),
    ('self.o = obj', 'self.o = obj\n        opaque(obj)'),
    ('return setters', 'return self.o'),
    ('setters.append(name[4:])', 'setters.append(self.o)'),
    ('setters.append(name[4:])', 'setters.append(lambda: self.o)'),
    ('fn = getattr(self.o, name)', 'names.append("unsafe")\n            fn = getattr(self.o, name)'),
    ('def get_setters(self):\n        setters = []',
     'def get_setters(self):\n        flag = False\n        setters = []'),
    ('def iterable(value):', 'def iterable(value):\n    opaque(value)'),
    ('return False\n    return True', 'return True\n    return True'),
    ('self.original = obj', 'global leaked\n        leaked = obj\n        self.original = obj'),
    ('class Observer:', 'class Observer:\n    def __getattribute__(self, name): return opaque'),
])
def test_class_capabilities_open_protocols_and_iterable_mutations_are_not_readonly(tmp_path, old, new):
    source = SOURCE.replace(old, new)
    if old.startswith('def get_setters'):
        source = source.replace('setters.append(name[4:])',
            'if flag: opaque(self.o)\n            flag = True\n            setters.append(name[4:])')
    analyzer, target, _ = prepare(tmp_path, source)
    assert observer_query(analyzer, target, 'get_setters') is None


def test_observer_specialization_does_not_rewrite_source_methods(tmp_path):
    analyzer, target, _ = prepare(tmp_path)
    before = ast.dump(target[1])
    assert observer_query(analyzer, target, 'get_setters') is not None
    assert ast.dump(target[1]) == before


def test_constructor_source_protocol_can_use_a_module_attribute_alias(tmp_path):
    helper = '''def iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
'''
    (tmp_path / 'helper.py').write_text(helper, encoding='utf-8')
    source = 'import helper as lib\n' + SOURCE.replace('if iterable(obj):', 'if lib.iterable(obj):')
    analyzer, target, _ = prepare(tmp_path, source)
    result = observer_query(analyzer, target, 'get_setters')
    assert result is not None
    assert result['native_iterability_queries'][0]['callee'] == 'helper.iterable'


def test_observer_effects_are_published_as_conditional_source_facts(tmp_path):
    analyzer, _, _ = prepare(tmp_path)
    result = analyzer.analyze(FunctionRef('example', 'Observer.get_setters'))
    summary = next(item for item in result.functions
                   if item['function']['qualname'] == 'Observer.get_setters')
    fact = summary['native_class_metadata_observers'][0]
    assert fact['status'] == 'requires_native_class_metadata'
    assert fact['owner_binding']['status'] == 'requires_source_member_bindings'
    assert fact['input_preconditions']['observer_members'] == 'source_declarations_hold'
    # A template does not remove open entry-receiver or helper-call boundaries.
    assert result.boundaries
