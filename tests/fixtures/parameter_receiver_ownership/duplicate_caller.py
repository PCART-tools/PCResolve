import sys


class DuplicateWriter:
    def emit(self, out):
        out.write("caller")

    def run(self, out):
        self.emit(out)


DuplicateWriter().emit(sys.stdout)
DuplicateWriter().run(sys.stdout)
