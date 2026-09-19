## @package pcresolve.instance_method_resolution
#  Resolve ownership for structured instance-method sources.
#
#  The mixin owns receiver-specific resolution order while ProjectAnalyzer
#  supplies project indexes, recursive resolution, and import-origin evidence.

from .builtin_ownership import _BUILTIN_CONTAINER_METHODS, _is_builtin
from .ownership_contracts import _is_verified_result_owner
from .sources import (
    CallResult, ContainerIter, DerivedResult, InstanceAttribute,
    InstanceMethod, ParameterSource, SourceSet, is_structured_source,
    normalize_source, source_display,
)


## Check a receiver's proven container kind from single-file analysis.
#  @param tracer Single-file analyzer.
#  @param receiver_name Variable name.
#  @return Container kind string or None.
def _receiver_container_kind(tracer, receiver_name):
    return getattr(tracer, "container_kinds", {}).get(receiver_name)


## Resolve InstanceMethod ownership through project-level provenance facts.
class InstanceMethodResolutionMixin:
    ## Resolve ownership for one structured instance-method source.
    #
    #  @param module Module containing the method call.
    #  @param direct_source Full InstanceMethod source and receiver metadata.
    #  @param a Receiver source extracted by the structured-source dispatcher.
    #  @param b Method name extracted by the structured-source dispatcher.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Structured-source recursion guard.
    #  @return Resolved display, module, and owner tuple, or None.
    def _resolve_instance_method_source(self, module, direct_source, a, b,
                                        tracers, _seen):
        tracer = tracers.get(module)
        if not tracer:
            return None
        if (isinstance(direct_source, InstanceMethod)
                and isinstance(
                    direct_source.receiver, InstanceAttribute)):
            attribute_top = self._resolve_instance_attribute_method_top(
                module, direct_source.receiver, direct_source.method,
                tracers, _seen=set(_seen))
            return (
                "%s.%s" % (
                    source_display(direct_source.receiver),
                    direct_source.method),
                module,
                attribute_top,
            )
        if (isinstance(direct_source, InstanceMethod)
                and direct_source.parameter_scope):
            parameter_top = self._resolve_parameter_method_top(
                module, direct_source, tracer, tracers,
                _seen=set(_seen))
            return (
                f"{source_display(a)}.{b}",
                module,
                parameter_top,
            )
        if isinstance(a, ContainerIter):
            candidates = self._argument_method_owner_candidates(
                module, a, b, tracers, _seen=set(_seen))
            return (f"{source_display(a)}.{b}", module,
                    self._bounded_candidates_top(candidates))
        if isinstance(a, ParameterSource) and a.derived:
            candidates = self._argument_method_owner_candidates(
                module, a, b, tracers, _seen=set(_seen))
            return (f"{source_display(a)}.{b}", module,
                    self._bounded_candidates_top(candidates))
        if (isinstance(direct_source, InstanceMethod)
                and isinstance(direct_source.receiver, DerivedResult)
                and self._is_bounded_expression_source(
                    direct_source.receiver)):
            parameter_top = self._resolve_derived_expression_method_top(
                module, direct_source.receiver, direct_source.method,
                tracer, tracers)
            return (
                f"{source_display(a)}.{b}",
                module,
                parameter_top,
            )
        if (isinstance(direct_source, InstanceMethod)
                and isinstance(direct_source.receiver, DerivedResult)):
            expression_top = self._resolve_expression_external_top(
                module, direct_source.receiver, tracers)
            if (expression_top != "unknown"
                    or self._has_expression_owner_evidence(
                        direct_source.receiver)):
                return (
                    f"{source_display(a)}.{b}",
                    module,
                    expression_top,
                )
        if (isinstance(a, InstanceMethod)
                and isinstance(a.receiver, str)
                and _is_verified_result_owner(a.receiver)):
            return (
                f"{source_display(a)}.{b}",
                module,
                a.receiver,
            )
        if isinstance(a, (CallResult, SourceSet)):
            local_classes = self._local_class_candidates(
                module, a, tracers, visited=set(_seen))
            branch_evidence = isinstance(a, CallResult)
            if isinstance(a, SourceSet):
                branch_evidence = bool(a.sources) and all(
                    self._local_class_candidates(
                        module, item, tracers, visited=set(_seen))
                    for item in a.sources
                )
            if branch_evidence:
                local_method_classes = [
                    identity for identity in local_classes
                    if self._local_class_defines_method(
                        identity[0], identity[1], b, tracers)
                ]
                if len(local_method_classes) == 1:
                    return (f"{source_display(a)}.{b}", module, "local")
                if len(local_method_classes) > 1:
                    return (f"{source_display(a)}.{b}", module, "unknown")
            if isinstance(a, CallResult) and isinstance(a.callee, str):
                for target_module, module_cg in self.project_cg.modules.items():
                    prefix = target_module + "."
                    if a.callee.startswith(prefix):
                        qualname = a.callee[len(prefix):]
                    elif (target_module == module
                          and a.callee in module_cg.functions):
                        qualname = a.callee
                    else:
                        continue
                    summary = module_cg.functions.get(qualname)
                    if (summary is not None
                            and self._has_unresolved_method_result(
                                summary.returns)):
                        return (
                            f"{source_display(a)}.{b}",
                            module,
                            "unknown",
                        )
        if is_structured_source(a):
            receiver = self._resolve_structured_source(
                module, a, tracers, _seen=set(_seen))
            if receiver is None:
                return (f"{source_display(a)}.{b}", module, "unknown")
            _, receiver_module, receiver_symbol = receiver
            explicit_owner = (
                a.result_source if isinstance(a, CallResult) else None)
            if (isinstance(explicit_owner, str)
                    and explicit_owner not in (
                        "", "local", "python", "unknown")):
                receiver_top = explicit_owner
            else:
                receiver_top = self._top_source(
                    receiver_module, receiver_symbol, tracers,
                    _seen=set(_seen))
            # A local callable identity does not prove the type of its
            # returned object.  Preserve ``local`` only when the call
            # result resolves to one project-local class that actually
            # defines this method; otherwise the receiver owner is
            # unresolved rather than project-local.
            if (receiver_top == "local"
                    and isinstance(a, CallResult)
                    and not local_classes):
                receiver_top = "unknown"
            if (receiver_top == "local"
                    and isinstance(a, InstanceMethod)
                    and isinstance(a.receiver, InstanceMethod)
                    and a.receiver.parameter_scope):
                receiver_top = "unknown"
            if not receiver_top:
                receiver_top = "unknown"
            return (f"{source_display(a)}.{b}",
                    receiver_module, receiver_top)
        # A dynamically indexed homogeneous mapping can be resolved only
        # after the complete file has been visited.  This post-pass keeps
        # the evidence generic: every statically resolved value must
        # converge to one owner before it is used for the method call.
        if isinstance(a, str):
            homogeneous = getattr(
                tracer, "homogeneous_container_value_sources", {}
            ).get(a)
            if homogeneous is not None:
                resolved = self._resolve_structured_source(
                    module, homogeneous, tracers, _seen=set(_seen))
                if resolved is not None:
                    _, receiver_module, receiver_symbol = resolved
                    receiver_top = self._top_source(
                        receiver_module, receiver_symbol, tracers,
                        _seen=set(_seen))
                    if receiver_top not in (None, "local", "python", "unknown", ""):
                        return (f"{a}.{b}", receiver_module, receiver_top)
        if a in tracer.import_from_symbols:
            class_symbol = a
        else:
            class_symbol = tracer.symbols.direct.get(a)
            if (isinstance(class_symbol, tuple)
                    and len(class_symbol) == 3
                    and class_symbol[0] == "call_result"):
                class_symbol = class_symbol[1]
            class_symbol = normalize_source(class_symbol)
            if isinstance(class_symbol, CallResult):
                class_symbol = class_symbol.callee
            if a in tracer.class_methods and class_symbol == "local":
                class_symbol = a
        # 1.0.5 P1: unified receiver object ownership.
        receiver_top = self._resolve_receiver_object_top(
            module, a, tracer, tracers)
        if receiver_top:
            return (f"{a}.{b}", module, receiver_top)
        if not class_symbol:
            if isinstance(a, str) and _is_builtin(a):
                return (f"{a}.{b}", module, "python")
            if isinstance(a, str) and self._has_import_origin(tracer, a):
                return (f"{a}.{b}", module, a)
            # No factory top: trace through parameter sources
            # using a hardcoded "local" starting point.
            # Must NOT use call_assign_funcs — those carry
            # file-level final state that may include the
            # current call itself (e.g. s = s.strip()).
            receiver_chain = self.trace_symbol(
                module, a, tracers, set(), _direct_source="local")
            receiver_top = self.extract_final_source(receiver_chain)
            if receiver_top:
                return (f"{a}.{b}", module, receiver_top)
            return None
        # P0: if the method is explicitly defined in a local class,
        # preserve its primary identity as local.  The method body
        # may call library APIs internally, but the callable itself
        # is project-local.
        if class_symbol in tracer.class_methods:
            if b in tracer.class_methods[class_symbol]:
                return (f"{a}.{b}", module, "local")
            ext = self._resolve_local_method_to_external(
                module, class_symbol, b, a, tracer, tracers)
            if ext:
                return (f"{a}.{b}", module, ext)
        resolved = self._resolve_method_symbol(module, class_symbol, b, tracers, set())
        if not resolved:
            if class_symbol != a and isinstance(a, str) and a in tracer.symbols.direct:
                resolved = self._resolve_method_symbol(module, a, b, tracers, set())
            if not resolved:
                class_direct = tracer.symbols.direct.get(class_symbol)
                if isinstance(class_direct, str) and self.is_local(class_direct):
                    cg_attr = self._lookup_cg_class_attr_source(module, class_symbol, b)
                    if cg_attr is not None:
                        cg_mod, cg_top = cg_attr
                        return (f"{a}.{b}", cg_mod, cg_top)
                    return (f"{a}.{b}", module, "local")
                if class_direct == "local":
                    ext = self._resolve_local_method_to_external(
                        module, a, b, a, tracer, tracers)
                    if ext:
                        return (f"{a}.{b}", module, ext)
                    cg_attr = self._lookup_cg_class_attr_source(module, class_symbol, b)
                    if cg_attr is not None:
                        cg_mod, cg_top = cg_attr
                        return (f"{a}.{b}", cg_mod, cg_top)
                    return (f"{a}.{b}", module, "local")
                if isinstance(class_symbol, str) and '.' in class_symbol:
                    top = self._top_source(
                        module, class_symbol, tracers, _seen=set(_seen))
                    if top and top not in ("local", "python", "unknown", ""):
                        return (f"{a}.{b}", module, top)
                # 1.0.5 P1: builtin container method on receiver
                # whose container kind is known from the tracer.
                # This fallback only sees module-level legacy maps.
                # Function-local receiver kinds are carried by the
                # call-site snapshot from single_file.
                kind = _receiver_container_kind(tracer, a)
                if (kind is not None
                        and b in _BUILTIN_CONTAINER_METHODS.get(kind, frozenset())
                        and a in tracer.symbols.direct):
                    return (f"{a}.{b}", module, "python")
                return None
        src_module, src_symbol = resolved
        ## 7B-full PR3: if the resolved method is local, try constructor attrs.
        top = self._top_source(
            src_module, src_symbol, tracers, _seen=set(_seen))
        if top in ("local", "unknown", ""):
            cg_attr = self._lookup_cg_class_attr_source(
                module, class_symbol, b)
            if cg_attr is not None:
                cg_mod, cg_top = cg_attr
                return (f"{a}.{b}", cg_mod, cg_top)
        return (f"{a}.{b}", src_module, src_symbol)
