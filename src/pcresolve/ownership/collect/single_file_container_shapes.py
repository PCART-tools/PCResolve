## @package pcresolve.ownership.collect.single_file_container_shapes
#  Collect single-file value shapes.
#
#
#  Container, item, field, and Python value-shape facts for one source file.
#  收集单个源码文件中的容器、元素、字段和 Python 值形状事实。



import ast
from pcresolve.ownership.collect.single_file_query import memoized_expression_query

from pcresolve.ownership.builtin_ownership import _builtin_method_return_shape
from pcresolve.ownership.ownership_contracts import (
    _BUILTIN_METHOD_RESULT_ITEM_KINDS, _match_attribute_python_shape,
    _match_result_python_shape,
)
from pcresolve.ownership.scope import SCOPE_MODULE
from pcresolve.ownership.collect.single_file_source_resolution import _uniform_python_shape
from pcresolve.ownership.sources import (
    CallResult, ContainerItem, ContainerIter, InstanceMethod, PythonShape,
    SourceSet, TupleSource, UnknownSource, normalize_source, source_display,
)

## Check whether a call uses defaultdict with a supported builtin factory.
## 检查调用是否使用 defaultdict 和受支持的内建工厂。
#
#  @param node Candidate call expression.
#  @return True for a statically recognized list/dict/set/tuple/str factory.
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
## 返回表达式产生的具体 Python 容器类型。
#
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
## 返回对容器表达式执行下标访问后得到的具体类型。
#  Dict literals qualify only when every value has the same known kind.
#
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
## Container-shape collection mixed into SingleFileAnalyzer.
## 混入 SingleFileAnalyzer 的容器形状收集逻辑。
class SingleFileContainerShapeMixin:
    ## Return assignment metadata for a name in the active lexical scope.
    ## 返回当前词法作用域中名称对应的赋值元数据。
    #  A found binding with no metadata is authoritative and prevents a
    #  same-name binding from another scope leaking through legacy maps.
    #  找到但不含元数据的词法绑定仍具有权威性，可防止其他作用域的同名旧映射泄漏进来。
    #
    #  @param name Receiver variable name.
    #  @param item Whether to request the subscript item kind.
    #  @return Container kind string or None.
    def _lookup_container_kind(self, name, item=False):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            attr = "container_item_kind" if item else "container_kind"
            return getattr(binding, attr, "") or None

        # Compatibility maps are file-wide and can contain a same-name local
        # from a previously visited function. Only module code may use their
        # fallback; nested scopes require a lexical Binding as evidence.
        # 兼容映射是文件级的，可能包含此前访问函数中的同名局部变量；仅模块代码可回退使用，
        # 嵌套作用域必须提供词法 Binding 作为证据。
        if self.current_scope().kind != SCOPE_MODULE:
            return None
        if item:
            return self.container_item_kinds.get(name)
        return self.container_kinds.get(name)

    ## Return field shapes for elements of a statically known container.
    ## 返回静态已知容器元素的字段形状。
    #
    #  @param node Container expression or bound name.
    #  @return Mapping of literal field names to shape tuples.
    def _expression_container_item_fields(self, node):
        if isinstance(node, (ast.List, ast.Tuple)):
            field_sets = []
            for element in node.elts:
                fields = self._literal_dict_field_shapes(element)
                if not fields:
                    return {}
                field_sets.append(fields)
            if field_sets and all(fields == field_sets[0]
                                  for fields in field_sets):
                return dict(field_sets[0])
            return {}
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            return dict(getattr(binding, "container_item_fields", {}) or {})
        if isinstance(node, ast.Attribute):
            name = self._attribute_name(node)
            if name and name.startswith("self.") and self._class_stack:
                return dict(self.instance_attr_item_fields.get(
                    (self._class_stack[-1], name), {}) or {})
        return {}

    ## Return positional sources for a homogeneous tuple/list comprehension.
    ## 返回同质元组/列表推导式的各位置来源。
    #
    #  The fact is intentionally limited to a comprehension whose element is
    #  a tuple or list and whose every field has an explicit source. It lets
    #  ``for value, label in pairs`` preserve the source of ``value`` without
    #  inferring ownership from the loop variable or method name.
    #
    #  @param node Candidate list comprehension.
    #  @return Tuple of field sources, or None when incomplete.
    def _expression_tuple_item_sources(self, node):
        if not isinstance(node, ast.ListComp):
            return None
        element = node.elt
        if not isinstance(element, (ast.Tuple, ast.List)):
            return None
        sources = []
        for field in element.elts:
            source = self.trace_source(field)
            if source is None:
                source = self.get_base(field)
            if source is None:
                return None
            sources.append(normalize_source(source))
        return tuple(sources)

    ## Return module-level tuple-field facts for an active container binding.
    ## 返回当前容器绑定的模块级元组字段事实。
    #
    #  @param name Container name.
    #  @return Tuple of sources, or None when unavailable or shadowed.
    def _lookup_tuple_item_sources(self, name):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None and binding.scope_kind != SCOPE_MODULE:
            return None
        return self.homogeneous_container_tuple_items.get(name)

    ## Return the lexical identity of an attribute-backed container.
    #
    #  The root binding's monotonic assignment index keeps same-spelled local
    #  objects in separate functions isolated without relying on reusable
    #  Python object ids. Attribute facts are shared across functions only
    #  when their root resolves to the same enclosing binding.
    ## 返回属性容器的词法身份键。
    #  根绑定的单调赋值索引可区分不同函数中同名的局部对象。
    #  仅当属性根解析到同一个外围绑定时，才跨函数共享事实。
    #
    #
    #  @param node Attribute expression naming the container.
    #  @return Tuple of root binding identity and attribute path, or None.
    def _attribute_container_key(self, node):
        chain = self._attribute_chain_list(node)
        if not chain or len(chain) < 2:
            return None
        binding = self.current_scope().lookup(
            chain[0], skip_parent_classes=True)
        if binding is None:
            return None
        return (binding.assignment_index, tuple(chain[1:]))

    ## Return tuple-field facts recorded for an attribute-backed list.
    ## 返回属性列表记录的元组字段事实。
    #
    #  @param node Attribute expression naming the list.
    #  @return TupleSource fields, or None when unresolved or conflicting.
    def _lookup_attribute_tuple_item_sources(self, node):
        key = self._attribute_container_key(node)
        if key is None or key in self._attribute_append_tuple_conflicts:
            return None
        source = self._attribute_append_tuple_sources.get(key)
        return source.items if isinstance(source, TupleSource) else None

    ## Invalidate tuple-field facts when an attribute container is rebound.
    ## 属性容器重绑定时，使其元组字段事实失效。
    #
    #  @param node Attribute assignment target naming the container.
    #  @return None; prior tuple facts are removed and conflict state is cleared.
    def _invalidate_attribute_tuple_item_sources(self, node):
        key = self._attribute_container_key(node)
        if key is None:
            return
        self._attribute_append_tuple_sources.pop(key, None)
        self._attribute_append_tuple_conflicts.discard(key)

    ## Check whether two tuple item facts have the same positional owners.
    ## 检查两个元组元素事实是否具有相同的位置所有者。
    #  Call locations and expression spellings are not ownership differences.
    #  Unresolved positions never converge.
    #
    #  @param left Existing TupleSource fact.
    #  @param right Newly observed TupleSource fact.
    #  @return True when every field has one matching resolved owner.
    def _tuple_item_owners_match(self, left, right):
        if (not isinstance(left, TupleSource)
                or not isinstance(right, TupleSource)
                or len(left.items) != len(right.items)):
            return False
        for left_item, right_item in zip(left.items, right.items):
            left_owner = self._structured_source_owner_top(left_item)
            right_owner = self._structured_source_owner_top(right_item)
            if (left_owner in (None, "unknown", "")
                    or left_owner != right_owner):
                return False
        return True

    ## Infer field shapes from a literal dictionary element.
    ## 从字面量字典元素推导字段形状。
    #
    #  @param node Candidate dictionary AST node.
    #  @return Mapping of literal string keys to shape tuples.
    def _literal_dict_field_shapes(self, node):
        if not isinstance(node, ast.Dict):
            return {}
        fields = {}
        for key_node, value_node in zip(node.keys, node.values):
            if (not isinstance(key_node, ast.Constant)
                    or not isinstance(key_node.value, str)):
                continue
            kind, item_kind = self._expression_container_shape(value_node)
            if not kind:
                continue
            fields[key_node.value] = (kind, item_kind)
        return fields

    ## Return the shape of a literal-key field on a known element.
    ## 返回已知元素中字面量键字段的形状。
    #
    #  @param node Subscript AST node.
    #  @return (container kind, item kind), or empty strings.
    def _expression_subscript_field_shape(self, node):
        if not isinstance(node, ast.Subscript):
            return ("", "")
        key = self._get_slice(node.slice)
        if not isinstance(key, str):
            return ("", "")
        fields = self._expression_container_item_fields(node.value)
        shape = fields.get(key)
        if shape is None:
            return ("", "")
        return shape

    ## Resolve a structured source to one uniform owner within the file.
    ## 在当前文件内将结构化来源解析为单一统一所有者。
    #
    #  This follows existing provenance only. It does not infer ownership from
    #  an attribute or method name, and mixed SourceSet owners stay unresolved.
    #
    #  @param source Source value to inspect.
    #  @param seen Recursion guard for cyclic structured sources.
    #  @return Uniform owner string or None.
    def _structured_source_owner_top(self, source, seen=None):
        source = normalize_source(source)
        visited = set(seen or set())
        key = (type(source).__name__, source_display(source))
        if key in visited:
            return None
        visited.add(key)

        if isinstance(source, str):
            if source in ("local", "python", "unknown", ""):
                return source or None
            return self.symbols.get_top(source) or source
        if isinstance(source, PythonShape):
            return "python"
        if isinstance(source, UnknownSource):
            return "unknown"
        if isinstance(source, CallResult):
            if source.result_source is not None:
                return self._structured_source_owner_top(
                    source.result_source, visited)
            return self._structured_source_owner_top(
                source.callee, visited)
        if isinstance(source, InstanceMethod):
            return self._structured_source_owner_top(
                source.receiver, visited)
        if isinstance(source, ContainerIter):
            return self._structured_source_owner_top(
                source.container, visited)
        if isinstance(source, ContainerItem):
            return self._structured_source_owner_top(
                source.container, visited)
        if isinstance(source, SourceSet):
            owners = {
                self._structured_source_owner_top(item, set(visited))
                for item in source.sources
            }
            owners.discard(None)
            if len(owners) == 1:
                return next(iter(owners))

        # Mixed or partially unresolved alternatives cannot establish one owner.
        # 候选来源混杂或部分未解析时，无法确定单一所有者。
        return None

    ## Infer a Python-provided container shape from local expression evidence.
    ## 根据局部表达式证据推导 Python 内建容器形状。
    #
    #  @param node Value expression.
    #  @return Pair of container kind and item kind, or empty strings.
    @memoized_expression_query(lambda: ('', ''))
    def _expression_container_shape(self, node):
        direct_kind = _container_kind(node)
        if direct_kind is not None:
            return (direct_kind, _container_item_kind(node) or "")

        # Prefer literal syntax, then lexical facts, then supported producer protocols.
        # 依次优先使用字面量语法、词法事实和受支持的生产者协议。
        if (isinstance(node, ast.Constant)
                and type(node.value) in (bool, int, float, complex, bytes)):
            return (type(node.value).__name__, "")
        if isinstance(node, ast.JoinedStr):
            return ("str", "")
        if isinstance(node, ast.Name):
            return (
                self._lookup_container_kind(node.id) or "",
                self._lookup_container_kind(node.id, item=True) or "")
        if isinstance(node, ast.Attribute):
            return self._attribute_container_shape(node)
        if isinstance(node, ast.Subscript):
            return self._subscript_container_shape(node)
        if isinstance(node, ast.BinOp):
            return self._binary_container_shape(node)
        if isinstance(node, ast.IfExp):
            body = self._expression_container_shape(node.body)
            orelse = self._expression_container_shape(node.orelse)

            # Conditional branches contribute a shape only when both agree exactly.
            # 条件分支只有在形状完全一致时才提供共同形状。
            return body if body[0] and body == orelse else ("", "")
        if isinstance(node, ast.Call):
            return self._call_container_shape(node)
        return ("", "")

    ## Resolve the shape of an attribute expression from lexical evidence.
    ## 根据词法证据解析属性表达式的形状。
    #
    #  @param node Attribute AST node.
    #  @return Pair of container kind and item kind.
    def _attribute_container_shape(self, node):
        name = self._attribute_name(node)
        if name and name.startswith("self.") and self._class_stack:
            key = (self._class_stack[-1], name)
            return (
                self.instance_attr_kinds.get(key, ""),
                self.instance_attr_item_kinds.get(key, ""))
        if name:
            binding = self.current_scope().lookup(
                name, skip_parent_classes=True)
            if binding is not None:
                return (
                    getattr(binding, "container_kind", "") or "",
                    getattr(binding, "container_item_kind", "") or "")
            parts = name.split(".", 1)
            if len(parts) == 2:
                for scope_key in self._local_instance_field_scope_keys(parts[0]):
                    shape = self._local_instance_field_shapes.get(
                        (scope_key, parts[0], parts[1]))
                    if shape is not None:
                        return shape
        receiver_top = self._expr_receiver_top(node.value)
        if receiver_top is None:
            receiver_top = self._structured_source_owner_top(
                self.trace_source(node.value))
        shape = _match_attribute_python_shape(receiver_top, node.attr)
        return ((shape.kind, shape.item_kind)
                if shape is not None else ("", ""))

    ## Resolve the shape of a subscript expression.
    ## 解析下标表达式的形状。
    #
    #  @param node Subscript AST node.
    #  @return Pair of container kind and item kind.
    def _subscript_container_shape(self, node):
        field_kind = self._expression_subscript_field_shape(node)
        if field_kind[0]:
            return field_kind
        value_kind, item_kind = self._expression_container_shape(node.value)
        if isinstance(node.slice, ast.Slice):
            if value_kind in ("list", "tuple", "str"):
                return (value_kind, item_kind)
            return ("", "")
        if item_kind:
            return (item_kind, "")
        if value_kind == "str":
            return ("str", "")
        return ("", "")

    ## Resolve shape-preserving binary operators.
    ## 解析保持容器形状的二元运算符。
    #
    #  @param node Binary-operation AST node.
    #  @return Pair of container kind and item kind.
    def _binary_container_shape(self, node):
        left = self._expression_container_shape(node.left)
        if isinstance(node.op, ast.Mod):
            return ("str", "") if left[0] == "str" else ("", "")
        if isinstance(node.op, ast.Add):
            right = self._expression_container_shape(node.right)
            if left[0] in ("list", "tuple", "str") and left == right:
                return left
        return ("", "")

    ## Resolve call-result and receiver-method container shapes.
    ## 解析调用结果和接收者方法产生的容器形状。
    #
    #  @param node Call AST node.
    #  @return Pair of container kind and item kind.
    def _call_container_shape(self, node):
        call_key = self.get_base(node, call_lookup=True)
        if isinstance(call_key, str):
            local_shape = _uniform_python_shape(
                self.return_sources.get(call_key))
            if local_shape is not None:
                return (local_shape.kind, local_shape.item_kind)
        func_top, func_name = self._resolve_func_top(node.func)
        if func_top is None and isinstance(node.func, ast.Attribute):
            func_top = self._expr_receiver_top(node.func.value)
            func_name = node.func.attr
        if func_top is None and isinstance(node.func, ast.Attribute):
            method_source = normalize_source(self._resolve_methods(node))
            if isinstance(method_source, InstanceMethod):
                receiver = normalize_source(method_source.receiver)
                if isinstance(receiver, str):
                    func_top = self.symbols.get_top(receiver) or receiver
                elif isinstance(receiver, CallResult):
                    result_source = normalize_source(receiver.result_source)
                    if isinstance(result_source, str):
                        func_top = result_source
                    elif isinstance(receiver.callee, str):
                        func_top = (
                            self.symbols.get_top(receiver.callee)
                            or receiver.callee)
                func_name = method_source.method
        shape = _match_result_python_shape(func_top, func_name)
        if shape is not None:
            return (shape.kind, shape.item_kind)
        if isinstance(node.func, ast.Attribute):
            receiver_kind, receiver_item_kind = (
                self._expression_container_shape(node.func.value))
            method = node.func.attr
            if (receiver_kind == "dict" and method == "get"
                    and receiver_item_kind):
                return (receiver_item_kind, "")
            shape = _builtin_method_return_shape(
                PythonShape(receiver_kind, receiver_item_kind), method)
            if shape is not None:
                return (shape.kind, shape.item_kind)
        return ("", "")
    ## Preserve a concrete Python value shape for local call arguments.
    ## 为本地调用实参保留具体的 Python 值形状。
    #
    #  Container shapes reuse lexical flow facts. Scalar literals are carried
    #  by their builtin type so downstream method resolution can validate the
    #  protocol instead of treating every Python value as interchangeable.
    #
    #  @param node Value expression.
    #  @return PythonShape or None.
    def _expression_python_shape(self, node):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and node.elts:
            item_shapes = [
                self._expression_python_shape(item) for item in node.elts
            ]
            if (any(item is None for item in item_shapes)
                    or any(item.kind != item_shapes[0].kind
                           for item in item_shapes[1:])):
                return None
            return PythonShape(
                _container_kind(node) or "", item_shapes[0].kind)
        kind, item_kind = self._expression_container_shape(node)
        if kind:
            return PythonShape(kind, item_kind)
        if isinstance(node, ast.Constant):
            value = node.value
            if value is None:
                return PythonShape("NoneType")
            value_type = type(value)
            if value_type in (bytes, bool, int, float, complex):
                return PythonShape(value_type.__name__)
        return None

    ## Return the container kind relevant to a method call receiver.
    ## 返回与方法调用接收者相关的容器类型。
    #
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
            if isinstance(receiver.value, ast.Name):
                root = receiver.value.id
                class_name = self._class_stack[-1]
                active_receiver = (
                    self._class_receiver_stack[-1]
                    if self._class_receiver_stack else "")
                if root == class_name or (
                        active_receiver and root == active_receiver):
                    return self.class_attr_kinds.get(
                        (class_name, receiver.attr))
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
        receiver_kind, _ = self._expression_container_shape(receiver)
        if receiver_kind:
            return receiver_kind
        return None

    ## Record the concrete kind assigned through a dictionary subscript.
    ## 记录通过字典下标赋值的具体元素类型。
    #
    #  The evidence is accepted only for a receiver already known to be a
    #  Python dict. All writes must converge to one concrete item kind.
    #  Conflicting or unresolved writes invalidate the fact for that binding.
    #
    #  @param target Assignment target AST node.
    #  @param value_kind Concrete kind of the assigned value, or None.
    #  @return None; conflicting or unknown writes invalidate the binding fact.
    def _record_subscript_item_kind(self, target, value_kind):
        if (not isinstance(target, ast.Subscript)
                or not isinstance(target.value, ast.Name)):
            return
        container_name = target.value.id
        binding = self.current_scope().lookup(
            container_name, skip_parent_classes=True)
        if binding is None or binding.container_kind != "dict":
            return

        conflict_key = self._binding_key(binding)
        if conflict_key in self._container_item_kind_conflicts:
            return
        current = binding.container_item_kind or ""
        if not value_kind or (current and current != value_kind):

            # Conflicting writes invalidate the binding instead of widening its item type.
            # 写入冲突时使该绑定失效，不将元素类型扩大成多个候选。
            binding.container_item_kind = ""
            self.container_item_kinds.pop(container_name, None)
            self._container_item_kind_conflicts.add(conflict_key)
            return
        binding.container_item_kind = value_kind
        self.container_item_kinds[container_name] = value_kind

    ## Record owner, tuple, kind, and field facts for one list append.
    ## 记录一次列表 append 的所有者、元组、类型和字段事实。
    #
    #  @param node Append call AST node.
    #  @return None; compatible append facts are merged into the active binding.
    def _record_container_append_shape(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr != "append"
                or len(node.args) != 1):
            return
        receiver = node.func.value
        receiver_kind, _ = self._expression_container_shape(receiver)
        if receiver_kind != "list":
            return

        value = node.args[0]

        # Collect ownership, tuple layout, Python kind, and literal fields independently.
        # 分别收集所有者、元组布局、Python 类型和字面量字段事实。
        item_source = normalize_source(self.trace_source(value))
        tuple_source = self._appended_tuple_source(value)
        if isinstance(receiver, ast.Name):
            binding = self.current_scope().lookup(
                receiver.id, skip_parent_classes=True)
            self._record_appended_item_source(binding, item_source)
            self._record_named_append_tuple(binding, tuple_source)
        elif isinstance(receiver, ast.Attribute):
            self._record_attribute_append_tuple(receiver, tuple_source)

        item_shape = self._expression_python_shape(value)
        item_kind = (
            item_shape.kind
            if isinstance(item_shape, PythonShape) and item_shape.kind
            else "")
        if isinstance(receiver, ast.Name):
            binding = self.current_scope().lookup(
                receiver.id, skip_parent_classes=True)
            self._record_appended_item_kind(
                binding, receiver.id, item_kind)
        fields = self._literal_dict_field_shapes(value)
        self._record_appended_fields(receiver, fields, item_kind)

    ## Merge one appended item's owner into a list binding.
    ## 将单个追加元素的所有者合并到列表绑定中。
    #
    #  @param binding Active receiver binding.
    #  @param item_source Traced appended-value source.
    #  @return None; conflicting or unresolved item owners remain unknown.
    def _record_appended_item_source(self, binding, item_source):
        if binding is None or binding.container_kind != "list":
            return
        key = self._binding_key(binding)
        current = normalize_source(self._iterated_append_sources.get(key))
        current_owner = (
            self._structured_source_owner_top(current)
            if current is not None else None)
        item_owner = self._structured_source_owner_top(item_source)
        if (isinstance(current, UnknownSource)
                and current.display == "empty iterable"):
            current_owner = None
        if item_owner is None:
            self._iterated_append_sources[key] = UnknownSource(
                "unresolved appended item")
        elif current_owner is None or current_owner == item_owner:
            self._iterated_append_sources[key] = item_owner
        else:
            self._iterated_append_sources[key] = UnknownSource(
                "conflicting iterable items")

    ## Return exact positional evidence for an appended tuple or list.
    ## 返回追加的元组或列表的精确位置证据。
    #
    #  @param value Appended value AST node.
    #  @return TupleSource or None.
    def _appended_tuple_source(self, value):
        if not isinstance(value, (ast.Tuple, ast.List)):
            return None
        items = []
        for field in value.elts:
            shape = self._expression_python_shape(field)
            if shape is not None:
                items.append(shape)
                continue
            source = normalize_source(self._call_edge_argument_source(field))
            if source is None or isinstance(source, UnknownSource):
                return None
            items.append(source)
        return TupleSource(tuple(items))

    ## Merge tuple evidence for a named list binding.
    ## 合并具名列表绑定的元组证据。
    #
    #  @param binding Active receiver binding.
    #  @param tuple_source New positional evidence or None.
    #  @return None; conflicting tuple layouts invalidate the binding fact.
    def _record_named_append_tuple(self, binding, tuple_source):
        if binding is None:
            return
        key = self._binding_key(binding)
        if key in self._iterated_append_tuple_conflicts:
            return
        if tuple_source is None:
            self._iterated_append_tuple_sources.pop(key, None)
            self._iterated_append_tuple_conflicts.add(key)
            return
        previous = self._iterated_append_tuple_sources.get(key)
        if previous is None or previous == tuple_source:
            self._iterated_append_tuple_sources[key] = tuple_source
        else:
            self._iterated_append_tuple_sources.pop(key, None)
            self._iterated_append_tuple_conflicts.add(key)

    ## Merge tuple evidence for an attribute-backed list.
    ## 合并属性列表的元组证据。
    #
    #  @param receiver Attribute receiver AST node.
    #  @param tuple_source New positional evidence or None.
    #  @return None; conflicting tuple layouts invalidate the attribute fact.
    def _record_attribute_append_tuple(self, receiver, tuple_source):
        key = self._attribute_container_key(receiver)
        if key is None or key in self._attribute_append_tuple_conflicts:
            return
        if tuple_source is None:
            self._attribute_append_tuple_sources.pop(key, None)
            self._attribute_append_tuple_conflicts.add(key)
            return
        previous = self._attribute_append_tuple_sources.get(key)
        if (previous is None or previous == tuple_source
                or self._tuple_item_owners_match(previous, tuple_source)):
            self._attribute_append_tuple_sources[key] = tuple_source
        else:
            self._attribute_append_tuple_sources.pop(key, None)
            self._attribute_append_tuple_conflicts.add(key)

    ## Merge one appended item's Python kind into a list binding.
    ## 将单个追加元素的 Python 类型合并到列表绑定中。
    #
    #  @param binding Active receiver binding.
    #  @param container_name Receiver name.
    #  @param item_kind Concrete appended item kind or empty.
    #  @return None; conflicting or unknown item kinds invalidate the fact.
    def _record_appended_item_kind(self, binding, container_name, item_kind):
        if binding is None or binding.container_kind != "list":
            return
        key = self._binding_key(binding)
        if key in self._container_item_kind_conflicts:
            return
        current = binding.container_item_kind or ""
        if not item_kind or (current and current != item_kind):
            binding.container_item_kind = ""
            self.container_item_kinds.pop(container_name, None)
            self._container_item_kind_conflicts.add(key)
            return
        binding.container_item_kind = item_kind
        self.container_item_kinds[container_name] = item_kind

    ## Record literal dictionary fields or attribute item-kind fallback.
    ## 记录字面量字典字段，或更新属性元素类型的回退事实。
    #
    #  @param receiver List receiver AST node.
    #  @param fields Literal field-shape mapping.
    #  @param item_kind Concrete item kind or empty.
    #  @return None; field and item-kind facts are updated or cleared.
    def _record_appended_fields(self, receiver, fields, item_kind):
        if not fields:
            if isinstance(receiver, ast.Attribute):
                name = self._attribute_name(receiver)
                if name and name.startswith("self.") and self._class_stack:
                    key = (self._class_stack[-1], name)
                    if item_kind:
                        self.instance_attr_item_kinds[key] = item_kind
                    else:
                        self.instance_attr_item_kinds.pop(key, None)
            return
        if isinstance(receiver, ast.Name):
            binding = self.current_scope().lookup(
                receiver.id, skip_parent_classes=True)
            if binding is not None and binding.container_kind == "list":
                binding.container_item_fields = dict(fields)
            return
        if isinstance(receiver, ast.Attribute):
            name = self._attribute_name(receiver)
            if name and name.startswith("self.") and self._class_stack:
                self.instance_attr_item_fields[
                    (self._class_stack[-1], name)] = dict(fields)
