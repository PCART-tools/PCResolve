## @package pcresolve.symbol_table
#  Provide per-symbol chain tracking from definition site to ultimate origin.
#
#  The SymbolTable class records direct symbol-to-source mappings and
#  recursively traces each symbol through aliases, assignments, and imports
#  to determine its top-level origin library.

import builtins


## Tracks symbol definitions and resolves each to its top-level source.
#
#  Maintains three data structures:
#  - direct: immediate source of each symbol (module name, "local", etc.)
#  - chains: full resolution chain from symbol to origin
#  - top: cached top-level origin for each symbol
class SymbolTable:
    ## Initialize an empty symbol table.
    def __init__(self):
        self.direct = {}
        self.top = {}
        self.chains = {}

    ## Recursively trace a symbol to build its resolution chain.
    #
    #  Follows the direct-source mapping until a terminal symbol is reached.
    #  @param symbol The symbol to trace.
    #  @param visited Set of already-visited symbols to detect cycles.
    #  @return Ordered list forming the resolution chain.
    def trace(self, symbol, visited=None):
        if visited is None:
            visited = set()
        if symbol in visited:
            return []
        visited.add(symbol)
        if symbol not in self.direct:
            return [symbol]
        source = self.direct[symbol]
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
            self.top[symbol] = chain[-1]
