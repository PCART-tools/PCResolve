## @package tests.test_native_class_protocol

from pcresolve._native_class_protocol import _public_helper_export
from pcresolve._source_protocols import SourceProtocolResolver
from pcresolve import FlowAnalyzer
from pcresolve._native_class_protocol import iterability_query
import ast
import pytest


def test_public_iterability_reexport_is_bound_on_the_normal_setup_branch(tmp_path):
    package = tmp_path / 'numpy'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''
try:
    __NUMPY_SETUP__
except NameError:
    __NUMPY_SETUP__ = False
if __NUMPY_SETUP__:
    pass
else:
    from .lib import *
''', encoding='utf-8')
    (library / '__init__.py').write_text('''
from .impl import *
__all__ = ['iterable']
''', encoding='utf-8')
    (library / 'impl.py').write_text('''
__all__ = ['iterable']
def iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
''', encoding='utf-8')

    resolver = SourceProtocolResolver([tmp_path])
    fact = _public_helper_export(resolver, 'numpy', 'iterable')

    assert fact is not None
    assert fact['target'] == 'numpy.lib.impl.iterable'
    assert fact['status'] == 'source_bound'
    assert 'no_external_module_global_injection' in fact['assumptions']
    assert fact['binding']['may_be_unbound'] is True
    assert fact['binding']['paths'][0]['conditions'][0]['branch'] == 'else'


def test_public_iterability_reexport_stays_open_without_setup_default(tmp_path):
    package = tmp_path / 'numpy'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''
if __NUMPY_SETUP__:
    pass
else:
    from .lib import *
''', encoding='utf-8')
    (library / '__init__.py').write_text("from .impl import *\n__all__ = ['iterable']\n",
                                        encoding='utf-8')
    (library / 'impl.py').write_text("__all__ = ['iterable']\ndef iterable(value): return False\n",
                                     encoding='utf-8')

    fact = _public_helper_export(SourceProtocolResolver([tmp_path]), 'numpy', 'iterable')
    assert fact is None


@pytest.mark.parametrize('extra', [
    'feature = False\n',
    '__PACKAGE_BUILD__ = True\n',
])
def test_reexport_default_guard_does_not_discharge_other_unbound_paths(tmp_path, extra):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    branch = ('    if feature:\n        from .lib import *\n'
              if extra.startswith('feature') else '    from .lib import *\n')
    (package / '__init__.py').write_text('''try:
    __PACKAGE_BUILD__
except NameError:
    __PACKAGE_BUILD__ = False
''' + extra + 'if __PACKAGE_BUILD__:\n    pass\nelse:\n' + branch, encoding='utf-8')
    (library / '__init__.py').write_text("from .impl import *\n__all__ = ['accepts']\n",
                                        encoding='utf-8')
    (library / 'impl.py').write_text("__all__ = ['accepts']\ndef accepts(value): return False\n",
                                     encoding='utf-8')

    assert _public_helper_export(SourceProtocolResolver([tmp_path]), 'sample', 'accepts') is None


def test_reexport_default_guard_cannot_assume_unmodified_wildcard_prefix(tmp_path):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / 'switch.py').write_text(
        "__all__ = ['__PACKAGE_BUILD__']\n__PACKAGE_BUILD__ = True\n", encoding='utf-8')
    (package / '__init__.py').write_text('''from .switch import *
try:
    __PACKAGE_BUILD__
except NameError:
    __PACKAGE_BUILD__ = False
if __PACKAGE_BUILD__:
    pass
else:
    from .lib import *
''', encoding='utf-8')
    (library / '__init__.py').write_text("from .impl import *\n__all__ = ['accepts']\n", encoding='utf-8')
    (library / 'impl.py').write_text("__all__ = ['accepts']\ndef accepts(value): return False\n", encoding='utf-8')

    assert _public_helper_export(SourceProtocolResolver([tmp_path]), 'sample', 'accepts') is None


def test_public_iterability_reexport_uses_library_neutral_false_guard(tmp_path):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''
try:
    __PACKAGE_BUILD__
except NameError:
    __PACKAGE_BUILD__ = False
if __PACKAGE_BUILD__:
    pass
else:
    from .lib import *
''', encoding='utf-8')
    (library / '__init__.py').write_text('''
from .impl import *
__all__ = ['accepts_iterable']
''', encoding='utf-8')
    (library / 'impl.py').write_text('''
__all__ = ['accepts_iterable']
def accepts_iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
''', encoding='utf-8')

    fact = _public_helper_export(SourceProtocolResolver([tmp_path]),
                                 'sample', 'accepts_iterable')

    assert fact is not None
    assert fact['target'] == 'sample.lib.impl.accepts_iterable'
    assert 'no_external_module_global_injection' in fact['assumptions']


@pytest.mark.parametrize('later_exports,expected', [
    ("__all__ = ['other']\ndef other(): pass\n", 'sample.lib.impl.accepts'),
    ("__all__ = ['accepts']\ndef accepts(value): return True\n", 'sample.more.accepts'),
])
def test_ordered_public_wildcards_select_the_last_exported_binding(tmp_path, later_exports, expected):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''try:
    __PACKAGE_BUILD__
except NameError:
    __PACKAGE_BUILD__ = False
if __PACKAGE_BUILD__:
    pass
else:
    from .lib import *
    from .more import *
''', encoding='utf-8')
    (library / '__init__.py').write_text(
        "from .impl import *\n__all__ = ['accepts']\n", encoding='utf-8')
    (library / 'impl.py').write_text(
        "__all__ = ['accepts']\ndef accepts(value): return False\n", encoding='utf-8')
    (package / 'more.py').write_text(later_exports, encoding='utf-8')

    fact = _public_helper_export(SourceProtocolResolver([tmp_path]), 'sample', 'accepts')

    assert fact is not None
    assert fact['target'] == expected


def test_public_binding_stays_unknown_after_a_later_local_replacement(tmp_path):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''
from .lib import *
__all__ = ['accepts']
def replacement(value): return False
accepts = replacement
''', encoding='utf-8')
    (library / '__init__.py').write_text(
        "from .impl import *\n__all__ = ['accepts']\n", encoding='utf-8')
    (library / 'impl.py').write_text(
        "__all__ = ['accepts']\ndef accepts(value): return True\n", encoding='utf-8')

    fact = _public_helper_export(SourceProtocolResolver([tmp_path]), 'sample', 'accepts')

    assert fact is None


def test_public_binding_stays_open_after_dynamic_namespace_write(tmp_path):
    package = tmp_path / 'sample'
    library = package / 'lib'
    library.mkdir(parents=True)
    (package / '__init__.py').write_text('''
from .lib import *
__all__ = ['accepts']
globals().update({'accepts': lambda value: False})
''', encoding='utf-8')
    (library / '__init__.py').write_text(
        "from .impl import *\n__all__ = ['accepts']\n", encoding='utf-8')
    (library / 'impl.py').write_text(
        "__all__ = ['accepts']\ndef accepts(value): return True\n", encoding='utf-8')

    fact = _public_helper_export(SourceProtocolResolver([tmp_path]), 'sample', 'accepts')

    assert fact is None


def test_external_iterability_protocol_requires_opt_in_and_stable_binding(tmp_path):
    helper = tmp_path / 'helpers.py'
    helper.write_text('''def accepts(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
''', encoding='utf-8')
    caller = tmp_path / 'consumer.py'
    caller.write_text('import helpers as h\ndef check(value): return h.accepts(value)\n',
                      encoding='utf-8')

    def query(opt_in):
        analyzer = FlowAnalyzer(source_files=[caller], import_roots=[tmp_path],
                                support_source_protocols=opt_in)
        analyzer._index()
        selected = analyzer._definition_index.find('consumer', 'check')[0]
        call = next(node for node in ast.walk(selected[1]) if isinstance(node, ast.Call))
        return iterability_query(analyzer, selected, call.func)

    assert query(False) is None
    assert query(True) is not None
    caller.write_text('import helpers as h\nh.accepts = lambda value: True\n'
                      'def check(value): return h.accepts(value)\n', encoding='utf-8')
    assert query(True) is None
    caller.write_text('import helpers as h\ndef check(value): return h.accepts(value)\n',
                      encoding='utf-8')
    helper.write_text('def accepts(value): return True\n', encoding='utf-8')
    assert query(True) is None
