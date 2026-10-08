## @package tests.fixtures.recursive_method_dispatch.main
#  Minimal receiver/parameter cycle reduced from pandas 0.21.0 Index.equals.

import json


class Index:
    ## Compare through an unresolved peer receiver.
    #  @param other Peer whose runtime class is not established.
    #  @return Result of the peer comparison.
    def equals(self, other):
        return other.equals(self)

    ## Forward to another method in the same source file.
    #  @param other Value to append.
    #  @return Concatenated value.
    def append(self, other):
        return self._concat(other)

    ## Forward to the implementation method.
    #  @param other Value to concatenate.
    #  @return Concatenated value.
    def _concat(self, other):
        return self._concat_same_dtype(other)

    ## Return an explicit parameter dependency.
    #  @param other Value to return.
    #  @return The supplied value.
    def _concat_same_dtype(self, other):
        return other


## Preserve independent import-backed result evidence.
#  @param value JSON source.
#  @return Parsed value.
def parse(value):
    return json.loads(value)


parse('{}')
