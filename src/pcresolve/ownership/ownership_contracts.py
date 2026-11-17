## @package pcresolve.ownership.ownership_contracts
#  Define evidence-backed ownership contracts.
#
#
#  Evidence-backed ownership and Python-shape result contracts.
#
#  These rules are ownership policy, not shared program facts. Both the
#  single-file and project analyzers import them without depending on each
#  other's implementation.
#  根据已记录证据提供归属和 Python 结果形态契约，供两种归属分析器使用。



from pcresolve.ownership.sources import PythonShape

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
        "python", "public-api:bs4.PageElement.text", PythonShape("str")),
    ("requests", "text"): (
        "python", "public-api:requests.Response.text", PythonShape("str")),
    ("spacy", "text"): (
        "python", "public-api:spacy Token/Span/Doc.text",
        PythonShape("str")),
    ("xml", "text"): (
        "python", "python-stdlib:xml.etree.ElementTree.Element.text",
        PythonShape("str")),
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
        "python", "python-stdlib:json.dumps", PythonShape("str")),
    ("json", "load"): (
        "python", "python-stdlib:json.load"),
    ("json", "loads"): (
        "python", "python-stdlib:json.loads"),
    ("re", "sub"): (
        "python", "python-stdlib:re.sub", PythonShape("str")),
    ("re", "split"): (
        "python", "python-stdlib:re.split", PythonShape("list", "str")),
    ("re", "group"): (
        "python", "python-stdlib:re.Match.group", PythonShape("str")),
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
    ("glob", "glob"): ("python", PythonShape("str")),
    ("glob", "iglob"): ("python", PythonShape("str")),
    ("os", "listdir"): ("python", PythonShape("str")),
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

## Match a verified owner for an import-backed call result.
## 匹配导入来源调用结果的已验证归属。
#
#  @param top Established callable owner or qualified prefix.
#  @param func_name Called function or method name.
#  @return Result owner or None when no contract matches.
def _match_result_owner(top, func_name):
    if top is None:
        return None
    for (lib_prefix, fn), contract in _RESULT_OWNER_CONTRACTS.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[0]
    return None


## Check whether any result-owner contract names a method.
## 检查是否存在针对该方法名的结果归属契约。
#
#  @param func_name Function or method name.
#  @return True if at least one contract uses the name.
def _has_result_owner_contract(func_name):
    return any(
        contract_name == func_name
        for _, contract_name in _RESULT_OWNER_CONTRACTS
    )


## Match a verified owner for an import-backed attribute value.
## 匹配导入来源属性值的已验证归属。
#
#  @param top Established receiver owner or qualified prefix.
#  @param attribute Attribute name.
#  @return Result owner or None when no contract matches.
def _match_attribute_result_owner(top, attribute):
    if top is None:
        return None
    for (lib_prefix, name), contract in (
            _ATTRIBUTE_RESULT_OWNER_CONTRACTS.items()):
        if (name == attribute
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[0]
    return None


## Match a concrete Python shape from an attribute-result contract.
## 从属性结果契约匹配具体 Python 形态。
#
#  @param top Established receiver owner or qualified prefix.
#  @param attribute Attribute name.
#  @return PythonShape or None when no shape contract matches.
def _match_attribute_python_shape(top, attribute):
    if top is None:
        return None
    for (lib_prefix, name), contract in (
            _ATTRIBUTE_RESULT_OWNER_CONTRACTS.items()):
        if (name == attribute
                and len(contract) >= 3
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[2]
    return None


## Match a concrete Python shape from a call-result contract.
## 从调用结果契约匹配具体 Python 形态。
#
#  @param top Established callable owner or qualified prefix.
#  @param func_name Called function or method name.
#  @return PythonShape or None when no shape contract matches.
def _match_result_python_shape(top, func_name):
    if top is None:
        return None
    for (lib_prefix, fn), contract in _RESULT_OWNER_CONTRACTS.items():
        if (fn == func_name
                and len(contract) >= 3
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[2]
    return None


## Check whether an owner occurs in the verified result contracts.
## 检查归属是否出现在已验证的结果契约中。
#
#  @param owner Candidate result owner.
#  @return True if a result contract names that owner.
def _is_verified_result_owner(owner):
    return owner in _VERIFIED_RESULT_OWNERS


## Match the uniform owner of indexed or unpacked call-result items.
## 匹配调用结果索引或解包元素的统一归属。
#
#  @param top Established callable owner or qualified prefix.
#  @param func_name Called function or method name.
#  @return Item owner or None when no contract matches.
def _match_result_item_owner(top, func_name):
    if top is None:
        return None
    for (lib_prefix, fn), owner in _RESULT_ITEM_OWNER_CONTRACTS.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return owner
    return None


## Match the owner of elements from a verified iterator contract.
## 匹配已验证迭代器契约中元素的归属。
#
#  @param top Established callable owner or qualified prefix.
#  @param func_name Called function or method name.
#  @return Element owner or None when no contract matches.
def _match_iterator_element_owner(top, func_name):
    if top is None:
        return None
    for (lib_prefix, fn), contract in _ITERATOR_ELEMENT_OWNER_MAP.items():
        if (fn == func_name
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[0] if isinstance(contract, tuple) else contract
    return None


## Match the Python shape of elements from a verified iterator contract.
## 匹配已验证迭代器契约中元素的 Python 形态。
#
#  @param top Established callable owner or qualified prefix.
#  @param func_name Called function or method name.
#  @return PythonShape or None when no shape contract matches.
def _match_iterator_element_shape(top, func_name):
    if top is None:
        return None
    for (lib_prefix, fn), contract in _ITERATOR_ELEMENT_OWNER_MAP.items():
        if (fn == func_name
                and isinstance(contract, tuple)
                and (top == lib_prefix
                     or top.startswith(lib_prefix + "."))):
            return contract[1]
    return None

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
