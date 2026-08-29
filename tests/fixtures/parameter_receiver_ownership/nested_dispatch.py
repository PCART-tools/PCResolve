def consume(packed_options):
    return packed_options.get('value')


REGISTRY = {'module': {'consume': consume}}


def invoke(module, function, options):
    functions = REGISTRY.get(module)
    if functions:
        callback = functions.get(function)
        if callback:
            return callback(options)


def launch(module, function):
    options = {}
    options['value'] = 'text'
    return invoke(module, function, options)


launch('module', 'consume')
