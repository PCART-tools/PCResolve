# Exact function excerpts from CPython; see SOURCE.json and LICENSE_PYTHON.txt.

def _get_sep(path):
    if isinstance(path, bytes):
        return b'/'
    else:
        return '/'
