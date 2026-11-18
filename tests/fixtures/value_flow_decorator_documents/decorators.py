class Document:
    def __init__(self, text, indents=0):
        if indents > 0:
            unknown_indent(text)
        self.text = text

    def __call__(self, func):
        func.__doc__ = self.text
        return func


class ConditionalDocument:
    def __init__(self, mode=0):
        if mode == 0:
            self.change = False
        else:
            self.change = True

    def __call__(self, func):
        if self.change:
            func.__defaults__ = (1,)
        return func


def opaque_document():
    return unknown_object


class Normalize:
    def __init__(self, text=None):
        self.text = text
        self.separator = ''

    def __call__(self, func):
        self.text = self.text if self.text else ''
        parts = [func.__doc__ or '', self.text]
        func.__doc__ = self.separator.join(parts)
        return func


shared = Normalize('shared')


class UnknownNormalize(Normalize):
    def __call__(self, func):
        self.text = unknown_value
        return super().__call__(func)


class EscapingNormalize(Normalize):
    def __call__(self, func):
        unknown_effect(self)
        return super().__call__(func)


class ConditionalNormalize(Normalize):
    def __init__(self):
        self.change = False

    def __call__(self, func):
        if func.__doc__:
            self.change = True
        if self.change:
            func.__defaults__ = (1,)
        return func


def unsafe_join(func):
    func.__doc__ = ''.join([func.__doc__ or '', unknown_value])
    return func


def missing_helper(func):
    func.__doc__ = unknown_cleaner(''.join([func.__doc__ or '', 'text']))
    return func
