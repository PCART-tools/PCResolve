## @package pcresolve.ownership.collect.single_file_query
#  Query-local reuse for single-file receiver and container-shape resolution.
#  单文件接收者与容器形态解析中的查询内结果复用。

from functools import wraps


_ACTIVE = object()


## Reuse expression facts only during one uninterrupted lexical query.
## 仅在一次连续词法查询中复用表达式事实。
#
#  @param fallback Factory for a conservative result on reentrant queries.
#  @return Decorator sharing ephemeral results across receiver/shape queries.
def memoized_expression_query(fallback):
    ## Wrap one expression query with an ephemeral cache.
    ## 使用临时缓存包装表达式查询。
    #
    #  @param query Expression query to wrap.
    #  @return Memoized query.
    def decorate(query):
        ## Reuse completed results and stop reentrant resolution cycles.
        ## 复用已完成结果并阻止重入解析循环。
        #
        #  @param node Expression node being resolved.
        #  @return Query result or conservative fallback on reentry.
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
                # 赋值、分支合并或作用域变化后必须重新证明，不保留本次缓存。
                if root:
                    self._expression_query_cache = None
        return memoized
    return decorate
