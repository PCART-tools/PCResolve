import fileinput
import gzip


class LocalWriter:
    def close(self):
        return None


class LocalReader:
    def close(self):
        return None


def imported_branches(path, compressed):
    if compressed:
        stream = gzip.open(path)
    else:
        stream = fileinput.FileInput(path)
    stream.close()


def local_and_imported(path, use_local):
    if use_local:
        stream = LocalWriter()
    else:
        stream = gzip.open(path)
    stream.close()


def python_branches(flag):
    if flag:
        values = []
    else:
        values = list()
    values.append(1)


def local_branches(flag):
    if flag:
        reader = LocalReader()
    else:
        reader = LocalReader()
    reader.close()
