def fixed(value=None):
    return value


def accepts(**kwargs):
    return kwargs


def lambda_forward(**kwargs):
    target = lambda **options: fixed(**options)
    return target(**kwargs)


def lambda_closed(**kwargs):
    target = lambda **options: accepts(**options)
    return target(**kwargs)


def lambda_pair(**kwargs):
    safe, sink = (lambda **options: accepts(**options)), (lambda **options: fixed(**options))
    safe(**kwargs)
    return sink(**kwargs)


def lambda_rebound(**kwargs):
    target = lambda **options: fixed(**options)
    target = lambda **options: accepts(**options)
    return target(**kwargs)


def lambda_capture(**kwargs):
    target = lambda: fixed(**kwargs)
    return target()


def lambda_capture_clear(**kwargs):
    target = lambda: fixed(**kwargs)
    kwargs.clear()
    return target()


def lambda_capture_shadow(**kwargs):
    target = lambda kwargs: fixed(**kwargs)
    return target({'value': 0})


def lambda_return(**kwargs):
    target = lambda data: data
    return fixed(**target(kwargs))


try:
    import missing_optional_dependency
except ImportError:
    class Fallback:
        def run(self, **kwargs):
            return fixed(**kwargs)


if False:
    class Never:
        def run(self, **kwargs):
            return fixed(**kwargs)


if configured:
    class Choice:
        def run(self, **kwargs):
            return fixed(**kwargs)
else:
    class Choice:
        def run(self, **kwargs):
            return accepts(**kwargs)


def delete_keys(mapping, keys):
    for key in keys:
        if key in mapping:
            del mapping[key]


def clean(mapping, keys):
    delete_keys(mapping, keys)
    return mapping


def finite_return(**kwargs):
    options = clean(kwargs, ('out', 'p'))
    options.pop('unused', None)
    return fixed(**options)


def cleared_return(**kwargs):
    options = clean(kwargs, ('out', 'p'))
    options.clear()
    return fixed(**options)


def unknown_keys(keys, **kwargs):
    return fixed(**clean(kwargs, keys))


def finite_input(**kwargs):
    return fixed(**clean({'value': kwargs.get('value')}, ('out',)))
