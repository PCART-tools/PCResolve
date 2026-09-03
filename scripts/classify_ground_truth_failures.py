#!/usr/bin/env python3
## @package scripts.classify_ground_truth_failures
#  Classify locked ground-truth ownership mismatches into release dispositions.

import argparse
import ast
import collections
import json
import os
import sys
import warnings

from static_boundary_reviews import (
    load_static_boundary_reviews,
    validate_static_boundary_reviews,
)


ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
GT_DIR = os.path.join(ROOT_DIR, "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")
VERIFICATION_DIR = os.path.join(GT_DIR, "verification")
DEFAULT_JSONL = os.path.join(VERIFICATION_DIR, "failure-dispositions.jsonl")
DEFAULT_MARKDOWN = os.path.join(
    VERIFICATION_DIR, "failure-dispositions.md")
STATIC_BOUNDARY_REVIEWS_FILE = os.path.join(
    VERIFICATION_DIR, "static-boundary-reviews.json")

DISPOSITION_FIX = "fix_1_0_5"
DISPOSITION_ACCEPTED_UNKNOWN = "accepted_unknown"
DISPOSITION_GT = "ground_truth_correction"

SCOPE_CONSERVATIVE = "conservative_identity"
SCOPE_LOCAL = "local_identity"
SCOPE_SAME = "same_scope_result_protocol"
SCOPE_INTERPROC = "bounded_receiver_flow"
SCOPE_EVIDENCE_UNKNOWN = "evidence_limited_unknown"
SCOPE_GT = "label_correction"

SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE = (
    "unbound_parameter_without_project_reference")
SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT = (
    "parameter_attribute_item_requires_external_contract")
SOURCE_NON_SYNTACTIC_RECEIVER_TYPE = (
    "receiver_owner_requires_value_type_evidence")
SOURCE_DYNAMIC_CALLABLE_ARGUMENT = (
    "dynamic_callable_argument_requires_dispatch_evidence")
SOURCE_UNRESOLVED_METHOD_ARGUMENT = (
    "local_method_argument_requires_receiver_dispatch_evidence")
SOURCE_INSTANCE_ATTRIBUTE_VALUE = (
    "instance_attribute_owner_requires_value_type_evidence")

_SAME_SCOPE_CATEGORIES = frozenset({
    "builtin",
    "builtin_callable",
    "builtin_container_method",
    "builtin_method_local_receiver",
    "builtin_string_method",
    "conversion_boundary",
    "direct_import",
    "library_result_boundary",
    "numpy_result_receiver",
    "numpy_scalar_receiver",
    "pandas_receiver_chain",
    "python_protocol_method",
    "regex_receiver",
})


## Return a stable location key for one GT record.
#
#  @param record Ground-truth JSON object.
#  @return Tuple identifying one call site and expression.
def record_key(record):
    return (
        record.get("project", ""),
        record.get("file", "").replace("\\", "/"),
        record.get("lineno", 0),
        record.get("col_offset", 0),
        record.get("expression", ""),
    )


## Return the root name of a receiver expression.
#
#  @param node Receiver AST node.
#  @return Root lexical name or an empty string.
def _receiver_root_name(node):
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _receiver_root_name(node.func)
    return ""


## Return the parameter root and attribute selected before a method chain.
#
#  For ``frame.loc[key].product().sum()``, this returns ``("frame", "loc")``.
#  The project can establish the owner of ``frame`` without establishing the
#  runtime type returned by the external attribute/subscript protocol.
#  @param call Call expression represented by a GT record.
#  @return Tuple of root name and selected attribute, or None.
def _parameter_attribute_item(call):
    receiver = call.func.value
    while (isinstance(receiver, ast.Call)
           and isinstance(receiver.func, ast.Attribute)):
        receiver = receiver.func.value
    if (not isinstance(receiver, ast.Subscript)
            or not isinstance(receiver.value, ast.Attribute)):
        return None
    attribute = receiver.value
    root = _receiver_root_name(attribute)
    if not root:
        return None
    return (root, attribute.attr)


## Return all parameter names declared by a function.
#
#  @param node FunctionDef or AsyncFunctionDef node.
#  @return Set of parameter names.
def _function_parameters(node):
    args = node.args
    names = {
        item.arg for item in (
            list(getattr(args, "posonlyargs", []))
            + list(args.args) + list(args.kwonlyargs))
    }
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return names


## Check declarations that need more than a missing-reference audit.
#  Defaults, annotations, decorators and implicit protocols can supply source
#  evidence without an ordinary named call. None is an automatic waiver.
#  @param function Function declaration.
#  @param parameter Receiver parameter name.
#  @return True when independent declaration or dispatch review is required.
def _requires_declaration_review(function, parameter):
    if (function.decorator_list
            or (function.name.startswith("__")
                and function.name.endswith("__"))):
        return True
    args = function.args
    positional = list(getattr(args, "posonlyargs", [])) + list(args.args)
    defaults = positional[len(positional) - len(args.defaults):]
    if any(item.arg == parameter for item in defaults):
        return True
    if any(item.arg == parameter and value is not None
           for item, value in zip(args.kwonlyargs, args.kw_defaults)):
        return True
    return any(item.arg == parameter and item.annotation is not None
               for item in positional + list(args.kwonlyargs))


## Return names introduced by import statements in one module.
#  @param tree Parsed module AST.
#  @return Set of lexical import binding names.
def _import_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


## Return project-local classes and their directly defined methods.
#  @param tree Parsed module AST.
#  @return Mapping of class name to method-name set.
def _local_class_methods(tree):
    return {
        node.name: {
            item.name for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


## Check whether a name is visibly constructed from one local class.
#  @param tree Parsed module AST.
#  @param name Receiver variable name.
#  @param call Represented call position.
#  @param local_classes Known local class names.
#  @return True when a preceding assignment is ``name = LocalClass(...)``.
def _is_local_constructor_binding(tree, name, call, local_classes):
    candidates = []
    for node in ast.walk(tree):
        if (not isinstance(node, (ast.Assign, ast.AnnAssign))
                or getattr(node, "lineno", 0) >= call.lineno):
            continue
        value = getattr(node, "value", None)
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Name)
                or value.func.id not in local_classes):
            continue
        targets = (
            node.targets if isinstance(node, ast.Assign)
            else [node.target])
        if any(isinstance(target, ast.Name) and target.id == name
               for target in targets):
            candidates.append((node.lineno, value.func.id))
    return bool(candidates)


## Check whether receiver ownership needs value-type or result-type evidence.
#
#  Direct import receivers, literals, and visibly defined local class methods
#  have callable identity in syntax. Parameters, local values, subscripts,
#  expressions, callback values, and call results need their source bindings
#  followed. This labels a dependency, not a static impossibility.
#  @param call Exact represented Call node.
#  @param tree Parsed module AST.
#  @return True when source syntax does not identify the receiver owner.
def _receiver_requires_value_type_evidence(call, tree):
    if not isinstance(call.func, ast.Attribute):
        return False
    receiver = call.func.value
    imports = _import_names(tree)
    local_classes = _local_class_methods(tree)

    if isinstance(receiver, ast.Constant):
        return False
    if isinstance(receiver, ast.Call):
        return not (
            isinstance(receiver.func, ast.Name)
            and receiver.func.id in local_classes
            and call.func.attr in local_classes[receiver.func.id]
        )
    if isinstance(receiver, ast.Name):
        if receiver.id in imports:
            return False
        if (receiver.id in local_classes
                and call.func.attr in local_classes[receiver.id]):
            return False
        if _is_local_constructor_binding(
                tree, receiver.id, call, local_classes):
            return False
        return True
    if isinstance(receiver, ast.Attribute):
        root = _receiver_root_name(receiver)
        if root in imports:
            return False
        return True
    return True


## Return the argument bound to one named parameter at a direct call site.
#  @param call Candidate invocation.
#  @param parameter Parameter name.
#  @param index Positional parameter index including self/cls.
#  @param has_receiver True for an instance/class method declaration.
#  @return Bound argument AST node or None.
def _bound_call_argument(call, parameter, index, has_receiver=False):
    positional_index = index - 1 if has_receiver else index
    if 0 <= positional_index < len(call.args):
        return call.args[positional_index]
    for keyword in call.keywords:
        if keyword.arg == parameter:
            return keyword.value
    return None


## Check whether argument syntax directly establishes a value owner.
#  @param node Argument expression.
#  @param import_names Project import binding names.
#  @param local_classes Project-local class names.
#  @return True for literals, direct import objects, and local constructors.
def _argument_has_syntactic_owner(node, import_names, local_classes):
    if isinstance(node, (ast.Constant, ast.JoinedStr, ast.List, ast.Tuple,
                         ast.Set, ast.Dict)):
        return True
    if isinstance(node, ast.Name):
        return node.id in import_names or node.id in local_classes
    if isinstance(node, ast.Attribute):
        return _receiver_root_name(node) in import_names
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in local_classes
    return False


## Check whether a value has direct source-level owner evidence.
#
#  Imported calls remain repair candidates because their callable identity is
#  visible and may have a verified result contract. Plain parameters,
#  attributes, subscripts, and method results still require value-type
#  evidence.
#  @param node Value expression.
#  @param import_names Project import binding names.
#  @param local_classes Project-local class names.
#  @return True when source syntax exposes an owner-bearing origin.
def _value_has_direct_owner_evidence(node, import_names, local_classes):
    if _argument_has_syntactic_owner(
            node, import_names, local_classes):
        return True
    if isinstance(node, ast.Call):
        return _receiver_root_name(node.func) in import_names
    if isinstance(node, ast.UnaryOp):
        return _value_has_direct_owner_evidence(
            node.operand, import_names, local_classes)
    if isinstance(node, ast.BinOp):
        return (
            _value_has_direct_owner_evidence(
                node.left, import_names, local_classes)
            and _value_has_direct_owner_evidence(
                node.right, import_names, local_classes)
        )
    return False


## Return whether an assignment target directly binds one name.
#  Attribute and subscript mutations do not rebind their root object.
#  @param target Assignment target.
#  @param name Name to locate.
#  @return True for direct or unpacked name bindings.
def _target_binds_name(target, name):
    if isinstance(target, ast.Name):
        return target.id == name
    if isinstance(target, ast.Starred):
        return _target_binds_name(target.value, name)
    if isinstance(target, (ast.Tuple, ast.List)):
        return any(_target_binds_name(item, name)
                   for item in target.elts)
    return False


## Return the latest direct assignment value before one represented call.
#  @param function Enclosing function.
#  @param name Binding name.
#  @param call Represented call.
#  @return Assignment value, or None when no direct assignment reaches it.
def _latest_name_binding_value(function, name, call):
    candidates = []
    for node in ast.walk(function):
        if (not isinstance(node, (ast.Assign, ast.AnnAssign,
                                  ast.NamedExpr))
                or getattr(node, "lineno", 0) >= call.lineno):
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            targets = [node.target]
        if any(_target_binds_name(target, name) for target in targets):
            candidates.append((node.lineno, node.col_offset, node.value))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


## Check whether one self attribute is assigned from an unproven value.
#  @param tree Parsed module AST.
#  @param attribute Attribute name without the self prefix.
#  @param call Represented call.
#  @param import_names Project import binding names.
#  @param local_classes Project-local class names.
#  @return True when at least one reaching source needs value-type evidence.
def _instance_attribute_requires_value_evidence(
        tree, attribute, call, import_names, local_classes):
    assignments = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                    and target.attr == attribute):
                assignments.append(node.value)
    return bool(assignments) and any(
        not _value_has_direct_owner_evidence(
            value, import_names, local_classes)
        for value in assignments
    )


## Check whether an expression depends on an unproven self attribute.
#  @param expression Receiver expression.
#  @param tree Parsed module AST.
#  @param call Represented call.
#  @param import_names Project import binding names.
#  @param local_classes Project-local class names.
#  @return True when an operand's owner needs value-type evidence.
def _expression_has_unproven_instance_attribute(
        expression, tree, call, import_names, local_classes):
    attributes = {
        node.attr for node in ast.walk(expression)
        if (isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self")
    }
    return any(_instance_attribute_requires_value_evidence(
        tree, attribute, call, import_names, local_classes)
        for attribute in attributes)


## Check whether one callable-object method has an exact invocation.
#  @param tree Parsed module AST.
#  @param class_name Enclosing local class name.
#  @param parameter Parameter name in __call__.
#  @param parameter_index Position including self.
#  @param import_names Project import binding names.
#  @param local_classes Project-local class names.
#  @return True when an exact local instance call supplies a direct owner.
def _has_exact_callable_argument(tree, class_name, parameter,
                                 parameter_index, import_names,
                                 local_classes):
    instance_names = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = getattr(node, "value", None)
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Name)
                or value.func.id != class_name):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        instance_names.update(
            target.id for target in targets if isinstance(target, ast.Name))

    arguments = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        exact = (
            isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Name)
            and node.func.func.id == class_name
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id in instance_names
        )
        if not exact:
            continue
        argument = _bound_call_argument(
            node, parameter, parameter_index, has_receiver=True)
        if argument is not None:
            arguments.append(argument)
    return any(_value_has_direct_owner_evidence(
        argument, import_names, local_classes) for argument in arguments)


## Return whether an AST subtree contains a specific node object.
#
#  @param root AST subtree root.
#  @param target Node to locate by identity.
#  @return True when target occurs below root.
def _contains_node(root, target):
    return any(node is target for node in ast.walk(root))


## Check whether a parameter is rebound around a represented call.
#
#  Nested lexical bodies are skipped. Their definition names still bind in
#  the containing function and therefore count as a rebind. An assignment
#  whose value contains the represented call does not rebind the parameter
#  until after that call has evaluated.
#  @param function FunctionDef or AsyncFunctionDef node.
#  @param parameter Parameter name.
#  @param call Exact call represented by the ground-truth record.
#  @return True when project source changes or deletes the binding.
def _parameter_is_rebound(function, parameter, call=None):
    repeated_regions = []
    if call is not None:
        for node in ast.walk(function):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                if any(_contains_node(statement, call)
                       for statement in node.body):
                    repeated_regions.extend(node.body)
            elif isinstance(node, ast.While) and _contains_node(node, call):
                repeated_regions.extend([node.test] + node.body)

    class RebindVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found = False

        def _visit_assignment(self, targets, value):
            self.visit(value)
            if call is not None and _contains_node(value, call):
                return
            if (any(_target_binds_name(target, parameter)
                    for target in targets)
                    and self._precedes_call(targets[0])):
                self.found = True

        def visit_Assign(self, node):
            self._visit_assignment(node.targets, node.value)

        def visit_AnnAssign(self, node):
            if node.value is not None:
                self._visit_assignment([node.target], node.value)
            else:
                self.visit(node.target)

        def visit_AugAssign(self, node):
            self._visit_assignment([node.target], node.value)

        def visit_NamedExpr(self, node):
            self._visit_assignment([node.target], node.value)

        def visit_Name(self, node):
            if (node.id == parameter
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and self._precedes_call(node)):
                self.found = True

        @staticmethod
        def _precedes_call(node):
            if call is None:
                return True
            if any(_contains_node(region, node)
                   for region in repeated_regions):
                return True
            return (
                getattr(node, "lineno", 0),
                getattr(node, "col_offset", 0),
            ) < (
                getattr(call, "lineno", 0),
                getattr(call, "col_offset", 0),
            )

        def visit_FunctionDef(self, node):
            if node.name == parameter and self._precedes_call(node):
                self.found = True

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            if node.name == parameter and self._precedes_call(node):
                self.found = True

        def visit_Lambda(self, node):
            return

        def visit_Import(self, node):
            if not self._precedes_call(node):
                return
            for alias in node.names:
                name = alias.asname or alias.name.split(".", 1)[0]
                if name == parameter:
                    self.found = True

        def visit_ImportFrom(self, node):
            if not self._precedes_call(node):
                return
            for alias in node.names:
                name = alias.asname or alias.name
                if name == parameter:
                    self.found = True

        def visit_ExceptHandler(self, node):
            if (node.name == parameter
                    and self._precedes_call(node)):
                self.found = True
            for statement in node.body:
                self.visit(statement)

    visitor = RebindVisitor()
    for statement in function.body:
        visitor.visit(statement)
    return visitor.found


## Normalize source text for call-expression matching.
#
#  @param text Expression source.
#  @return Whitespace-normalized expression.
def _normalize_expression(text):
    return " ".join((text or "").split())


## Return a syntax-stable key for one expression string.
#
#  Ground-truth expressions may use ast.unparse quoting while source segments
#  retain the author's original quoting and escapes. Comparing AST structure
#  avoids treating those formatting differences as missing source evidence.
#  @param text Python expression text.
#  @return AST dump without source positions, or an empty string on failure.
def _expression_ast_key(text):
    try:
        expression = ast.parse(text or "", mode="eval").body
    except SyntaxError:
        return ""
    return ast.dump(expression, annotate_fields=True,
                    include_attributes=False)


## Locate the exact Call node represented by a GT record.
#
#  @param tree Parsed module AST.
#  @param source Original module source.
#  @param record Ground-truth call record.
#  @return Matching Call node or None.
def _find_record_call(tree, source, record):
    candidates = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and node.lineno == record.get("lineno", 0)
        and node.col_offset == record.get("col_offset", 0)
    ]
    if len(candidates) == 1:
        return candidates[0]
    expected = _normalize_expression(record.get("expression", ""))
    matches = [
        node for node in candidates
        if _normalize_expression(
            ast.get_source_segment(source, node)) == expected
    ]
    if len(matches) == 1:
        return matches[0]
    expected_ast = _expression_ast_key(record.get("expression", ""))
    if not expected_ast:
        return None
    matches = [
        node for node in candidates
        if ast.dump(node, annotate_fields=True,
                    include_attributes=False) == expected_ast
    ]
    return matches[0] if len(matches) == 1 else None


## Load project roots from the GT manifest.
#
#  @return Mapping of logical project name to absolute project root.
def _load_project_paths():
    with open(PROJECTS_FILE, encoding="utf-8") as stream:
        projects = json.load(stream).get("projects", {})
    return {
        name: os.path.normpath(os.path.join(ROOT_DIR, info["path"]))
        for name, info in projects.items()
    }


## Build a conservative source-evidence index for mismatch disposition.
#
#  A direct parameter receiver is evidence-limited only when its function has
#  no source reference anywhere in the project and the parameter is never
#  rebound before the represented call. Alias/dispatch-table references keep
#  the record open because another call may invoke that stored callable.
#  Other dependency labels are triage hints, not release exemptions.
#  @param records Iterable of GT records.
#  @param project_paths Optional logical-name to project-root mapping.
#  @return Mapping of record_key to source-evidence label.
def build_source_evidence(records, project_paths=None):
    records = list(records)
    paths = project_paths or _load_project_paths()
    project_cache = {}

    for project in sorted({item.get("project", "") for item in records}):
        project_root = paths.get(project)
        if not project_root or not os.path.isdir(project_root):
            continue
        files = {}
        call_name_references = collections.Counter()
        call_attribute_references = collections.Counter()
        direct_calls = collections.defaultdict(list)
        assigned_attributes = set()
        project_import_names = set()
        project_local_classes = set()
        references_complete = True
        for dir_path, _, file_names in os.walk(project_root):
            for file_name in file_names:
                if not file_name.endswith((".py", ".pyi")):
                    continue
                path = os.path.join(dir_path, file_name)
                try:
                    with open(path, encoding="utf-8") as stream:
                        source = stream.read()
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", SyntaxWarning)
                        tree = ast.parse(source)
                except (OSError, UnicodeDecodeError, SyntaxError):
                    references_complete = False
                    continue
                relative = os.path.relpath(
                    path, project_root).replace("\\", "/")
                files[relative] = (source, tree)
                project_import_names.update(_import_names(tree))
                project_local_classes.update(_local_class_methods(tree))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Name)
                            and isinstance(node.ctx, ast.Load)):
                        call_name_references[node.id] += 1
                    elif (isinstance(node, ast.Attribute)
                          and isinstance(node.ctx, ast.Load)):
                        call_attribute_references[node.attr] += 1
                    elif (isinstance(node, ast.Constant)
                          and isinstance(node.value, str)):
                        # A literal name may be used by globals/getattr or a
                        # registry. Counting it only blocks an automatic waiver.
                        call_name_references[node.value.rsplit(".", 1)[-1]] += 1
                    if not isinstance(node, ast.Call):
                        continue
                    if isinstance(node.func, ast.Name):
                        direct_calls[node.func.id].append(node)
                    elif isinstance(node.func, ast.Attribute):
                        direct_calls[node.func.attr].append(node)
                for item in ast.walk(tree):
                    if (isinstance(item, ast.Attribute)
                            and isinstance(
                                item.ctx, (ast.Store, ast.Del))):
                        assigned_attributes.add(item.attr)
        project_cache[project] = (
            files, call_name_references, call_attribute_references,
            assigned_attributes, direct_calls, project_import_names,
            project_local_classes, references_complete)

    evidence = {}
    for record in records:
        cached = project_cache.get(record.get("project", ""))
        if cached is None:
            continue
        (files, call_name_references, call_attribute_references,
         assigned_attributes, direct_calls, project_import_names,
         project_local_classes, references_complete) = cached
        relative = record.get("file", "").replace("\\", "/")
        parsed = files.get(relative)
        if parsed is None:
            suffix_matches = [
                item for item in files
                if item.endswith("/" + relative)
                or relative.endswith("/" + item)
            ]
            if len(suffix_matches) == 1:
                parsed = files[suffix_matches[0]]
        if parsed is None:
            continue
        source, tree = parsed
        call = _find_record_call(tree, source, record)
        if call is None or not isinstance(call.func, ast.Attribute):
            continue
        receiver = _receiver_root_name(call.func.value)
        if not receiver:
            if _expression_has_unproven_instance_attribute(
                    call.func.value, tree, call,
                    project_import_names, project_local_classes):
                evidence[record_key(record)] = (
                    SOURCE_INSTANCE_ATTRIBUTE_VALUE)
            continue
        if receiver in ("self", "cls"):
            if (receiver == "self"
                    and _expression_has_unproven_instance_attribute(
                        call.func.value, tree, call,
                        project_import_names, project_local_classes)):
                evidence[record_key(record)] = (
                    SOURCE_INSTANCE_ATTRIBUTE_VALUE)
            continue

        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.lineno <= record.get("lineno", 0)
            <= getattr(node, "end_lineno", node.lineno)
        ]
        if not functions:
            if _receiver_requires_value_type_evidence(call, tree):
                evidence[record_key(record)] = (
                    SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)
            continue
        function = max(functions, key=lambda node: node.lineno)
        if function.name == "__call__":
            parameters = list(
                item.arg for item in (
                    list(getattr(function.args, "posonlyargs", []))
                    + list(function.args.args)
                    + list(function.args.kwonlyargs)))
            classes = [
                node for node in ast.walk(tree)
                if (isinstance(node, ast.ClassDef)
                    and node.lineno <= function.lineno
                    <= getattr(node, "end_lineno", node.lineno))
            ]
            if (receiver in parameters and classes
                    and not _has_exact_callable_argument(
                        tree,
                        max(classes, key=lambda node: node.lineno).name,
                        receiver, parameters.index(receiver),
                        project_import_names, project_local_classes)):
                evidence[record_key(record)] = (
                    SOURCE_DYNAMIC_CALLABLE_ARGUMENT)
            continue
        attribute_item = _parameter_attribute_item(call)
        if attribute_item is not None:
            parameter, attribute = attribute_item
            if (parameter in _function_parameters(function)
                    and attribute not in assigned_attributes
                    and not _parameter_is_rebound(
                        function, parameter, call)):
                evidence[record_key(record)] = (
                    SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT)
                continue
            if (parameter in _function_parameters(function)
                    and attribute in assigned_attributes):
                continue
        if receiver in _function_parameters(function):
            if _parameter_is_rebound(function, receiver, call):
                latest_value = _latest_name_binding_value(
                    function, receiver, call)
                if (latest_value is not None
                        and not _value_has_direct_owner_evidence(
                            latest_value, project_import_names,
                            project_local_classes)):
                    evidence[record_key(record)] = (
                        SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)
                continue
            references = (
                call_name_references.get(function.name, 0)
                + call_attribute_references.get(function.name, 0))
            if (references_complete and not references
                    and not _requires_declaration_review(function, receiver)):
                evidence[record_key(record)] = (
                    SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)
                continue
            parameters = list(
                item.arg for item in (
                    list(getattr(function.args, "posonlyargs", []))
                    + list(function.args.args)
                    + list(function.args.kwonlyargs)))
            parameter_index = parameters.index(receiver)
            has_receiver = bool(
                parameters and parameters[0] in ("self", "cls"))
            eligible_invocations = [
                invocation
                for invocation in direct_calls.get(function.name, [])
                if (isinstance(invocation.func, ast.Name)
                    or (isinstance(invocation.func, ast.Attribute)
                        and _receiver_root_name(invocation.func.value)
                        in project_import_names))
            ]
            arguments = [
                argument
                for invocation in eligible_invocations
                for argument in [
                    _bound_call_argument(
                        invocation, receiver, parameter_index,
                        has_receiver=has_receiver)]
                if argument is not None
            ]
            if not arguments:
                if has_receiver:
                    evidence[record_key(record)] = (
                        SOURCE_UNRESOLVED_METHOD_ARGUMENT)
                continue
            if any(_argument_has_syntactic_owner(
                        argument, project_import_names,
                        project_local_classes)
                        for argument in arguments):
                continue
        if _receiver_requires_value_type_evidence(call, tree):
            evidence[record_key(record)] = (
                SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)
    return evidence


## Return True when a locked positive record is a primary ownership mismatch.
#
#  @param record Ground-truth JSON object.
#  @return True for a current primary mismatch.
def is_primary_mismatch(record):
    if record.get("annotation_status") != "locked":
        return False
    if record.get("status") != "positive":
        return False
    expected = (
        record.get("expected_kind", ""),
        record.get("expected_top_library", ""),
    )
    actual = (
        record.get("pcresolve_kind", ""),
        record.get("pcresolve_top_library", ""),
    )
    return expected != actual


## Return whether a record is the documented Flask mapping payload boundary.
#
#  @param record Ground-truth JSON object.
#  @return True only for request.json.get calls in flask2.
def _is_flask_payload_boundary(record):
    return (
        record.get("project") == "flask2"
        and record.get("category") == "mapping_protocol_method"
        and record.get("expression", "").startswith("request.json.get(")
        and record.get("expected_kind") == "python"
        and record.get("pcresolve_top_library") in ("flask", "unknown")
    )


## Return whether a record has a GT label unsupported by its source program.
#
#  @param record Ground-truth JSON object.
#  @return True for the reviewed unreachable tensor-parameter records.
def _needs_dead_code_gt_correction(record):
    notes = record.get("verification_notes", "").lower()
    return (
        record.get("category") == "framework_tensor_receiver"
        and "unreachable" in notes
        and record.get("expected_kind") == "library"
    )


## Return whether a visible monkey patch still has an unresolved receiver type.
#
#  The source proves that a local callable was assigned to selected imported
#  classes, but a library-level receiver owner does not prove which runtime
#  class supplies the method descriptor.
#  @param record Ground-truth JSON object.
#  @return True when unknown is the sound static primary owner.
def _is_ambiguous_monkey_patch(record):
    return (
        record.get("category") == "monkey_patched_local_method"
        and record.get("pcresolve_kind") == "unknown"
    )


## Classify one primary mismatch into a release disposition and repair scope.
#
#  The disposition answers whether 1.0.5 must repair the record, retain a
#  justified unknown, or correct the GT label. The repair scope groups
#  fixable records by implementation strategy without encoding library-name
#  whitelists.
#
#  @param record Ground-truth JSON object.
#  @param source_evidence Optional project-source recoverability label.
#  @param reviewed_boundary Optional validated independent boundary review.
#  @return Tuple of disposition, repair scope, and explanation.
def classify_disposition(
        record, source_evidence="", reviewed_boundary=None):
    if _is_flask_payload_boundary(record):
        if record.get("pcresolve_kind") == "unknown":
            return (
                DISPOSITION_ACCEPTED_UNKNOWN,
                SCOPE_EVIDENCE_UNKNOWN,
                "request.json has mapping-like runtime behavior, but its "
                "concrete value type is not proven by project source",
            )
        return (
            DISPOSITION_FIX,
            SCOPE_CONSERVATIVE,
            "request.json runtime mapping type is not proven by project "
            "source; replace flask certainty with unknown",
        )

    if _needs_dead_code_gt_correction(record):
        return (
            DISPOSITION_GT,
            SCOPE_GT,
            "unreachable parameter has no concrete owner in source",
        )

    expected_kind = record.get("expected_kind", "")
    actual_kind = record.get("pcresolve_kind", "")
    category = record.get("category", "")

    if (reviewed_boundary
            and actual_kind == "unknown"
            and record.get("pcresolve_top_library") == "unknown"):
        return (
            DISPOSITION_ACCEPTED_UNKNOWN,
            SCOPE_EVIDENCE_UNKNOWN,
            "review %s: %s" % (
                reviewed_boundary.get("id", ""),
                reviewed_boundary.get("reason", ""),
            ),
        )

    if _is_ambiguous_monkey_patch(record):
        return (
            DISPOSITION_ACCEPTED_UNKNOWN,
            SCOPE_EVIDENCE_UNKNOWN,
            "project source proves a local monkey patch, but the receiver's "
            "runtime class is not recoverable from project source",
        )

    if source_evidence == SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE:
        if actual_kind == "unknown":
            return (
                DISPOSITION_ACCEPTED_UNKNOWN,
                SCOPE_EVIDENCE_UNKNOWN,
                "receiver is an unbound parameter whose function has no "
                "project-source reference; no project source supplies "
                "an argument owner",
            )
        return (
            DISPOSITION_FIX,
            SCOPE_CONSERVATIVE,
            "receiver is an unbound parameter whose function has no "
            "project-source reference; replace unsupported certainty with "
            "unknown",
        )

    if expected_kind == "unknown":
        return (
            DISPOSITION_FIX,
            SCOPE_CONSERVATIVE,
            "replace unsupported local/library certainty with unknown",
        )

    if expected_kind == "local":
        return (
            DISPOSITION_FIX,
            SCOPE_LOCAL,
            "protect project-local callable identity",
        )

    if source_evidence in (
            SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT,
            SOURCE_NON_SYNTACTIC_RECEIVER_TYPE,
            SOURCE_DYNAMIC_CALLABLE_ARGUMENT,
            SOURCE_UNRESOLVED_METHOD_ARGUMENT,
            SOURCE_INSTANCE_ATTRIBUTE_VALUE):
        return (
            DISPOSITION_FIX,
            SCOPE_INTERPROC,
            "source triage identifies a value or dispatch dependency, not "
            "proof of impossibility; trace its bindings or record an "
            "independently reviewed static boundary before release",
        )

    if category in _SAME_SCOPE_CATEGORIES:
        return (
            DISPOSITION_FIX,
            SCOPE_SAME,
            "propagate result or protocol ownership within local flow",
        )

    return (
        DISPOSITION_FIX,
        SCOPE_INTERPROC,
        "propagate receiver ownership through bounded project call evidence",
    )


## Return the release target classification for one disposition.
#
#  @param record Ground-truth JSON object.
#  @param disposition Release disposition.
#  @param repair_scope Implementation repair scope.
#  @return Pair of target kind and target top library.
def _target_classification(record, disposition, repair_scope):
    if (
            disposition == DISPOSITION_ACCEPTED_UNKNOWN
            or repair_scope == SCOPE_CONSERVATIVE
            or disposition == DISPOSITION_GT):
        return ("unknown", "unknown")
    return (
        record.get("expected_kind", ""),
        record.get("expected_top_library", ""),
    )


## Load every JSONL record from the canonical calls directory.
#
#  @return List of ground-truth records.
def load_records():
    records = []
    for name in sorted(os.listdir(CALLS_DIR)):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(CALLS_DIR, name)
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    records.append(json.loads(line))
    return records


## Build deterministic sidecar entries for current primary mismatches.
#
#  @param records Iterable of ground-truth records.
#  @param boundary_reviews Optional validated record-key to review mapping.
#  @return Sorted list of compact failure disposition dictionaries.
def build_entries(records, boundary_reviews=None):
    records = list(records)
    mismatches = [
        record for record in records if is_primary_mismatch(record)
    ]
    source_evidence = build_source_evidence(mismatches)
    boundary_reviews = boundary_reviews or {}
    entries = []
    for record in mismatches:
        evidence = source_evidence.get(record_key(record), "")
        boundary_review = boundary_reviews.get(record_key(record))
        disposition, repair_scope, explanation = classify_disposition(
            record, evidence, boundary_review)
        target_kind, target_top = _target_classification(
            record, disposition, repair_scope)
        entry = {
            "project": record.get("project", ""),
            "file": record.get("file", ""),
            "lineno": record.get("lineno", 0),
            "col_offset": record.get("col_offset", 0),
            "expression": record.get("expression", ""),
            "expected_kind": record.get("expected_kind", ""),
            "expected_top_library": record.get(
                "expected_top_library", ""),
            "pcresolve_kind": record.get("pcresolve_kind", ""),
            "pcresolve_top_library": record.get(
                "pcresolve_top_library", ""),
            "pcresolve_reason": record.get("pcresolve_reason", ""),
            "category": record.get("category", ""),
            "verification_level": record.get("verification_level", ""),
            "source_evidence": evidence,
            "disposition": disposition,
            "repair_scope": repair_scope,
            "disposition_reason": explanation,
            "target_kind": target_kind,
            "target_top_library": target_top,
        }
        if boundary_review:
            entry["boundary_review_id"] = boundary_review.get("id", "")
        entries.append(entry)
    entries.sort(key=lambda item: (
        item["project"], item["file"], item["lineno"],
        item["col_offset"], item["expression"],
    ))
    return entries


## Serialize sidecar entries as deterministic JSONL.
#
#  @param entries Failure disposition entries.
#  @return UTF-8 JSONL text.
def render_jsonl(entries):
    return "".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        for entry in entries
    )


## Escape one value for a Markdown table cell.
#
#  @param value Arbitrary scalar value.
#  @return Single-line Markdown-safe text.
def _markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\r", "").replace(
        "\n", "<br>")


## Return unresolved entries that block the stable 1.0.5 release.
#
#  accepted_unknown records are reviewed static boundaries and remain scored
#  misses, but they do not block release. Repair and GT-correction records do.
#  @param entries Failure disposition entries.
#  @return List of release-blocking entries.
def release_blockers(entries):
    return [
        entry for entry in entries
        if entry.get("disposition") in (DISPOSITION_FIX, DISPOSITION_GT)
    ]


## Render a human-readable failure disposition summary.
#
#  @param entries Failure disposition entries.
#  @return Markdown report text.
def render_markdown(entries):
    disposition_counts = collections.Counter(
        entry["disposition"] for entry in entries)
    scope_counts = collections.Counter(
        entry["repair_scope"] for entry in entries)
    project_counts = collections.Counter(
        entry["project"] for entry in entries)
    category_counts = collections.Counter(
        entry["category"] for entry in entries)
    evidence_counts = collections.Counter(
        (entry["verification_level"], entry["disposition"])
        for entry in entries)
    source_evidence_counts = collections.Counter(
        entry.get("source_evidence", "") or "bounded_or_pending"
        for entry in entries)
    unknown_outcome_counts = collections.Counter(
        (
            entry["project"],
            entry["category"],
            entry["disposition"],
        )
        for entry in entries
        if entry["target_kind"] == "unknown"
        and entry["disposition"] != DISPOSITION_GT)
    boundary_review_counts = collections.Counter(
        entry.get("boundary_review_id", "")
        for entry in entries
        if entry.get("boundary_review_id", ""))

    lines = [
        "# PCResolve 1.0.5 Failure Dispositions",
        "",
        "This report classifies every current locked primary ownership "
        "mismatch. The canonical call labels remain in `ground_truth/calls/`; "
        "the JSONL sidecar records release disposition only.",
        "",
        "## Classification Policy",
        "",
        "Ground truth records semantic or runtime ownership. Release "
        "disposition asks a different question: whether project source proves "
        "that exact owner under PCResolve's project-source-only static "
        "analysis contract.",
        "",
        "1. Verification levels describe GT evidence, not source "
        "recoverability. In particular, `dynamic_probe` and "
        "`manual_reasoned` are not automatic static-boundary waivers.",
        "2. A runtime-only owner with a current `unknown` result is accepted "
        "as an honest static boundary and remains a scored GT miss.",
        "3. A runtime-only owner with a current `local` or library result must "
        "first drop that unsupported certainty to `unknown`.",
        "4. A still-unbound parameter in a function with no project source "
        "reference is considered only after a complete parse and declaration "
        "review. Defaults, annotations, decorators, implicit protocols, aliases "
        "and dispatch-table references prevent an automatic boundary waiver.",
        "5. No library-name or external return-type whitelist is introduced "
        "to turn runtime observations into static guesses.",
        "6. Value-type, attribute and dispatch dependencies are triage "
        "hints, not proofs of irrecoverability. They remain release blockers "
        "until bindings are traced or an independent boundary is reviewed.",
        "",
        "## Release Disposition",
        "",
        "| Disposition | Records | Meaning |",
        "|---|---:|---|",
    ]
    meanings = {
        DISPOSITION_FIX: "Must be closed in 1.0.5",
        DISPOSITION_ACCEPTED_UNKNOWN:
            "Current unknown is justified by the static evidence boundary",
        DISPOSITION_GT: "Canonical GT label must be corrected",
    }
    for name in (
            DISPOSITION_FIX, DISPOSITION_ACCEPTED_UNKNOWN, DISPOSITION_GT):
        lines.append("| `%s` | %d | %s |" % (
            name, disposition_counts.get(name, 0), meanings[name]))
    lines.append("| **Total** | **%d** | |" % len(entries))

    lines.extend([
        "",
        "## Repair Scope",
        "",
        "| Repair scope | Records |",
        "|---|---:|",
    ])
    scope_order = (
        SCOPE_SAME,
        SCOPE_INTERPROC,
        SCOPE_CONSERVATIVE,
        SCOPE_LOCAL,
        SCOPE_EVIDENCE_UNKNOWN,
        SCOPE_GT,
    )
    for name in scope_order:
        lines.append("| `%s` | %d |" % (
            name, scope_counts.get(name, 0)))
    lines.append("| **Total** | **%d** |" % len(entries))

    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "| Verification level | Disposition | Records |",
        "|---|---|---:|",
    ])
    for (level, disposition), count in sorted(evidence_counts.items()):
        lines.append("| `%s` | `%s` | %d |" % (
            level, disposition, count))

    lines.extend([
        "",
        "## Source Recoverability",
        "",
        "This table includes both boundary evidence and pending triage "
        "hints. Only the disposition and its justification determine "
        "whether a record is accepted for release.",
        "",
        "| Source evidence | Records |",
        "|---|---:|",
    ])
    for name, count in sorted(source_evidence_counts.items()):
        lines.append("| `%s` | %d |" % (name, count))

    lines.extend([
        "",
        "## Independently Reviewed Static Boundaries",
        "",
        "These records remain raw GT misses. Each review is tied to an exact "
        "call identity and a digest of every Python source in its project; "
        "source or GT drift invalidates the release audit.",
        "",
        "| Review | Active records |",
        "|---|---:|",
    ])
    for review_id, count in sorted(boundary_review_counts.items()):
        lines.append("| `%s` | %d |" % (review_id, count))
    if not boundary_review_counts:
        lines.append("| - | 0 |")

    lines.extend([
        "",
        "## Project Queue",
        "",
        "| Project | Records |",
        "|---|---:|",
    ])
    for name, count in sorted(
            project_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (name, count))

    lines.extend([
        "",
        "## Failure Families",
        "",
        "| Category | Records |",
        "|---|---:|",
    ])
    for name, count in sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (name or "(none)", count))

    lines.extend([
        "",
        "## Unknown Outcome Queue",
        "",
        "These records either already have a justified `unknown` result or "
        "must drop a source-unsupported `local`/library claim to `unknown`.",
        "",
        "| Project | Category | Disposition | Records |",
        "|---|---|---|---:|",
    ])
    for (project, category, disposition), count in sorted(
            unknown_outcome_counts.items()):
        lines.append("| `%s` | `%s` | `%s` | %d |" % (
            project, category or "(none)", disposition, count))

    corrections = [
        entry for entry in entries
        if entry["disposition"] == DISPOSITION_GT
    ]
    lines.extend([
        "",
        "## Ground Truth Corrections",
        "",
        "| Location | Expression | Reason |",
        "|---|---|---|",
    ])
    for entry in corrections:
        location = "%s/%s:%d:%d" % (
            entry["project"], entry["file"], entry["lineno"],
            entry["col_offset"])
        expression = entry["expression"].replace("|", "\\|")
        reason = entry["disposition_reason"].replace("|", "\\|")
        lines.append("| `%s` | `%s` | %s |" % (
            location, expression, reason))
    if not corrections:
        lines.append("| - | - | None in the current locked GT |")

    accepted_unknown = [
        entry for entry in entries
        if entry["disposition"] == DISPOSITION_ACCEPTED_UNKNOWN
    ]
    lines.extend([
        "",
        "## Accepted Unknown Details",
        "",
        "Every accepted static boundary is listed below. Ground truth names "
        "the reviewed semantic or runtime owner; the current result remains "
        "`unknown` because project source does not prove that owner.",
        "",
    ])
    detail_number = 0
    for project in sorted({entry["project"] for entry in accepted_unknown}):
        project_entries = [
            entry for entry in accepted_unknown
            if entry["project"] == project
        ]
        lines.extend([
            "### %s (%d)" % (_markdown_cell(project), len(project_entries)),
            "",
            "| # | Location | Expression | GT owner | Verification | "
            "Source boundary | Why `unknown` |",
            "|---:|---|---|---|---|---|---|",
        ])
        for entry in project_entries:
            detail_number += 1
            location = "%s:%d:%d" % (
                entry["file"], entry["lineno"], entry["col_offset"])
            gt_owner = "%s / %s" % (
                entry["expected_kind"], entry["expected_top_library"])
            lines.append(
                "| %d | `%s` | `%s` | `%s` | `%s` | `%s` | %s |" % (
                    detail_number,
                    _markdown_cell(location),
                    _markdown_cell(entry["expression"]),
                    _markdown_cell(gt_owner),
                    _markdown_cell(entry["verification_level"]),
                    _markdown_cell(
                        entry.get("source_evidence", "")
                        or "bounded_or_pending"),
                    _markdown_cell(entry["disposition_reason"]),
                )
            )
        lines.append("")

    lines.extend([
        "## Release Rule",
        "",
        "1. Every `fix_1_0_5` entry must either become a primary hit or be "
        "reclassified with reviewed evidence.",
        "2. `accepted_unknown` entries remain scored as GT misses, but do not "
        "require a guessed exact owner for release.",
        "3. `ground_truth_correction` entries must update the canonical GT "
        "before algorithm work continues.",
        "4. No mismatch may remain without a disposition.",
        "5. The stable 1.0.5 release requires zero `fix_1_0_5` and zero "
        "`ground_truth_correction` entries.",
        "",
    ])
    return "\n".join(lines)


## Write or check generated disposition artifacts.
#
#  @param path Output file path.
#  @param content Expected file content.
#  @param check Whether to compare without writing.
#  @return True when the file matches or was written successfully.
def _write_or_check(path, content, check):
    if check:
        try:
            with open(path, encoding="utf-8") as stream:
                actual = stream.read()
        except OSError:
            print("MISSING: %s" % path)
            return False
        if actual != content:
            print("STALE: %s" % path)
            return False
        print("OK: %s" % path)
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    print("Wrote: %s" % path)
    return True


## CLI entry point.
#  @return None; exits with status 1 when generated artifacts are stale.
def main():
    parser = argparse.ArgumentParser(
        description="Classify locked GT ownership failures")
    parser.add_argument(
        "--check", action="store_true",
        help="fail when generated disposition artifacts are stale")
    parser.add_argument(
        "--release-check", action="store_true",
        help="check artifacts and fail while release blockers remain")
    parser.add_argument("--jsonl", default=DEFAULT_JSONL)
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    records = load_records()
    try:
        review_document = load_static_boundary_reviews(
            STATIC_BOUNDARY_REVIEWS_FILE)
        boundary_reviews, review_errors = validate_static_boundary_reviews(
            review_document, records, _load_project_paths())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        boundary_reviews = {}
        review_errors = ["cannot load static boundary reviews: %s" % error]
    for error in review_errors:
        print("BOUNDARY REVIEW ERROR: %s" % error)
    if review_errors:
        sys.exit(1)
    entries = build_entries(records, boundary_reviews=boundary_reviews)
    check = args.check or args.release_check
    ok_json = _write_or_check(
        args.jsonl, render_jsonl(entries), check)
    ok_markdown = _write_or_check(
        args.markdown, render_markdown(entries), check)
    print("Classified %d primary mismatches" % len(entries))
    blockers = release_blockers(entries) if args.release_check else []
    if blockers:
        counts = collections.Counter(
            entry["disposition"] for entry in blockers)
        print(
            "RELEASE BLOCKED: fix_1_0_5=%d ground_truth_correction=%d"
            % (
                counts.get(DISPOSITION_FIX, 0),
                counts.get(DISPOSITION_GT, 0),
            )
        )
    if not (ok_json and ok_markdown) or blockers:
        sys.exit(1)


if __name__ == "__main__":
    main()
