## @package pcresolve.single_file_parameter_dependency
#  Parameter-derived expression evidence for single-file ownership analysis.

import ast

from .sources import (
    CallResult, ContainerItem, DerivedResult, InstanceAttribute,
    ParameterSource, UnknownSource, normalize_source,
)


## Parameter-dependency source behavior mixed into SingleFileAnalyzer.
class SingleFileParameterDependencyMixin:
    ## Preserve whether an assignment value has unresolved parameter origin.
    #  @param node Assignment value expression.
    #  @return ParameterSource, DerivedResult, UnknownSource, "local", or
    #  None.
    def _parameter_dependency_source(self, node, expression_context=False):
        if isinstance(node, ast.Name):
            return self._name_parameter_dependency(node, expression_context)
        if isinstance(node, ast.Attribute):
            return self._attribute_parameter_dependency(
                node, expression_context)
        if isinstance(node, ast.Subscript):
            return self._subscript_parameter_dependency(
                node, expression_context)
        if isinstance(node, ast.UnaryOp):
            dependency = self._parameter_dependency_source(
                node.operand, expression_context=expression_context)
            if dependency is not None:
                return UnknownSource(
                    "unresolved parameter-derived expression")
            return None
        if isinstance(node, ast.BinOp):
            return self._binary_parameter_dependency(node)
        if isinstance(node, ast.Compare):
            return self._compare_parameter_dependency(node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return self._call_parameter_dependency(node)
        return None

    ## Resolve a name binding that carries parameter-origin evidence.
    def _name_parameter_dependency(self, node, expression_context):
        if not self._caller_stack:
            return None
        binding = self.current_scope().lookup(
            node.id, skip_parent_classes=True)
        if binding is None:
            return None
        existing = normalize_source(binding.source)
        if isinstance(existing, (
                ParameterSource, UnknownSource, DerivedResult)):
            return existing
        if expression_context and isinstance(existing, ContainerItem):
            return UnknownSource("unresolved container-item expression")
        if (expression_context
                and isinstance(existing, CallResult)
                and existing.result_source is None):
            callee = existing.callee
            callee_root = (
                callee.split(".", 1)[0]
                if isinstance(callee, str) else "")
            imported = (
                callee_root in self.import_aliases
                or callee_root in self.import_from_symbols
                or (callee_root in self.symbols.direct
                    and self.symbols.direct.get(callee_root)
                    not in (None, "local", "python", "unknown")))
            if imported:
                return UnknownSource(
                    "unresolved call-result expression")
            return None
        if binding.binding_kind != "parameter":
            return None
        return ParameterSource(
            self._caller_stack[-1].qualname, node.id)

    ## Extend parameter provenance through one attribute access.
    def _attribute_parameter_dependency(self, node, expression_context):
        if (expression_context
                and isinstance(node.value, ast.Name)
                and node.value.id in ("self", "cls")):
            return self._instance_attribute_dependency(node)
        dependency = self._parameter_dependency_source(
            node.value, expression_context=expression_context)
        if isinstance(dependency, ParameterSource):
            return ParameterSource(
                dependency.scope,
                dependency.name,
                derived=dependency.derived,
                attributes=dependency.attributes + (node.attr,),
                derived_operation=dependency.derived_operation,
            )
        if isinstance(dependency, UnknownSource):
            return dependency
        return None

    ## Resolve self/cls field evidence used by an expression.
    def _instance_attribute_dependency(self, node):
        attr_name = self._attribute_name(node)
        existing = None
        if self._class_stack and attr_name:
            existing = self.instance_attrs.get(
                (self._class_stack[-1], attr_name))
        existing = normalize_source(existing)
        if existing is not None:
            if isinstance(existing, (
                    ParameterSource, UnknownSource, DerivedResult)):
                return existing
            return None
        scope_name = (
            self._caller_stack[-1].qualname
            if self._caller_stack else "")
        if not self._class_stack:
            return "local"
        return InstanceAttribute(
            self._class_stack[-1], attr_name, scope_name)

    ## Extend parameter provenance through one subscript or slice.
    def _subscript_parameter_dependency(self, node, expression_context):
        dependency = self._parameter_dependency_source(
            node.value, expression_context=expression_context)
        if isinstance(dependency, ParameterSource):
            return ParameterSource(
                dependency.scope,
                dependency.name,
                derived=True,
                attributes=dependency.attributes,
                derived_operation=(
                    "slice" if isinstance(node.slice, ast.Slice)
                    else "item"),
            )
        if isinstance(dependency, UnknownSource):
            return dependency
        return None

    ## Preserve dependencies from both operands of a binary expression.
    def _binary_parameter_dependency(self, node):
        left = self._parameter_dependency_source(
            node.left, expression_context=True)
        right = self._parameter_dependency_source(
            node.right, expression_context=True)
        if left is None and right is None:
            return None
        if left is None:
            traced_left = self.trace_source(node.left)
            if traced_left != "local":
                left = traced_left
        if right is None:
            traced_right = self.trace_source(node.right)
            if traced_right != "local":
                right = traced_right
        operands = tuple(
            source for source in (left, right) if source is not None)
        return DerivedResult(
            "expression", operands, type(node.op).__name__)

    ## Preserve dependencies across all operands of a comparison.
    def _compare_parameter_dependency(self, node):
        operands = []
        has_dependency = False
        for operand in [node.left] + list(node.comparators):
            dependency = self._parameter_dependency_source(
                operand, expression_context=True)
            if dependency is not None:
                has_dependency = True
                operands.append(dependency)
                continue
            traced = self.trace_source(operand)
            if traced != "local" and traced is not None:
                operands.append(traced)
        if not has_dependency:
            return None
        return DerivedResult(
            "expression", tuple(operands), "Compare")

    ## Preserve a parameter-dependent method result as an explicit call result.
    def _call_parameter_dependency(self, node):
        dependency = self._parameter_dependency_source(node.func.value)
        if dependency is None:
            return None
        method_source = self._resolve_methods(node)
        if method_source is None:
            return UnknownSource("unresolved parameter method result")
        return CallResult(
            method_source,
            display_name=ast.unparse(node.func),
            call_lineno=node.lineno,
            call_col_offset=node.col_offset,
            result_source=DerivedResult(
                "method_result", (method_source,), node.func.attr),
        )
