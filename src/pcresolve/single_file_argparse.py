## @package pcresolve.single_file_argparse
#  Track argparse Namespace fields and their conservative Python shapes.

import ast

from .builtin_ownership import _is_builtin
from .sources import PythonShape


## Collect argparse-specific ownership facts using SingleFileAnalyzer state.
class SingleFileArgparseMixin:
    ## Return argparse destination fields tracked for a parser binding.
    #
    #  @param parser_name Parser variable name.
    #  @return Mutable destination-name set, or None.
    def _argparse_destinations(self, parser_name):
        scope = self.current_scope()
        while scope is not None:
            destinations = self._argparse_parsers.get(
                (id(scope), parser_name))
            if destinations is not None:
                return destinations
            scope = scope.parent
        return None

    ## Return Python shapes tracked for an argparse parser binding.
    #
    #  @param parser_name Parser variable name.
    #  @return Destination-to-PythonShape mapping, or None.
    def _argparse_destination_shape_map(self, parser_name):
        scope = self.current_scope()
        while scope is not None:
            shapes = self._argparse_destination_shapes.get(
                (id(scope), parser_name))
            if shapes is not None:
                return shapes
            scope = scope.parent
        return None

    ## Record an argparse add_argument() destination with Python value shape.
    #
    #  Custom type/action callables are intentionally excluded because their
    #  return object may be project-local or import-backed.
    #  @param node Candidate add_argument() call.
    def _collect_argparse_destination(self, node):
        if (not isinstance(node.func, ast.Attribute)
                or node.func.attr != "add_argument"
                or not isinstance(node.func.value, ast.Name)):
            return
        destinations = self._argparse_destinations(node.func.value.id)
        if destinations is None:
            return
        shapes = self._argparse_destination_shape_map(node.func.value.id)

        keywords = {
            keyword.arg: keyword.value for keyword in node.keywords
            if keyword.arg is not None
        }
        type_node = keywords.get("type")
        if (type_node is not None
                and (not isinstance(type_node, ast.Name)
                     or not _is_builtin(type_node.id))):
            return
        action_node = keywords.get("action")
        if (action_node is not None
                and (not isinstance(action_node, ast.Constant)
                     or not isinstance(action_node.value, str))):
            return

        destination = None
        dest_node = keywords.get("dest")
        if (isinstance(dest_node, ast.Constant)
                and isinstance(dest_node.value, str)):
            destination = dest_node.value
        else:
            option_strings = [
                arg.value for arg in node.args
                if (isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str))
            ]
            long_options = [
                option for option in option_strings
                if option.startswith("--")
            ]
            if long_options:
                destination = long_options[0][2:].replace("-", "_")
            elif option_strings and not option_strings[0].startswith("-"):
                destination = option_strings[0].replace("-", "_")
        if destination:
            destinations.add(destination)
            if shapes is not None:
                shape = self._expression_python_shape(
                    keywords.get("default"))
                if shape is None and isinstance(type_node, ast.Name):
                    if _is_builtin(type_node.id):
                        shape = PythonShape(type_node.id)
                if (shape is None
                        and isinstance(action_node, ast.Constant)
                        and action_node.value in (
                            "store_true", "store_false")):
                    shape = PythonShape("bool")
                if shape is None:
                    shapes.pop(destination, None)
                else:
                    existing = shapes.get(destination)
                    if existing is None or existing == shape:
                        shapes[destination] = shape
                    else:
                        shapes.pop(destination, None)

    ## Record ArgumentParser construction or parse_args Namespace attributes.
    #
    #  @param node Assignment being visited.
    def _collect_argparse_assignment(self, node):
        if (not isinstance(node.value, ast.Call)
                or not isinstance(node.value.func, ast.Attribute)):
            return
        targets = [
            target.id for target in node.targets
            if isinstance(target, ast.Name)
        ]
        if not targets:
            return

        # ArgumentGroup.add_argument() populates the same Namespace as its
        # owning ArgumentParser.  Preserve that destination set when a group
        # is assigned to a local name, so grouped options receive the same
        # Python value-shape evidence as parser-level options.
        if (node.value.func.attr == "add_argument_group"
                and isinstance(node.value.func.value, ast.Name)):
            destinations = self._argparse_destinations(
                node.value.func.value.id)
            shapes = self._argparse_destination_shape_map(
                node.value.func.value.id)
            if destinations is not None:
                for target in targets:
                    self._argparse_parsers[
                        (id(self.current_scope()), target)] = destinations
                    if shapes is not None:
                        self._argparse_destination_shapes[
                            (id(self.current_scope()), target)] = shapes
                return

        func_top, func_name = self._resolve_func_top(node.value.func)
        if func_top == "argparse" and func_name == "ArgumentParser":
            for target in targets:
                self._argparse_parsers[
                    (id(self.current_scope()), target)] = set()
                self._argparse_destination_shapes[
                    (id(self.current_scope()), target)] = {}
            return

        if (node.value.func.attr not in ("parse_args",)
                or not isinstance(node.value.func.value, ast.Name)):
            return
        destinations = self._argparse_destinations(
            node.value.func.value.id)
        if destinations is None:
            return
        shapes = self._argparse_destination_shape_map(
            node.value.func.value.id)
        for target in targets:
            for destination in destinations:
                shape = shapes.get(destination) if shapes is not None else None
                self._bind_target_name(
                    target + "." + destination,
                    "python",
                    node,
                    "attribute",
                    container_kind=(shape.kind if shape is not None
                                    and shape.kind in (
                                        "list", "dict", "set", "tuple",
                                        "str") else ""),
                    container_item_kind=(shape.item_kind if shape is not None
                                         else ""),
                )
