import ast

from pcresolve import FlowAnalyzer
from pcresolve._class_definition import namespace_issues
from pcresolve._source_callable_metadata import wrapper_metadata


DOCSTRING = '''import inspect
class Substitution:
    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
        return func
class _ArtistPropertiesSubstitution(Substitution):
    def __call__(self, obj):
        super().__call__(obj)
        if isinstance(obj, type) and obj.__init__ != object.__init__:
            self(obj.__init__)
        return obj
dedent_interpd = interpd = _ArtistPropertiesSubstitution()
'''


def _analyzer(root, decorator_source=DOCSTRING):
    package = root / 'matplotlib'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / '_docstring.py').write_text(decorator_source, encoding='utf-8')
    (package / 'patches.py').write_text('''from . import _docstring
class Patch:
    @_docstring.interpd
    def set_capstyle(self, value): return value
    @_docstring.dedent_interpd
    def __init__(self, **kwargs): pass
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    target, node = analyzer._definition_index.find(
        'matplotlib.patches', 'Patch', kind='class')[0]
    return analyzer, (target, node)


def test_namespace_accepts_exact_matplotlib_docstring_identity_decorator(tmp_path):
    analyzer, patch = _analyzer(tmp_path)
    assumptions = set()
    issues = namespace_issues(analyzer, [patch], assumptions=assumptions)

    assert not [item for item in issues if item[0] == 'namespace_unconfirmed']
    assert 'source_callable_object_identity_decorator' in assumptions


def test_namespace_rejects_docstring_decorator_that_replaces_function(tmp_path):
    source = DOCSTRING.replace('        return obj\n', '        return object()\n')
    analyzer, patch = _analyzer(tmp_path, source)
    issues = namespace_issues(analyzer, [patch], assumptions=set())

    assert any(reason == 'namespace_unconfirmed' and isinstance(node, ast.FunctionDef)
               for reason, _, node in issues)


def test_namespace_recovers_matplotlib_rasterization_marker_from_source_wrapper(tmp_path):
    package = tmp_path / 'matplotlib'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'artist.py').write_text('''from functools import wraps
def allow_rasterization(draw):
    @wraps(draw)
    def draw_wrapper(artist, renderer):
        return draw(artist, renderer)
    draw_wrapper._supports_rasterization = True
    return draw_wrapper
''', encoding='utf-8')
    (package / 'patches.py').write_text('''from . import artist
class Patch:
    @artist.allow_rasterization
    def draw(self, renderer): pass
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    target, node = analyzer._definition_index.find(
        'matplotlib.patches', 'Patch', kind='class')[0]
    assumptions = set()
    issues = namespace_issues(analyzer, [(target, node)], assumptions=assumptions)
    draw_ref, draw = analyzer._definition_index.find(
        'matplotlib.patches', 'Patch.draw')[0]

    assert not [item for item in issues if item[0] == 'namespace_unconfirmed']
    metadata = wrapper_metadata(analyzer, (draw_ref, draw), '_supports_rasterization')
    assert metadata['kind'] == 'source_wrapper_custom_function_metadata'
    assert metadata['value'] is True
