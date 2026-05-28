## @package pcresolve.source_resolution
#  SourceSet primary convergence resolver.
#
#  Extracted from cross_file.ProjectAnalyzer to keep
#  _resolve_structured_source() and _top_source() from
#  tangling with SourceSet-resolution internals.
#
#  The class receives callbacks for the bits that still live
#  on ProjectAnalyzer so we avoid a circular import.

from pcresolve.sources import (normalize_source, CallResult,
                               is_structured_source)


## Resolves a SourceSet to a primary top-library candidate.
#
#  Uses origin-aware rules:
#  - "return": accepts local + single third-party convergence.
#  - "dict_lookup": strict — no local, no unknown, single third-party.
#  - default (no origin): same strict rules as dict_lookup.
#
#  Callbacks are injected so this module does not import ProjectAnalyzer.
class SourceSetResolver:
    ## @param top_source_cb fn(module, symbol, tracers) -> str|None
    ## @param cg_return_cb  fn(module, callee) -> str|None
    ## @param known_local_cb fn(tracer, symbol) -> bool
    ## @param resolve_structured_cb fn(module, source, tracers) -> tuple|None
    ## @param dedupe_cb fn(items) -> list
    def __init__(self, top_source_cb, cg_return_cb, known_local_cb,
                 resolve_structured_cb, dedupe_cb):
        self._top_source = top_source_cb
        self._lookup_cg_return_source = cg_return_cb
        self._is_known_local = known_local_cb
        self._resolve_structured_source = resolve_structured_cb
        self._dedupe_list = dedupe_cb

    # ── public API ──────────────────────────────────────────────────────

    ## Resolve a SourceSet to a primary top library, or None.
    #
    #  @param module   Current module name.
    #  @param sourceset SourceSet to resolve.
    #  @param tracers  Dict module_name -> SingleFileAnalyzer.
    #  @param _seen    Internal cycle-detection set.
    #  @return Top library string or None.
    def resolve_primary(self, module, sourceset, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        tops, has_local, has_unknown = self._collect_tops(
            module, sourceset, tracers, _seen=_seen)
        origin = getattr(sourceset, "origin", "")

        if origin == "dict_lookup":
            if len(tops) == 1 and not has_local and not has_unknown:
                return tops[0]
            return None

        if origin == "return":
            if len(tops) == 1 and not has_unknown:
                return tops[0]
            return None

        ## Default conservative: no local/unknown, single third-party.
        if len(tops) == 1 and not has_local and not has_unknown:
            return tops[0]
        return None

    # ── internal helpers ────────────────────────────────────────────────

    ## Collect third-party top candidates and local/unknown flags
    #  from every source inside a SourceSet.
    def _collect_tops(self, module, sourceset, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        tops = []
        has_local = False
        has_unknown = False
        for src in sourceset.sources:
            top = self._to_top_candidate(module, src, tracers, _seen=_seen)
            if top in ("", None, "unknown"):
                has_unknown = True
            elif top in ("local", "python"):
                has_local = True
            else:
                tops.append(top)
        return self._dedupe_list(tops), has_local, has_unknown

    ## Resolve a single source to its top-library candidate.
    #
    #  CallResult resolution is restricted to import-backed callees
    #  to avoid recursive SourceSet loops: a local symbol whose
    #  direct binding is itself a SourceSet would re-enter
    #  convergence resolution and overflow the stack.
    def _to_top_candidate(self, module, source, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        source = normalize_source(source)
        if isinstance(source, str):
            key = (module, "str", source)
            if key in _seen:
                return None
            _seen.add(key)
            cg = self._lookup_cg_return_source(module, source)
            if cg:
                return self._top_source(module, cg, tracers) or cg
            return self._top_source(module, source, tracers)
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            key = (module, "cr", source.callee)
            if key in _seen:
                return None
            _seen.add(key)
            cg = self._lookup_cg_return_source(module, source.callee)
            if cg:
                return self._top_source(module, cg, tracers) or cg
            tracer = tracers.get(module)
            if tracer:
                first = source.callee.split(".")[0]
                if (first in getattr(tracer, "import_aliases", set()) or
                        first in getattr(tracer, "import_from_symbols", {})):
                    return self._top_source(module, source.callee, tracers)
                if self._is_known_local(tracer, source.callee):
                    return "local"
            return None
        if is_structured_source(source):
            resolved = self._resolve_structured_source(
                module, source, tracers)
            if resolved:
                _, src_module, src_symbol = resolved
                return self._top_source(src_module, src_symbol, tracers)
        return None
