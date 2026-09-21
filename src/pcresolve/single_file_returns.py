## @package pcresolve.single_file_returns
#  Collect return ownership and call-graph summaries during single-file analysis.

import ast

from .single_file_container_shapes import _container_kind
from .sources import (
    ContainerIter, DerivedResult, PythonShape, UnknownSource,
    make_source_set, normalize_source,
)


## Collect return summaries using SingleFileAnalyzer visitor state.
class SingleFileReturnMixin:
    ## Build a positional source summary for a tuple return expression.
    #
    #  @param value Tuple AST node.
    #  @return DerivedResult with one source per tuple element, or None.
    def _tuple_return_source(self, value):
        if not isinstance(value, ast.Tuple):
            return None
        elements = []
        for element in value.elts:
            source = self.trace_source(element)
            if source is None:
                return None
            elements.append(normalize_source(source))
        return DerivedResult("tuple", tuple(elements))

    ## Check whether a statement sequence definitely cannot fall through.
    #
    #  @param statements Function or branch statements.
    #  @return True for a proven return/raise on every path.
    def _block_exits(self, statements):
        for statement in statements:
            if isinstance(statement, (ast.Return, ast.Raise)):
                return True
            if (isinstance(statement, ast.If)
                    and self._block_exits(statement.body)
                    and self._block_exits(statement.orelse)):
                return True
        return False

    ## Preserve arithmetic return operands at their evaluation point.
    #
    #  @param node Return expression or one of its operands.
    #  @return Structured value source, including unsupported operands.
    def _return_expression_source(self, node):
        if isinstance(node, ast.BinOp):
            return DerivedResult("expression", (
                self._return_expression_source(node.left),
                self._return_expression_source(node.right)),
                type(node.op).__name__)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return PythonShape("bool")
            return DerivedResult("expression", (
                self._return_expression_source(node.operand),),
                type(node.op).__name__)
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is None:
                return UnknownSource("unbound return operand")
        shape = self._expression_python_shape(node)
        if shape is not None:
            if shape.kind == "NoneType":
                return UnknownSource("non-arithmetic None operand")
            return shape
        dependency = self._parameter_dependency_source(
            node, expression_context=True)
        return (dependency or self._call_edge_argument_source(node)
                or UnknownSource("unresolved return operand"))

    ## Visit a Return node and record return-value flow for the function.
    #
    #  @param node The Return AST node.
    def visit_Return(self, node):
        if node.value is not None:
            self._mapping_facts.escape(node.value)
        self._record_return_element_sources(node)
        legacy_source = self._record_legacy_return_source(node)
        self._record_call_graph_return_value(node, legacy_source)
        self.generic_visit(node)

    ## Record iterable element alternatives for one return statement.
    def _record_return_element_sources(self, node):
        if not self._caller_stack:
            return
        return_key = self._caller_stack[-1].qualname
        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            elements = [
                self._expression_python_shape(element)
                or self._call_edge_argument_source(element)
                or UnknownSource("unresolved returned element")
                for element in node.value.elts
            ]
        else:
            returned = None
            if node.value is not None:
                returned = (self._expression_python_shape(node.value)
                            or self._call_edge_argument_source(node.value))
            elements = [ContainerIter(returned) if returned is not None
                        else UnknownSource("unresolved returned iterable")]
        self.return_element_sources.setdefault(return_key, []).extend(
            elements)

    ## Record the legacy ownership return summary and symbol provenance.
    def _record_legacy_return_source(self, node):
        if not self._func_stack or node.value is None:
            return None
        func_name = self._func_stack[-1]
        source, tuple_source = self._legacy_return_expression_source(node)
        if not source:
            return None
        resolved_source = self._resolved_return_binding_source(
            source, node.value, func_name)
        return_key = self._return_summary_key(func_name)
        call_graph_source = tuple_source or resolved_source
        self._merge_legacy_return_source(
            return_key, resolved_source, tuple_source is not None)
        self._add_symbol_ref(
            func_name + ".return", source, "return", node)
        return call_graph_source

    ## Resolve the source expression used by the ownership return summary.
    def _legacy_return_expression_source(self, node):
        source = None
        if isinstance(node.value, (ast.BinOp, ast.UnaryOp)):
            source = self._return_expression_source(node.value)
        elif (isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Attribute)):
            source = self._parameter_dependency_source(
                node.value, expression_context=True)
        tuple_source = self._tuple_return_source(node.value)
        result_kind = _container_kind(node.value)
        if tuple_source is not None:
            source = tuple_source
        elif source is not None:
            pass
        elif result_kind is not None and result_kind != "tuple":
            source = "python"
        elif (isinstance(node.value, ast.Name)
              and self._lookup_container_kind(node.value.id) is not None):
            source = "python"
        else:
            source = self.trace_source(node.value)
        return source, tuple_source

    ## Dereference a local binding while preserving parameter passthrough.
    def _resolved_return_binding_source(self, source, value, func_name):
        if isinstance(source, str) and source in self.symbols.direct:
            bound_source = self.symbols.direct[source]
            resolved = bound_source if bound_source else source
        else:
            resolved = source
        if (source == "local" and isinstance(value, ast.Name)
                and value.id in self.function_params.get(func_name, [])):
            return value.id
        return resolved

    ## Build the class-qualified key used by return summaries.
    def _return_summary_key(self, func_name):
        if self._class_stack:
            return self._class_stack[-1] + "." + func_name
        return func_name

    ## Merge one resolved source into tuple-aware legacy summary maps.
    def _merge_legacy_return_source(
            self, return_key, source, is_tuple_source):
        if is_tuple_source:
            old_source = self.call_graph_return_sources.get(return_key)
            self.call_graph_return_sources[return_key] = make_source_set(
                [old_source, source] if old_source else [source],
                origin="return")
            return
        old_source = self.return_sources.get(return_key)
        self.return_sources[return_key] = make_source_set(
            [old_source, source] if old_source else [source],
            origin="return")
        if return_key in self.call_graph_return_sources:
            old_call_graph = self.call_graph_return_sources[return_key]
            self.call_graph_return_sources[return_key] = make_source_set(
                [old_call_graph, source], origin="return")

    ## Record the protocol-oriented return value used by the call graph.
    def _record_call_graph_return_value(self, node, legacy_source):
        if not self._caller_stack:
            return
        source = self._call_graph_return_value_source(node, legacy_source)
        return_key = self._caller_stack[-1].qualname
        old_source = self.call_graph_return_values.get(return_key)
        self.call_graph_return_values[return_key] = make_source_set(
            [old_source, source] if old_source else [source],
            origin="return")

    ## Resolve one protocol-oriented return branch source.
    def _call_graph_return_value_source(self, node, legacy_source):
        if node.value is None:
            return PythonShape("NoneType")
        shape = self._call_edge_protocol_source(node.value)
        if isinstance(node.value, ast.Tuple):
            source = DerivedResult("tuple", tuple(
                self._call_edge_protocol_source(element)
                or self._call_edge_argument_source(element)
                or UnknownSource("unresolved returned tuple item")
                for element in node.value.elts))
        elif shape is not None:
            source = shape
        elif isinstance(node.value, (ast.Name, ast.Subscript)):
            source = self._call_edge_argument_source(node.value)
        else:
            source = legacy_source
        return source or UnknownSource("unresolved return branch")
