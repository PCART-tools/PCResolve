from pcresolve import FlowAnalyzer, FunctionRef


_MANAGER = '''from contextlib import contextmanager as managed
@managed
def temporary_values(obj, **kwargs):
    sentinel = object()
    origs = {}
    for attr in kwargs:
        orig = getattr(obj, attr, sentinel)
        if attr in obj.__dict__ or orig is sentinel:
            origs[attr] = orig
        else:
            cls_orig = getattr(type(obj), attr)
            if isinstance(cls_orig, property):
                origs[attr] = orig
            else:
                origs[attr] = sentinel
    try:
        for attr, val in kwargs.items():
            setattr(obj, attr, val)
        yield
    finally:
        for attr, orig in origs.items():
            if orig is sentinel:
                delattr(obj, attr)
            else:
                setattr(obj, attr, orig)
'''


def _effects(tmp_path, manager_source=_MANAGER):
    source = manager_source + '''\
class Surface:
    def __init__(self):
        with temporary_values(self, active=False):
            self.draw()
    def draw(self):
        pass
'''
    (tmp_path / 'custom_runtime.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef(module='custom_runtime', qualname='Surface'), max_depth=5)
    summary = next(item for item in result.functions
                   if item['function']['qualname'] == 'Surface.__init__')
    return summary['context_managers'][0].get('bounded_temporary_receiver_effects')


def test_custom_context_manager_produces_library_neutral_temporary_effect(tmp_path):
    effect = _effects(tmp_path)

    assert effect is not None
    assert effect['kind'] == 'bounded_temporary_receiver_attributes'
    assert effect['manager']['module'] == 'custom_runtime'
    assert effect['manager']['qualname'] == 'temporary_values'
    assert effect['attributes'] == ['active']
    assert effect['restored_on_all_exits'] is True
    assert effect['body_exception_behavior'] == 'propagates_if_cleanup_completes'
    assert effect['runtime_protocol_confirmed'] is False


def test_context_manager_exception_handler_does_not_get_a_rethrow_effect(tmp_path):
    source = _MANAGER.replace(
        '    finally:\n',
        '    except Exception:\n        return\n    finally:\n',
    )

    assert _effects(tmp_path, source) is None
