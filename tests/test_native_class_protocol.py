## @package tests.test_native_class_protocol

from pcresolve._native_class_protocol import _public_helper_export
from pcresolve._source_protocols import SourceProtocolResolver


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
