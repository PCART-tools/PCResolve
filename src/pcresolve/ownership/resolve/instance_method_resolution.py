## @package pcresolve.ownership.resolve.instance_method_resolution
#  Resolve ownership for structured instance-method sources.
#
#  The mixin owns receiver-specific resolution order while ProjectAnalyzer
#  supplies project indexes, recursive resolution, and import-origin evidence.
#  使用项目索引、递归解析和导入来源证据解析实例方法归属。

from pcresolve.ownership.builtin_ownership import _BUILTIN_CONTAINER_METHODS, _is_builtin
from pcresolve.ownership.ownership_contracts import _is_verified_result_owner
from pcresolve.ownership.sources import (
    CallResult, ContainerIter, DerivedResult, InstanceAttribute,
    InstanceMethod, ParameterSource, SourceSet, is_structured_source,
    normalize_source, source_display,
)


## Check a receiver's proven container kind from single-file analysis.
## 查询单文件分析已证明的接收者容器类型。
#
#  @param tracer Single-file analyzer.
#  @param receiver_name Variable name.
#  @return Container kind string or None.
def _receiver_container_kind(tracer, receiver_name):
    return getattr(tracer, "container_kinds", {}).get(receiver_name)


## Resolve InstanceMethod ownership through project-level provenance facts.
## 通过项目级来源事实解析 InstanceMethod 归属。
class InstanceMethodResolutionMixin:
    ## Resolve ownership for one structured instance-method source.
    ## 解析单个结构化实例方法来源的归属。
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
        direct = self._direct_instance_method_source(
            module, direct_source, a, b, tracer, tracers, _seen)
        if direct is not None:
            return direct

        # Check local class branches before interpreting a structured receiver.
        # 解释结构化接收者前先检查本地类分支。
        local_classes = []
        if isinstance(a, (CallResult, SourceSet)):
            local_resolution, local_classes = (
                self._local_class_instance_method_source(
                    module, a, b, tracers, _seen))
            if local_resolution is not None:
                return local_resolution
        if is_structured_source(a):
            return self._structured_instance_method_source(
                module, a, b, local_classes, tracers, _seen)
        if isinstance(a, str):
            homogeneous = self._homogeneous_instance_method_source(
                module, a, b, tracer, tracers, _seen)
            if homogeneous is not None:
                return homogeneous
        class_symbol = self._instance_method_class_symbol(a, tracer)
        receiver_top = self._resolve_receiver_object_top(
            module, a, tracer, tracers)
        if receiver_top:
            return (f"{a}.{b}", module, receiver_top)
        if not class_symbol:
            return self._unbound_instance_method_source(
                module, a, b, tracer, tracers)
        if class_symbol in tracer.class_methods:
            if b in tracer.class_methods[class_symbol]:
                return (f"{a}.{b}", module, "local")
            ext = self._resolve_local_method_to_external(
                module, class_symbol, b, a, tracer, tracers)
            if ext:
                return (f"{a}.{b}", module, ext)
        resolved = self._resolve_method_symbol(
            module, class_symbol, b, tracers, set())
        if not resolved:
            if (class_symbol != a and isinstance(a, str)
                    and a in tracer.symbols.direct):
                resolved = self._resolve_method_symbol(
                    module, a, b, tracers, set())
            if not resolved:
                return self._unresolved_instance_method_source(
                    module, a, b, class_symbol, tracer, tracers, _seen)
        src_module, src_symbol = resolved
        top = self._top_source(
            src_module, src_symbol, tracers, _seen=set(_seen))
        if top in ("local", "unknown", ""):
            cg_attr = self._lookup_cg_class_attr_source(
                module, class_symbol, b)
            if cg_attr is not None:
                cg_mod, cg_top = cg_attr
                return (f"{a}.{b}", cg_mod, cg_top)
        return (f"{a}.{b}", src_module, src_symbol)

    ## Resolve bounded and directly proven receiver sources first.
    ## 优先解析有界且已直接证明的接收者来源。
    #
    #  @param module Module containing the call.
    #  @param direct_source Structured method source.
    #  @param receiver Receiver source.
    #  @param method_name Method name.
    #  @param tracer Analyzer for the calling module.
    #  @param tracers Per-module analyzers.
    #  @param _seen Structured-source recursion guard.
    #  @return Resolved tuple or None when no direct rule applies.
    def _direct_instance_method_source(
            self, module, direct_source, receiver, method_name,
            tracer, tracers, _seen):
        display = f"{source_display(receiver)}.{method_name}"
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
                module, attribute_top)
        if (isinstance(direct_source, InstanceMethod)
                and direct_source.parameter_scope):
            parameter_top = self._resolve_parameter_method_top(
                module, direct_source, tracer, tracers,
                _seen=set(_seen))
            return (display, module, parameter_top)
        if isinstance(receiver, (ContainerIter, ParameterSource)):
            if (isinstance(receiver, ContainerIter)
                    or receiver.derived):
                candidates = self._argument_method_owner_candidates(
                    module, receiver, method_name, tracers,
                    _seen=set(_seen))
                return (display, module,
                        self._bounded_candidates_top(candidates))
        if (isinstance(direct_source, InstanceMethod)
                and isinstance(direct_source.receiver, DerivedResult)):
            if self._is_bounded_expression_source(direct_source.receiver):
                parameter_top = self._resolve_derived_expression_method_top(
                    module, direct_source.receiver, direct_source.method,
                    tracer, tracers)
                return (display, module, parameter_top)
            expression_top = self._resolve_expression_external_top(
                module, direct_source.receiver, tracers)
            if (expression_top != "unknown"
                    or self._has_expression_owner_evidence(
                        direct_source.receiver)):
                return (display, module, expression_top)
        if (isinstance(receiver, InstanceMethod)
                and isinstance(receiver.receiver, str)
                and _is_verified_result_owner(receiver.receiver)):
            return (display, module, receiver.receiver)
        return None

    ## Resolve local-class branches and unresolved method-return summaries.
    ## 解析本地类分支和未解析的方法返回摘要。
    #
    #  @param module Calling module.
    #  @param receiver Receiver source.
    #  @param method_name Method name.
    #  @param tracers Per-module analyzers.
    #  @param _seen Structured-source recursion guard.
    #  @return Pair of optional resolution and local class candidates.
    def _local_class_instance_method_source(
            self, module, receiver, method_name, tracers, _seen):
        local_classes = self._local_class_candidates(
            module, receiver, tracers, visited=set(_seen))
        branch_evidence = isinstance(receiver, CallResult)
        if isinstance(receiver, SourceSet):
            branch_evidence = bool(receiver.sources) and all(
                self._local_class_candidates(
                    module, item, tracers, visited=set(_seen))
                for item in receiver.sources)
        display = f"{source_display(receiver)}.{method_name}"
        if branch_evidence:
            method_classes = [
                identity for identity in local_classes
                if self._local_class_defines_method(
                    identity[0], identity[1], method_name, tracers)]
            if len(method_classes) == 1:
                return (display, module, "local"), local_classes
            # Multiple matching local classes do not identify a unique method owner.
            # 多个匹配的本地类不能确定唯一的方法归属。
            if len(method_classes) > 1:
                return (display, module, "unknown"), local_classes
        if (isinstance(receiver, CallResult)
                and isinstance(receiver.callee, str)
                and self._call_result_has_unresolved_method(
                    module, receiver.callee)):
            return (display, module, "unknown"), local_classes
        return None, local_classes

    ## Return whether a call-result summary contains unresolved method output.
    ## 判断调用结果摘要是否包含未解析的方法输出。
    #
    #  @param module Calling module.
    #  @param callee Callee name to locate.
    #  @return True if a matching summary contains an unresolved method result.
    def _call_result_has_unresolved_method(self, module, callee):
        for target_module, module_cg in self.project_cg.modules.items():
            prefix = target_module + "."
            if callee.startswith(prefix):
                qualname = callee[len(prefix):]
            elif target_module == module and callee in module_cg.functions:
                qualname = callee
            else:
                continue
            summary = module_cg.functions.get(qualname)
            if (summary is not None
                    and self._has_unresolved_method_result(summary.returns)):
                return True
        return False

    ## Resolve a structured receiver after bounded local-class checks.
    ## 在有界本地类检查后解析结构化接收者。
    #
    #  @param module Calling module.
    #  @param receiver Structured receiver source.
    #  @param method_name Method name.
    #  @param local_classes Previously discovered local class candidates.
    #  @param tracers Per-module analyzers.
    #  @param _seen Structured-source recursion guard.
    #  @return Display, module, and resolved or unknown owner tuple.
    def _structured_instance_method_source(
            self, module, receiver, method_name, local_classes,
            tracers, _seen):
        display = f"{source_display(receiver)}.{method_name}"
        resolved = self._resolve_structured_source(
            module, receiver, tracers, _seen=set(_seen))
        if resolved is None:
            return (display, module, "unknown")
        _, receiver_module, receiver_symbol = resolved
        explicit_owner = (
            receiver.result_source
            if isinstance(receiver, CallResult) else None)
        if (isinstance(explicit_owner, str)
                and explicit_owner not in (
                    "", "local", "python", "unknown")):
            receiver_top = explicit_owner
        else:
            receiver_top = self._top_source(
                receiver_module, receiver_symbol, tracers,
                _seen=set(_seen))
        if (receiver_top == "local"
                and isinstance(receiver, CallResult)
                and not local_classes):
            receiver_top = "unknown"
        if (receiver_top == "local"
                and isinstance(receiver, InstanceMethod)
                and isinstance(receiver.receiver, InstanceMethod)
                and receiver.receiver.parameter_scope):
            receiver_top = "unknown"
        return (display, receiver_module, receiver_top or "unknown")

    ## Resolve homogeneous mapping values after the full file visit.
    ## 完成文件遍历后解析同源映射值。
    #
    #  @param module Calling module.
    #  @param receiver Receiver name.
    #  @param method_name Method name.
    #  @param tracer Analyzer for the calling module.
    #  @param tracers Per-module analyzers.
    #  @param _seen Structured-source recursion guard.
    #  @return External owner tuple or None when not proven.
    def _homogeneous_instance_method_source(
            self, module, receiver, method_name, tracer, tracers, _seen):
        homogeneous = getattr(
            tracer, "homogeneous_container_value_sources", {}).get(receiver)
        if homogeneous is None:
            return None
        resolved = self._resolve_structured_source(
            module, homogeneous, tracers, _seen=set(_seen))
        if resolved is None:
            return None
        _, receiver_module, receiver_symbol = resolved
        receiver_top = self._top_source(
            receiver_module, receiver_symbol, tracers, _seen=set(_seen))
        if receiver_top in (None, "local", "python", "unknown", ""):
            return None
        return (f"{receiver}.{method_name}", receiver_module, receiver_top)

    ## Resolve the class identity stored for a receiver name.
    ## 解析接收者名称保存的类标识。
    #
    #  @param receiver Receiver name.
    #  @param tracer Analyzer containing its bindings.
    #  @return Stored class source or None when unavailable.
    def _instance_method_class_symbol(self, receiver, tracer):
        if receiver in tracer.import_from_symbols:
            return receiver
        class_symbol = tracer.symbols.direct.get(receiver)
        if (isinstance(class_symbol, tuple)
                and len(class_symbol) == 3
                and class_symbol[0] == "call_result"):
            class_symbol = class_symbol[1]
        class_symbol = normalize_source(class_symbol)
        if isinstance(class_symbol, CallResult):
            class_symbol = class_symbol.callee
        if receiver in tracer.class_methods and class_symbol == "local":
            return receiver
        return class_symbol

    ## Resolve a receiver without a known class identity.
    ## 解析缺少已知类标识的接收者。
    #
    #  @param module Calling module.
    #  @param receiver Receiver source.
    #  @param method_name Method name.
    #  @param tracer Analyzer for the calling module.
    #  @param tracers Per-module analyzers.
    #  @return Resolved tuple or None when no owner is established.
    def _unbound_instance_method_source(
            self, module, receiver, method_name, tracer, tracers):
        if isinstance(receiver, str) and _is_builtin(receiver):
            return (f"{receiver}.{method_name}", module, "python")
        if (isinstance(receiver, str)
                and self._has_import_origin(tracer, receiver)):
            return (f"{receiver}.{method_name}", module, receiver)
        receiver_chain = self.trace_symbol(
            module, receiver, tracers, set(), _direct_source="local")
        receiver_top = self.extract_final_source(receiver_chain)
        if receiver_top:
            return (f"{receiver}.{method_name}", module, receiver_top)
        return None

    ## Resolve conservative fallbacks when no method symbol is found.
    ## 找不到方法符号时解析保守回退结果。
    #
    #  @param module Calling module.
    #  @param receiver Receiver source.
    #  @param method_name Method name.
    #  @param class_symbol Candidate class source.
    #  @param tracer Analyzer for the calling module.
    #  @param tracers Per-module analyzers.
    #  @param _seen Structured-source recursion guard.
    #  @return Resolved tuple or None when no fallback is proven.
    def _unresolved_instance_method_source(
            self, module, receiver, method_name, class_symbol,
            tracer, tracers, _seen):
        class_direct = tracer.symbols.direct.get(class_symbol)
        if isinstance(class_direct, str) and self.is_local(class_direct):
            resolved = self._call_graph_attribute_method_source(
                module, receiver, method_name, class_symbol)
            return resolved or (f"{receiver}.{method_name}", module, "local")
        if class_direct == "local":
            external = self._resolve_local_method_to_external(
                module, receiver, method_name, receiver, tracer, tracers)
            if external:
                return (f"{receiver}.{method_name}", module, external)
            resolved = self._call_graph_attribute_method_source(
                module, receiver, method_name, class_symbol)
            return resolved or (f"{receiver}.{method_name}", module, "local")
        if isinstance(class_symbol, str) and "." in class_symbol:
            top = self._top_source(
                module, class_symbol, tracers, _seen=set(_seen))
            if top and top not in ("local", "python", "unknown", ""):
                return (f"{receiver}.{method_name}", module, top)
        kind = _receiver_container_kind(tracer, receiver)
        if (kind is not None
                and method_name in _BUILTIN_CONTAINER_METHODS.get(
                    kind, frozenset())
                and receiver in tracer.symbols.direct):
            return (f"{receiver}.{method_name}", module, "python")
        return None

    ## Resolve constructor/class attribute evidence from the project graph.
    ## 从项目调用关系中解析构造函数或类属性证据。
    #
    #  @param module Calling module.
    #  @param receiver Receiver source.
    #  @param method_name Method name.
    #  @param class_symbol Candidate class source.
    #  @return Resolved tuple or None when no attribute evidence exists.
    def _call_graph_attribute_method_source(
            self, module, receiver, method_name, class_symbol):
        call_graph_attr = self._lookup_cg_class_attr_source(
            module, class_symbol, method_name)
        if call_graph_attr is None:
            return None
        source_module, source_top = call_graph_attr
        return (f"{receiver}.{method_name}", source_module, source_top)
