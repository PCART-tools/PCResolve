## @package pcresolve.single_file_query
#  Query-local reuse for single-file receiver and container-shape resolution.

from functools import wraps


_ACTIVE = object()


## Reuse expression facts only during one uninterrupted lexical query.
#  @param fallback Factory for a conservative result on reentrant queries.
#  @return Decorator sharing ephemeral results across receiver/shape queries.
def memoized_expression_query(fallback):
    def decorate(query):
        @wraps(query)
        def memoized(self, node):
            root = self._expression_query_cache is None
            if root:
                self._expression_query_cache = {}
            cache = self._expression_query_cache
            key = (query, node, id(self.current_scope()))
            if key in cache:
                result = cache[key]
                return fallback() if result is _ACTIVE else result
            cache[key] = _ACTIVE
            try:
                result = query(self, node)
                cache[key] = result
                return result
            except Exception:
                cache.pop(key, None)
                raise
            finally:
                # Visitor assignments, branch joins and scope changes must
                # start fresh proofs; no completed-query facts survive here.
                if root:
                    self._expression_query_cache = None
        return memoized
    return decorate
