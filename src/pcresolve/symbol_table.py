## @package pcresolve.symbol_table
#  Provide per-symbol chain tracking from definition site to ultimate origin.
#
#  The SymbolTable class records direct symbol-to-source mappings and
#  recursively traces each symbol through aliases, assignments, and imports
#  to determine its top-level origin library.

import builtins
from .sources import CallResult, SourceSet, normalize_source, source_display


## Tracks symbol definitions and resolves each to its top-level source.
#
#  Maintains three data structures:
#  - direct: immediate source of each symbol (module name, "local", etc.)
#  - chains: full resolution chain from symbol to origin
#  - top: cached top-level origin for each symbol
class SymbolTable:
    ## Initialize an empty symbol table.
    def __init__(self, return_sources=None):
        self.direct = {}
        self.top = {}
        self.chains = {}
        self.return_sources = return_sources if return_sources is not None else {}

    ## Recursively trace a symbol to build its resolution chain.
    #
    #  Follows the direct-source mapping until a terminal symbol is reached.
    #  @param symbol The symbol to trace.
    #  @param visited Set of already-visited symbols to detect cycles.
    #  @return Ordered list forming the resolution chain.
    def trace(self, symbol, visited=None):
        if visited is None:
            visited = set()
        symbol = normalize_source(symbol)
        if isinstance(symbol, CallResult):
            if symbol in visited:
                return []
            visited.add(symbol)
            callee = symbol.callee
            rs = self.return_sources.get(callee)
            if rs:
                rs = normalize_source(rs)
                if isinstance(rs, CallResult):
                    return self.trace(rs, visited)
                if isinstance(rs, SourceSet):
                    for src in rs.sources:
                        sub = self.trace(src, visited)
                        if sub and sub != [source_display(src)]:
                            return sub
                if isinstance(rs, str):
                    return self.trace(rs, visited)
            return self.trace(callee, visited)
        if symbol in visited:
            return []
        visited.add(symbol)
        if not isinstance(symbol, str):
            return [source_display(symbol)]
        if symbol not in self.direct:
            return [symbol]
        source = normalize_source(self.direct[symbol])
        if isinstance(source, CallResult):
            callee = source.callee
            rs = self.return_sources.get(callee)
            if rs:
                rs = normalize_source(rs)
                if isinstance(rs, CallResult):
                    sub = self.trace(rs, visited)
                elif isinstance(rs, SourceSet):
                    sub = None
                    for src in rs.sources:
                        sub = self.trace(src, visited)
                        if sub and sub != [source_display(src)]:
                            break
                    if not sub:
                        sub = self.trace(callee, visited)
                elif isinstance(rs, str):
                    sub = self.trace(rs, visited)
                else:
                    sub = self.trace(callee, visited)
            else:
                sub = self.trace(callee, visited)
            return [symbol] + sub
        if not isinstance(source, str):
            return [symbol, source_display(source)]
        subchain = self.trace(source, visited)
        return [symbol] + subchain

    ## Get the top-level origin for a symbol.
    #
    #  Resolves through the chain and returns the last element.
    #  @param symbol The symbol to look up.
    #  @return Top-level source string, or None.
    def get_top(self, symbol):
        if symbol in self.top:
            return self.top[symbol]
        chain = self.trace(symbol)
        if chain:
            self.top[symbol] = chain[-1]
            return chain[-1]
        return None

    ## Get the full resolution chain for a symbol.
    #  @param symbol The symbol to look up.
    #  @return Resolution chain list, or empty list.
    def get_chain(self, symbol):
        return self.chains.get(symbol, [])

    ## Add a symbol-to-source mapping and update chains.
    #
    #  Records the direct source, then recomputes the chain and top origin.
    #  @param symbol The symbol being defined.
    #  @param source The immediate source (module name, "local", etc.).
    def add(self, symbol, source):
        if not symbol or not source:
            return
        self.direct[symbol] = source
        chain = self.trace(symbol)
        self.chains[symbol] = chain
        if chain:
            last = chain[-1]
            self.top[symbol] = last if isinstance(last, str) else str(last)

    ## Snapshot direct/chains/top for branch analysis rollback.
    #  @return Tuple of (direct, chains, top) dict copies.
    def snapshot(self):
        return (dict(self.direct), dict(self.chains), dict(self.top))

    ## Restore direct/chains/top from a snapshot.
    #  @param state Tuple of (direct, chains, top) dicts.
    def restore(self, state):
        direct, chains, top = state
        self.direct = dict(direct)
        self.chains = dict(chains)
        self.top = dict(top)
