## @package pcresolve.single_file
#  Provide single-file AST-based API call tracing.
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved top-level origin libraries.

import ast
import builtins
from .symbol_table import SymbolTable
from .scope import Scope, Binding, SCOPE_MODULE, SCOPE_FUNCTION, SCOPE_CLASS, SCOPE_COMPREHENSION
from .sources import (ContainerItem, ContainerIter, InstanceMethod, CallResult,
                       normalize_source, source_display)

## Python 2 builtins not present in Python 3's builtins module.
_PY2_BUILTINS = frozenset({
    "apply", "basestring", "buffer", "cmp", "coerce", "execfile",
    "file", "intern", "long", "raw_input", "reduce", "reload",
    "StandardError", "unichr", "unicode", "xrange",
})


## Check if a name is a Python builtin (including Python 2 builtins).
def _is_builtin(name):
    return isinstance(name, str) and (hasattr(builtins, name) or name in _PY2_BUILTINS)
from .types import FileAnalysis, ApiCall


## AST visitor that traces all symbols and API calls in a single Python file.
#
#  Walks the AST to:
#  - Record import mappings and their aliases
#  - Track assignments, function/class definitions, decorators
#  - Resolve with/for return-value flows
#  - Handle container indexing, class inheritance, method resolution
#  - Detect and classify all API call expressions
class SingleFileAnalyzer(ast.NodeVisitor):
    ## Initialize the analyzer with empty state.
    #  @param module_name Optional dotted module name for resolving relative imports.
    #  @param is_package Whether the file is a package __init__.py.
    #  @param scope_model "v1" (legacy single-slot) or "v2" (lexical scopes).
    def __init__(self, module_name=None, is_package=False, scope_model="v1"):
        self.module_name = module_name
        self.is_package = is_package
        self.scope_model = scope_model
        self.return_sources = {}
        self.symbols = SymbolTable(self.return_sources)
        self.api_calls = []
        self.attr_accesses = []
        self.local = set()
        self._func_stack = []
        self._class_stack = []
        self._seen_api_call_ids = set()
        self.defined_functions = set()
        self.function_params = {}
        self.container_items = {}
        self.container_lengths = {}
        self.container_set_sources = {}
        self.class_methods = {}
        self.class_bases = {}
        self.import_from_symbols = {}
        self.wildcard_modules = []
        self.call_sites = {}
        self.call_assign_funcs = {}
        self._assignment_counter = 0
        self.module_scope = Scope(SCOPE_MODULE, self.module_name or "<module>")
        self.scope_stack = [self.module_scope]

    ## Return the current innermost scope.
    def current_scope(self):
        return self.scope_stack[-1]

    ## Push a new scope onto the stack.
    #  @param kind Scope kind constant.
    #  @param name Human-readable scope name.
    #  @return The new Scope.
    def push_scope(self, kind, name):
        parent = self.current_scope()
        scope = Scope(kind, name, parent)
        self.scope_stack.append(scope)
        return scope

    ## Pop the current scope from the stack.
    #  @return The popped Scope.
    def pop_scope(self):
        return self.scope_stack.pop()

    ## Bind a name in the current scope and optionally in the compat symbols table.
    #
    #  In v2 mode, only module-scope bindings also go into self.symbols.
    #  In v1 mode, all bindings write to self.symbols (legacy behaviour).
    #  @param name Symbol name.
    #  @param source Source value.
    #  @param node Optional AST node for position info.
    def _bind_target_name(self, name, source, node=None):
        self._assignment_counter += 1
        lineno = getattr(node, "lineno", 0) if node is not None else 0
        col = getattr(node, "col_offset", 0) if node is not None else 0
        self.current_scope().bind(name, source, lineno, col, self._assignment_counter)
        if self.scope_model == "v1" or self.current_scope().kind == SCOPE_MODULE:
            self.symbols.add(name, source)

    ## Look up a name in the lexical scope chain (v2) or return the name as-is.
    #
    #  Unified helper so that trace_source, get_base, and _resolve_call_receiver
    #  all use the same scope-aware resolution.
    #  @param name The raw AST name string.
    #  @return Scope binding source in v2, or the name itself in v1 / not found.
    def _lookup_name_source(self, name):
        if self.scope_model == "v2":
            binding = self.current_scope().lookup(name)
            if binding is not None:
                return binding.source
        return name

    ## --- Import visitors ---

    ## Visit an Import node and record alias-to-module mappings.
    #  @param node The Import AST node.
    def visit_Import(self, node):
        for alias in node.names:
            symbol = alias.asname if alias.asname else alias.name
            self._bind_target_name(symbol, alias.name, node)
        self.generic_visit(node)

    ## Visit an ImportFrom node and record alias-to-module mappings.
    #  @param node The ImportFrom AST node.
    def visit_ImportFrom(self, node):
        for alias in node.names:
            symbol = alias.asname if alias.asname else alias.name
            if symbol == '*':
                if node.module:
                    if node.level > 0 and self.module_name:
                        resolved = self._resolve_relative_import(node.module, node.level)
                        self.wildcard_modules.append(resolved)
                    else:
                        self.wildcard_modules.append(node.module)
                continue
            if node.level > 0 and self.module_name:
                resolved = self._resolve_relative_import(node.module, node.level)
                self._bind_target_name(symbol, resolved, node)
                self.import_from_symbols[symbol] = (resolved + '.' + alias.name) if resolved else alias.name
            else:
                self._bind_target_name(symbol, node.module, node)
                self.import_from_symbols[symbol] = (node.module + '.' + alias.name) if node.module else alias.name
        self.generic_visit(node)

    ## Resolve a relative import to its full dotted module name.
    #  @param module The module portion after the dots (may be None for "from . import X").
    #  @param level The number of leading dots (1 = current package, 2 = parent, etc.).
    #  @return The full dotted module name.
    def _resolve_relative_import(self, module, level):
        if not self.module_name:
            return module or ''
        parts = self.module_name.split('.')
        ## __package__: for packages use module_name, else use parent
        if self.is_package:
            pkg_parts = parts
        else:
            if len(parts) < 2:
                return module or ''
            pkg_parts = parts[:-1]
        ## level dots = go up (level-1) from __package__
        strip = level - 1
        if strip >= len(pkg_parts):
            base = ''
        elif strip == 0:
            base = '.'.join(pkg_parts)
        else:
            base = '.'.join(pkg_parts[:-strip])
        if module:
            return f"{base}.{module}" if base else module
        return base

    ## --- Source tracing ---

    ## Trace an AST expression node back to its source symbol/structured origin.
    #
    #  Handles Name, Call, Attribute, Lambda, Subscript, and literal nodes.
    #  For Call nodes, tries getattr(), importlib.import_module(), partial(),
    #  method resolution, and chained-call receiver resolution.
    #  @param node The AST expression node.
    #  @return A symbol string, a structured tuple, or None.
    def trace_source(self, node):
        if isinstance(node, ast.Name):
            return self._lookup_name_source(node.id)
        elif isinstance(node, ast.Call):
            getattr_src = self._resolve_getattr_trace(node)
            if getattr_src:
                return getattr_src
            import_mod = self._resolve_import_module_trace(node)
            if import_mod:
                return import_mod
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0])
            me = self._resolve_methods(node)
            if me:
                return me
            ## For chained calls (A().B()), resolve via the inner call's
            ## return source so the outer call traces to the correct library.
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                inner_source = self.trace_source(node.func.value)
                if isinstance(inner_source, str):
                    rs = self.return_sources.get(inner_source)
                    if rs is not None:
                        return rs
                if inner_source:
                    return inner_source
            call_key = self.get_base(node, call_lookup=True)
            if call_key:
                if isinstance(call_key, CallResult):
                    return call_key
                return CallResult(call_key)
            return self.get_base(node.func)
        elif isinstance(node, ast.Attribute):
            name = self._attribute_name(node)
            if name and name in self.symbols.direct:
                return name
            return self.get_base(node)
        elif isinstance(node, ast.Lambda):
            body_base = self.get_base(node.body)
            if isinstance(body_base, str):
                param_names = {a.arg for a in node.args.args}
                if node.args.vararg:
                    param_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    param_names.add(node.args.kwarg.arg)
                if body_base in param_names:
                    return "local"
            return body_base
        elif isinstance(node, ast.Subscript):
            container_name = self.trace_source(node.value)
            key_idx = self._get_slice(node.slice)
            if container_name is not None and key_idx is not None:
                key_value = self._container_index(container_name, key_idx)
                lookup_key = (container_name, key_value)
                if lookup_key in self.container_items:
                    return self.container_items[lookup_key]
                return ContainerItem(container_name, key_idx)
            return container_name
        elif isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
            if isinstance(node, ast.Dict):
                value_nodes = node.values
            else:
                value_nodes = node.elts
            bases = set()
            for v in value_nodes:
                base = self.get_base(v)
                if base:
                    bases.add(base)
            if len(bases) == 1:
                return next(iter(bases))
            return None
        elif isinstance(node, ast.Constant):
            return None
        return None

    ## Extract a string literal from an AST node.
    #  @param node The AST node.
    #  @return String value, or None.
    def _literal_str(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    ## Check if a call node is a functools.partial() call.
    #  @param node The Call AST node.
    #  @return True if the call is partial().
    def _is_partial_call(self, node):
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        if isinstance(func, ast.Name) and func.id == 'partial':
            return True
        if isinstance(func, ast.Attribute) and func.attr == 'partial':
            return True
        return False

    ## Check if a call node is a getattr() call.
    #  @param node The Call AST node.
    #  @return True if the call is getattr().
    def _is_getattr_call(self, node):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            return False
        func = node.func
        if isinstance(func, ast.Name) and func.id == "getattr":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "getattr":
            return True
        return False

    ## Resolve a getattr(obj, name) call to the object's base.
    #  @param node The Call AST node.
    #  @return The object's source, or None.
    def _resolve_getattr_trace(self, node):
        if not self._is_getattr_call(node):
            return None
        name_lit = self._literal_str(node.args[1])
        if name_lit is None:
            return None
        obj_key = self.trace_source(node.args[0])
        if obj_key is None:
            return None
        return obj_key

    ## Check if a symbol ultimately originates from importlib.
    #  @param symbol The symbol to check.
    #  @return True if the symbol traces to importlib.
    def _is_importlib_module(self, symbol):
        if not isinstance(symbol, str):
            return False
        if symbol == "importlib":
            return True
        top = self.symbols.get_top(symbol)
        return top == "importlib"

    ## Check if a call node is importlib.import_module().
    #  @param node The Call AST node.
    #  @return True if the call is import_module().
    def _is_import_module_call(self, node):
        if not isinstance(node, ast.Call) or not node.args:
            return False
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            root = self.get_base(func.value)
            if root and self._is_importlib_module(root):
                return True
            return False
        if isinstance(func, ast.Name) and func.id == "import_module":
            if (self.import_from_symbols.get("import_module") or "").startswith("importlib"):
                return True
            return False
        return False

    ## Resolve an importlib.import_module("name") call to the module name.
    #  @param node The Call AST node.
    #  @return The module name string, or None.
    def _resolve_import_module_trace(self, node):
        if not self._is_import_module_call(node):
            return None
        name = self._literal_str(node.args[0])
        if name is None:
            return None
        return name

    ## Extract a constant integer or negated constant from a slice node.
    #  @param slice_node The AST slice node.
    #  @return Integer value, or None.
    def _get_slice(self, slice_node):
        if isinstance(slice_node, ast.Constant):
            return slice_node.value
        if isinstance(slice_node, ast.UnaryOp) and isinstance(slice_node.op, ast.USub) and isinstance(slice_node.operand, ast.Constant):
            return -slice_node.operand.value
        return None

    ## Normalize a negative container index to its positive equivalent.
    #  @param container_name The name of the container variable.
    #  @param idx The raw index value.
    #  @return Adjusted index value.
    def _container_index(self, container_name, idx):
        if not isinstance(idx, int):
            return idx
        if idx >= 0:
            return idx
        n = self.container_lengths.get(container_name)
        if n:
            return idx + n
        return idx

    ## --- Method resolution ---

    ## Attempt to resolve an instance method call to a class member.
    #
    #  Handles self.method(), known_object.method(), and chained attribute calls.
    #  @param node The Call AST node.
    #  @return Method name, structured ("instance_method", ...) tuple, or None.
    def _resolve_methods(self, node):
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None
        re = func.value
        method_name = func.attr

        def _resolve_on_class(class_name, receiver_key):
            if not class_name:
                return None
            methods = self.class_methods.get(class_name, [])
            if methods and method_name in methods:
                return method_name
            if class_name in self.class_methods or class_name in self.import_from_symbols:
                return InstanceMethod(receiver_key, method_name)
            return None

        if isinstance(re, ast.Name):
            if re.id == "self" and self._class_stack:
                cn = self._class_stack[-1]
                return _resolve_on_class(cn, cn)
            class_name = self.symbols.direct.get(re.id)
            class_name = normalize_source(class_name)
            if isinstance(class_name, CallResult):
                class_name = class_name.callee
            if not class_name:
                return None
            methods = self.class_methods.get(class_name)
            if methods and method_name in methods:
                return method_name
            if class_name in self.class_methods:
                return InstanceMethod(re.id, method_name)
            if class_name in self.import_from_symbols:
                return InstanceMethod(class_name, method_name)
            return None

        if isinstance(re, ast.Attribute):
            chain = self._attribute_chain_list(re)
            if chain:
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    result = _resolve_on_class(cn, cn)
                    if isinstance(normalize_source(result), InstanceMethod):
                        attr_name = "self." + ".".join(chain[1:])
                        attr_source = self.symbols.direct.get(attr_name)
                        attr_source = normalize_source(attr_source)
                        if isinstance(attr_source, CallResult):
                            callee = attr_source.callee
                            if '.' not in callee and callee in self.symbols.direct:
                                return InstanceMethod(callee, method_name)
                        if isinstance(attr_source, str) and '.' not in attr_source and attr_source in self.symbols.direct:
                            return InstanceMethod(attr_source, method_name)
                    return result
                root = chain[0]
                if root in self.import_from_symbols:
                    return InstanceMethod(root, method_name)
                root_src = self.symbols.direct.get(root)
                root_src = normalize_source(root_src)
                if isinstance(root_src, CallResult):
                    root_src = root_src.callee
                if root_src in self.import_from_symbols:
                    return InstanceMethod(root_src, method_name)
        return None

    ## Flatten an attribute chain (e.g. a.b.c) into a list ["a", "b", "c"].
    #  @param node The starting Attribute node.
    #  @return List of name parts from root to leaf, or None.
    def _attribute_chain_list(self, node):
        parts = []
        remain = node
        while isinstance(remain, ast.Attribute):
            parts.append(remain.attr)
            remain = remain.value
        if isinstance(remain, ast.Name):
            parts.append(remain.id)
            return list(reversed(parts))
        return None

    ## Reconstruct a dotted attribute name from an AST node.
    #  @param node The Attribute or Name node.
    #  @return Dotted name string (e.g. "os.path.join"), or None.
    def _attribute_name(self, node):
        chain = self._attribute_chain_list(node)
        if chain:
            return ".".join(chain)
        return None

    ## Find the root receiver of a call expression.
    #
    #  Unwinds chained calls and attributes to find the base object.
    #  @param receiver_node The receiver AST node.
    #  @return Base symbol name, or None.
    def _resolve_call_receiver(self, receiver_node):
        if isinstance(receiver_node, ast.Name):
            return self._lookup_name_source(receiver_node.id)
        if isinstance(receiver_node, ast.Attribute):
            receiver_name = self._attribute_name(receiver_node)
            if receiver_name is not None:
                return receiver_name
            return self._resolve_call_receiver(receiver_node.value)
        if isinstance(receiver_node, ast.Call):
            inner_receiver = self.get_base(receiver_node, call_lookup=True)
            if inner_receiver is not None:
                return inner_receiver
            return self.get_base(receiver_node.func, call_lookup=False)
        if isinstance(receiver_node, ast.BinOp):
            left = self.get_base(receiver_node.left, call_lookup=True)
            if left is not None:
                return left
            return self.get_base(receiver_node.right, call_lookup=True)
        if isinstance(receiver_node, ast.Subscript):
            return self._resolve_call_receiver(receiver_node.value)
        return None

    ## --- Decorator binding ---

    ## Bind a decorated target to its decorator's source.
    #
    #  Applies decorators from innermost to outermost, so the target resolves
    #  to whatever the outermost decorator returns.
    #  @param target_name Name of the decorated function/class.
    #  @param decorator_nodes List of decorator AST nodes.
    def _bind_decorated_target(self, target_name, decorator_nodes):
        if not decorator_nodes:
            return
        current_source = target_name
        for deco in reversed(decorator_nodes):
            deco_source = self.trace_source(deco)
            if deco_source and not (isinstance(deco_source, str) and _is_builtin(deco_source)):
                current_source = deco_source
        if current_source and current_source != target_name:
            self._bind_target_name(target_name, current_source)

    ## --- Assignment helpers ---

    ## Bind assignment targets to a source value.
    #
    #  Handles simple names, self.attr, and tuple/list unpacking.
    #  @param target The assignment target AST node.
    #  @param source The source symbol or structured tuple.
    def _target_to_source(self, target, source):
        if not source:
            return
        if isinstance(target, ast.Name):
            self._bind_target_name(target.id, source, target)
            return
        if isinstance(target, ast.Attribute):
            name = self._attribute_name(target)
            if name and name.startswith("self."):
                self._bind_target_name(name, source, target)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._target_to_source(elt, source)

    ## Trace the source of a for-loop iterator.
    #  @param iter_node The iterator AST node.
    #  @return Source symbol, structured tuple, or None.
    def _iter_source(self, iter_node):
        if isinstance(iter_node, ast.Name):
            container_name = iter_node.id
            has_items = False
            for k in self.container_items.keys():
                if k[0] == container_name:
                    has_items = True
                    break
            has_set = container_name in self.container_set_sources
            if has_items or has_set:
                return ContainerIter(container_name)
        source = self.trace_source(iter_node)
        if source:
            return source
        return self.get_base(iter_node)

    ## --- Base extraction ---

    ## Extract the root/base name from an expression node.
    #
    #  For simple names returns the name. For attributes returns the chain root.
    #  For calls with call_lookup=True, resolves the call receiver.
    #  @param node The AST expression node.
    #  @param call_lookup If True, resolve call receivers instead of just func base.
    #  @return Root symbol name, or None.
    def get_base(self, node, call_lookup=False):
        if isinstance(node, ast.Name):
            return self._lookup_name_source(node.id)
        elif isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            if chain:
                name = '.'.join(chain)
                if name in self.symbols.direct:
                    return name
                return chain[0]
            return self.get_base(node.value, call_lookup=call_lookup)
        elif isinstance(node, ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0], call_lookup=call_lookup)
            if call_lookup:
                func = node.func
                if isinstance(func, ast.Attribute):
                    return self._resolve_call_receiver(func.value)
                if isinstance(func, ast.Call):
                    return self._resolve_call_receiver(func)
                if isinstance(func, ast.Name):
                    return self._lookup_name_source(func.id)
                return None
            return self.get_base(node.func, call_lookup=False)
        elif isinstance(node, ast.BinOp):
            left = self.get_base(node.left, call_lookup=call_lookup)
            if left is not None:
                return left
            return self.get_base(node.right, call_lookup=call_lookup)
        elif isinstance(node, ast.Lambda):
            return self.get_base(node.body, call_lookup=call_lookup)
        elif isinstance(node, ast.Subscript):
            return self.get_base(node.value, call_lookup=call_lookup)
        return None

    ## --- Visit handlers ---

    ## Visit an Assign node and record symbol bindings.
    #
    #  Handles dict/list/tuple/set container tracking, and traces the
    #  right-hand side to bind target symbols.
    #  @param node The Assign AST node.
    def visit_Assign(self, node):
        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    for key_node, value_node in zip(node.value.keys, node.value.values):
                        if isinstance(key_node, ast.Constant):
                            key_value = key_node.value
                            value_source = self.get_base(value_node)
                            if value_source:
                                self.container_items[(container_name, key_value)] = value_source

        if isinstance(node.value, (ast.List, ast.Tuple)):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    n = len(node.value.elts)
                    self.container_lengths[container_name] = n
                    for i, elt in enumerate(node.value.elts):
                        value_source = self.get_base(elt)
                        if value_source:
                            self.container_items[(container_name, i)] = value_source

        if isinstance(node.value, ast.Set):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    bases = set()
                    for elt in node.value.elts:
                        base = self.get_base(elt)
                        if base:
                            bases.add(base)
                    if bases:
                        self.container_set_sources[container_name] = bases

        right = self.trace_source(node.value)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            func_full = self._attribute_name(node.value.func)
            if func_full:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.call_assign_funcs[target.id] = func_full
        if right:
            right_norm = normalize_source(right)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if (
                        isinstance(right_norm, InstanceMethod)
                        and right_norm.receiver == target.id
                    ):
                        continue
                    if (
                        isinstance(right_norm, CallResult)
                        and (right_norm.callee == target.id or (isinstance(right_norm.callee, str) and right_norm.callee.startswith(target.id + ".")))
                    ):
                        continue
                    ## skip self-assign: df = df[...] where right resolves to "df"
                    if isinstance(right, str) and right == target.id:
                        continue
                    self._bind_target_name(target.id, right, target)
                elif isinstance(target, ast.Attribute):
                    name = self._attribute_name(target)
                    if name and name.startswith("self."):
                        if isinstance(right_norm, InstanceMethod):
                            continue
                        self._bind_target_name(name, right, target)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            if isinstance(right_norm, InstanceMethod):
                                continue
                            self._bind_target_name(elt.id, right, elt)
        else:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._bind_target_name(target.id, 'local', target)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            self._bind_target_name(elt.id, 'local', elt)
        self.generic_visit(node)

    ## --- API call detection ---

    ## Resolve the base of an API call for origin tracking.
    #
    #  Tries getattr(), import_module(), method resolution, and
    #  call-lookup receiver resolution in order.
    #  @param node The Call AST node.
    #  @return Base symbol, structured tuple, or None.
    def _resolve_call_base_for_api(self, node):
        if self._is_getattr_call(node):
            if self._literal_str(node.args[1]) is not None:
                g = self.trace_source(node.args[0])
                if g is not None:
                    return g
        if self._is_import_module_call(node):
            im = self._resolve_import_module_trace(node)
            if im is not None:
                return im
        base = self._resolve_methods(node)
        if base is not None:
            return base
        ## For chained calls (A().B()), resolve via the inner call's
        ## return source so the outer call traces to the correct library.
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            inner_source = self.trace_source(node.func.value)
            if isinstance(inner_source, str):
                rs = self.return_sources.get(inner_source)
                if rs is not None:
                    return rs
        call_lookup_base = self.get_base(node, call_lookup=True)
        if call_lookup_base is not None:
            return call_lookup_base
        return self.get_base(node.func)

    ## Collect all prefix calls in a chained call expression.
    #
    #  For a.b().c().d(), returns [a.b(), c(), d()] in call order.
    #  @param node The outermost Call AST node.
    #  @return List of Call nodes from outermost to innermost chain, reversed.
    def _chained_prefix_calls(self, node):
        if not isinstance(node, ast.Call):
            return []
        out = []
        cur = node
        while isinstance(cur, ast.Call):
            out.append(cur)
            f = cur.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call):
                cur = f.value
            else:
                break
        out.reverse()
        return out

    ## Record a single API call with its resolved top-level origin.
    #  @param node The Call AST node.
    def _one_api_call(self, node):
        if id(node) in self._seen_api_call_ids:
            return
        self._seen_api_call_ids.add(id(node))
        api_string = self.get_call(node)
        func_name, parameters = self._get_call_parts(node)
        base = self._resolve_call_base_for_api(node)
        if not base:
            return

        if isinstance(node.func, ast.Name):
            direct_name = node.func.id
        else:
            direct_name = None

        loc = {
            'func_name': func_name,
            'parameters': parameters,
            'lineno': node.lineno,
            'col_offset': node.col_offset,
            'end_lineno': getattr(node, 'end_lineno', 0) or 0,
            'end_col_offset': getattr(node, 'end_col_offset', 0) or 0,
        }

        if isinstance(base, CallResult):
            # Resolve top through the callee so s.get() shows 'requests'
            # instead of 'requests()' when s = Session().
            callee = base.callee
            if isinstance(callee, str):
                rs = self.return_sources.get(callee)
                if rs is not None:
                    resolved = normalize_source(rs)
                    if isinstance(resolved, CallResult):
                        inner_callee = resolved.callee
                        if isinstance(inner_callee, str):
                            callee = inner_callee
                top = self.symbols.get_top(callee) or source_display(base)
            else:
                top = source_display(base)
            chain = [source_display(base)] if (self.scope_model == "v2") else []
            record = {
                'api': api_string,
                'top': top,
                'chain': chain,
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            return

        if isinstance(base, tuple) or isinstance(base, (ContainerItem, ContainerIter, InstanceMethod)):
            display = source_display(base)
            chain = [display] if (self.scope_model == "v2" and display) else []
            record = {
                'api': api_string,
                'top': display,
                'chain': chain,
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            return

        # Handle "local" base (v2 scope binding returns "local" for params/locals)
        if base == "local":
            record = {
                'api': api_string,
                'top': 'local',
                'chain': ['local'],
                'base': 'local',
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            return

        top = self.symbols.get_top(base)
        if not top:
            return

        record = {
            'api': api_string,
            'top': top,
            'chain': self.symbols.get_chain(base),
            'base': base,
            'direct_name_callee': direct_name,
        }
        record.update(loc)
        self.api_calls.append(record)

    ## Return (func_str, args_str) tuple for a Call node.
    #  @param node The Call AST node.
    #  @return Tuple of (function expression, arguments string).
    def _get_call_parts(self, node):
        func_str = ast.unparse(node.func)
        parts = [ast.unparse(a) for a in node.args]
        if node.keywords:
            for kw in node.keywords:
                if kw.arg:
                    parts.append(f"{kw.arg}={ast.unparse(kw.value)}")
                else:
                    parts.append(f"**{ast.unparse(kw.value)}")
        args_str = ", ".join(parts)
        return func_str, args_str

    ## Reconstruct a call expression as a string.
    #  @param node The Call AST node.
    #  @return String representation like "func(arg1, arg2, kw=val)".
    def get_call(self, node):
        func_str, args_str = self._get_call_parts(node)
        return f"{func_str}({args_str})"

    ## Visit a Call node and record API calls from its chained prefix calls.
    #  @param node The Call AST node.
    def visit_Call(self, node):
        for sub in self._chained_prefix_calls(node):
            self._one_api_call(sub)
        if isinstance(node.func, ast.Name) and node.func.id in self.defined_functions:
            arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(name if name else self.trace_source(arg))
                else:
                    arg_sources.append(self.trace_source(arg))
            self.call_sites.setdefault(node.func.id, []).append({
                "module": self.module_name,
                "args": arg_sources,
            })
        self.generic_visit(node)

    ## Visit an Attribute access node and record the top-level origin.
    #  @param node The Attribute AST node.
    def visit_Attribute(self, node):
        attr_string = ast.unparse(node)
        name = self._attribute_name(node)
        if name and name in self.symbols.direct:
            base = name
        else:
            base = self.get_base(node)
        if base:
            top = self.symbols.get_top(base)
            if top:
                self.attr_accesses.append({
                    'attr': attr_string,
                    'top': top,
                    'chain': self.symbols.get_chain(base)
                })
        self.generic_visit(node)

    ## Visit a FunctionDef node and register it as a local definition.
    #  @param node The FunctionDef AST node.
    def _visit_function_def(self, node):
        """Common handler for FunctionDef and AsyncFunctionDef."""
        self.local.add(node.name)
        self.defined_functions.add(node.name)
        self._bind_target_name(node.name, "local", node)
        params = []
        self.push_scope(SCOPE_FUNCTION, node.name)
        for arg in (getattr(node.args, "posonlyargs", []) + node.args.args + getattr(node.args, "kwonlyargs", [])):
            if arg.arg != "self":
                params.append(arg.arg)
                self._bind_target_name(arg.arg, "local", arg)
        if getattr(node.args, "vararg", None) is not None and node.args.vararg.arg != "self":
            params.append(node.args.vararg.arg)
            self._bind_target_name(node.args.vararg.arg, "local")
        if getattr(node.args, "kwarg", None) is not None and node.args.kwarg.arg != "self":
            params.append(node.args.kwarg.arg)
            self._bind_target_name(node.args.kwarg.arg, "local")
        self.function_params[node.name] = params
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()
        self.pop_scope()
        self._bind_decorated_target(node.name, node.decorator_list)

    ## Visit a FunctionDef node and register it as a local definition.
    #  @param node The FunctionDef AST node.
    def visit_FunctionDef(self, node):
        self._visit_function_def(node)

    ## Visit an AsyncFunctionDef node and register it as a local definition.
    #  @param node The AsyncFunctionDef AST node.
    def visit_AsyncFunctionDef(self, node):
        self._visit_function_def(node)

    ## Visit a ClassDef node and register it with its method and base lists.
    #  @param node The ClassDef AST node.
    def visit_ClassDef(self, node):
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
        self._class_stack.append(node.name)
        self.push_scope(SCOPE_CLASS, node.name)
        self.generic_visit(node)
        self.pop_scope()
        self._class_stack.pop()
        self._bind_decorated_target(node.name, node.decorator_list)

    ## Visit a With node and bind context-variable aliases.
    #  @param node The With AST node.
    def visit_With(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)

    ## Visit an AsyncWith node and bind context-variable aliases.
    #  @param node The AsyncWith AST node.
    def visit_AsyncWith(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)

    ## Visit a For node and bind the loop variable to the iterator source.
    #  @param node The For AST node.
    def visit_For(self, node):
        source = self._iter_source(node.iter)
        self._target_to_source(node.target, source)
        self.generic_visit(node)

    ## Visit an AsyncFor node and bind the loop variable to the iterator source.
    #  @param node The AsyncFor AST node.
    def visit_AsyncFor(self, node):
        source = self._iter_source(node.iter)
        self._target_to_source(node.target, source)
        self.generic_visit(node)

    ## Common handler for all comprehension node types.
    #  @param node A ListComp, SetComp, DictComp, or GeneratorExp AST node.
    def _visit_comprehension(self, node):
        self.push_scope(SCOPE_COMPREHENSION, "<comprehension>")
        for gen in node.generators:
            source = self._iter_source(gen.iter)
            self._target_to_source(gen.target, source)
        self.generic_visit(node)
        self.pop_scope()

    ## Visit a ListComp node and bind loop variables to the iterator source.
    #  @param node The ListComp AST node.
    def visit_ListComp(self, node):
        self._visit_comprehension(node)

    ## Visit a DictComp node and bind loop variables to the iterator source.
    #  @param node The DictComp AST node.
    def visit_DictComp(self, node):
        self._visit_comprehension(node)

    ## Visit a SetComp node and bind loop variables to the iterator source.
    #  @param node The SetComp AST node.
    def visit_SetComp(self, node):
        self._visit_comprehension(node)

    ## Visit a GeneratorExp node and bind loop variables to the iterator source.
    #  @param node The GeneratorExp AST node.
    def visit_GeneratorExp(self, node):
        self._visit_comprehension(node)

    ## Visit a Return node and record return-value flow for the function.
    #  @param node The Return AST node.
    def visit_Return(self, node):
        if self._func_stack and node.value is not None:
            func_name = self._func_stack[-1]
            if not isinstance(node.value, ast.Constant):
                source = self.trace_source(node.value)
                if source:
                    if isinstance(source, str) and source in self.symbols.direct:
                        s = self.symbols.direct[source]
                        self.return_sources[func_name] = s if s else source
                    else:
                        self.return_sources[func_name] = source
        self.generic_visit(node)


## Analyze a single Python source string and return structured results.
#
#  Convenience function that parses source code and runs a full analysis
#  pass, returning a FileAnalysis object.
#  @param source Python source code as a string.
#  @param file_path Optional file path for the FileAnalysis record.
#  @return FileAnalysis with symbols, chains, and API calls.
## Analyze a single source string and return per-file results.
#  @param source Python source code string.
#  @param file_path Optional file path for reporting.
#  @param scope_model "v1" (legacy) or "v2" (lexical scopes).
#  @return FileAnalysis object.
def analyze_source(source, file_path="<string>", scope_model="v1"):
    tree = ast.parse(source)
    tracer = SingleFileAnalyzer(scope_model=scope_model)
    tracer.visit(tree)
    return FileAnalysis(
        file_path=file_path,
        module_name="",
        symbols=dict(tracer.symbols.direct),
        chains=dict(tracer.symbols.chains),
        api_calls=[
            ApiCall(
                expression=c['api'],
                top_library=c['top'],
                base_symbol=source_display(c.get('base', '')),
                chain=c.get('chain', []),
                file_path=file_path,
                lineno=c.get('lineno', 0),
                col_offset=c.get('col_offset', 0),
                end_lineno=c.get('end_lineno', 0),
                end_col_offset=c.get('end_col_offset', 0),
                func_name=c.get('func_name', ''),
                parameters=c.get('parameters', ''),
                resolved_func=c.get('func_name', ''),
                resolved_chain=[c.get('func_name', ''), c.get('func_name', ''), c.get('top', '')],
            )
            for c in tracer.api_calls
        ],
    )
