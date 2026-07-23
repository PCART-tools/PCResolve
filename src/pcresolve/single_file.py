## @package pcresolve.single_file
#  Provide single-file AST-based API call tracing.
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved top-level origin libraries.

import ast
import builtins
from .symbol_table import SymbolTable
from .ir import CallSite, SymbolRef
from .scope import (Scope, Binding, SCOPE_MODULE, SCOPE_FUNCTION, SCOPE_CLASS,
                       SCOPE_COMPREHENSION, merge_snapshots)
from .sources import (ContainerItem, ContainerIter, InstanceMethod,
                       ParameterSource, SuperMethod, CallResult,
                       DerivedResult, UnknownSource,
                       SourceSet, is_structured_source, normalize_source,
                       source_display, make_source_set)
from .call_graph import (FunctionId, FunctionSummary, ClassSummary, CallEdge,
                         ModuleCallGraph)

## Python 2 builtins not present in Python 3's builtins module.
_PY2_BUILTINS = frozenset({
    "apply", "basestring", "buffer", "cmp", "coerce", "execfile",
    "file", "intern", "long", "raw_input", "reduce", "reload",
    "StandardError", "unichr", "unicode", "xrange",
})

## 1.0.5 P1: builtin container/type method names whose receiver is a
#  Python-provided object even when the receiver variable is local.
#  When a call like x.append(...) has a receiver tracing to "local"
#  and the method name is in this set, the callable owner is python.
## 1.0.5 P1: builtin container/type methods keyed by container kind.
#  The container kind (list/dict/set/tuple/str) provides context so
#  that method classification is safe from local-class name collisions.
_BUILTIN_CONTAINER_METHODS = {
    "list": frozenset([
        "append", "extend", "insert", "remove", "pop", "clear",
        "index", "count", "sort", "reverse", "copy",
    ]),
    "dict": frozenset([
        "get", "keys", "values", "items", "update", "pop",
        "popitem", "clear", "copy",
    ]),
    "set": frozenset([
        "add", "remove", "discard", "pop", "clear", "copy",
        "update", "difference", "intersection", "union",
        "symmetric_difference", "issubset", "issuperset",
    ]),
    "tuple": frozenset(["count", "index"]),
    "str": frozenset([
        "strip", "rstrip", "lstrip", "split", "rsplit", "join",
        "replace", "find", "rfind", "rindex", "startswith",
        "endswith", "upper", "lower", "title", "capitalize",
        "swapcase", "center", "ljust", "rjust", "encode", "zfill",
        "format", "format_map",
        "isalnum", "isalpha", "isascii", "isdecimal", "isdigit",
        "isidentifier", "islower", "isnumeric", "isprintable",
        "isspace", "istitle", "isupper",
    ]),
}


## Check if a name is a Python builtin (including Python 2 builtins).
def _is_builtin(name):
    return isinstance(name, str) and (hasattr(builtins, name) or name in _PY2_BUILTINS)


## 1.0.5 P2: builtin return-object ownership semantics.
#
#  Maps builtin callable names to their result_source:
#  - "python": result object is a Python-provided type (open, list, str, …).
#  - None: use legacy return_sources / call-graph resolution.
#  - "unknown": result is statically unresolvable (eval, dynamic __import__).
_BUILTIN_PYTHON_OWNED_RESULT = frozenset({
    "open", "super",
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "complex", "frozenset", "object",
    "range", "slice", "memoryview",
    "staticmethod", "classmethod", "property",
    "enumerate", "filter", "map", "zip", "sorted",
    "len", "print", "exec",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "StopIteration", "OSError", "NotImplementedError",
    "AttributeError", "ImportError", "NameError", "SyntaxError",
    "ZeroDivisionError", "OverflowError", "EOFError", "IOError",
    "FileNotFoundError", "StopAsyncIteration",
})

_BUILTIN_ARBITRARY_RESULT = frozenset({
    "eval", "exec",
})

_BUILTIN_ELEMENT_DERIVED = frozenset({"next", "min", "max"})
_BUILTIN_PROTOCOL_DERIVED = frozenset({"abs"})


## Check whether a builtin name is not shadowed by a local definition.
#
#  @param self SingleFileAnalyzer instance.
#  @param node The ast.Call node.
#  @return True if the call is to an unshadowed builtin.
def _is_unshadowed_builtin_call(tracer, node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False
    name = node.func.id
    if not _is_builtin(name):
        return False
    if name in tracer.defined_functions:
        return False
    if name in tracer.import_from_symbols:
        return False
    if name in tracer.local:
        return False
    # Check scope binding for shadowing
    if tracer.scope_model == "v2":
        binding = tracer.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            return False
    return True


## Trace an expression used as a builtin result candidate.
#
#  Literal values are Python-owned.  Other expressions retain their full
#  source IR so cross-file resolution can preserve every possible owner.
#  @param node Candidate AST expression.
#  @param trace_fn Callable to trace an AST expression.
#  @return Source value or UnknownSource.
def _builtin_value_source(node, trace_fn):
    if isinstance(node, ast.Constant):
        return "python"
    source = trace_fn(node)
    if source is not None:
        return source
    return UnknownSource("builtin value")


## Resolve the element source carried by an iterable expression.
#
#  Named containers use ContainerIter so their tracked item bindings remain
#  available cross-file.  iter()/reversed() results expose their element
#  evidence without claiming that the iterator object's owner is the owner of
#  each yielded value.
#  @param node Iterable AST expression.
#  @param trace_fn Callable to trace an AST expression.
#  @return Source value describing the iterable's possible elements.
def _iterable_element_source(node, trace_fn):
    if isinstance(node, ast.Name):
        traced = normalize_source(trace_fn(node))
        if isinstance(traced, CallResult):
            result_source = normalize_source(traced.result_source)
            if (isinstance(result_source, DerivedResult)
                    and result_source.kind == "iterator"
                    and result_source.sources):
                return result_source.sources[0]
        return ContainerIter(node.id)

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        sources = [_builtin_value_source(elt, trace_fn) for elt in node.elts]
        if sources:
            return make_source_set(sources, origin="builtin_element")
        return UnknownSource("empty iterable")

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("iter", "reversed") and node.args:
            return _iterable_element_source(node.args[0], trace_fn)
        if node.func.id == "enumerate" and node.args:
            # enumerate yields Python tuples regardless of the item owner.
            return "python"

    traced = normalize_source(trace_fn(node))
    if isinstance(traced, CallResult):
        result_source = normalize_source(traced.result_source)
        if (isinstance(result_source, DerivedResult)
                and result_source.kind == "iterator"
                and result_source.sources):
            return result_source.sources[0]
    if traced is not None:
        return ContainerIter(traced)
    return UnknownSource("iterable element")


## Resolve element source for min/max/next arguments.
#
#  min/max with multiple values select from those values.  Their one-argument
#  forms and next() select an iterable element.  A default value is a separate
#  possible result and therefore participates in the same SourceSet.
#  @param name Bare builtin name.
#  @param call_node The ast.Call node.
#  @param trace_fn Callable to trace an AST expression.
#  @return DerivedResult("element", ...) or UnknownSource.
def _element_source(name, call_node, trace_fn):
    sources = []
    if name in ("min", "max") and len(call_node.args) > 1:
        sources.extend(_builtin_value_source(arg, trace_fn)
                       for arg in call_node.args)
    elif call_node.args:
        sources.append(_iterable_element_source(call_node.args[0], trace_fn))

    if name in ("min", "max"):
        for keyword in call_node.keywords:
            if keyword.arg == "default":
                sources.append(_builtin_value_source(keyword.value, trace_fn))
    elif name == "next" and len(call_node.args) > 1:
        sources.append(_builtin_value_source(call_node.args[1], trace_fn))

    if not sources:
        return UnknownSource("element")
    return DerivedResult(
        "element", (make_source_set(sources, origin="builtin_element"),))


## Return the result_source for a known builtin callable.
#
#  @param name Bare builtin name.
#  @param call_node The ast.Call node (for argument tracing).
#  @param trace_fn Callable to trace an AST expression to its source.
#  @return "python", UnknownSource, DerivedResult, module name string, or None.
def _resolve_builtin_result(name, call_node, trace_fn):
    if not isinstance(name, str):
        return None
    if name in _BUILTIN_PYTHON_OWNED_RESULT:
        return "python"
    if name in _BUILTIN_ARBITRARY_RESULT:
        return UnknownSource(name)
    if name in _BUILTIN_ELEMENT_DERIVED and call_node and call_node.args:
        return _element_source(name, call_node, trace_fn)
    if name == "type" and call_node and call_node.args:
        arg_node = call_node.args[0]
        arg_source = trace_fn(arg_node)
        if isinstance(arg_node, ast.Call):
            # type(A()) — resolve the constructor's callee identity
            from .sources import normalize_source as _ns
            callee_id = None
            if isinstance(arg_node.func, ast.Name):
                callee_id = arg_node.func.id
            elif isinstance(arg_node.func, ast.Attribute):
                callee_id = trace_fn(arg_node)
            if callee_id is not None:
                callee_norm = _ns(callee_id)
                if isinstance(callee_norm, CallResult) and isinstance(callee_norm.callee, str):
                    callee_id = callee_norm.callee
                return DerivedResult("type_of", (callee_id,))
        if arg_source is not None:
            return DerivedResult("type_of", (arg_source,))
        return UnknownSource("type")
    if name == "__import__" and call_node and call_node.args:
        first_arg = call_node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value.split(".")[0]
        return UnknownSource("__import__")
    if name in ("iter", "reversed") and call_node and call_node.args:
        element = _iterable_element_source(call_node.args[0], trace_fn)
        return DerivedResult("iterator", (element,))
    if name in _BUILTIN_PROTOCOL_DERIVED:
        return UnknownSource(name)
    return None


## Check if a Call node is a defaultdict(list) call with a statically
#  known default factory (list/dict/set/tuple/str).
def _is_defaultdict_itemkind(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False
    if node.func.id != "defaultdict" or len(node.args) < 1:
        return False
    factory = node.args[0]
    return isinstance(factory, ast.Name) and factory.id in ("list", "dict", "set", "tuple", "str")


## Return the concrete Python container kind produced by an expression.
#  @param node Assignment right-hand side AST node.
#  @return Container kind string or None.
def _container_kind(node):
    if isinstance(node, (ast.List, ast.ListComp)):
        return "list"
    if isinstance(node, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(node, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(node, ast.Tuple):
        return "tuple"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "str"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("list", "dict", "set", "tuple", "str"):
            return node.func.id
        if node.func.id == "defaultdict":
            return "dict"
    return None


## Return the concrete kind produced by subscripting a container expression.
#  Dict literals qualify only when every value has the same known kind.
#  @param node Assignment right-hand side AST node.
#  @return Item kind string or None.
def _container_item_kind(node):
    if isinstance(node, ast.Dict) and node.values:
        kinds = [_container_kind(value) for value in node.values]
        if kinds[0] is not None and all(kind == kinds[0] for kind in kinds):
            return kinds[0]
    if _is_defaultdict_itemkind(node):
        return node.args[0].id
    return None
from .types import FileAnalysis, ApiCall

# 1.0.5 P1: known conversion targets.  Method calls (to_numpy())
# change the result type; bare attribute reads (values) also
# change the result type.  Bare method references (df.to_numpy
# without calling) are NOT conversions.
_CONVERSION_METHOD_TARGETS = {
    ("pandas", "to_numpy"): "numpy",
}
_CONVERSION_ATTRIBUTE_TARGETS = {
    ("pandas", "values"): "numpy",
}

# Verified attribute-result contracts.  The receiver owner must already be
# import-backed; matching an attribute name alone is never sufficient.
_ATTRIBUTE_RESULT_OWNER_CONTRACTS = {
    ("bs4", "text"): (
        "python", "public-api:bs4.PageElement.text"),
    ("requests", "text"): (
        "python", "public-api:requests.Response.text"),
    ("spacy", "text"): (
        "python", "public-api:spacy Token/Span/Doc.text"),
    ("xml", "text"): (
        "python", "python-stdlib:xml.etree.ElementTree.Element.text"),
}

# Verified result-object contracts for import-backed calls.  The callable keeps
# its own library owner; each contract applies only to the object returned
# across an assignment or chained-call boundary.  Values contain
# (result_owner, evidence).  Evidence points to a checked Python/stdlib
# contract, a public API contract, or a committed runtime probe.
_RESULT_OWNER_CONTRACTS = {
    ("Box2D", "CreateDynamicBody"): (
        "Box2D", "probe:parameter_receiver_ownership"),
    ("Box2D", "CreateStaticBody"): (
        "Box2D", "probe:parameter_receiver_ownership"),
    ("scipy", "cdist"): (
        "numpy", "probe:receiver_ownership"),
    # svd() returns a Python tuple whose unpacked items are NumPy arrays.
    ("scipy", "svd"): (
        "python", "probe:machine_learning_svd"),
    ("scipy", "bisplev"): (
        "numpy", "public-api:scipy.interpolate.bisplev"),
    ("numpy", "dot"): (
        "numpy", "probe:receiver_ownership"),
    ("numpy", "reshape"): (
        "numpy", "public-api:numpy.reshape"),
    ("seaborn", "barplot"): (
        "matplotlib", "public-api:seaborn.barplot"),
    ("seaborn", "stripplot"): (
        "matplotlib", "public-api:seaborn.stripplot"),
    ("seaborn", "swarmplot"): (
        "matplotlib", "public-api:seaborn.swarmplot"),
    ("matplotlib", "figure"): (
        "matplotlib", "public-api:matplotlib.pyplot.figure"),
    ("matplotlib", "gca"): (
        "matplotlib", "public-api:matplotlib.pyplot.gca"),
    ("matplotlib", "gcf"): (
        "matplotlib", "public-api:matplotlib.pyplot.gcf"),
    ("matplotlib", "subplot"): (
        "matplotlib", "public-api:matplotlib.pyplot.subplot"),
    # subplots() returns a Python tuple.  Its second unpacked item may be a
    # Matplotlib Axes or a NumPy array, so no uniform item owner is claimed.
    ("matplotlib", "subplots"): (
        "python", "public-api:matplotlib.pyplot.subplots"),
    ("matplotlib", "add_subplot"): (
        "matplotlib", "public-api:matplotlib.figure.Figure.add_subplot"),
    ("skimage", "downscale_local_mean"): (
        "numpy", "probe:ground_truth/probes/round6_probe.py"),
    ("torchvision", "to_tensor"): (
        "torch", "public-api:torchvision.transforms.functional.to_tensor"),
    # Stable standard-library contracts.  Both functions return a
    # Python-provided str/bytes object, not an object owned by the module.
    ("json", "dumps"): (
        "python", "python-stdlib:json.dumps"),
    ("json", "load"): (
        "python", "python-stdlib:json.load"),
    ("json", "loads"): (
        "python", "python-stdlib:json.loads"),
    ("re", "sub"): (
        "python", "python-stdlib:re.sub"),
    ("re", "split"): (
        "python", "python-stdlib:re.split"),
    ("re", "group"): (
        "python", "python-stdlib:re.Match.group"),
    ("re", "compile"): (
        "re", "python-stdlib:re.compile"),
    ("re", "match"): (
        "re", "python-stdlib:re.match"),
    ("re", "search"): (
        "re", "python-stdlib:re.search"),
    ("re", "fullmatch"): (
        "re", "python-stdlib:re.fullmatch"),
}
_VERIFIED_RESULT_OWNERS = frozenset(
    contract[0] for contract in _RESULT_OWNER_CONTRACTS.values()
)

# Owners of elements yielded by selected import-backed iterator calls. This is
# deliberately separate from _RESULT_OWNER_CONTRACTS: the iterator object and
# each yielded object do not necessarily have the same ownership semantics.
_ITERATOR_ELEMENT_OWNER_MAP = {
    ("re", "finditer"): "re",
    ("glob", "glob"): "python",
    ("glob", "iglob"): "python",
    ("os", "listdir"): "python",
}

# Owners of items selected from selected call results.  Keep this separate
# from _RESULT_OWNER_CONTRACTS because the aggregate result may be a Python
# tuple while its destructured or indexed items are import-backed objects.
_RESULT_ITEM_OWNER_CONTRACTS = {
    ("scipy", "svd"): "numpy",
    ("GPy", "predict"): "numpy",
    ("re", "split"): "python",
}

# Verified predicates that narrow a receiver owner in their true branch.
# The evidence is part of the contract so these rules remain distinguishable
# from method-name guessing.
_TYPE_GUARD_OWNER_CONTRACTS = {
    ("scipy", "issparse"): (
        "scipy", "public-api:scipy.sparse.issparse"),
}

# Verified callback-parameter contracts.  Each key is
# (library, callable, callback argument index, callback parameter index).
_CALLBACK_PARAMETER_OWNER_CONTRACTS = {
    ("re", "sub", 1, 0): (
        "re", "python-stdlib:re.sub replacement callback"),
    ("re", "subn", 1, 0): (
        "re", "python-stdlib:re.subn replacement callback"),
}

# Item kind produced by indexing selected builtin-method results.  Keep this
# table limited to contracts guaranteed by Python itself; arbitrary local
# methods with the same name do not enter this path unless their receiver kind
# is independently known.
_BUILTIN_METHOD_RESULT_ITEM_KINDS = {
    ("str", "split"): "str",
    ("str", "rsplit"): "str",
}

def _match_result_owner(top, func_name):
    """Return the verified owner of an import-backed call's result object."""
    if top is None:
        return None
    for (lib_prefix, fn), contract in _RESULT_OWNER_CONTRACTS.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[0]
    return None


def _match_attribute_result_owner(top, attribute):
    """Return the verified owner of an import-backed attribute's value."""
    if top is None:
        return None
    for (lib_prefix, name), contract in (
            _ATTRIBUTE_RESULT_OWNER_CONTRACTS.items()):
        if (name == attribute
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[0]
    return None


def _is_verified_result_owner(owner):
    """Return whether owner is produced by a verified result contract."""
    return owner in _VERIFIED_RESULT_OWNERS


def _match_result_item_owner(top, func_name):
    """Return a uniform owner for destructured or indexed call-result items."""
    if top is None:
        return None
    for (lib_prefix, fn), owner in _RESULT_ITEM_OWNER_CONTRACTS.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return owner
    return None


def _match_iterator_element_owner(top, func_name):
    """Return the owner of elements from a known import-backed iterator."""
    if top is None:
        return None
    for (lib_prefix, fn), owner in _ITERATOR_ELEMENT_OWNER_MAP.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return owner
    return None


## Check whether every possible return source is Python-owned.
#
#  SourceSet values represent branch-dependent returns.  A local call may use
#  the Python result contract only when every branch independently proves the
#  same owner; mixed or unresolved branches remain conservative.
#  @param source Return source or SourceSet.
#  @return True when all possible sources are exactly "python".
def _is_uniform_python_result(source):
    source = normalize_source(source)
    if source == "python":
        return True
    if isinstance(source, SourceSet) and source.sources:
        return all(_is_uniform_python_result(item)
                   for item in source.sources)
    return False


## Check whether any possible return source is Python-owned.
#  @param source Return source or SourceSet.
#  @return True when at least one branch is exactly "python".
def _has_python_result(source):
    source = normalize_source(source)
    if source == "python":
        return True
    if isinstance(source, SourceSet):
        return any(_has_python_result(item) for item in source.sources)
    return False

# 1.0.5 P1: numpy ufuncs that preserve the receiver's type when
# applied to pandas objects.  Probe-backed: np.log(pd.Series)
# returns pd.Series.
_RECEIVER_PRESERVE_UFUNCS = frozenset({
    "log", "exp", "sqrt", "abs", "divide",
})

# Methods known to be valid on compare-result objects, keyed by
# the result owner.  Only these (owner, method) pairs allow a
# compare-receiver call to be classified as that owner.
_COMPARE_RESULT_METHODS = {
    "numpy": frozenset(["any", "all"]),
}


## AST visitor that traces all symbols and API calls in a single Python file.
#
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
    #  @param scope_model "v1" (legacy) or "v2" (lexical scopes, default).
    def __init__(self, module_name=None, is_package=False, scope_model="v2",
                 file_path=""):
        self.module_name = module_name
        self.is_package = is_package
        self.scope_model = scope_model
        self._file_path = file_path
        self.return_sources = {}
        self.symbols = SymbolTable(self.return_sources)
        self.api_calls = []
        self.attr_accesses = []
        self.local = set()
        self._func_stack = []
        self._class_stack = []
        self._seen_api_call_ids = set()
        self._receiver_owner_guards = []
        self.defined_functions = set()
        self.function_params = {}
        self.parameter_sources = {}
        self._assigned_call_sources = {}
        self.container_items = {}
        self.homogeneous_container_items = {}
        self.container_lengths = {}
        self.container_kinds = {}  # 1.0.5 P1: name -> "list"|"dict"|"set"|"tuple"|"str"
        self.container_item_kinds = {}  # 1.0.5 P1+: name -> "list"|"dict"|... for defaultdict(list) etc.
        self.container_set_sources = {}
        self.class_methods = {}
        self.class_bases = {}
        self.instance_attrs = {}
        self.instance_attr_kinds = {}
        self.instance_attr_item_kinds = {}
        self.import_from_symbols = {}
        self.wildcard_modules = []
        self.import_aliases = set()
        self.call_sites = {}
        self.call_assign_funcs = {}
        self._assignment_counter = 0
        self._global_names = set()
        self.call_site_objects = []
        self.symbol_refs = []
        self.module_scope = Scope(SCOPE_MODULE, self.module_name or "<module>")
        self.scope_stack = [self.module_scope]
        ## Call-graph facts (Phase 7B-full PR1: read-only collection).
        self.module_cg = ModuleCallGraph(module=module_name or "")
        ## Stack of FunctionId for tracking the current caller context.
        self._caller_stack = [FunctionId(module_name or "", "<module>")]
        ## Map from RHS top-level expression node id -> list of target names.
        ## Only the outermost RHS call (not nested inner calls) consumes targets.
        self._literal_values = {}
        self._pending_call_targets_by_node = {}
        self._argparse_parsers = {}

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
    #  @param kind Optional symbol kind for provenance ("variable", "parameter", "attribute").
    def _bind_target_name(self, name, source, node=None, kind="variable",
                          container_kind="", container_item_kind="",
                          callable_key=""):
        self._assignment_counter += 1
        lineno = getattr(node, "lineno", 0) if node is not None else 0
        col = getattr(node, "col_offset", 0) if node is not None else 0
        self.current_scope().bind(
            name, source, lineno, col, self._assignment_counter,
            container_kind=container_kind,
            container_item_kind=container_item_kind,
            callable_key=callable_key,
            binding_kind=kind)
        if name in self._global_names or self.scope_model == "v1" or self.current_scope().kind == SCOPE_MODULE:
            self.symbols.add(name, source)
        if name.startswith("self.") and self._class_stack:
            attr_key = (self._class_stack[-1], name)
            self.instance_attrs[attr_key] = source
            if container_kind:
                self.instance_attr_kinds[attr_key] = container_kind
            else:
                self.instance_attr_kinds.pop(attr_key, None)
            if container_item_kind:
                self.instance_attr_item_kinds[attr_key] = container_item_kind
            else:
                self.instance_attr_item_kinds.pop(attr_key, None)
        if kind:
            self._add_symbol_ref(name, source, kind, node)

    ## Look up a name in the lexical scope chain (v2) or return the name as-is.
    #
    #  Unified helper so that trace_source, get_base, and _resolve_call_receiver
    #  all use the same scope-aware resolution.
    #  @param name The raw AST name string.
    #  @return Scope binding source in v2, or the name itself in v1 / not found.
    def _lookup_name_source(self, name):
        if self.scope_model == "v2":
            binding = self.current_scope().lookup(name, skip_parent_classes=True)
            if binding is not None:
                if binding.source == "local":
                    return binding.source
                if name in self.import_aliases and isinstance(binding.source, str) and '.' not in binding.source:
                    return name
                return binding.source
        return name

    ## Return assignment metadata for a name in the active lexical scope.
    #  A found binding with no metadata is authoritative and prevents a
    #  same-name binding from another scope leaking through legacy maps.
    #  @param name Receiver variable name.
    #  @param item Whether to request the subscript item kind.
    #  @return Container kind string or None.
    def _lookup_container_kind(self, name, item=False):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            attr = "container_item_kind" if item else "container_kind"
            return getattr(binding, attr, "") or None
        if item:
            return self.container_item_kinds.get(name)
        return self.container_kinds.get(name)

    ## Return the container kind relevant to a method call receiver.
    #  @param node The ast.Call node.
    #  @return Container or subscript-item kind string, or None.
    def _call_receiver_container_kind(self, node):
        if not isinstance(node, ast.Call):
            return None
        if not isinstance(node.func, ast.Attribute):
            return None
        receiver = node.func.value
        literal_kind = _container_kind(receiver)
        if literal_kind is not None:
            return literal_kind
        if isinstance(receiver, ast.Name):
            return self._lookup_container_kind(receiver.id)
        if isinstance(receiver, ast.Attribute) and self._class_stack:
            name = self._attribute_name(receiver)
            if name and name.startswith("self."):
                return self.instance_attr_kinds.get(
                    (self._class_stack[-1], name))
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Name)):
            return self._lookup_container_kind(receiver.value.id, item=True)
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Attribute)
                and self._class_stack):
            name = self._attribute_name(receiver.value)
            if name and name.startswith("self."):
                return self.instance_attr_item_kinds.get(
                    (self._class_stack[-1], name))
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Call)):
            producer = receiver.value
            producer_kind = self._call_receiver_container_kind(producer)
            producer_method = (
                producer.func.attr
                if isinstance(producer.func, ast.Attribute) else "")
            item_kind = _BUILTIN_METHOD_RESULT_ITEM_KINDS.get(
                (producer_kind, producer_method))
            if item_kind is not None:
                return item_kind
            producer_owner = self.get_base(producer, call_lookup=True)
            if producer_owner == "python":
                return _BUILTIN_METHOD_RESULT_ITEM_KINDS.get(
                    ("str", producer_method))
        return None

    ## Build a scope-qualified key for a locally assigned callable.
    #  @param name Assignment target name.
    #  @return Stable key used in return_sources.
    def _local_callable_key(self, name):
        parts = list(self._class_stack) + list(self._func_stack) + [name]
        return ".".join(parts)

    ## Preserve a local callable's identity when stored as a value.
    #  @param node Value expression.
    #  @return Qualified callable key or ordinary traced source.
    def _value_source(self, node):
        if (isinstance(node, (ast.Constant, ast.JoinedStr))
                or _container_kind(node) is not None):
            return "python"
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is not None and binding.callable_key:
                return binding.callable_key
        return self.trace_source(node) or self.get_base(node)

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

        func_top, func_name = self._resolve_func_top(node.value.func)
        if func_top == "argparse" and func_name == "ArgumentParser":
            for target in targets:
                self._argparse_parsers[
                    (id(self.current_scope()), target)] = set()
            return

        if (node.value.func.attr not in ("parse_args",)
                or not isinstance(node.value.func.value, ast.Name)):
            return
        destinations = self._argparse_destinations(
            node.value.func.value.id)
        if destinations is None:
            return
        for target in targets:
            for destination in destinations:
                self._bind_target_name(
                    target + "." + destination,
                    "python",
                    node,
                    "attribute",
                )

    ## Preserve a direct import-from callable for argument-flow evidence.
    #
    #  This metadata is intentionally separate from the ordinary symbol
    #  binding so public provenance and legacy call classification keep their
    #  established representation.
    #
    #  @param node Candidate call expression.
    #  @return Qualified CallResult or None.
    def _imported_call_result_source(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)):
            return None
        qualified = self.import_from_symbols.get(node.func.id)
        if not qualified:
            return None
        return CallResult(
            qualified,
            display_name=node.func.id,
            call_lineno=node.lineno,
            call_col_offset=node.col_offset,
        )

    ## Preserve parameter forwarding in call-edge argument facts.
    #  @param node Argument expression.
    #  @return ParameterSource or ordinary argument source.
    def _call_edge_argument_source(self, node):
        if self.scope_model != "v2":
            return self.get_base(node)
        if isinstance(node, ast.Name) and self._caller_stack:
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None
                    and binding.binding_kind == "parameter"):
                return ParameterSource(
                    self._caller_stack[-1].qualname, node.id)
            assigned_call = self._assigned_call_sources.get(
                (id(self.current_scope()), node.id))
            if assigned_call is not None:
                return assigned_call
        imported_call = self._imported_call_result_source(node)
        if imported_call is not None:
            return imported_call
        return self._value_source(node)

    ## Preserve whether an assignment value has unresolved parameter origin.
    #  @param node Assignment value expression.
    #  @return ParameterSource, UnknownSource, or None.
    def _parameter_dependency_source(self, node):
        if self.scope_model != "v2":
            return None

        if isinstance(node, ast.Name):
            if not self._caller_stack:
                return None
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is None:
                return None
            existing = normalize_source(binding.source)
            if isinstance(existing, (ParameterSource, UnknownSource)):
                return existing
            if binding.binding_kind != "parameter":
                return None
            return ParameterSource(
                self._caller_stack[-1].qualname, node.id)

        if isinstance(node, ast.Attribute):
            dependency = self._parameter_dependency_source(node.value)
            if isinstance(dependency, ParameterSource):
                return ParameterSource(
                    dependency.scope,
                    dependency.name,
                    derived=dependency.derived,
                    attributes=dependency.attributes + (node.attr,),
                )
            if isinstance(dependency, UnknownSource):
                return dependency
            return None

        if isinstance(node, ast.Subscript):
            dependency = self._parameter_dependency_source(node.value)
            if isinstance(dependency, ParameterSource):
                return ParameterSource(
                    dependency.scope,
                    dependency.name,
                    derived=True,
                    attributes=dependency.attributes,
                )
            if isinstance(dependency, UnknownSource):
                return dependency
            return None

        if isinstance(node, ast.UnaryOp):
            dependency = self._parameter_dependency_source(node.operand)
            if dependency is not None:
                return UnknownSource("unresolved parameter-derived expression")
            return None

        if isinstance(node, ast.BinOp):
            left = self._parameter_dependency_source(node.left)
            right = self._parameter_dependency_source(node.right)
            if left is not None or right is not None:
                return UnknownSource("unresolved parameter-derived expression")
            return None

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            dependency = self._parameter_dependency_source(node.func.value)
            if dependency is not None:
                method_source = self._resolve_methods(node)
                if method_source is None:
                    return UnknownSource("unresolved parameter method result")
                return CallResult(
                    method_source,
                    display_name=ast.unparse(node.func),
                    call_lineno=node.lineno,
                    call_col_offset=node.col_offset,
                    result_source=DerivedResult(
                        "method_result",
                        (method_source,),
                        node.func.attr,
                    ),
                )
        return None

    ## Record a SymbolRef for provenance tracking.
    #  @param symbol Display name.
    #  @param source Source value.
    #  @param kind Symbol category.
    #  @param node Optional AST node for position.
    def _add_symbol_ref(self, symbol, source, kind, node=None):
        scope_name = ""
        if self.scope_model == "v2":
            cs = self.current_scope()
            if cs.kind != SCOPE_MODULE:
                scope_name = cs.name
        self.symbol_refs.append(SymbolRef(
            symbol=symbol,
            source=source,
            kind=kind,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            scope_name=scope_name,
            lineno=getattr(node, "lineno", 0) if node is not None else 0,
            col_offset=getattr(node, "col_offset", 0) if node is not None else 0,
        ))

    ## --- Import visitors ---

    ## Visit an Import node and record alias-to-module mappings.
    #  @param node The Import AST node.
    def visit_Import(self, node):
        for alias in node.names:
            symbol = alias.asname if alias.asname else alias.name
            self.import_aliases.add(symbol)
            self._bind_target_name(symbol, alias.name, node, "import")
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
                self._bind_target_name(symbol, resolved, node, "import")
                self.import_from_symbols[symbol] = (resolved + '.' + alias.name) if resolved else alias.name
            else:
                self.import_aliases.add(symbol)
                self._bind_target_name(symbol, node.module, node, "import")
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
                receiver_kind = self._call_receiver_container_kind(node)
                if (receiver_kind is not None
                        and isinstance(me, InstanceMethod)
                        and me.method in _BUILTIN_CONTAINER_METHODS.get(
                            receiver_kind, frozenset())):
                    return CallResult(
                        me,
                        display_name=ast.unparse(node.func),
                        call_lineno=node.lineno,
                        call_col_offset=node.col_offset,
                        result_source="python",
                    )
                if (isinstance(me, InstanceMethod)
                        and me.receiver == "python"):
                    return CallResult(
                        me,
                        display_name=ast.unparse(node.func),
                        call_lineno=node.lineno,
                        call_col_offset=node.col_offset,
                        result_source="python",
                    )
                ## 7B-full PR5: if a local class method has an import-backed
                ## return source, propagate it so assigned variables carry
                ## library provenance.
                if (isinstance(me, InstanceMethod) and isinstance(me.method, str)
                        and isinstance(me.receiver, str)):
                    # Check whether the receiver is a local class instance.
                    local_class = me.receiver in self.class_methods
                    if not local_class and self.scope_model == "v2":
                        binding = self.current_scope().lookup(me.receiver)
                        if binding is not None:
                            src = normalize_source(binding.source)
                            if isinstance(src, CallResult) and isinstance(src.callee, str):
                                local_class = src.callee in self.class_methods
                    if local_class:
                        # Determine the qualname for return_sources lookup.
                        class_name = me.receiver
                        if not (me.receiver in self.class_methods):
                            binding = self.current_scope().lookup(me.receiver)
                            if binding is not None:
                                src = normalize_source(binding.source)
                                if isinstance(src, CallResult) and isinstance(src.callee, str):
                                    class_name = src.callee
                        method_key = class_name + "." + me.method
                        # Keep the local callable identity instead of choosing
                        # one return branch during the single-file pass.
                        # Cross-file resolution evaluates the completed return
                        # summary after the whole module has been visited.
                        return CallResult(
                            method_key,
                            display_name=ast.unparse(node.func),
                            call_lineno=node.lineno,
                            call_col_offset=node.col_offset,
                        )
                ## 1.0.5 P2: SuperMethod identifies the call target;
                #  wrap in CallResult so the return value does not inherit
                #  the base-class owner.  result_source=UnknownSource:
                #  without return-type evidence, result is unknowable.
                if isinstance(me, SuperMethod):
                    return CallResult(me,
                                      display_name="super().%s" % me.method,
                                      call_lineno=node.lineno,
                                      call_col_offset=node.col_offset,
                                      result_source=UnknownSource("super()"))
                return me
            ## For chained calls (A().B()), resolve via the inner call's
            ## return source so the outer call traces to the correct library.
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                inner_source = self.trace_source(node.func.value)
                if isinstance(inner_source, str):
                    rs = self.return_sources.get(inner_source)
                    if rs is not None:
                        rs = normalize_source(rs)
                        if isinstance(rs, SourceSet):
                            inner_source = rs
                        else:
                            return rs
                if isinstance(inner_source, CallResult):
                    if inner_source.result_source is not None:
                        result_owner = inner_source.result_source
                        if (isinstance(result_owner, str)
                                and isinstance(node.func, ast.Attribute)):
                            mapped_owner = _match_result_owner(
                                result_owner, node.func.attr)
                            if mapped_owner is not None:
                                return CallResult(
                                    InstanceMethod(
                                        result_owner, node.func.attr),
                                    display_name=ast.unparse(node.func),
                                    call_lineno=node.lineno,
                                    call_col_offset=node.col_offset,
                                    result_source=mapped_owner)
                        return result_owner
                    rs = self.return_sources.get(inner_source.callee)
                    if rs is not None:
                        rs = normalize_source(rs)
                        if isinstance(rs, SourceSet):
                            inner_source = rs
                        else:
                            return rs
                if isinstance(inner_source, SourceSet):
                    return inner_source
                if inner_source:
                    return inner_source
            if isinstance(node.func, ast.Name):
                binding = self.current_scope().lookup(
                    node.func.id, skip_parent_classes=True)
                if binding is not None and binding.callable_key:
                    call_key = binding.callable_key
                elif (node.func.id in self.defined_functions
                      or node.func.id in self.class_methods):
                    call_key = node.func.id
                else:
                    call_key = self.get_base(node, call_lookup=True)
            else:
                call_key = self.get_base(node, call_lookup=True)
            method_source = normalize_source(self._resolve_methods(node))
            if (isinstance(method_source, InstanceMethod)
                    and isinstance(method_source.receiver, str)
                    and _is_verified_result_owner(
                        method_source.receiver)):
                call_key = method_source.receiver
            if call_key:
                if isinstance(call_key, CallResult):
                    return call_key
                ## Resolve self.attr through instance_attrs so that
                ## chained calls propagate library provenance, e.g.
                ## predictions = self.model.predict(X)[0].reshape(...)
                ## where self.model -> GPy.models.GPRegression.
                if isinstance(call_key, str) and call_key.startswith("self.") and self._class_stack:
                    cn = self._class_stack[-1]
                    attr_src = self.instance_attrs.get((cn, call_key))
                    if isinstance(attr_src, CallResult) and isinstance(attr_src.callee, str):
                        call_key = attr_src.callee
                ## Extract import-backed receiver from InstanceMethod.
                if isinstance(call_key, InstanceMethod) and isinstance(call_key.receiver, str):
                    call_key = call_key.receiver
                display = ""
                try:
                    display = ast.unparse(node.func)
                except Exception:
                    pass
                if isinstance(call_key, str) and '.' not in display:
                    display = ""
                ## 1.0.5 P2: determine result-object ownership for builtin callees.
                rs = None
                if isinstance(call_key, str):
                    local_returns = self.return_sources.get(call_key)
                    if _is_uniform_python_result(local_returns):
                        rs = "python"
                    elif _has_python_result(local_returns):
                        rs = UnknownSource("mixed local return")
                    func_top, func_name = self._resolve_func_top(node.func)
                    mapped_owner = _match_result_owner(func_top, func_name)
                    if mapped_owner is not None:
                        rs = mapped_owner
                    else:
                        preserved = self._receiver_preserving_result_owner(
                            node, func_top, func_name)
                        if preserved is not None:
                            rs = preserved
                    if _is_unshadowed_builtin_call(self, node):
                        rs = _resolve_builtin_result(
                            call_key, node, self.trace_source)
                return CallResult(call_key, display_name=display,
                                  call_lineno=node.lineno,
                                  call_col_offset=node.col_offset,
                                  result_source=rs)
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
            if isinstance(node.value, ast.Call):
                item_owner = self._resolve_call_result_item_owner(node.value)
                if item_owner is not None:
                    return item_owner
            container_name = self.trace_source(node.value)
            key_idx = self._get_slice(node.slice)
            if container_name is not None and key_idx is not None:
                # Use the variable *name* for the container_items lookup
                # (container_items is keyed by name, not by trace source).
                lookup_name = node.value.id if isinstance(node.value, ast.Name) else container_name
                key_value = self._container_index(lookup_name, key_idx)
                lookup_key = (lookup_name, key_value)
                if lookup_key in self.container_items:
                    return self.container_items[lookup_key]
                return ContainerItem(lookup_name, key_idx)
            ## 7B-full PR7: try to resolve static key from literal assignment.
            resolved_key = None
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                if isinstance(node.slice, ast.Name):
                    resolved_key = self._literal_values.get(node.slice.id)
                if resolved_key is not None:
                    lookup = self.container_items.get((var_name, resolved_key))
                    if lookup is not None:
                        return lookup
            ## Fallback: collect item sources; only create SourceSet if
            ## all candidates are consistent (single-source or same library).
            if container_name is not None and isinstance(node.value, ast.Name):
                var_name = node.value.id
                item_sources = []
                for (cn, _), src in self.container_items.items():
                    if cn == var_name:
                        item_sources.append(src)
                if item_sources:
                    return make_source_set(item_sources, origin="dict_lookup")
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

    ## Resolve a method inherited from a statically known builtin base class.
    #
    #  Follows local base classes in declared MRO order.  A local override wins;
    #  an external or otherwise unknown base stops inference so a later builtin
    #  base cannot be claimed speculatively.
    #  @param class_name Local class whose bases should be inspected.
    #  @param method_name Method looked up on the instance.
    #  @param seen Local classes already visited during recursive lookup.
    #  @return Builtin type name, "local", or None when unresolved.
    def _inherited_builtin_method_owner(self, class_name, method_name,
                                        seen=None):
        if seen is None:
            seen = set()
        if class_name in seen:
            return None
        seen = set(seen)
        seen.add(class_name)

        for base in self.class_bases.get(class_name, []):
            if base in self.class_methods:
                if method_name in self.class_methods.get(base, []):
                    return "local"
                inherited = self._inherited_builtin_method_owner(
                    base, method_name, seen)
                if inherited is not None:
                    return inherited
                continue

            direct = normalize_source(self.symbols.direct.get(base))
            if direct == "local":
                return None

            imported = self.import_from_symbols.get(base, "")
            resolved_base = imported or base
            builtin_name = resolved_base.rsplit(".", 1)[-1]
            builtin_origin = (
                resolved_base == builtin_name
                or resolved_base.startswith("builtins."))
            if (builtin_origin
                    and method_name in _BUILTIN_CONTAINER_METHODS.get(
                        builtin_name, frozenset())):
                return builtin_name
            if builtin_name == "object" and builtin_origin:
                continue

            # An earlier unknown/external base may provide the descriptor.
            return None
        return None

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

        ## 1.0.5 P2: super().method() — capture enclosing class context
        #  while _class_stack is still available during AST visit.
        if isinstance(re, ast.Call):
            if isinstance(re.func, ast.Name) and re.func.id == "super":
                if self._class_stack:
                    class_key = self._class_stack[-1]
                    class_qualname = ".".join(self._class_stack)
                    return SuperMethod(class_key, class_qualname, method_name)
                return InstanceMethod("super", method_name)

            inner_result = normalize_source(self.trace_source(re))
            if isinstance(inner_result, CallResult):
                inner_owner = normalize_source(inner_result.result_source)
                if isinstance(inner_owner, str):
                    return InstanceMethod(inner_owner, method_name)

            # A direct chained method belongs to the object explicitly
            # returned by a project-local method.  Gate this path on local
            # method identity so direct library calls such as np.log(...)
            # continue through receiver-preserving return rules below.
            inner_method = self._resolve_methods(re)
            local_method = False
            if (isinstance(inner_method, InstanceMethod)
                    and isinstance(inner_method.receiver, str)):
                local_method = inner_method.receiver in self.class_methods
                if not local_method and self.scope_model == "v2":
                    binding = self.current_scope().lookup(
                        inner_method.receiver)
                    if binding is not None:
                        binding_source = normalize_source(binding.source)
                        if (isinstance(binding_source, CallResult)
                                and isinstance(binding_source.callee, str)):
                            local_method = (
                                binding_source.callee in self.class_methods)
            if local_method:
                result_source = normalize_source(self.trace_source(re))
                if isinstance(result_source, CallResult):
                    if (isinstance(result_source.callee, str)
                            and result_source.callee in self.return_sources):
                        return InstanceMethod(result_source, method_name)
                    candidate = result_source.result_source
                    if not isinstance(candidate, str):
                        candidate = result_source.callee
                    if isinstance(candidate, str):
                        candidate_top = self.symbols.get_top(candidate)
                        if candidate_top not in (
                                None, "", "local", "python", "unknown"):
                            return InstanceMethod(candidate, method_name)

        def _lookup_instance_attr(attr_name):
            if self._class_stack:
                class_name = self._class_stack[-1]
                if (class_name, attr_name) in self.instance_attrs:
                    return self.instance_attrs[(class_name, attr_name)]
            return self.symbols.direct.get(attr_name)

        def _resolve_on_class(class_name, receiver_key):
            if not class_name:
                return None
            methods = self.class_methods.get(class_name, [])
            if methods and method_name in methods:
                return InstanceMethod(receiver_key, method_name)
            inherited_owner = self._inherited_builtin_method_owner(
                class_name, method_name)
            if inherited_owner == "local":
                return InstanceMethod(receiver_key, method_name)
            if inherited_owner is not None:
                return InstanceMethod(inherited_owner, method_name)
            if class_name in self.class_methods:
                return InstanceMethod(receiver_key, method_name)
            if class_name in self.import_from_symbols:
                return InstanceMethod(class_name, method_name)
            return None

        def _parameter_method(receiver, parameter_name):
            if not self._caller_stack:
                return None
            binding = self.current_scope().lookup(
                parameter_name, skip_parent_classes=True)
            if (binding is None
                    or binding.binding_kind != "parameter"):
                return None
            scope_name = self._caller_stack[-1].qualname
            params = self.function_params.get(scope_name)
            if params is None:
                params = self.function_params.get(
                    scope_name.rsplit(".", 1)[-1], [])
            if parameter_name not in params:
                return None
            return InstanceMethod(
                receiver,
                method_name,
                parameter_scope=scope_name,
                parameter_name=parameter_name,
            )

        if isinstance(re, ast.Name):
            for guards in reversed(self._receiver_owner_guards):
                guarded_owner = guards.get(re.id)
                if guarded_owner is not None:
                    return InstanceMethod(guarded_owner, method_name)
            if re.id == "self" and self._class_stack:
                cn = self._class_stack[-1]
                return _resolve_on_class(cn, cn)
            class_name = self.symbols.direct.get(re.id)
            class_name = normalize_source(class_name)
            if isinstance(class_name, CallResult):
                if isinstance(
                        normalize_source(class_name.result_source),
                        (str, UnknownSource)):
                    return InstanceMethod(class_name, method_name)
                class_name = class_name.callee
            # 1.0.5 P1: treat "local" class_name the same as
            # absent — still create InstanceMethod so the
            # builtin container method check applies.
            if not class_name or class_name == "local":
                if self.scope_model == "v2":
                    binding = self.current_scope().lookup(re.id)
                    if binding is not None:
                        src_norm = normalize_source(binding.source)
                        if isinstance(src_norm, ParameterSource):
                            if src_norm.derived:
                                receiver = re.id
                            else:
                                receiver = ".".join(
                                    (src_norm.name,) + src_norm.attributes)
                            return InstanceMethod(
                                receiver, method_name,
                                parameter_scope=src_norm.scope,
                                parameter_name=src_norm.name)
                        if binding.source == "local":
                            parameter = _parameter_method(re.id, re.id)
                            if parameter is not None:
                                return parameter
                            return InstanceMethod(re.id, method_name)
                        if isinstance(src_norm, CallResult):
                            cn = src_norm.callee
                            if isinstance(cn, str) and cn in self.class_methods:
                                return _resolve_on_class(cn, cn)
                            if isinstance(cn, str) and cn in self.import_from_symbols:
                                return InstanceMethod(cn, method_name)
                            return InstanceMethod(src_norm, method_name)
                        if is_structured_source(src_norm):
                            return InstanceMethod(src_norm, method_name)
                        if (isinstance(src_norm, str)
                                and binding.binding_kind != "import"
                                and src_norm not in (
                                    "", "local", "python", "unknown")):
                            return InstanceMethod(src_norm, method_name)
                # Module-level local bindings — scope lookup
                # may return None at module scope; fall back
                # to the direct symbol table.
                if self.symbols.direct.get(re.id) == "local":
                    return InstanceMethod(re.id, method_name)
                return None
            return _resolve_on_class(class_name, re.id)

        if isinstance(re, ast.Attribute):
            attribute_receiver_top = self._expr_receiver_top(re.value)
            attribute_owner = _match_attribute_result_owner(
                attribute_receiver_top, re.attr)
            if attribute_owner is not None:
                return InstanceMethod(attribute_owner, method_name)
            receiver_name = self._attribute_name(re)
            if receiver_name:
                receiver_binding = self.current_scope().lookup(
                    receiver_name, skip_parent_classes=True)
                if (receiver_binding is not None
                        and receiver_binding.source == "python"):
                    return InstanceMethod("python", method_name)
            chain = self._attribute_chain_list(re)
            if chain:
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    result = _resolve_on_class(cn, cn)
                    if isinstance(normalize_source(result), InstanceMethod):
                        attr_name = "self." + ".".join(chain[1:])
                        attr_source = _lookup_instance_attr(attr_name)
                        attr_source = normalize_source(attr_source)
                        if isinstance(attr_source, ParameterSource):
                            receiver = ".".join(
                                (attr_source.name,) + attr_source.attributes)
                            return InstanceMethod(
                                receiver,
                                method_name,
                                parameter_scope=attr_source.scope,
                                parameter_name=attr_source.name)
                        if isinstance(attr_source, CallResult):
                            callee = attr_source.callee
                            if not isinstance(callee, str):
                                return InstanceMethod(
                                    attr_source, method_name)
                            callee_parts = callee.rsplit(".", 1)
                            is_local_method_result = (
                                len(callee_parts) == 2
                                and callee_parts[0] in self.class_methods
                                and callee_parts[1] in self.class_methods[
                                    callee_parts[0]]
                            )
                            if (callee in self.return_sources
                                    or is_local_method_result):
                                return InstanceMethod(
                                    attr_source, method_name)
                            if ('.' not in callee
                                    and callee in self.symbols.direct):
                                return InstanceMethod(callee, method_name)
                            if '.' in callee:
                                prefix = callee.split('.')[0]
                                prefix_is_origin = any(
                                    isinstance(v, str) and (v == prefix or v.startswith(prefix + "."))
                                    for v in self.symbols.direct.values())
                                if prefix_is_origin:
                                    return InstanceMethod(prefix, method_name)
                                if prefix in self.import_from_symbols:
                                    return InstanceMethod(prefix, method_name)
                                if prefix in self.symbols.direct:
                                    return InstanceMethod(prefix, method_name)
                                return InstanceMethod(callee, method_name)
                        if isinstance(attr_source, str) and '.' not in attr_source and attr_source in self.symbols.direct:
                            return InstanceMethod(attr_source, method_name)
                        if isinstance(attr_source, str) and attr_source != "local":
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
                # P0: resolve instance attributes for non-self receivers
                # whose root traces to a local class instance.
                # e.g. client.backend.loads() where client=Client()
                # and self.backend=json  →  trace client.backend
                # through instance_attrs to find json, then
                # classify loads as json.loads.
                target_class = root_src
                if not target_class and self.scope_model == "v2":
                    binding = self.current_scope().lookup(root)
                    if binding is not None:
                        target_class = normalize_source(binding.source)
                        if isinstance(target_class, CallResult):
                            target_class = target_class.callee
                        if target_class == "local":
                            parameter = _parameter_method(
                                ".".join(chain), root)
                            if parameter is not None:
                                return parameter
                if isinstance(target_class, str) and target_class in self.class_methods:
                    if len(chain) >= 2:
                        attr_name = "self." + ".".join(chain[1:])
                        attr_source = self.instance_attrs.get(
                            (target_class, attr_name))
                        attr_source = normalize_source(attr_source)
                        if isinstance(attr_source, CallResult):
                            callee = attr_source.callee
                            if isinstance(callee, str):
                                return InstanceMethod(callee, method_name)
                        if isinstance(attr_source, str) and attr_source not in ("local", "python", "unknown", ""):
                            return InstanceMethod(attr_source, method_name)
                    return _resolve_on_class(target_class, root)
        if isinstance(re, ast.Constant):
            # Literal constant method call: "str".format() → python.
            # The receiver is a literal Python builtin type, so the
            # method callable is always python.
            if isinstance(re.value, str):
                return InstanceMethod("str", method_name)
            if isinstance(re.value, bytes):
                return InstanceMethod("bytes", method_name)
        if (isinstance(re, ast.Subscript)
                and isinstance(re.value, ast.Call)):
            item_owner = self._resolve_call_result_item_owner(re.value)
            if item_owner is not None:
                return InstanceMethod(item_owner, method_name)
        if isinstance(re, ast.Compare):
            result = self._resolve_compare_result_top(re, method_name)
            if result is not None:
                return result
            # Owner could not be resolved — still collect the call
            # so it isn't silently dropped.  The cross-file resolver
            # will treat it conservatively.
            return InstanceMethod("__unresolved_compare__", method_name)
        return None

    ## Resolve the owner of a comparison-result method call.
    #
    #  For (np.diag(W) == np.zeros(...)).any(), both sides of the
    #  comparison are numpy expressions, so the result is a boolean
    #  ndarray and .any() belongs to numpy.
    #
    #  Only returns an owner when ALL operands resolve to the same
    #  library AND the method is in _COMPARE_RESULT_METHODS for that
    #  library.  Returns None otherwise — no fallback to the first
    #  operand (which would overclaim ownership for mixed libraries).
    #  @param compare_node The ast.Compare node.
    #  @param method_name The method being called on the result.
    #  @return InstanceMethod or None.
    def _resolve_compare_result_top(self, compare_node, method_name):
        # Collect the top library of every operand.
        operands = [compare_node.left] + list(compare_node.comparators)
        tops = []
        for op in operands:
            base = self.get_base(op)
            if isinstance(base, str):
                top = self.symbols.get_top(base)
                if top and top not in ("local", "python", "unknown", ""):
                    tops.append(top)
                    continue
            # Could not resolve this operand — conservative bail-out.
            return None

        if not tops:
            return None

        first = tops[0]
        # All operands must have the same owner.
        if any(t != first for t in tops[1:]):
            return None

        # Only allow methods known to exist on compare-result objects.
        allowed = _COMPARE_RESULT_METHODS.get(first)
        if allowed is None or method_name not in allowed:
            return None

        return InstanceMethod(first, method_name)

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
    ## Resolve an Attribute receiver through scope binding.
    #
    #  When the root of the attribute chain (e.g. "v" in "v.armW.mean")
    #  has a scope binding with a library source, propagate it instead
    #  of returning the raw dotted name.
    #  @param receiver_node The Attribute AST node.
    #  @param receiver_name The full dotted name (e.g. "v.armW").
    #  @return Resolved source or the original receiver_name.
    def _resolve_attribute_receiver_chain(self, receiver_node, receiver_name):
        if receiver_name in self.symbols.direct:
            return receiver_name
        chain = self._attribute_chain_list(receiver_node)
        if chain and self.scope_model == "v2":
            root_src = self._lookup_name_source(chain[0])
            if root_src and root_src != chain[0]:
                return root_src
        return receiver_name

    def _resolve_call_receiver(self, receiver_node):
        if isinstance(receiver_node, ast.Name):
            return self._lookup_name_source(receiver_node.id)
        if isinstance(receiver_node, ast.Attribute):
            receiver_name = self._attribute_name(receiver_node)
            if receiver_name is not None:
                return self._resolve_attribute_receiver_chain(
                    receiver_node, receiver_name)
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

    ## Record decorator evidence without overwriting the target's primary binding.
    #
    #  Each decorator expression is traced and recorded as a separate
    #  provenance record (kind="decorated_by"), while the decorated
    #  function/class keeps its "local" primary identity.
    #  @param target_name Name of the decorated function/class.
    #  @param decorator_nodes List of decorator AST nodes.
    def _bind_decorated_target(self, target_name, decorator_nodes):
        if not decorator_nodes:
            return
        for deco in reversed(decorator_nodes):
            deco_source = self.trace_source(deco)
            if not deco_source or (isinstance(deco_source, str) and _is_builtin(deco_source)):
                continue
            if deco_source == "local" and isinstance(deco, ast.Name):
                fn = deco.id
                rs = self.return_sources.get(fn)
                if rs is not None and not (isinstance(rs, str) and rs == "local"):
                    deco_source = rs
                else:
                    deco_source = fn
            self._add_symbol_ref(
                target_name, deco_source, "decorated_by", deco)

    ## --- Assignment helpers ---

    ## Bind assignment targets to a source value.
    #
    #  Handles simple names, self.attr, and tuple/list unpacking.
    #  @param target The assignment target AST node.
    #  @param source The source symbol or structured tuple.
    def _target_to_source(self, target, source, kind="variable",
                          container_kind="", container_item_kind=""):
        if not source:
            return
        if isinstance(target, ast.Name):
            self._bind_target_name(
                target.id, source, target, kind,
                container_kind=container_kind,
                container_item_kind=container_item_kind)
            return
        if isinstance(target, ast.Attribute):
            name = self._attribute_name(target)
            if name and name.startswith("self."):
                self._bind_target_name(name, source, target, "attribute")
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._target_to_source(
                    elt, source, kind,
                    container_kind=container_kind,
                    container_item_kind=container_item_kind)

    ## Trace the source of a for-loop iterator.
    #  @param iter_node The iterator AST node.
    #  @return Source symbol, structured tuple, or None.
    def _iter_source(self, iter_node):
        if isinstance(iter_node, ast.Name):
            container_name = iter_node.id
            item_source = self.homogeneous_container_items.get(
                container_name)
            if item_source is not None:
                binding = self.current_scope().lookup(
                    container_name, skip_parent_classes=True)
                if binding is None or binding.scope_kind == SCOPE_MODULE:
                    return item_source
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
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    attr_source = self.instance_attrs.get((cn, name))
                    if attr_source is not None:
                        if isinstance(attr_source, str):
                            if attr_source in self.symbols.direct or '.' in attr_source:
                                return attr_source
                        else:
                            return attr_source
                root = chain[0]
                if self.scope_model == "v2":
                    return self._lookup_name_source(root)
                return root
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
        assignment_container_kind = _container_kind(node.value)
        assignment_item_kind = _container_item_kind(node.value)

        # Homogeneous comprehension evidence is flow-sensitive at module
        # scope. Any real rebind invalidates the previous element source.
        if self.current_scope().kind == SCOPE_MODULE:
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                is_self_assignment = (
                    isinstance(node.value, ast.Name)
                    and node.value.id == target.id
                )
                if not is_self_assignment:
                    self.homogeneous_container_items.pop(
                        target.id, None)

        ## Track literal assignments for static key resolution (PR7).
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (str, int)):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._literal_values[target.id] = node.value.value

        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    self.container_kinds[container_name] = "dict"
                    for key_node, value_node in zip(node.value.keys, node.value.values):
                        if isinstance(key_node, ast.Constant):
                            key_value = key_node.value
                            if isinstance(value_node, ast.Constant):
                                value_source = "python"
                            else:
                                value_source = self._value_source(value_node)
                            if value_source:
                                self.container_items[(container_name, key_value)] = value_source

        if isinstance(node.value, (ast.List, ast.Tuple)):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    n = len(node.value.elts)
                    self.container_lengths[container_name] = n
                    self.container_kinds[container_name] = (
                        "list" if isinstance(node.value, ast.List) else "tuple")
                    for i, elt in enumerate(node.value.elts):
                        value_source = _builtin_value_source(
                            elt, self.get_base)
                        if value_source:
                            self.container_items[(container_name, i)] = value_source

        if isinstance(node.value, ast.Set):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    self.container_kinds[container_name] = "set"
                    bases = set()
                    for elt in node.value.elts:
                        base = _builtin_value_source(elt, self.get_base)
                        if base:
                            bases.add(base)
                    if bases:
                        self.container_set_sources[container_name] = bases

        # 1.0.5 P1: track container kinds for comprehensions and constructors.
        if isinstance(node.value, ast.ListComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "list"
                    if self.current_scope().kind == SCOPE_MODULE:
                        item_source = self.trace_source(node.value.elt)
                        if item_source is not None:
                            self.homogeneous_container_items[
                                target.id] = item_source
        if isinstance(node.value, ast.SetComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "set"
        if isinstance(node.value, ast.DictComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "dict"
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "str"
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            func_id = node.value.func.id
            if func_id in ("list", "dict", "set", "tuple", "str"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.container_kinds[target.id] = func_id
            # 1.0.5 P1+: track defaultdict(list) / defaultdict(dict) etc.
            # so d[k].append(v) can be classified from the item kind.
            if func_id == "defaultdict" and len(node.value.args) >= 1:
                factory = node.value.args[0]
                if isinstance(factory, ast.Name):
                    factory_name = factory.id
                    if factory_name in ("list", "dict", "set", "tuple", "str"):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                self.container_item_kinds[target.id] = factory_name

        # 1.0.5 P1: invalidate container kind for non-container RHS so
        # re-binding (e.g. x=[] then x=Bag()) does not leak the old kind.
        _container_rhs_types = (ast.Dict, ast.List, ast.Tuple, ast.Set,
                                ast.ListComp, ast.SetComp, ast.DictComp)
        _container_funcs = {"list", "dict", "set", "tuple", "str"}
        if not isinstance(node.value, _container_rhs_types):
            if not (isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                if not (isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and (node.value.func.id in _container_funcs
                             or _is_defaultdict_itemkind(node.value))):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.container_kinds.pop(target.id, None)
                            self.container_item_kinds.pop(target.id, None)

        ## Collect assignment target names and delegate to shared pipeline.
        targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        targets.append(elt.id)
        right = self._visit_assignment(node, targets)
        callable_keys = {}
        if isinstance(node.value, ast.Lambda):
            lambda_result = right or UnknownSource("lambda result")
            for name in targets:
                callable_key = self._local_callable_key(name)
                callable_keys[name] = callable_key
                self.return_sources[callable_key] = lambda_result
            # The lambda expression defines a project-local callable. Its
            # body source describes only the object returned by that call.
            right = "local"
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
                    self._bind_target_name(
                        target.id, right, target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(target.id, ""))
                elif isinstance(target, ast.Attribute):
                    name = self._attribute_name(target)
                    if name and name.startswith("self."):
                        if isinstance(right_norm, InstanceMethod):
                            continue
                        attr_source = right
                        if (
                            self.scope_model == "v2"
                            and isinstance(node.value, ast.Name)
                            and right == "local"
                        ):
                            attr_source = node.value.id
                        self._bind_target_name(
                            name, attr_source, target,
                            container_kind=assignment_container_kind or "",
                            container_item_kind=assignment_item_kind or "")
                elif isinstance(target, (ast.Tuple, ast.List)):
                    unpacked_owner = None
                    if isinstance(node.value, ast.Call):
                        func_top, func_name = self._resolve_func_top(
                            node.value.func)
                        unpacked_owner = _match_result_item_owner(
                            func_top, func_name)
                    for index, elt in enumerate(target.elts):
                        if isinstance(elt, ast.Name):
                            if (isinstance(node.value, (ast.Tuple, ast.List))
                                    and index < len(node.value.elts)):
                                dependency = self._parameter_dependency_source(
                                    node.value.elts[index])
                                if dependency is not None:
                                    self._bind_target_name(
                                        elt.id, dependency, elt)
                                    continue
                            if unpacked_owner is not None:
                                self._bind_target_name(
                                    elt.id, unpacked_owner, elt)
                                continue
                            # Preserve positional provenance when unpacking a
                            # named value.  Flattening every element to the
                            # traced top (often "local" for a parameter)
                            # allows a module-level symbol with the same name
                            # to leak back in during cross-file resolution.
                            if isinstance(node.value, ast.Name):
                                self._bind_target_name(
                                    elt.id,
                                    ContainerItem(node.value.id, index),
                                    elt)
                                continue
                            if isinstance(right_norm, InstanceMethod):
                                if isinstance(right_norm.receiver, str):
                                    # 1.0.5 P1: consult result-owner map
                                    # before binding.  linalg.svd(arr)
                                    # returns numpy arrays even though
                                    # linalg is scipy.
                                    rcvr_top = self.symbols.get_top(
                                        right_norm.receiver)
                                    if rcvr_top:
                                        ret = _match_result_item_owner(
                                            rcvr_top, right_norm.method)
                                        if ret:
                                            self._bind_target_name(
                                                elt.id, ret, elt)
                                            continue
                                    self._bind_target_name(
                                        elt.id, right_norm.receiver, elt)
                                continue
                            self._bind_target_name(elt.id, right, elt)
        else:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._bind_target_name(
                        target.id, 'local', target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(target.id, ""))
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            self._bind_target_name(elt.id, 'local', elt)
                elif isinstance(target, ast.Attribute):
                    name = self._attribute_name(target)
                    if name and name.startswith("self."):
                        self._bind_target_name(
                            name, 'local', target,
                            container_kind=assignment_container_kind or "",
                            container_item_kind=assignment_item_kind or "")
        # 1.0.5 P0: generic_visit already called above, before target binding.
        self._collect_argparse_assignment(node)

    ## Resolve a receiver name to its top library (v2 scope-aware).
    def _receiver_top(self, name):
        if self.scope_model == "v2":
            binding = self.current_scope().lookup(
                name, skip_parent_classes=True)
            if binding is not None:
                src = normalize_source(binding.source)
                if isinstance(src, str):
                    if src in ("local", "python", "unknown", ""):
                        return src or None
                    source_top = self.symbols.get_top(src)
                    return source_top or src
                if isinstance(src, InstanceMethod):
                    receiver = normalize_source(src.receiver)
                    if isinstance(receiver, str):
                        receiver_top = self.symbols.get_top(receiver)
                        return receiver_top or receiver
                    return None
                if isinstance(src, CallResult):
                    result_owner = normalize_source(src.result_source)
                    if isinstance(result_owner, str):
                        owner_top = self.symbols.get_top(result_owner)
                        return owner_top or result_owner
                    if isinstance(result_owner, UnknownSource):
                        return "unknown"
                    if not isinstance(src.callee, str):
                        return None
                    callee_top = self.symbols.get_top(src.callee)
                    if callee_top and callee_top not in ("local", name):
                        return callee_top
                    # Follow return_sources through local functions
                    rs = self.return_sources.get(src.callee)
                    if rs is not None:
                        rs = normalize_source(rs)
                        sources = rs.sources if isinstance(rs, SourceSet) else [rs]
                        for s in sources:
                            s = normalize_source(s)
                            if isinstance(s, CallResult) and isinstance(s.callee, str):
                                callee_top = self.symbols.get_top(s.callee)
                                if callee_top and callee_top not in ("local", name):
                                    return callee_top
                    return callee_top
                # A lexical binding is authoritative.  Do not consult a
                # same-name module binding when its structured source cannot
                # be resolved here.
                return None
        top = self.symbols.get_top(name)
        return top

    ## Resolve the ownership top of an expression node.
    #  Recursively handles ast.Call arguments so that
    #  np.log(price.dropna()).diff() preserves the inner call's
    #  receiver owner (pandas).
    #  Respects conversion boundaries: data.to_numpy() returns
    #  numpy even though the receiver is pandas.
    def _expr_receiver_top(self, expr):
        if isinstance(expr, ast.Name):
            return self._receiver_top(expr.id)
        if isinstance(expr, ast.Constant):
            return "python"
        if isinstance(expr, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return "python"
        if isinstance(expr, ast.UnaryOp):
            return self._expr_receiver_top(expr.operand)
        if isinstance(expr, ast.BinOp):
            left_top = self._expr_receiver_top(expr.left)
            right_top = self._expr_receiver_top(expr.right)
            if left_top == right_top:
                return left_top
            external = [
                top for top in (left_top, right_top)
                if top not in (None, "", "local", "python", "unknown")]
            other = [
                top for top in (left_top, right_top)
                if top not in external]
            if (len(set(external)) == 1
                    and all(top == "python" for top in other)):
                return external[0]
            return None
        if isinstance(expr, ast.Subscript):
            return self._expr_receiver_top(expr.value)
        if isinstance(expr, ast.Attribute):
            receiver = expr.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top:
                    return _CONVERSION_ATTRIBUTE_TARGETS.get(
                        (receiver_top, expr.attr))
            return None
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            receiver = expr.func.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    # Check conversion boundary first:
                    # data.to_numpy() return is numpy, not pandas.
                    conv = _CONVERSION_METHOD_TARGETS.get((receiver_top, expr.func.attr))
                    if conv:
                        return conv
                    return receiver_top
        return None

    ## Resolve (top_library, function_name) for a function expression.
    #  Handles both bare names (cdist) and dotted names (np.log).
    def _resolve_func_top(self, func_node):
        if isinstance(func_node, ast.Name):
            name = func_node.id
            top = self._receiver_top(name)
            imported_name = self.import_from_symbols.get(name, "")
            func_name = (
                imported_name.rsplit(".", 1)[-1]
                if imported_name else name)
            if (top and top not in ("local", "python", "unknown", "")
                    and (top != name
                         or name in self.import_aliases
                         or name in self.import_from_symbols)):
                return (top, func_name)
        if isinstance(func_node, ast.Attribute):
            full_name = self._attribute_name(func_node)
            prefix = ""
            if full_name:
                imported_prefixes = sorted(
                    (
                        name for name in self.import_aliases
                        if (full_name == name
                            or full_name.startswith(name + "."))
                    ),
                    key=len,
                    reverse=True,
                )
                if imported_prefixes:
                    prefix = imported_prefixes[0]
                else:
                    prefix = full_name.split(".", 1)[0]
            prefix_top = self._receiver_top(prefix)
            if (prefix_top
                    and prefix_top not in ("local", "python", "unknown", "")
                    and (prefix_top != prefix
                         or prefix in self.import_aliases
                         or prefix in self.import_from_symbols)):
                return (prefix_top, func_node.attr)
        return (None, None)

    ## Resolve a true-branch receiver-owner guard.
    #
    #  @param test_node Conditional expression.
    #  @return (receiver_name, owner) or None.
    def _resolve_receiver_owner_guard(self, test_node):
        if (not isinstance(test_node, ast.Call)
                or len(test_node.args) != 1
                or not isinstance(test_node.args[0], ast.Name)):
            return None
        func_top, func_name = self._resolve_func_top(test_node.func)
        for (lib_prefix, name), contract in (
                _TYPE_GUARD_OWNER_CONTRACTS.items()):
            if (name == func_name
                    and func_top is not None
                    and (func_top == lib_prefix
                         or func_top.startswith(lib_prefix + "."))):
                return (test_node.args[0].id, contract[0])
        return None

    ## Visit nodes under an optional receiver-owner guard.
    #
    #  @param nodes Iterable of AST nodes.
    #  @param guard Optional (receiver_name, owner) pair.
    def _visit_guarded_nodes(self, nodes, guard):
        if guard is not None:
            self._receiver_owner_guards.append({guard[0]: guard[1]})
        try:
            for child in nodes:
                self.visit(child)
        finally:
            if guard is not None:
                self._receiver_owner_guards.pop()

    ## Resolve a verified owner for an item selected from a call result.
    #
    #  Direct import calls use _resolve_func_top().  Receiver calls additionally
    #  use _resolve_methods(), which can recover owners stored on instance
    #  attributes such as self.model = GPRegression(...).
    #  @param call_node The call whose result is indexed or destructured.
    #  @return Verified item owner string, or None.
    def _resolve_call_result_item_owner(self, call_node):
        func_top, func_name = self._resolve_func_top(call_node.func)
        owner = _match_result_item_owner(func_top, func_name)
        if owner is not None:
            return owner
        method_source = normalize_source(self._resolve_methods(call_node))
        if isinstance(method_source, InstanceMethod):
            receiver = normalize_source(method_source.receiver)
            if isinstance(receiver, str):
                receiver_top = self.symbols.get_top(receiver) or receiver
                if receiver_top not in (
                        None, "", "local", "python", "unknown"):
                    return _match_result_item_owner(
                        receiver_top, method_source.method)
        if (not isinstance(call_node.func, ast.Attribute)
                or not isinstance(call_node.func.value, ast.Attribute)
                or not self._class_stack):
            return None
        receiver_name = self._attribute_name(call_node.func.value)
        if not receiver_name or not receiver_name.startswith("self."):
            return None
        attr_source = normalize_source(self.instance_attrs.get(
            (self._class_stack[-1], receiver_name)))
        if isinstance(attr_source, CallResult):
            attr_source = normalize_source(
                attr_source.result_source or attr_source.callee)
        if not isinstance(attr_source, str):
            return None
        attr_top = self.symbols.get_top(attr_source) or attr_source
        if attr_top in (None, "", "local", "python", "unknown"):
            return None
        return _match_result_item_owner(attr_top, call_node.func.attr)

    ## Resolve the result owner of a protocol-dispatched NumPy ufunc.
    #
    #  Pandas and NumPy inputs retain their owner.  Python literals and
    #  containers produce NumPy results.  An unresolved or other import-backed
    #  receiver remains unknown because array protocols may override dispatch.
    #  @param call_node Ufunc call expression.
    #  @param func_top Resolved callable owner.
    #  @param func_name Resolved function name.
    #  @return Owner string, UnknownSource, or None when not applicable.
    def _receiver_preserving_result_owner(self, call_node, func_top,
                                          func_name):
        if (func_top != "numpy"
                or func_name not in _RECEIVER_PRESERVE_UFUNCS
                or not call_node.args):
            return None
        arg_tops = []
        for argument in call_node.args:
            arg_top = self._expr_receiver_top(argument)
            if (_container_kind(argument) is not None
                    or isinstance(argument, ast.Constant)):
                arg_top = "python"
            if arg_top in (None, "", "local", "unknown"):
                return UnknownSource("receiver-preserving ufunc result")
            arg_tops.append(arg_top)

        external = set(top for top in arg_tops if top != "python")
        if not external:
            return "numpy"
        if len(external) == 1:
            owner = next(iter(external))
            if owner in ("pandas", "numpy"):
                return owner
        return UnknownSource("receiver-preserving ufunc result")

    ## Check whether a call expression is a known library-to-library conversion.
    #
    #  Unwraps trailing attribute chains (e.g. data.to_numpy().T) to find
    #  the inner conversion call, then looks up (source_library, method).
    #  @param value_node The RHS expression node.
    #  @return The conversion target library name, or None.
    def _resolve_conversion_target(self, value_node):
        # Unwrap trailing attribute chain: data.to_numpy().T → data.to_numpy()
        call_node = value_node
        while isinstance(call_node, ast.Attribute) and isinstance(call_node.value, (ast.Call, ast.Attribute)):
            call_node = call_node.value

        if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Attribute):
            # Method call: data.to_numpy() → conversion if method in table.
            method = call_node.func.attr
            receiver = call_node.func.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    conv = _CONVERSION_METHOD_TARGETS.get((receiver_top, method))
                    if conv:
                        return conv
            # Not a known conversion method — fall through to check
            # function-call return types (e.g. np.log, cdist).

        if isinstance(call_node, ast.Attribute):
            # Bare attribute read: data.values → conversion if attr in table.
            # Bare method references (data.to_numpy without call) are NOT
            # conversions — saving a method object does not change the result type.
            attr_name = call_node.attr
            receiver = call_node.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    return _CONVERSION_ATTRIBUTE_TARGETS.get((receiver_top, attr_name))
            return None

        # 1.0.5 P1: function-call return type.  cdist(...) → numpy,
        # receiver-preserving ufunc np.log(pd.Series) → pandas.
        if isinstance(call_node, ast.Call):
            func_top, func_name = self._resolve_func_top(call_node.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                # Check explicit result-owner map (cdist → numpy).
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    call_node, func_top, func_name)
                if preserved is not None:
                    return preserved
        return None

    ## Shared assignment pipeline: pending targets, trace RHS, visit, call_assign_funcs.
    #
    #  @param node The Assign or AnnAssign AST node.
    #  @param target_names Flat list of target name strings.
    #  @return The traced RHS source (right-hand value).
    def _visit_assignment(self, node, target_names):
        imported_call = self._imported_call_result_source(node.value)
        for name in target_names:
            key = (id(self.current_scope()), name)
            if imported_call is None:
                self._assigned_call_sources.pop(key, None)
            else:
                self._assigned_call_sources[key] = imported_call
        if target_names and isinstance(node.value, ast.Call):
            self._pending_call_targets_by_node[id(node.value)] = target_names

        result_item_owner = None
        if (isinstance(node.value, ast.Subscript)
                and isinstance(node.value.value, ast.Call)):
            result_item_owner = self._resolve_call_result_item_owner(
                node.value.value)
        right = (result_item_owner
                 or self._parameter_dependency_source(node.value)
                 or self.trace_source(node.value))
        # 1.0.5 P1: if the RHS is a known conversion call
        # (e.g. data.to_numpy()), override the bound source
        # so subsequent calls on the target use the post-conversion
        # library.  Also handles data.to_numpy().T chains.
        conversion = self._resolve_conversion_target(node.value)
        if conversion:
            right_norm = normalize_source(right)
            if isinstance(right_norm, CallResult):
                right = CallResult(
                    right_norm.callee,
                    display_name=right_norm.display_name,
                    call_lineno=right_norm.call_lineno,
                    call_col_offset=right_norm.call_col_offset,
                    result_source=conversion,
                )
            else:
                right = conversion
        # 1.0.5 P0: visit RHS before binding targets
        self.generic_visit(node)
        # 1.0.5 P0: call_assign_funcs after generic_visit
        value_node = node.value
        # Unwrap trailing attributes for call_assign_funcs:
        # data = data.to_numpy().T  →  extract data.to_numpy
        while isinstance(value_node, ast.Attribute):
            value_node = value_node.value
        if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Attribute):
            func_full = self._attribute_name(value_node.func)
            if func_full:
                for name in target_names:
                    self.call_assign_funcs[name] = func_full
        return right

    ## Visit an AnnAssign node (x: T = expr) with RHS-before-target ordering.
    #
    #  Same contract as visit_Assign: visit the RHS value before binding
    #  the target symbol so nested RHS calls use the pre-assignment state.
    #  @param node The AnnAssign AST node.
    def visit_AnnAssign(self, node):
        if node.value is None:
            return
        assignment_container_kind = _container_kind(node.value)
        assignment_item_kind = _container_item_kind(node.value)
        targets = []
        if isinstance(node.target, ast.Name):
            targets.append(node.target.id)
        elif isinstance(node.target, ast.Attribute):
            name = self._attribute_name(node.target)
            if name and name.startswith("self."):
                targets.append(name)
        elif isinstance(node.target, (ast.Tuple, ast.List)):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    targets.append(elt.id)
        right = self._visit_assignment(node, targets)
        callable_keys = {}
        if isinstance(node.value, ast.Lambda):
            lambda_result = right or UnknownSource("lambda result")
            for name in targets:
                callable_key = self._local_callable_key(name)
                callable_keys[name] = callable_key
                self.return_sources[callable_key] = lambda_result
            right = "local"

        if right:
            right_norm = normalize_source(right)
            if isinstance(node.target, ast.Name):
                if isinstance(right, str) and right == node.target.id:
                    pass  # skip self-assign
                else:
                    self._bind_target_name(
                        node.target.id, right, node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(node.target.id, ""))
            elif isinstance(node.target, ast.Attribute):
                name = self._attribute_name(node.target)
                if name and name.startswith("self."):
                    self._bind_target_name(
                        name, right, node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "")
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        self._bind_target_name(elt.id, right, elt)
        else:
            if isinstance(node.target, ast.Name):
                self._bind_target_name(
                    node.target.id, 'local', node.target,
                    container_kind=assignment_container_kind or "",
                    container_item_kind=assignment_item_kind or "",
                    callable_key=callable_keys.get(node.target.id, ""))
            elif isinstance(node.target, ast.Attribute):
                name = self._attribute_name(node.target)
                if name and name.startswith("self."):
                    self._bind_target_name(
                        name, 'local', node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "")
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        self._bind_target_name(elt.id, 'local', elt)

    ## --- API call detection ---

    ## Resolve the base of an API call for origin tracking.
    #
    #  Tries getattr(), import_module(), method resolution, and
    #  call-lookup receiver resolution in order.
    #  @param node The Call AST node.
    #  @return Base symbol, structured tuple, or None.
    def _resolve_call_base_for_api(self, node):
        # P0 (1.0.5): bare getattr() builtin calls must be classified as
        # python, not traced through the argument's provenance.  Only
        # trace through obj.getattr("name") style calls where getattr is
        # accessed as an attribute on a receiver object.
        if self._is_getattr_call(node) and not isinstance(node.func,
                                                          ast.Name):
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
        # 1.0.5 P1+: defaultdict(list) item kind — d[k].append(v) where
        # d = defaultdict(list) has item kind "list".
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Subscript):
                sub = node.func.value
                if isinstance(sub.value, ast.Name):
                    item_kind = self._lookup_container_kind(
                        sub.value.id, item=True)
                    if item_kind is not None:
                        return InstanceMethod(sub.value.id, node.func.attr)
        ## For chained calls (A().B()), resolve via the inner call's
        ## return source so the outer call traces to the correct library.
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            inner_source = self.trace_source(node.func.value)
            if isinstance(inner_source, str):
                rs = self.return_sources.get(inner_source)
                if rs is not None:
                    return rs
            if isinstance(inner_source, CallResult):
                if inner_source.result_source is not None:
                    return inner_source.result_source
                rs = self.return_sources.get(inner_source.callee)
                if rs is not None:
                    return rs
            if isinstance(inner_source, SourceSet):
                return inner_source
            # 1.0.5 P1: library-function return types for chained
            # calls (cdist(...).argmin(), np.log(s).diff()).
            inner_call = node.func.value
            func_top, func_name = self._resolve_func_top(inner_call.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    inner_call, func_top, func_name)
                if preserved is not None:
                    return preserved
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

        ## Record CallEdge fact for Phase 7B-full call graph.
        if self._caller_stack:
            caller = self._caller_stack[-1]
            ## Collect receiver source for obj.method() calls.
            receiver_source = None
            if isinstance(node.func, ast.Attribute):
                receiver = node.func.value
                if (isinstance(receiver, ast.Name)
                        and receiver.id in ("self", "cls")):
                    receiver_source = self.get_base(receiver)
                else:
                    receiver_source = self._call_edge_argument_source(
                        receiver)
            ## Collect arg sources — positional indexed, keyword by name.
            arg_sources = {"pos": {}, "kw": {}}
            for i, arg in enumerate(node.args):
                arg_src = self._call_edge_argument_source(arg)
                if arg_src is not None:
                    arg_sources["pos"][i] = arg_src
            for kw in getattr(node, "keywords", []) or []:
                arg_src = (
                    self._call_edge_argument_source(kw.value)
                    if kw.arg else None)
                if arg_src is not None and kw.arg:
                    arg_sources["kw"][kw.arg] = arg_src
            ## Consume assigned_to only for the top-level RHS call.
            assigned = self._pending_call_targets_by_node.pop(id(node), [])
            edge = CallEdge(
                caller=caller,
                callee=base,
                callee_name=func_name or "",
                callee_source=self.trace_source(node.func),
                receiver_source=receiver_source,
                arg_sources=arg_sources,
                assigned_to=assigned,
                call_lineno=node.lineno,
                call_col_offset=node.col_offset,
            )
            self.module_cg.edges.append(edge)

        if isinstance(node.func, ast.Name):
            direct_name = node.func.id
        else:
            direct_name = None

        scope_name = ""
        if self.scope_model == "v2":
            cs = self.current_scope()
            if cs.kind != SCOPE_MODULE:
                scope_name = cs.name
        loc = {
            'func_name': func_name,
            'parameters': parameters,
            'lineno': node.lineno,
            'col_offset': node.col_offset,
            'end_lineno': getattr(node, 'end_lineno', 0) or 0,
            'end_col_offset': getattr(node, 'end_col_offset', 0) or 0,
            'scope_name': scope_name,
        }
        # 1.0.5 P0: snapshot call_assign_funcs for dotted calls so
        # cross-file _resolve_func_name reads the pre-assignment
        # state, not the final map that may include later
        # reassignments.
        if func_name and '.' in func_name:
            first = func_name.split('.')[0]
            loc['call_assign_func'] = self.call_assign_funcs.get(first)

        # The callable identity of an unshadowed builtin is independent of
        # the object it returns.  Record it before return-value provenance can
        # introduce an unrelated same-name assignment from another scope.
        if direct_name and _is_unshadowed_builtin_call(self, node):
            record = {
                'api': api_string,
                'top': 'python',
                'chain': ['python'] if self.scope_model == "v2" else [],
                'base': direct_name,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    direct_name, loc)
            return

        # A concrete receiver kind determines the callable owner even when
        # legacy base resolution represents the receiver as a plain string.
        # This covers names, self attributes, and homogeneous subscript items.
        receiver_kind = self._call_receiver_container_kind(node)
        method_name = (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if (receiver_kind is not None
                and method_name in _BUILTIN_CONTAINER_METHODS.get(
                    receiver_kind, frozenset())):
            loc["receiver_container_kind"] = receiver_kind
            record = {
                'api': api_string,
                'top': 'python',
                'chain': ['python'] if self.scope_model == "v2" else [],
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if isinstance(base, UnknownSource):
            record = {
                'api': api_string,
                'top': 'unknown',
                'chain': ['unknown'] if self.scope_model == "v2" else [],
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if isinstance(base, CallResult):
            # Resolve top through the callee so s.get() shows 'requests'
            # instead of 'requests()' when s = Session().
            callee = base.callee
            ## 1.0.5 P2: explicit result_source carries result-object ownership.
            #  When set, it overrides callee-based tracing — the callable's
            #  identity is determined by what the called function returns,
            #  not who was called.
            rs_explicit = getattr(base, 'result_source', None)
            if rs_explicit is not None:
                if isinstance(rs_explicit, UnknownSource):
                    top = "unknown"
                elif rs_explicit == "python":
                    top = "python"
                elif isinstance(rs_explicit, DerivedResult):
                    # Structured: defer to cross_file for resolution.
                    # In single-file, use source_display as placeholder.
                    top = source_display(base)
                else:
                    # String source — direct ownership.
                    top = str(rs_explicit)
            elif isinstance(callee, str):
                rs = self.return_sources.get(callee)
                if rs is not None:
                    resolved = normalize_source(rs)
                    if isinstance(resolved, CallResult):
                        inner_callee = resolved.callee
                        if isinstance(inner_callee, str):
                            callee = inner_callee
                    elif isinstance(resolved, SourceSet):
                        top = source_display(base)
                        chain = [top] if (self.scope_model == "v2") else []
                        record = {
                            'api': api_string,
                            'top': top,
                            'chain': chain,
                            'base': base,
                            'direct_name_callee': direct_name,
                        }
                        record.update(loc)
                        self.api_calls.append(record)
                        self._collect_call_site(api_string, func_name, parameters,
                                                base, loc)
                        return
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
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if isinstance(base, tuple) or isinstance(base, (ContainerItem, ContainerIter, InstanceMethod, SuperMethod, SourceSet)):
            # Unresolved compare receiver: owner cannot be determined.
            # Emit as unknown so the call is collected but not
            # misattributed to local.
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, str)
                    and base.receiver == "__unresolved_compare__"):
                display = "unknown"
                chain = ["unknown"] if (self.scope_model == "v2") else []
                record = {
                    'api': api_string,
                    'top': display,
                    'chain': chain,
                    'base': base,
                    'direct_name_callee': direct_name,
                }
                record.update(loc)
                self.api_calls.append(record)
                self._collect_call_site(api_string, func_name, parameters,
                                        base, loc)
                return

            display = source_display(base)
            if isinstance(base, InstanceMethod) and isinstance(base.receiver, str):
                top_from_receiver = self.symbols.get_top(base.receiver)
                # 1.0.5 P1: builtin container methods on receivers
                # whose container kind is known.  The receiver may be
                # local via get_top, scope binding, or item kind
                # (defaultdict(list) — receiver traces to collections
                # but item kind is list).
                #
                rec_local = (top_from_receiver == "local")
                if (not rec_local and self.scope_model == "v2"):
                    binding = self.current_scope().lookup(base.receiver)
                    if (binding is not None
                            and binding.source == "local"):
                        rec_local = True
                # Use the exact call receiver shape to distinguish
                # d[k].append() item metadata from d.append(). Lexical
                # binding metadata prevents same-name scope leakage.
                kind = self._call_receiver_container_kind(node)
                if rec_local or kind is not None:
                    if (kind is not None
                            and base.method in _BUILTIN_CONTAINER_METHODS.get(
                                kind, frozenset())):
                        display = "python"
                        # Record kind at call-site time so cross-file
                        # phase doesn't see later invalidation.
                        loc["receiver_container_kind"] = kind
                    elif rec_local and not base.parameter_scope:
                        display = "local"
                    else:
                        display = display  # keep source_display default
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
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
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
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
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
        self._collect_call_site(api_string, func_name, parameters,
                                base, loc)

    ## Collect a CallSite from the raw call data.
    #  @param expression Full call expression.
    #  @param func_name Function part.
    #  @param parameters Arguments string.
    #  @param base Base symbol or source.
    #  @param loc Dict with lineno/col_offset/end_lineno/end_col_offset.
    def _collect_call_site(self, expression, func_name, parameters,
                           base, loc):
        scope_name = ""
        if self.scope_model == "v2":
            cs = self.current_scope()
            if cs.kind != SCOPE_MODULE:
                scope_name = cs.name
        self.call_site_objects.append(CallSite(
            expression=expression,
            func_name=func_name,
            parameters=parameters,
            base=base,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            lineno=loc.get('lineno', 0),
            col_offset=loc.get('col_offset', 0),
            end_lineno=loc.get('end_lineno', 0),
            end_col_offset=loc.get('end_col_offset', 0),
            scope_name=scope_name,
        ))

    ## Record verified owner evidence supplied to callback parameters.
    #
    #  @param node The call expression accepting a callback.
    def _collect_callback_parameter_sources(self, node):
        func_top, func_name = self._resolve_func_top(node.func)
        if not func_top or not func_name:
            return
        for (owner, name, callback_index, parameter_index), contract in (
                _CALLBACK_PARAMETER_OWNER_CONTRACTS.items()):
            if (name != func_name
                    or not (func_top == owner
                            or func_top.startswith(owner + "."))
                    or callback_index >= len(node.args)):
                continue
            callback = node.args[callback_index]
            callback_key = self._value_source(callback)
            if not isinstance(callback_key, str):
                continue
            bare_key = callback_key.rsplit(".", 1)[-1]
            params = (self.function_params.get(callback_key)
                      or self.function_params.get(bare_key, []))
            if parameter_index >= len(params):
                continue
            parameter = params[parameter_index]
            self.parameter_sources.setdefault(
                (callback_key, parameter), []).append(contract[0])

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
        self._collect_argparse_destination(node)
        self._collect_callback_parameter_sources(node)
        for sub in self._chained_prefix_calls(node):
            self._one_api_call(sub)
        if isinstance(node.func, ast.Name) and node.func.id in self.defined_functions:
            arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
            self.call_sites.setdefault(node.func.id, []).append({
                "module": self.module_name,
                "args": arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
            })
        elif isinstance(node.func, ast.Name) and node.func.id in self.class_methods:
            arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
            self.call_sites.setdefault(node.func.id + ".__init__", []).append({
                "module": self.module_name,
                "args": arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
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

    ## Collect statically declared pytest parameter values.
    #
    #  pytest.mark.parametrize supplies concrete call-site-like evidence for
    #  test parameters even though pytest performs the invocation at runtime.
    #  Only literal parameter names and literal value sequences are accepted.
    #  @param node Function definition carrying decorators.
    #  @param qualname Qualified function name.
    #  @param params Declared function parameter names.
    def _collect_parametrize_sources(self, node, qualname, params):
        if self.scope_model != "v2":
            return
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

    ## Visit a FunctionDef node and register it as a local definition.
    #  @param node The FunctionDef AST node.
    def _visit_function_def(self, node):
        """Common handler for FunctionDef and AsyncFunctionDef."""
        self.local.add(node.name)
        ## Only module-level functions shadow builtins through bare-name
        ## calls.  Class methods are reachable only via self.<name>().
        if not self._class_stack:
            self.defined_functions.add(node.name)
        callable_key = self._local_callable_key(node.name)
        self._bind_target_name(
            node.name, "local", node, callable_key=callable_key)
        params = []
        self.push_scope(SCOPE_FUNCTION, node.name)
        for arg in (getattr(node.args, "posonlyargs", []) + node.args.args + getattr(node.args, "kwonlyargs", [])):
            if arg.arg != "self":
                params.append(arg.arg)
                self._bind_target_name(arg.arg, "local", arg, "parameter")
        if getattr(node.args, "vararg", None) is not None and node.args.vararg.arg != "self":
            params.append(node.args.vararg.arg)
            self._bind_target_name(node.args.vararg.arg, "local", kind="parameter")
        if getattr(node.args, "kwarg", None) is not None and node.args.kwarg.arg != "self":
            params.append(node.args.kwarg.arg)
            self._bind_target_name(node.args.kwarg.arg, "local", kind="parameter")
        self.function_params[node.name] = params
        if self._class_stack:
            self.function_params[self._class_stack[-1] + "." + node.name] = params
        self._func_stack.append(node.name)
        ## Determine qualified name for call-graph facts.
        ## Use full _func_stack so nested functions get "outer.inner".
        if self._class_stack:
            qualname = self._class_stack[-1] + "." + ".".join(self._func_stack)
        else:
            qualname = ".".join(self._func_stack)
        self._collect_parametrize_sources(node, qualname, params)
        fid = FunctionId(self.module_name or "", qualname)
        self._caller_stack.append(fid)
        # Save and clear _global_names so each function independently
        # scopes global declarations.
        saved_globals = self._global_names
        self._global_names = set()
        self.generic_visit(node)
        self._global_names = saved_globals
        self._caller_stack.pop()
        self._func_stack.pop()
        self.pop_scope()
        ## Collect FunctionSummary for Phase 7B-full facts.
        ## Use qualname so class methods don't share bare-name keys.
        func_returns = self.return_sources.get(qualname)
        if func_returns is None and not self._class_stack:
            func_returns = self.return_sources.get(node.name)
        local_assignments = {}
        fs = FunctionSummary(
            id=fid,
            params=list(params),
            returns=func_returns,
            local_assignments=local_assignments,
        )
        self.module_cg.functions[qualname] = fs
        ## Link method to its class summary (created before class body visit).
        if self._class_stack:
            cn = self._class_stack[-1]
            if cn in self.module_cg.classes:
                if self._func_stack:
                    method_qualname = ".".join(self._func_stack)
                else:
                    method_qualname = node.name
                self.module_cg.classes[cn].methods[method_qualname] = fs
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
        ## Create ClassSummary BEFORE generic_visit so methods can link to it.
        class_id = FunctionId(self.module_name or "", node.name)
        self.module_cg.classes[node.name] = ClassSummary(
            id=class_id,
            bases=list(bases),
            methods={},
            attrs={},
        )
        self._class_stack.append(node.name)
        self.push_scope(SCOPE_CLASS, node.name)
        self.generic_visit(node)
        self.pop_scope()
        self._class_stack.pop()
        ## Populate ClassSummary attrs collected during class body visit.
        class_attrs = {}
        for (cn, attr_name), src in self.instance_attrs.items():
            if cn == node.name:
                class_attrs[attr_name] = src
        self.module_cg.classes[node.name].attrs.update(class_attrs)
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
        yields = self._resolve_iterator_yields(node.iter, node.target)
        if yields is not None:
            for item in yields:
                target_elt, source = item[:2]
                container_kind = item[2] if len(item) > 2 else ""
                container_item_kind = item[3] if len(item) > 3 else ""
                self._target_to_source(
                    target_elt, source, "iteration",
                    container_kind=container_kind,
                    container_item_kind=container_item_kind)
        else:
            source = self._iter_source(node.iter)
            item_kind = ""
            if isinstance(node.iter, ast.Name):
                item_kind = (
                    self._lookup_container_kind(node.iter.id, item=True)
                    or "")
            self._target_to_source(
                node.target, source, "iteration",
                container_kind=item_kind)
        self.generic_visit(node)

    ## Resolve per-element ownership for for-loop iterator expressions.
    #
    #  For enumerate(X), zip(A, B) etc., decomposes the target tuple
    #  and binds each element to the appropriate ownership source.
    #  @param iter_node The iterator AST node.
    #  @param target The loop target AST node.
    #  @return List of (target_elt, source) pairs, or None to fall back.
    def _resolve_iterator_yields(self, iter_node, target):
        if not isinstance(iter_node, ast.Call):
            return None
        func_name = (
            iter_node.func.id if isinstance(iter_node.func, ast.Name)
            else None)

        # os.walk() and os.fwalk() have a stable stdlib yield contract.
        # Every yielded field is a Python-provided value; binding each tuple
        # position to python also lets nested loops preserve filename-string
        # method ownership without treating os itself as the item owner.
        if isinstance(iter_node.func, ast.Attribute):
            func_top, dotted_name = self._resolve_func_top(iter_node.func)
            if (func_top is None
                    and isinstance(iter_node.func.value, ast.Name)):
                root = iter_node.func.value.id
                candidate_top = self.symbols.get_top(root)
                if root in self.import_aliases:
                    func_top = candidate_top
                    dotted_name = iter_node.func.attr
            expected_arity = 3 if dotted_name == "walk" else 4
            if (func_top == "os"
                    and dotted_name in ("walk", "fwalk")
                    and isinstance(target, (ast.Tuple, ast.List))
                    and len(target.elts) == expected_arity):
                result = [
                    (target.elts[0], "python", "str", ""),
                    (target.elts[1], "python", "list", "str"),
                    (target.elts[2], "python", "list", "str"),
                ]
                if expected_arity == 4:
                    result.append((target.elts[3], "python", "", ""))
                return result

        if func_name in self.import_from_symbols:
            imported = self.import_from_symbols[func_name]
            expected_arity = 3 if imported == "os.walk" else 4
            if (imported in ("os.walk", "os.fwalk")
                    and isinstance(target, (ast.Tuple, ast.List))
                    and len(target.elts) == expected_arity):
                result = [
                    (target.elts[0], "python", "str", ""),
                    (target.elts[1], "python", "list", "str"),
                    (target.elts[2], "python", "list", "str"),
                ]
                if expected_arity == 4:
                    result.append((target.elts[3], "python", "", ""))
                return result

        # Explicit iterator result contracts keep the iterator object's owner
        # separate from the ownership of each yielded element.
        if isinstance(target, ast.Name):
            func_top, resolved_name = self._resolve_func_top(iter_node.func)
            element_owner = _match_iterator_element_owner(
                func_top, resolved_name)
            if element_owner is not None:
                element_source = CallResult(
                    InstanceMethod(func_top, resolved_name),
                    call_lineno=iter_node.lineno,
                    call_col_offset=iter_node.col_offset,
                    result_source=element_owner,
                )
                return [(target, element_source)]
            traced = normalize_source(self.trace_source(iter_node))
            if isinstance(traced, CallResult):
                result_source = normalize_source(traced.result_source)
                if (isinstance(result_source, DerivedResult)
                        and result_source.kind == "iterator"
                        and result_source.sources):
                    return [(target, result_source.sources[0])]

        if func_name is None:
            return None

        ## enumerate(X): for i, x in ... → i=python, x from container elements
        if func_name == "enumerate" and iter_node.args:
            container = iter_node.args[0]
            container_source = self._iterator_container_source(container)
            if isinstance(target, ast.Tuple):
                elts = target.elts
                if len(elts) == 2:
                    item_kind = ""
                    if isinstance(container, ast.Name):
                        item_kind = (
                            self._lookup_container_kind(
                                container.id, item=True) or "")
                    if item_kind:
                        return [(elts[0], "python"),
                                (elts[1], "python", item_kind, "")]
                    return [(elts[0], "python"),
                            (elts[1], ContainerIter(container_source) if container_source else None)]
            return [(target, "python")]

        ## zip(A, B, ...): positional propagation from each input container
        if func_name == "zip" and iter_node.args:
            if isinstance(target, ast.Tuple):
                elts = target.elts
                if len(elts) == len(iter_node.args):
                    result = []
                    for elt, arg in zip(elts, iter_node.args):
                        arg_source = self._iterator_container_source(arg)
                        result.append((elt, ContainerIter(arg_source) if arg_source else None))
                    return result

        return None

    ## Return the container identity for iterator yield resolution.
    #
    #  Preserves AST Name identity for container_items lookup;
    #  falls back to trace_source for complex expressions.
    #  @param node The container AST node.
    #  @return Name string or traced source.
    def _iterator_container_source(self, node):
        if isinstance(node, ast.Name):
            return node.id
        return self.trace_source(node)

    ## Visit an AsyncFor node and bind the loop variable to the iterator source.
    #  @param node The AsyncFor AST node.
    def visit_AsyncFor(self, node):
        source = self._iter_source(node.iter)
        self._target_to_source(node.target, source, "iteration")
        self.generic_visit(node)

    ## Visit an If node with branch merging in v2 mode.
    #
    #  At module level, snapshots the current scope before the if, visits
    #  each branch independently, then merges the resulting bindings. At
    #  function level, falls back to generic_visit.
    #  TYPE_CHECKING guards are skipped at all levels.
    #  @param node The If AST node.
    def visit_If(self, node):
        if self.scope_model != "v2":
            self.generic_visit(node)
            return

        self.visit(node.test)
        receiver_guard = self._resolve_receiver_owner_guard(node.test)

        if self._is_type_checking_guard(node):
            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)
            return

        if self.current_scope().kind != SCOPE_MODULE:
            self._visit_guarded_nodes(node.body, receiver_guard)
            for stmt in node.orelse:
                self.visit(stmt)
            return

        scope_base = self.current_scope().snapshot()
        symbols_base = self.symbols.snapshot()

        self._visit_guarded_nodes(node.body, receiver_guard)
        scope_left = self.current_scope().snapshot()

        self.current_scope().restore(scope_base)
        self.symbols.restore(symbols_base)

        if node.orelse:
            for stmt in node.orelse:
                self.visit(stmt)
            scope_right = self.current_scope().snapshot()
        else:
            scope_right = scope_base

        merged = merge_snapshots(scope_base, scope_left, scope_right)
        for name, value in list(merged.items()):
            if not isinstance(value, Binding):
                merged[name] = Binding(
                    name=name, source=value,
                    scope_kind=self.current_scope().kind,
                )
        self.current_scope().restore(merged)
        for name, binding in merged.items():
            if isinstance(binding, Binding):
                self.symbols.add(name, binding.source)

    ## Visit a conditional expression with true-branch receiver narrowing.
    #
    #  @param node The IfExp AST node.
    def visit_IfExp(self, node):
        self.visit(node.test)
        receiver_guard = self._resolve_receiver_owner_guard(node.test)
        self._visit_guarded_nodes((node.body,), receiver_guard)
        self.visit(node.orelse)

    ## Check whether an If node guards on TYPE_CHECKING.
    #  @param node The If AST node.
    #  @return True if the test is a bare TYPE_CHECKING reference.
    def _is_type_checking_guard(self, node):
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            return True
        if isinstance(node.test, ast.Attribute):
            if node.test.attr == "TYPE_CHECKING":
                return True
        return False

    ## Visit a Try node with conservative branch merging in v2 mode.
    #
    #  At module level, each except handler and the else clause are treated
    #  as independent branches merged conservatively.  At function level,
    #  falls back to generic_visit (deferred to Phase 6 CFG).
    #  @param node The Try AST node.
    def visit_Try(self, node):
        if self.scope_model != "v2":
            self.generic_visit(node)
            return

        if self.current_scope().kind != SCOPE_MODULE:
            self.generic_visit(node)
            return

        scope_base = self.current_scope().snapshot()
        symbols_base = self.symbols.snapshot()

        for stmt in node.body:
            self.visit(stmt)
        scope_try = self.current_scope().snapshot()
        symbols_try = self.symbols.snapshot()

        all_branches = [scope_try]
        for handler in node.handlers:
            self.current_scope().restore(scope_base)
            self.symbols.restore(symbols_base)
            if handler.type:
                self.visit(handler.type)
            if handler.name:
                self._bind_target_name(handler.name, "local", handler, "variable")
            for stmt in handler.body:
                self.visit(stmt)
            all_branches.append(self.current_scope().snapshot())

        if node.orelse:
            self.current_scope().restore(scope_try)
            self.symbols.restore(symbols_try)
            for stmt in node.orelse:
                self.visit(stmt)
            all_branches.append(self.current_scope().snapshot())

        merged = scope_base
        for branch in all_branches:
            merged = merge_snapshots(scope_base, merged, branch)
        for name, value in list(merged.items()):
            if not isinstance(value, Binding):
                merged[name] = Binding(
                    name=name, source=value,
                    scope_kind=self.current_scope().kind,
                )
        self.current_scope().restore(merged)

        for name, binding in merged.items():
            if isinstance(binding, Binding):
                self.symbols.add(name, binding.source)

        for stmt in node.finalbody:
            self.visit(stmt)

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

    ## Visit a Global node and mark names for module-scope routing.
    #  @param node The Global AST node.
    def visit_Global(self, node):
        for name in node.names:
            self._global_names.add(name)
        self.generic_visit(node)

    ## Visit a Nonlocal node. First edition: no-crash only.
    #  @param node The Nonlocal AST node.
    def visit_Nonlocal(self, node):
        self.generic_visit(node)

    ## Visit a Return node and record return-value flow for the function.
    #  @param node The Return AST node.
    def visit_Return(self, node):
        if self._func_stack and node.value is not None:
            func_name = self._func_stack[-1]
            source = (
                self._parameter_dependency_source(node.value)
                if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute))
                else None
            )
            result_kind = _container_kind(node.value)
            # A tuple owns only the aggregate object.  Its unpacked items may
            # have unrelated owners, so do not promote the function's entire
            # return contract to Python from a tuple literal alone.
            if source is not None:
                pass
            elif result_kind is not None and result_kind != "tuple":
                source = "python"
            elif (isinstance(node.value, ast.Name)
                  and self._lookup_container_kind(node.value.id) is not None):
                source = "python"
            else:
                source = self.trace_source(node.value)
            if source:
                if isinstance(source, str) and source in self.symbols.direct:
                    s = self.symbols.direct[source]
                    new_src = s if s else source
                else:
                    new_src = source
                if (source == "local" and isinstance(node.value, ast.Name)
                        and node.value.id in self.function_params.get(func_name, [])):
                    new_src = node.value.id
                ## Write qualified key for class methods; bare key only
                ## for non-class functions to prevent cross-class pollution.
                if self._class_stack:
                    qkey = self._class_stack[-1] + "." + func_name
                    old_q = self.return_sources.get(qkey)
                    self.return_sources[qkey] = make_source_set(
                        [old_q, new_src] if old_q else [new_src],
                        origin="return")
                else:
                    old = self.return_sources.get(func_name)
                    self.return_sources[func_name] = make_source_set(
                        [old, new_src] if old else [new_src],
                        origin="return")
                self._add_symbol_ref(
                    func_name + ".return", source, "return", node)
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
#  @param scope_model "v1" (legacy) or "v2" (lexical scopes, default).
#  @return FileAnalysis object.
def analyze_source(source, file_path="<string>", scope_model="v2"):
    tree = ast.parse(source)
    tracer = SingleFileAnalyzer(scope_model=scope_model, file_path=file_path)
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
