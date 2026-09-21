## @package pcresolve.single_file_definitions
#  Function, lambda, class, decorator, and constructor-field collection.

import ast
from dataclasses import dataclass

from .call_graph import ClassSummary, FunctionId, FunctionSummary
from .mapping_facts import bound_names as mapping_bound_names
from .program_facts import SourceSpan
from .scope import SCOPE_CLASS, SCOPE_FUNCTION, SCOPE_MODULE
from .sources import PythonShape, UnknownSource, make_source_set, normalize_source


## Immutable declaration facts computed before entering a function scope.
@dataclass(frozen=True)
class FunctionDefinitionFacts:
    is_direct_method: bool
    receiver_name: str
    params: tuple
    positional_params: tuple
    keyword_only_params: tuple
    vararg: str
    kwarg: str
    defaults: tuple
    positional_only_params: tuple


## Definition collection mixed into SingleFileAnalyzer.
class SingleFileDefinitionMixin:
    ## Collect statically declared pytest parameter values.
    #
    #  pytest.mark.parametrize supplies concrete call-site-like evidence for
    #  test parameters even though pytest performs the invocation at runtime.
    #  Only literal parameter names and literal value sequences are accepted.
    #  @param node Function definition carrying decorators.
    #  @param qualname Qualified function name.
    #  @param params Declared function parameter names.
    def _collect_parametrize_sources(self, node, qualname, params):
        for decorator in node.decorator_list:
            if (not isinstance(decorator, ast.Call)
                    or not isinstance(decorator.func, ast.Attribute)
                    or decorator.func.attr != "parametrize"
                    or len(decorator.args) < 2):
                continue
            owner = self.get_base(decorator.func.value)
            owner_top = self.symbols.get_top(owner) if owner else None
            if owner != "pytest" and owner_top != "pytest":
                continue

            names_node = decorator.args[0]
            if (isinstance(names_node, ast.Constant)
                    and isinstance(names_node.value, str)):
                names = [part.strip()
                         for part in names_node.value.split(",")
                         if part.strip()]
            elif isinstance(names_node, (ast.List, ast.Tuple)):
                names = [
                    item.value for item in names_node.elts
                    if (isinstance(item, ast.Constant)
                        and isinstance(item.value, str))
                ]
            else:
                continue
            if not names or any(name not in params for name in names):
                continue

            values_node = decorator.args[1]
            if not isinstance(values_node, (ast.List, ast.Tuple)):
                continue
            for case in values_node.elts:
                case_nodes = (
                    list(case.elts)
                    if len(names) > 1 and isinstance(case, (ast.List, ast.Tuple))
                    else [case]
                )
                if len(case_nodes) != len(names):
                    continue
                for name, value_node in zip(names, case_nodes):
                    source = self._value_source(value_node)
                    if source is not None:
                        self.parameter_sources.setdefault(
                            (qualname, name), []).append(source)

    ## Return a kwargs parameter for a direct __dict__.update contract.
    #  @param node The constructor AST node.
    #  @return kwargs parameter name, or None when no direct contract exists.
    def _constructor_kwargs_parameter(self, node):
        if node.name != "__init__" or node.args.kwarg is None:
            return None
        kwargs_name = node.args.kwarg.arg
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            if (not isinstance(child.func, ast.Attribute)
                    or child.func.attr != "update"
                    or not child.args
                    or not isinstance(child.args[0], ast.Name)
                    or child.args[0].id != kwargs_name):
                continue
            if (isinstance(child.func.value, ast.Attribute)
                    and self._attribute_name(child.func.value)
                    == "self.__dict__"):
                return kwargs_name
        return None

    ## Return one unambiguous wildcard-import owner, when available.
    #
    #  A wildcard import is still import evidence, but it does not identify
    #  the imported symbol.  It is therefore safe to use only when the file
    #  has one unique wildcard source.  Multiple wildcard sources remain
    #  unresolved rather than selecting one by name.
    #  @return Module name or None when wildcard evidence is ambiguous.
    def _unique_wildcard_import_owner(self):
        owners = []
        for owner in self.wildcard_modules:
            if not isinstance(owner, str) or not owner:
                continue
            top = owner.split(".", 1)[0]
            if top not in owners:
                owners.append(top)
        return owners[0] if len(owners) == 1 else None

    ## Return the lexical scope key for local instance field facts.
    #  @return Tuple identifying the current module, class, and function scope.
    def _local_instance_field_scope_key(self):
        scope = tuple(self._class_stack) + tuple(self._func_stack)
        return scope or ("<module>",)

    ## Return lexical scopes eligible for a local instance field lookup.
    #  A binding in the current scope blocks inherited field facts, including
    #  a function-local global rebinding. An unbound name may inherit facts
    #  from enclosing function, class, or module scope.
    #  @param root_name Root name of the instance expression.
    #  @return Scope keys ordered from innermost to outermost.
    def _local_instance_field_scope_keys(self, root_name):
        scope_key = self._local_instance_field_scope_key()
        keys = [scope_key]
        if (root_name in self.current_scope().bindings
                or root_name in self._local_instance_field_shadowed.get(
                    scope_key, set())):
            return keys
        if self._func_stack:
            for depth in range(len(self._func_stack) - 1, 0, -1):
                keys.append(tuple(self._class_stack)
                            + tuple(self._func_stack[:depth]))
        if keys[-1] != ("<module>",):
            keys.append(("<module>",))
        return keys

    ## Record fields established by a local kwargs-backed constructor call.
    #  Only direct keyword arguments are retained. Constructors without an
    #  explicit self.__dict__.update(kwargs) contract remain unresolved.
    #  @param node Assignment node.
    #  @param target_names Names assigned by the node.
    def _record_local_constructor_fields(self, node, target_names):
        scope_key = self._local_instance_field_scope_key()
        shadowed = self._local_instance_field_shadowed.setdefault(
            scope_key, set())
        for target_name in target_names:
            shadowed.add(target_name)
            for key in [key for key in self._local_instance_field_sources
                        if key[0] == scope_key and key[1] == target_name]:
                self._local_instance_field_sources.pop(key, None)
                self._local_instance_field_shapes.pop(key, None)
        if (not isinstance(node.value, ast.Call)
                or not isinstance(node.value.func, ast.Name)):
            return
        class_name = node.value.func.id
        if class_name not in self._constructor_kwargs_contracts:
            return
        keywords = [kw for kw in node.value.keywords if kw.arg is not None]
        for target_name in target_names:
            for keyword in keywords:
                source = self._value_source(keyword.value)
                if source is None:
                    source = self.trace_source(keyword.value)
                if source is not None:
                    self._local_instance_field_sources[
                        (scope_key, target_name, keyword.arg)] = source
                shape = self._expression_container_shape(keyword.value)
                if shape[0]:
                    self._local_instance_field_shapes[
                        (scope_key, target_name, keyword.arg)] = shape

    ## Visit a function definition through declaration, body, and summary stages.
    #  @param node FunctionDef or AsyncFunctionDef AST node.
    def _visit_function_def(self, node):
        facts = self._function_definition_facts(node)
        self._class_receiver_stack.append(facts.receiver_name)
        self._register_function_binding(node, facts)
        self.push_scope(SCOPE_FUNCTION, node.name)
        self._bind_function_parameters(node, facts)
        qualname = self._enter_function_body(node, facts)
        function_id = FunctionId(self.module_name or "", qualname)
        self._caller_stack.append(function_id)
        saved_globals = self._global_names
        self._global_names = set()
        self._mapping_local_names[id(self.current_scope())] = (
            mapping_bound_names(node.body))
        self.generic_visit(node)
        self._global_names = saved_globals
        self._caller_stack.pop()
        self._func_stack.pop()
        self.pop_scope()
        self._class_receiver_stack.pop()
        summary = self._build_function_summary(
            node, facts, qualname, function_id)
        self.module_cg.functions[qualname] = summary
        self._link_method_summary(node, summary)
        self._bind_decorated_target(node.name, node.decorator_list)

    ## Compute parameter and receiver facts in the defining lexical scope.
    #  @param node Function definition AST node.
    #  @return Immutable FunctionDefinitionFacts.
    def _function_definition_facts(self, node):
        is_direct_method = bool(self._class_stack and not self._func_stack)
        positional_nodes = (
            list(getattr(node.args, "posonlyargs", []))
            + list(node.args.args))
        receiver_name = ""
        if is_direct_method:
            decorator_names = {
                self._attribute_name(decorator)
                if isinstance(decorator, ast.Attribute)
                else decorator.id
                for decorator in node.decorator_list
                if isinstance(decorator, (ast.Name, ast.Attribute))
            }
            is_static = any(
                name == "staticmethod"
                or (isinstance(name, str)
                    and name.endswith(".staticmethod"))
                for name in decorator_names)
            if positional_nodes and not is_static:
                receiver_name = positional_nodes[0].arg

        positional_params = tuple(
            arg.arg for arg in positional_nodes
            if arg.arg != receiver_name)
        keyword_only_params = tuple(
            arg.arg for arg in getattr(node.args, "kwonlyargs", [])
            if arg.arg != receiver_name)
        vararg = (
            node.args.vararg.arg
            if (getattr(node.args, "vararg", None) is not None
                and node.args.vararg.arg != "self") else "")
        kwarg = (
            node.args.kwarg.arg
            if (getattr(node.args, "kwarg", None) is not None
                and node.args.kwarg.arg != "self") else "")
        params = positional_params + keyword_only_params
        if vararg:
            params += (vararg,)
        if kwarg:
            params += (kwarg,)

        defaults = {}
        default_nodes = list(getattr(node.args, "defaults", []))
        if default_nodes:
            default_params = positional_nodes[-len(default_nodes):]
            for argument, default_node in zip(default_params, default_nodes):
                source = self._default_argument_source(
                    self._call_edge_argument_source(default_node))
                if source is not None:
                    defaults[argument.arg] = source
        for argument, default_node in zip(
                getattr(node.args, "kwonlyargs", []),
                getattr(node.args, "kw_defaults", [])):
            if default_node is None:
                continue
            source = self._default_argument_source(
                self._call_edge_argument_source(default_node))
            if source is not None:
                defaults[argument.arg] = source
        return FunctionDefinitionFacts(
            is_direct_method, receiver_name, params, positional_params,
            keyword_only_params, vararg, kwarg, tuple(defaults.items()),
            tuple(arg.arg for arg in node.args.posonlyargs
                  if arg.arg in params))

    ## Register the callable in the enclosing scope before visiting its body.
    #  @param node Function definition AST node.
    #  @param facts Precomputed declaration facts.
    def _register_function_binding(self, node, facts):
        self.local.add(node.name)
        if self._class_stack:
            kwargs_name = self._constructor_kwargs_parameter(node)
            if kwargs_name is not None:
                self._constructor_kwargs_contracts[
                    self._class_stack[-1]] = kwargs_name
        if not self._class_stack:
            self.defined_functions.add(node.name)
        callable_key = self._local_callable_key(node.name)
        self._bind_target_name(
            node.name, "local", node, callable_key=callable_key)
        if not node.decorator_list and not facts.is_direct_method:
            self.current_scope().bindings[node.name].mapping_value = (
                self._mapping_facts.callable(FunctionId(
                    self.module_name or "", callable_key)))

    ## Bind declared parameters inside the newly pushed function scope.
    #  @param node Function definition AST node.
    #  @param facts Precomputed declaration facts.
    def _bind_function_parameters(self, node, facts):
        if facts.receiver_name and facts.receiver_name != "self":
            self._bind_target_name(
                facts.receiver_name, "local", node, "parameter")
        arguments = (
            list(getattr(node.args, "posonlyargs", []))
            + list(node.args.args)
            + list(getattr(node.args, "kwonlyargs", [])))
        declared = set(facts.positional_params + facts.keyword_only_params)
        for argument in arguments:
            if argument.arg in declared:
                self._bind_target_name(
                    argument.arg, "local", argument, "parameter")
        if facts.vararg:
            self._bind_target_name(facts.vararg, "local", kind="parameter")
        if facts.kwarg:
            self._bind_target_name(facts.kwarg, "local", kind="parameter")

    ## Enter function stacks and return the qualified definition name.
    #  @param node Function definition AST node.
    #  @param facts Precomputed declaration facts.
    #  @return Qualified function name.
    def _enter_function_body(self, node, facts):
        params = list(facts.params)
        self.function_params[node.name] = params
        if self._class_stack:
            self.function_params[
                self._class_stack[-1] + "." + node.name] = params
        self._func_stack.append(node.name)
        if self._class_stack:
            qualname = self._class_stack[-1] + "." + ".".join(
                self._func_stack)
        else:
            qualname = ".".join(self._func_stack)
        self._collect_parametrize_sources(node, qualname, params)
        return qualname

    ## Build the completed call-graph summary for a visited function body.
    #  @param node Function definition AST node.
    #  @param facts Precomputed declaration facts.
    #  @param qualname Qualified function name.
    #  @param function_id Stable project function identity.
    #  @return FunctionSummary.
    def _build_function_summary(self, node, facts, qualname, function_id):
        returns = self.call_graph_return_sources.get(qualname)
        if returns is None:
            returns = self.return_sources.get(qualname)
        if returns is None and not self._class_stack:
            returns = self.return_sources.get(node.name)
        yield_values = self.call_graph_yield_sources.get(qualname, [])
        yields = (
            make_source_set(yield_values, origin="yield")
            if yield_values else None)
        return_values = self.call_graph_return_values.get(qualname)
        if not self._block_exits(node.body):
            return_values = make_source_set(
                [return_values, PythonShape("NoneType")]
                if return_values is not None else [PythonShape("NoneType")],
                origin="return")
        if yields is not None or isinstance(node, ast.AsyncFunctionDef):
            return_values = UnknownSource("deferred function result")
        return FunctionSummary(
            id=function_id,
            params=list(facts.params),
            returns=returns,
            local_assignments={},
            positional_params=list(facts.positional_params),
            keyword_only_params=list(facts.keyword_only_params),
            vararg=facts.vararg,
            kwarg=facts.kwarg,
            defaults=dict(facts.defaults),
            yields=yields,
            return_values=return_values,
            positional_only_params=list(facts.positional_only_params),
            definition_span=SourceSpan.from_ast(self._file_path, node),
        )

    ## Link a direct method summary into its enclosing class summary.
    #  @param node Function definition AST node.
    #  @param summary Completed FunctionSummary.
    def _link_method_summary(self, node, summary):
        if not self._class_stack:
            return
        class_name = self._class_stack[-1]
        if class_name not in self.module_cg.classes:
            return
        method_qualname = (
            ".".join(self._func_stack) if self._func_stack else node.name)
        self.module_cg.classes[class_name].methods[method_qualname] = summary

    ## Visit a FunctionDef node and register it as a local definition.
    #  @param node The FunctionDef AST node.
    def visit_FunctionDef(self, node):
        self._visit_function_def(node)

    ## Visit an AsyncFunctionDef node and register it as a local definition.
    #  @param node The AsyncFunctionDef AST node.
    def visit_AsyncFunctionDef(self, node):
        self._visit_function_def(node)

    ## Visit a lambda as a first-class local call-graph target.
    #
    #  Inline callbacks stored in literal containers need the same bounded
    #  parameter substitution as named functions. The source location makes
    #  the identity stable without inferring a name from a dispatch key.
    #  @param node Lambda expression.
    def visit_Lambda(self, node):
        qualname = self._local_lambda_key(node)
        positional_nodes = (
            list(getattr(node.args, "posonlyargs", []))
            + list(node.args.args))
        positional_params = [arg.arg for arg in positional_nodes]
        keyword_only_params = [
            arg.arg for arg in getattr(node.args, "kwonlyargs", [])
        ]
        params = list(positional_params) + list(keyword_only_params)
        vararg_name = (
            node.args.vararg.arg if node.args.vararg is not None else "")
        kwarg_name = (
            node.args.kwarg.arg if node.args.kwarg is not None else "")
        if vararg_name:
            params.append(vararg_name)
        if kwarg_name:
            params.append(kwarg_name)

        defaults = {}
        default_nodes = list(getattr(node.args, "defaults", []))
        if default_nodes:
            default_params = positional_nodes[-len(default_nodes):]
            for arg, default_node in zip(default_params, default_nodes):
                source = self._default_argument_source(
                    self._call_edge_argument_source(default_node))
                if source is not None:
                    defaults[arg.arg] = source
        for arg, default_node in zip(
                getattr(node.args, "kwonlyargs", []),
                getattr(node.args, "kw_defaults", [])):
            if default_node is None:
                continue
            source = self._default_argument_source(
                self._call_edge_argument_source(default_node))
            if source is not None:
                defaults[arg.arg] = source

        self._class_receiver_stack.append("")
        self.push_scope(SCOPE_FUNCTION, qualname)
        for arg in positional_nodes:
            self._bind_target_name(arg.arg, "local", arg, "parameter")
        for arg in getattr(node.args, "kwonlyargs", []):
            self._bind_target_name(arg.arg, "local", arg, "parameter")
        if node.args.vararg is not None:
            self._bind_target_name(
                vararg_name, "local", node.args.vararg, "parameter")
        if node.args.kwarg is not None:
            self._bind_target_name(
                kwarg_name, "local", node.args.kwarg, "parameter")
        self.function_params[qualname] = list(params)
        self._func_stack.append(qualname.rsplit(".", 1)[-1])
        fid = FunctionId(self.module_name or "", qualname)
        self._caller_stack.append(fid)
        self.visit(node.body)
        result = self.trace_source(node.body) or self.get_base(node.body)
        result = result or UnknownSource("lambda result")
        self._caller_stack.pop()
        self._func_stack.pop()
        self.pop_scope()
        self._class_receiver_stack.pop()

        self.return_sources[qualname] = result
        self.module_cg.functions[qualname] = FunctionSummary(
            id=fid,
            params=list(params),
            returns=result,
            positional_params=list(positional_params),
            keyword_only_params=list(keyword_only_params),
            vararg=vararg_name,
            kwarg=kwarg_name,
            defaults=defaults,
            positional_only_params=[arg.arg for arg in node.args.posonlyargs],
            definition_span=SourceSpan.from_ast(self._file_path, node),
        )

    ## Qualify a name or attribute through its current lexical import binding.
    #  @param root Expression evaluated in the defining scope.
    #  @return Dotted import path, or None for non-import or ambiguous bindings.
    def _definition_import_path(self, root):
        attributes = []
        while isinstance(root, ast.Attribute):
            attributes.append(root.attr)
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        binding = self.current_scope().lookup(root.id, skip_parent_classes=True)
        if (binding is None or binding.binding_kind != 'import'
                or not isinstance(normalize_source(binding.source), str)):
            return None
        imported = self._import_binding_sources.get(self._binding_key(binding))
        if not isinstance(imported, str) or not imported:
            return None
        return '.'.join([imported] + list(reversed(attributes)))

    ## Recognize the narrow Keras registration contract that returns its class.
    #  @param node Class decorator expression.
    #  @return True for a proven registration call with literal configuration.
    def _is_class_preserving_keras_registration(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)
                or self.current_scope().kind != SCOPE_MODULE
                or self.wildcard_modules
                or self._definition_import_path(node.func)
                != 'tensorflow.keras.utils.register_keras_serializable'):
            return False
        binding = self.current_scope().lookup(node.func.id)
        statements = self._module_tree.body
        if not any(isinstance(statement, ast.ImportFrom)
                   and statement.lineno == binding.lineno
                   for statement in statements):
            return False
        # Only accept an unconditional module import. Some unsupported writes
        # (e.g. walrus or augmented assignment) retain an old import binding;
        # reject visible writes rather than inheriting that stale identity.
        for statement in statements:
            if binding.lineno <= statement.lineno < node.lineno:
                for item in ast.walk(statement):
                    if (isinstance(item, ast.Name) and item.id == node.func.id
                            and isinstance(item.ctx, (ast.Store, ast.Del))):
                        return False
        # TensorFlow v2.10.0 generic_utils.register_keras_serializable records
        # the class in registries and returns the same arg. Keep this contract
        # specific to that API; unknown decorators may replace the class.
        if len(node.args) > 2:
            return False
        arguments = dict(zip(('package', 'name'), node.args))
        for keyword in node.keywords:
            if keyword.arg not in ('package', 'name') or keyword.arg in arguments:
                return False
            arguments[keyword.arg] = keyword.value
        for name, value in arguments.items():
            if not isinstance(value, ast.Constant):
                return False
            if not (isinstance(value.value, str)
                    or (name == 'name' and value.value is None)):
                return False
        return True

    ## Capture a simple single base's import path at class definition time.
    #  @param node ClassDef node.
    #  @return Import-backed dotted path, or None for unsupported inheritance.
    def _super_base_import_path(self, node):
        if len(node.bases) != 1 or node.keywords:
            return None
        if any(not self._is_class_preserving_keras_registration(decorator)
               for decorator in node.decorator_list):
            return None
        return self._definition_import_path(node.bases[0])

    ## Visit a ClassDef node and register it with its method and base lists.
    #  @param node The ClassDef AST node.
    def visit_ClassDef(self, node):
        super_base_path = self._super_base_import_path(node)
        self.local.add(node.name)
        self._bind_target_name(node.name, "local", node)
        methods = []
        bases = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        for base_node in node.bases:
            base_symbol = None
            if isinstance(base_node, ast.Name):
                base_symbol = base_node.id
            elif isinstance(base_node, ast.Attribute):
                base_symbol = self._attribute_name(base_node) or self.get_base(base_node)
            else:
                base_symbol = self.get_base(base_node)
            if base_symbol:
                bases.append(base_symbol)
        self.class_methods[node.name] = methods
        self.class_bases[node.name] = bases
        ## Create ClassSummary BEFORE generic_visit so methods can link to it.
        class_id = FunctionId(self.module_name or "", node.name)
        self.module_cg.classes[node.name] = ClassSummary(
            id=class_id,
            bases=list(bases),
            methods={},
            attrs={},
            definition_span=SourceSpan.from_ast(self._file_path, node),
        )
        self._class_stack.append(node.name)
        self._super_base_path_stack.append((
            super_base_path,
            'tensorflow.keras.utils'
            if super_base_path and node.decorator_list else None,
        ))
        self.push_scope(SCOPE_CLASS, node.name)
        self.generic_visit(node)
        self.pop_scope()
        self._class_stack.pop()
        self._super_base_path_stack.pop()
        ## Populate ClassSummary attrs collected during class body visit.
        class_attrs = {}
        for (cn, attr_name), src in self.instance_attrs.items():
            if cn == node.name:
                class_attrs[attr_name] = src
        self.module_cg.classes[node.name].attrs.update(class_attrs)
        self._bind_decorated_target(node.name, node.decorator_list)
