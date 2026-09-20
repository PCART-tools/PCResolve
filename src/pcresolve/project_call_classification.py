## @package pcresolve.project_call_classification
#  Project call-record classification and owner-candidate resolution.

import ast

from .builtin_ownership import _BUILTIN_CONTAINER_METHODS, _is_builtin
from .call_graph import ProjectCallGraph
from .classification import classify_confidence
from .ir import ClassificationResult, REASON_DIRECT_IMPORT
from .ownership_contracts import _match_result_owner, _is_verified_result_owner
from .sources import (
    CallResult, ContainerItem, ContainerIter, DerivedResult, InstanceMethod,
    PythonShape, SourceSet, SuperMethod, UnknownSource,
    is_structured_source, normalize_source, source_display,
)


_KEEP_FUNC_NAME = object()
_NO_ORIGIN_CANDIDATES = object()


## Project call-classification behavior mixed into ProjectAnalyzer.
class ProjectCallClassificationMixin:
    ## Downgrade an import-backed method owner after a visible monkey patch.
    #
    #  A patch on one imported class does not prove that every receiver from
    #  that library has the patched class. When the receiver has already been
    #  reduced to the library owner, the only sound primary is unknown.
    #  @param call_detail Single-file call record.
    #  @param tracer Analyzer for the current module.
    #  @param top_source Resolved import-backed owner.
    #  @return top_source or "unknown".
    def _apply_external_override_ambiguity(
            self, call_detail, tracer, top_source):
        if top_source in ("", None, "local", "python", "unknown"):
            return top_source
        func_name = call_detail.get("func_name", "")
        if "." not in func_name:
            return top_source
        method_name = func_name.rsplit(".", 1)[-1]
        patches = getattr(
            tracer, "external_method_overrides", {}).get(
                (top_source, method_name), [])
        if not patches:
            return top_source
        call_scope = call_detail.get("scope_name", "")
        call_line = call_detail.get("lineno", 0)
        for patch_scope, patch_line, _ in patches:
            visible = (
                patch_scope == ""
                or (
                    patch_scope == call_scope
                    and patch_line <= call_line
                )
            )
            if visible:
                return "unknown"
        return top_source

    ## Promote a chained local-call receiver to structured result evidence.
    #
    #  Single-file collection intentionally keeps ``make_value().method``
    #  conservative because the return object is resolved only after the
    #  project call graph is available.  Once the exact local edge is known,
    #  represent the receiver as a CallResult so the existing return-summary
    #  resolver can follow it.  This is limited to an unambiguous project
    #  call edge and never infers an external library from the method name.
    #  @param module Current caller module.
    #  @param call_detail Raw single-file call record.
    #  @param module_tracers All module analyzers.
    #  @return InstanceMethod receiver, or None when the edge is unresolved.
    def _promote_chained_local_call_receiver(
            self, module, call_detail, module_tracers):
        base = normalize_source(call_detail.get("base"))
        func_name = call_detail.get("func_name", "")
        if not isinstance(base, str) or not isinstance(func_name, str):
            return None
        marker = "()."
        if func_name.startswith(base + marker):
            inner_name, _, suffix = func_name.partition(marker)
        else:
            # The legacy base may be a resolved class name while func_name
            # retains the source receiver spelling.  Recover the inner call
            # from the recorded expression instead of requiring those two
            # representations to share a prefix.
            try:
                expression = ast.parse(
                    call_detail.get("api", ""), mode="eval").body
            except (SyntaxError, ValueError, TypeError):
                return None
            if (not isinstance(expression, ast.Call)
                    or not isinstance(expression.func, ast.Attribute)
                    or not isinstance(expression.func.value, ast.Call)):
                return None
            inner_name = ast.unparse(expression.func.value.func)
            suffix = expression.func.attr
        if not inner_name or not suffix:
            return None
        edges = [
            edge for edge in self.project_cg.modules.get(
                module, ProjectCallGraph()).edges
            if edge.caller.qualname == (
                call_detail.get("scope_name", "") or "<module>")
            and edge.call_lineno == call_detail.get("lineno", 0)
            and edge.call_col_offset == call_detail.get("col_offset", 0)
            and edge.callee_name == inner_name
        ]
        if len(edges) != 1:
            return None
        targets = self._local_edge_targets(edges[0], module, module_tracers)
        if len(targets) != 1:
            return None
        target = targets[0]
        result = CallResult(
            target.module + "." + target.qualname,
            display_name=inner_name,
            call_lineno=edges[0].call_lineno,
            call_col_offset=edges[0].call_col_offset,
            source_module=module,
        )
        return InstanceMethod(result, suffix.rsplit(".", 1)[-1])

    ## Collect all API calls across all modules and resolve their top-level origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def get_calls(self, module_tracers):
        self._call_searched_global = set()
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            for call_detail in tracer.api_calls:
                call_detail["file_path"] = file_path or ""
            self.all_calls[module] = [
                self._classified_call_record(
                    module, call_detail, tracer, module_tracers)
                for call_detail in tracer.api_calls
            ]
        for module, tracer in module_tracers.items():
            for record in self.all_calls.get(module, []):
                record["resolved_func"] = self._resolve_func_name(
                    record, module, tracer)
        self._call_searched_global = None

    ## Build one project-level call record without changing call order.
    def _classified_call_record(
            self, module, call_detail, tracer, module_tracers):
        call_detail, base = self._prepared_call_base(
            module, call_detail, tracer, module_tracers)
        if (call_detail.get("top") == "unknown"
                or isinstance(base, UnknownSource)):
            return self._record_with_classification(
                call_detail, base, "unknown", module, tracer,
                module_tracers)
        if call_detail.get("top") == "local":
            top_source = None
            if isinstance(base, str) or is_structured_source(base):
                top_source = self._base_top_source(
                    module, base, tracer, module_tracers)
            if top_source and top_source != "local":
                top_source = self._apply_external_override_ambiguity(
                    call_detail, tracer, top_source)
                return self._record_with_classification(
                    call_detail, base, top_source, module, tracer,
                    module_tracers)
            return self._record_with_classification(
                call_detail, base, "local", module, tracer,
                module_tracers)
        top_source = self._preserved_python_call_owner(call_detail, base)
        if top_source is None:
            top_source = self._base_top_source(
                module, base, tracer, module_tracers)
            top_source = self._apply_external_override_ambiguity(
                call_detail, tracer, top_source)
        return self._record_with_classification(
            call_detail, base, top_source, module, tracer, module_tracers)

    ## Apply chained-call promotion and comprehension tuple boundaries.
    #  @return Possibly copied call detail and its effective base source.
    def _prepared_call_base(
            self, module, call_detail, tracer, module_tracers):
        base = call_detail.get("base")
        promoted_receiver = self._promote_chained_local_call_receiver(
            module, call_detail, module_tracers)
        if (promoted_receiver is not None
                and not isinstance(base, UnknownSource)):
            base = promoted_receiver
        base_receiver = (
            base.receiver if isinstance(base, InstanceMethod) else base)
        is_unbound_comprehension = (
            call_detail.get("scope_name") == "<comprehension>"
            and call_detail.get("func_name", "").split(".", 1)[0]
            in getattr(tracer, "comprehension_targets", set())
            and isinstance(base_receiver, CallResult)
            and base_receiver.result_source is None
            and self._is_unbound_tuple_call_result(
                module, base_receiver, module_tracers)
        )
        if is_unbound_comprehension:
            base = UnknownSource("unresolved tuple element")
            call_detail = dict(call_detail)
            call_detail["top"] = "unknown"
        return call_detail, base

    ## Preserve explicit builtin receiver evidence from the single-file pass.
    #  @return "python" when preserved, otherwise None.
    def _preserved_python_call_owner(self, call_detail, base):
        call_kind = call_detail.get("receiver_container_kind")
        direct_builtin = (
            call_detail.get("top") == "python"
            and call_detail.get("direct_name_callee") == base
            and _is_builtin(base)
        )
        if ((call_kind is not None
             and call_detail.get("top") == "python")
                or direct_builtin):
            return "python"
        return None

    ## Attach one classification result to a copied call record.
    def _record_with_classification(
            self, call_detail, base, top_source, module, tracer,
            module_tracers):
        record = dict(call_detail)
        record["top"] = top_source
        classification = self.classify_source(
            base, top_source, module, tracer, module_tracers)
        record["reason"] = classification.reason
        record["alternatives"] = classification.alternatives
        record["confidence"] = classification.confidence
        return record

    ## Check whether a call result used in a comprehension is an unbound
    #  project-local tuple result.
    #  @param module Caller module.
    #  @param source CallResult used as the comprehension receiver.
    #  @param tracers Per-module analyzers.
    #  @return True when the tuple item position is not statically known.
    def _is_unbound_tuple_call_result(self, module, source, tracers):
        context = self._bounded_call_context(
            module, source.call_lineno, source.call_col_offset,
            tracers)
        if context is None:
            return False
        module_cg = self.project_cg.modules.get(context.target.module)
        summary = (
            module_cg.functions.get(context.target.qualname)
            if module_cg is not None else None)
        return summary is not None and self._is_tuple_return_source(
            summary.returns)

    ## Resolve the top-level source of a base symbol, preferring call_assign_funcs.
    #  @param module The current module.
    #  @param base The base symbol string.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name.
    def _base_top_source(self, module, base, tracer, module_tracers):
        if is_structured_source(base):
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, str)
                    and _is_verified_result_owner(base.receiver)):
                return base.receiver
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, CallResult)):
                result_owner = normalize_source(
                    base.receiver.result_source)
                if isinstance(result_owner, str) and result_owner:
                    return result_owner
                candidates = self._bounded_call_result_method_candidates(
                    module, base.receiver, base.method, module_tracers,
                    None, set(), None)
                candidate = self._bounded_candidates_top(candidates or [])
                if _is_verified_result_owner(candidate):
                    # A resolved owner is not a lexical symbol. Looking it
                    # up again can redirect it through a local star import.
                    return candidate
            structured = self._resolve_structured_source(module, base, module_tracers)
            if structured is not None:
                ## Explicit result_source carries an owner, not a symbol to
                # resolve again in module scope.  InstanceMethod receivers
                # cover assignments from function-local import chains.
                result = base
                if (isinstance(base, InstanceMethod)
                        and isinstance(base.receiver, CallResult)):
                    result = base.receiver
                if isinstance(result, CallResult):
                    rs = getattr(result, 'result_source', None)
                    if (isinstance(rs, str)
                            and rs not in ("local", "python", "unknown", "")):
                        return rs
                _, src_module, src_symbol = structured
                if src_symbol in ("local", "python", "unknown"):
                    return src_symbol
                if _is_verified_result_owner(src_symbol):
                    return src_symbol
                if (isinstance(base, InstanceMethod)
                        and base.parameter_scope
                        and isinstance(src_symbol, str)
                        and src_symbol):
                    return src_symbol
                top = self._top_source(src_module, src_symbol, module_tracers)
                # 1.0.5 P1: builtin container method on a receiver
                # whose container kind is known from tracer-final state.
                # This fallback only sees module-level legacy maps.
                # Function-local receiver kinds are captured at the call
                # site and preserved before this path is reached.
                if (top == "local"
                        and isinstance(base, InstanceMethod)
                        and base.receiver not in tracer.class_methods
                        and base.receiver in tracer.symbols.direct):
                    kind = getattr(tracer, "container_item_kinds", {}).get(base.receiver)
                    if kind is None:
                        kind = getattr(tracer, "container_kinds", {}).get(base.receiver)
                    if (kind is not None
                            and base.method in _BUILTIN_CONTAINER_METHODS.get(kind, frozenset())):
                        return "python"
                return top
            return "local"
        if isinstance(base, str) and '.' in base:
            prefix = base.split('.')[0]
            if prefix in self.global_symbols.get(module, {}):
                return self.global_symbols[module][prefix]
            return self._top_source(module, base, module_tracers)
        if isinstance(base, str):
            caf = tracer.call_assign_funcs.get(base)
            if caf:
                caf_first = caf.split('.')[0]
                top = self._top_source(module, caf_first, module_tracers)
                if top and top != 'local':
                    return top
        if base in self.global_symbols.get(module, {}):
            return self.global_symbols[module][base]
        return self._top_source(module, base, module_tracers)

    ## Check whether a symbol is a known local definition in this tracer.
    #  @param tracer Single-file analyzer.
    #  @param symbol Candidate symbol name.
    #  @return True if the symbol is a local function/method/class/param.
    def _is_known_local_symbol(self, tracer, symbol):
        if not isinstance(symbol, str):
            return False
        first = symbol.split(".")[0]
        if first in ("self", "cls"):
            return True
        if first in getattr(tracer, "local", set()):
            return True
        if first in getattr(tracer, "defined_functions", set()):
            return True
        if first in getattr(tracer, "class_methods", {}):
            return True
        for methods in getattr(tracer, "class_methods", {}).values():
            if first in methods:
                return True
        direct = normalize_source(tracer.symbols.direct.get(first))
        if direct == "local":
            return True
        return False

    ## Check whether a string base represents a direct import.
    #  @param tracer Single-file analyzer.
    #  @param base Candidate base name.
    #  @return True if base is an import alias or from-import symbol.
    def _is_direct_import_base(self, tracer, base):
        if not isinstance(base, str):
            return False
        first = base.split(".")[0]
        if first in getattr(tracer, "import_aliases", set()):
            return True
        if first in getattr(tracer, "import_from_symbols", {}):
            return True
        direct = normalize_source(tracer.symbols.direct.get(first))
        if isinstance(direct, str) and direct not in ("local", "python", "unknown"):
            return True
        return False

    ## Check whether a SymbolProvenance import is a direct external import.
    #
    #  True when the import source is a non-local module and the resolved
    #  top matches the source's top-level name.  Local re-exports
    #  (local_lib -> requests) are not direct external imports.
    #  @param base The import source value (e.g. "functools").
    #  @param top The resolved top library.
    #  @param module The module where the import occurs.
    #  @return True if this is a direct external import.
    def _is_direct_external_import(self, base, top, module):
        if not isinstance(base, str) or not top:
            return False
        first = base.split(".")[0]
        if self.is_local(first):
            return False
        if top == first:
            return True
        return False

    ## Converge argument candidates under the receiver-preserving ufunc rule.
    #  @param candidate_groups One candidate-owner list per ufunc argument.
    #  @return Result owner or "unknown".
    def _receiver_preserving_ufunc_owner(self, candidate_groups):
        owners = []
        for candidates in candidate_groups:
            unique = self._dedupe_list(
                candidate for candidate in candidates
                if candidate not in (None, ""))
            if len(unique) != 1:
                return "unknown"
            owners.append(unique[0])
        if any(owner in ("local", "unknown") for owner in owners):
            return "unknown"
        external = self._dedupe_list(
            owner for owner in owners if owner != "python")
        if not external:
            return "numpy"
        if len(external) == 1 and external[0] in ("numpy", "pandas"):
            return external[0]
        return "unknown"

    ## Converge exact operands for a local arithmetic return expression.
    #  @param candidate_groups One candidate-owner list per expression operand.
    #  @return Result owner or "unknown".
    def _bounded_expression_owner(self, candidate_groups):
        owners = []
        for candidates in candidate_groups:
            unique = self._dedupe_list(
                candidate for candidate in candidates
                if candidate not in (None, ""))
            if len(unique) != 1 or unique[0] == "unknown":
                return "unknown"
            owners.append(unique[0])
        external = self._dedupe_list(
            owner for owner in owners
            if owner not in ("local", "python"))
        if len(external) == 1 and all(
                owner in (external[0], "python") for owner in owners):
            return external[0]
        if owners and all(owner == "python" for owner in owners):
            return "python"
        if owners and all(owner == "local" for owner in owners):
            return "local"
        return "unknown"

    ## Collect all origin candidates from a source value.
    #  @param module Current module name.
    #  @param source Source value to expand.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param include_local Whether to include "local" in results.
    #  @return List of candidate top strings.
    def _origin_candidates(self, module, source, tracers, include_local=True,
                           _seen=None):
        if _seen is None:
            _seen = set()
        source = normalize_source(source)
        key = (module, type(source).__name__, source_display(source))
        if key in _seen:
            return ["unknown"]
        seen = set(_seen)
        seen.add(key)
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._origin_candidates(
                    module, item, tracers, include_local,
                    _seen=set(seen)))
            return self._dedupe_list(candidates)
        if isinstance(source, PythonShape):
            return ["python"]
        if isinstance(source, DerivedResult):
            return self._derived_origin_candidates(
                module, source, tracers, include_local, seen)
        if isinstance(source, UnknownSource):
            return ["unknown"]
        if isinstance(source, ContainerItem):
            candidates = self._container_item_origin_candidates(
                module, source, tracers, include_local, seen)
            if candidates is not _NO_ORIGIN_CANDIDATES:
                return candidates
        if isinstance(source, ContainerIter):
            resolved = self._resolve_container_iter(
                module, source.container, tracers)
            if resolved is None:
                return ["unknown"]
            _, candidates = resolved
            return self._dedupe_list(candidates) or ["unknown"]
        if (isinstance(source, InstanceMethod)
                and isinstance(
                    normalize_source(source.receiver), CallResult)):
            return self._origin_candidates(
                module, normalize_source(source.receiver), tracers,
                include_local, _seen=set(seen))
        if isinstance(source, CallResult):
            return self._call_result_origin_candidates(
                module, source, tracers, include_local, seen)
        if is_structured_source(source):
            resolved = self._resolve_structured_source(
                module, source, tracers, _seen=set(seen))
            if resolved is not None:
                _, source_module, source_symbol = resolved
                return self._origin_candidates(
                    source_module, source_symbol, tracers, include_local,
                    _seen=set(seen))
            return ["unknown"]
        if isinstance(source, str):
            top = self._top_source(
                module, source, tracers, _seen=set(seen))
            return [top] if top else []
        return ["unknown"]

    ## Resolve one derived source into owner candidates.
    def _derived_origin_candidates(
            self, module, source, tracers, include_local, seen):
        if source.kind == "iterator":
            return ["unknown"]
        if source.kind == "receiver_preserving_ufunc":
            candidate_groups = [
                self._argument_owner_candidates(module, item, tracers)
                for item in source.sources
            ]
            return [self._receiver_preserving_ufunc_owner(candidate_groups)]
        if source.kind == "method_result":
            return self._method_result_origin_candidates(
                module, source, tracers, seen)
        if source.kind == "expression":
            return self._expression_origin_candidates(
                module, source, tracers)
        candidates = []
        for item in source.sources:
            candidates.extend(self._origin_candidates(
                module, item, tracers, include_local,
                _seen=set(seen)))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve the verified owner contract of a derived method result.
    def _method_result_origin_candidates(self, module, source, tracers, seen):
        if len(source.sources) != 1:
            return ["unknown"]
        method_source = normalize_source(source.sources[0])
        if not isinstance(method_source, InstanceMethod):
            return ["unknown"]
        resolved = self._resolve_structured_source(
            module, method_source, tracers, _seen=set(seen))
        if resolved is None:
            return ["unknown"]
        _, receiver_module, receiver_symbol = resolved
        receiver_top = self._top_source(
            receiver_module, receiver_symbol, tracers,
            _seen=set(seen))
        if receiver_top == "python":
            return ["python"]
        result_owner = _match_result_owner(
            receiver_top, method_source.method)
        return [result_owner or "unknown"]

    ## Converge owner evidence across one expression's operands.
    def _expression_origin_candidates(self, module, source, tracers):
        operand_candidates = []
        numeric_scalars = True
        saw_local = False
        saw_unresolved = False
        for item in source.sources:
            shape = self._returned_python_shape(module, item, tracers)
            candidates = (
                ["python"] if shape is not None
                else self._argument_owner_candidates(module, item, tracers))
            saw_local = saw_local or "local" in candidates
            saw_unresolved = saw_unresolved or "unknown" in candidates
            concrete = self._dedupe_list([
                candidate for candidate in candidates
                if candidate not in (None, "", "unknown", "local")
            ])
            if len(concrete) != 1:
                if concrete:
                    return ["unknown"]
                saw_unresolved = True
                continue
            if concrete[0] == "python":
                numeric_scalars = numeric_scalars and (
                    shape is not None and shape.kind in (
                        "bool", "int", "float", "complex"))
            operand_candidates.append(concrete[0])
        external = set(operand_candidates) - {"python"}
        if (len(external) == 1 and "python" in operand_candidates
                and numeric_scalars and not saw_unresolved
                and not saw_local and source.attribute in (
                    "Add", "Sub", "Mult", "Div", "FloorDiv", "Mod",
                    "Pow", "Compare")):
            return [next(iter(external))]
        if (operand_candidates and not saw_unresolved and not saw_local
                and all(owner == operand_candidates[0]
                        for owner in operand_candidates)):
            return [operand_candidates[0]]
        if not operand_candidates and saw_local:
            return ["local"]
        return ["unknown"]

    ## Resolve a positional item selected from a local call result.
    #  @return Candidates or the module sentinel when generic dispatch applies.
    def _container_item_origin_candidates(
            self, module, source, tracers, include_local, seen):
        container = normalize_source(source.container)
        if (not isinstance(container, CallResult)
                or not isinstance(source.index, int)):
            return _NO_ORIGIN_CANDIDATES
        source_module = container.source_module or module
        candidates = self._bounded_call_result_item_candidates(
            source_module, container, source.index, tracers, _seen=seen)
        if candidates is not None:
            return candidates
        return self._origin_candidates(
            source_module, container, tracers, include_local,
            _seen=set(seen))

    ## Resolve owner candidates for one call-result source.
    def _call_result_origin_candidates(
            self, module, source, tracers, include_local, seen):
        source_module = source.source_module or module
        if source.result_source is not None:
            if (isinstance(source.result_source, str)
                    and source.result_source not in (
                        "", "local", "python", "unknown")):
                return [source.result_source]
            return self._origin_candidates(
                source_module, source.result_source, tracers,
                include_local, _seen=set(seen))
        bounded = self._bounded_call_result_candidates(
            module, source, tracers, _seen=set(seen))
        if bounded is not None:
            return bounded
        if self._local_class_from_source(module, source) is not None:
            return ["local"]
        callee = source.callee
        tracer = tracers.get(module)
        return_source = tracer.return_sources.get(callee) if tracer else None
        if return_source is not None:
            return self._return_source_origin_candidates(
                module, callee, source, return_source, tracers,
                include_local, seen)
        top = self._top_source(
            source_module, callee, tracers, _seen=set(seen))
        return [top] if top else []

    ## Resolve a local return summary and its exact call-site parameter.
    def _return_source_origin_candidates(
            self, module, callee, call_result, return_source, tracers,
            include_local, seen):
        candidates = self._origin_candidates(
            module, return_source, tracers, include_local,
            _seen=set(seen))
        clean = [candidate for candidate in candidates
                 if candidate not in ("", None, "unknown")]
        if clean:
            return clean
        call_line = getattr(call_result, "call_lineno", 0) or 0
        call_column = getattr(call_result, "call_col_offset", 0) or 0
        if not call_line:
            return candidates
        normalized = normalize_source(return_source)
        if isinstance(normalized, SourceSet):
            parameter_sources = [item for item in normalized.sources
                                 if isinstance(item, str)]
        else:
            parameter_sources = [return_source]
        for parameter_source in parameter_sources:
            argument = self._resolve_param_to_arg(
                module, callee, parameter_source, tracers,
                call_lineno=call_line, call_col_offset=call_column)
            if argument is None:
                continue
            more = self._origin_candidates(
                module, argument, tracers, include_local,
                _seen=set(seen))
            for candidate in more:
                if candidate not in candidates:
                    candidates.append(candidate)
        return candidates

    ## Deduplicate a list preserving order.
    #  @param items List of strings.
    #  @return Deduplicated list.
    @staticmethod
    def _dedupe_list(items):
        seen = set()
        out = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    ## Determine the classification reason for a resolved API call.
    #  @param base The call's base symbol or source.
    #  @param top The resolved top-level library.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @return Reason constant string.
    # ── classification helpers ───────────────────────────────────────────

    ## Determine confidence for a classification result.
    #
    #  Delegates to the standalone classify_confidence() in
    #  classification.py so the confidence rules live in one place.
    #  @param reason Classification reason.
    #  @param alternatives List of alternative top libraries.
    #  @return Confidence score (0.0-1.0).
    def _classify_confidence(self, reason, alternatives=None):
        return classify_confidence(reason, alternatives)

    ## Unified classification entry point for a resolved top library.
    #
    #  Delegates to ClassificationPipeline.classify() (Phase 8B).
    #  Kept as a thin wrapper so callers in get_calls() and
    #  _build_symbol_provenance() do not need to change.
    #  @param base The call's base symbol or source.
    #  @param top The resolved top-level library.
    #  @param module Current module name.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return ClassificationResult with library/reason/confidence/alternatives.
    def classify_source(self, base, top, module, tracer, module_tracers,
                        expand_origins=True, symbol=None, kind=""):
        if kind == "import" and self._is_direct_external_import(base, top, module):
            # Override: direct external imports always use DIRECT_IMPORT reason.
            result = self._pipeline.classify(
                base, top, module, tracer, module_tracers,
                expand_origins=expand_origins)
            return ClassificationResult(
                library=result.library,
                reason=REASON_DIRECT_IMPORT,
                confidence=classify_confidence(REASON_DIRECT_IMPORT),
                alternatives=result.alternatives,
                is_usage_library=result.is_usage_library)
        return self._pipeline.classify(
            base, top, module, tracer, module_tracers,
            expand_origins=expand_origins)

    ## Resolve the first segment of func_name to its fully qualified path.
    #  @param call_dict Dict with 'func_name' and other call data.
    #  @param module The module where the call occurs.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param _visited Set of already-visited first names (cycle detection).
    #  @return Resolved function path string.
    def _resolve_func_name(self, call_dict, module, tracer, _visited=None):
        func_name = call_dict.get("func_name", "")
        if not func_name:
            return func_name
        base = normalize_source(call_dict.get("base"))
        if isinstance(base, SuperMethod):
            return self._resolved_super_func_name(
                call_dict, func_name, base)
        parts = func_name.split(".")
        first = parts[0]
        visited = set() if _visited is None else _visited
        if first in visited:
            return func_name
        visited.add(first)
        replacement = self._func_name_replacement(
            call_dict, module, tracer, first, visited)
        if replacement is None or replacement is _KEEP_FUNC_NAME:
            return func_name
        rep_first = replacement.split(".")[0]
        if rep_first == "self" or (rep_first and rep_first != first):
            rep_global = self.global_symbols.get(module, {}).get(rep_first)
            if rep_global == "local":
                return func_name
        if len(parts) == 1:
            return replacement
        precise = self._precise_instance_method_func_name(
            call_dict, tracer)
        if precise is not None:
            return precise
        return replacement + "." + ".".join(parts[1:])

    ## Resolve a super-method display name without claiming local decorators.
    def _resolved_super_func_name(self, call_dict, func_name, base):
        base_path = call_dict.get("super_base_path")
        decorator_module = call_dict.get("super_decorator_module")
        decorator_parts = (
            decorator_module.split(".") if decorator_module else [])
        local_decorator = any(
            self.is_local(".".join(decorator_parts[:length]))
            for length in range(1, len(decorator_parts) + 1)
        )
        if (isinstance(base_path, str) and base_path
                and not self.is_local(base_path.split(".")[0])
                and not local_decorator):
            return base_path + "." + base.method
        return func_name

    ## Select an import, assignment, direct-symbol, or global replacement.
    #  @return Replacement string, None, or the keep-name sentinel.
    def _func_name_replacement(
            self, call_dict, module, tracer, first, visited):
        import_source = (
            call_dict["call_import_source"]
            if "call_import_source" in call_dict
            else tracer.import_from_symbols.get(first))
        if import_source:
            if not self.is_local(import_source.split(".")[0]):
                return import_source
            return _KEEP_FUNC_NAME

        assigned = self._call_assignment_func(call_dict, first, tracer)
        if assigned and not assigned.startswith(first + "."):
            resolved = self._resolve_func_name(
                {"func_name": assigned}, module, tracer, visited)
            if resolved and not resolved.startswith("self."):
                return resolved
        direct = tracer.symbols.direct.get(first)
        if isinstance(direct, str):
            if (direct == "local" or direct == "self"
                    or direct.startswith("self.")):
                return _KEEP_FUNC_NAME
            if "." not in direct:
                global_direct = self.global_symbols.get(
                    module, {}).get(direct)
                if global_direct not in (None, "local", "python"):
                    return global_direct
            return direct
        global_source = self.global_symbols.get(module, {}).get(first)
        if isinstance(global_source, str):
            if global_source in ("local", "python"):
                return _KEEP_FUNC_NAME
            return global_source
        if global_source is not None:
            return _KEEP_FUNC_NAME
        return None

    ## Read the call-time assignment snapshot or exact factory call source.
    def _call_assignment_func(self, call_dict, first, tracer):
        if "call_assign_func" in call_dict:
            assigned = call_dict["call_assign_func"]
        else:
            assigned = tracer.call_assign_funcs.get(first)
        if assigned:
            return assigned
        call_base = normalize_source(call_dict.get("base"))
        if not isinstance(call_base, CallResult):
            return assigned
        factory_callee = normalize_source(call_base.callee)
        if not isinstance(factory_callee, str):
            return assigned
        if call_base.display_name and "." in call_base.display_name:
            return call_base.display_name
        return factory_callee

    ## Resolve an InstanceMethod receiver through an exact from-import.
    def _precise_instance_method_func_name(self, call_dict, tracer):
        base = normalize_source(call_dict.get("base", ""))
        if not isinstance(base, InstanceMethod):
            return None
        receiver = base.receiver
        if (not isinstance(receiver, str)
                or receiver not in tracer.import_from_symbols):
            return None
        import_source = tracer.import_from_symbols[receiver]
        if self.is_local(import_source.split(".")[0]):
            return None
        return import_source + "." + base.method
