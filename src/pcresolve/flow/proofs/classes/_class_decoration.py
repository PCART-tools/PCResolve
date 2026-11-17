## @package pcresolve.flow.proofs.classes._class_decoration
#  Prove class decorator slot preservation.
#
#
#  Constructor-slot preservation for bounded, identity-returning class decorators.
#  为有界且返回原类的类装饰器证明构造器槽位保持。



import ast
import copy
from dataclasses import asdict

from pcresolve.flow.proofs.protocols.class_attribute_effects import class_attribute_writes, _ClassEffectLimit
from pcresolve.flow.proofs.classes._class_partial import bind_partial
from pcresolve.flow.proofs.classes._class_literal_loops import specialize as literal_class_loops
from pcresolve.flow.proofs.classes._class_deferred import execution_nodes, prepare as deferred_class_functions
from pcresolve.facts.scope_facts import statement_scope_facts


## Build a source span record for one decorator or class write.
## 为一次装饰器或类属性写入构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Summarize a literal source-bound getter/setter alias factory.
## 汇总字面量且由源码绑定的 getter/setter 别名工厂。
#
#  @param analyzer Analyzer providing source identities and builtin bindings.
#  @param target Decorated class and its source identity.
#  @param selected Selected alias-factory definition.
#  @param late_parameter Class parameter bound when the decorator runs.
#  @param factory_binding Evidence for partial/factory argument binding.
#  @param prior_decorations Earlier inner-decorator facts affecting class attributes.
#  @return Alias-decoration fact, or None when the source shape differs.
def _literal_alias_decorator(analyzer, target, selected, late_parameter, factory_binding,
                             prior_decorations):
    ref, cls = target
    owner, function = selected
    if (not isinstance(function, ast.FunctionDef) or function.name not in ('define_aliases', '_define_aliases')
            or late_parameter != 'cls' or not isinstance(factory_binding, dict)):
        return None
    arguments = factory_binding.get('arguments', ())
    if (len(arguments) != 1 or arguments[0].get('parameter') != 'alias_d'
            or arguments[0].get('position') != 0):
        return None
    captured = arguments[0].get('value')
    if not isinstance(captured, dict) or captured.get('kind') != 'dict':
        return None
    mapping = {}
    for pair in captured.get('items', ()):
        if (not isinstance(pair, list) or len(pair) != 2 or type(pair[0]) is not str
                or not isinstance(pair[1], list) or any(type(alias) is not str for alias in pair[1])
                or pair[0] in mapping):
            return None
        mapping[pair[0]] = list(pair[1])
    if not mapping:
        return None
    body = [statement for statement in function.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    if (len(body) not in (4, 8) or not isinstance(body[0], ast.FunctionDef)
            or body[0].name != 'make_alias' or not isinstance(body[1], ast.For)
            or not isinstance(body[-1], ast.Return) or not isinstance(body[-1].value, ast.Name)
            or body[-1].value.id != late_parameter):
        return None
    full_alias_map = len(body) == 8
    if full_alias_map and (not isinstance(body[2], ast.FunctionDef)
            or body[2].name != 'get_aliased_and_aliases'
            or not isinstance(body[3], ast.Assign) or not isinstance(body[4], ast.Assign)
            or not isinstance(body[5], ast.If) or not isinstance(body[6], ast.Assign)):
        return None
    if not full_alias_map and not isinstance(body[2], ast.Assign):
        return None

    alias_factory = body[0]
    factory_args = alias_factory.args.posonlyargs + alias_factory.args.args
    if (len(factory_args) != 1 or alias_factory.args.defaults or alias_factory.args.kwonlyargs
            or alias_factory.args.vararg or alias_factory.args.kwarg or len(alias_factory.body) != 2
            or not isinstance(alias_factory.body[0], ast.FunctionDef)
            or not isinstance(alias_factory.body[1], ast.Return)
            or not isinstance(alias_factory.body[1].value, ast.Name)
            or alias_factory.body[1].value.id != alias_factory.body[0].name):
        return None
    wrapper = alias_factory.body[0]
    wraps_expr = (wrapper.decorator_list[0].func if len(wrapper.decorator_list) == 1
                  and isinstance(wrapper.decorator_list[0], ast.Call) else None)
    imports = analyzer.imports.get(owner.module, {})
    wraps_bound = (isinstance(wraps_expr, ast.Name)
            and imports.get(wraps_expr.id) == 'functools.wraps'
            or isinstance(wraps_expr, ast.Attribute) and wraps_expr.attr == 'wraps'
            and isinstance(wraps_expr.value, ast.Name)
            and imports.get(wraps_expr.value.id) == 'functools'
            and analyzer._stable_import_name(owner.module + '.' + wraps_expr.value.id))
    if not wraps_bound:
        return None
    wraps_call = wrapper.decorator_list[0]
    if (len(wraps_call.args) != 1 or not isinstance(wraps_call.args[0], ast.Call)
            or not isinstance(wraps_call.args[0].func, ast.Name)
            or wraps_call.args[0].func.id != 'getattr'
            or len(wraps_call.args[0].args) != 2
            or not isinstance(wraps_call.args[0].args[0], ast.Name)
            or wraps_call.args[0].args[0].id != late_parameter
            or not isinstance(wraps_call.args[0].args[1], ast.Name)
            or wraps_call.args[0].args[1].id != factory_args[0].arg):
        return None
    method_args = wrapper.args
    if (not method_args.args or method_args.args[0].arg != 'self' or method_args.vararg is None
            or method_args.kwarg is None or len(wrapper.body) != 1
            or not isinstance(wrapper.body[0], ast.Return)
            or not isinstance(wrapper.body[0].value, ast.Call)):
        return None
    delegate = wrapper.body[0].value
    if (not isinstance(delegate.func, ast.Call) or not isinstance(delegate.func.func, ast.Name)
            or delegate.func.func.id != 'getattr' or len(delegate.func.args) != 2
            or not isinstance(delegate.func.args[0], ast.Name)
            or delegate.func.args[0].id != 'self'
            or not isinstance(delegate.func.args[1], ast.Name)
            or delegate.func.args[1].id != factory_args[0].arg
            or len(delegate.args) != 1 or not isinstance(delegate.args[0], ast.Starred)
            or not isinstance(delegate.args[0].value, ast.Name)
            or delegate.args[0].value.id != method_args.vararg.arg
            or len(delegate.keywords) != 1 or delegate.keywords[0].arg is not None
            or not isinstance(delegate.keywords[0].value, ast.Name)
            or delegate.keywords[0].value.id != method_args.kwarg.arg):
        return None

    loop = body[1]
    if (not isinstance(loop.target, ast.Tuple) or len(loop.target.elts) != 2
            or any(not isinstance(item, ast.Name) for item in loop.target.elts)
            or not isinstance(loop.iter, ast.Call) or not isinstance(loop.iter.func, ast.Attribute)
            or loop.iter.func.attr != 'items' or loop.iter.args or loop.iter.keywords
            or not isinstance(loop.iter.func.value, ast.Name)
            or loop.iter.func.value.id != 'alias_d' or len(loop.body) != 3):
        return None
    prop_name, aliases_name = [item.id for item in loop.target.elts]
    exists_init, prefix_loop, missing = loop.body
    if (not isinstance(exists_init, ast.Assign) or len(exists_init.targets) != 1
            or not isinstance(exists_init.targets[0], ast.Name)
            or exists_init.targets[0].id != 'exists'
            or not isinstance(exists_init.value, ast.Constant) or exists_init.value.value is not False
            or not isinstance(prefix_loop, ast.For) or not isinstance(prefix_loop.target, ast.Name)
            or prefix_loop.target.id != 'prefix' or len(prefix_loop.body) != 1
            or not isinstance(prefix_loop.body[0], ast.If)
            or not isinstance(missing, ast.If) or len(missing.body) != 1
            or not isinstance(missing.body[0], ast.Raise)):
        return None
    if ast.unparse(prefix_loop.iter) != "['get_', 'set_']":
        return None
    branch = prefix_loop.body[0]
    if (not isinstance(branch.test, ast.Compare) or len(branch.test.ops) != 1
            or not isinstance(branch.test.ops[0], ast.In)
            or ast.unparse(branch.test.left) != 'prefix + ' + prop_name
            or ast.unparse(branch.test.comparators[0]) != 'vars(cls)'
            or len(branch.body) != 2 or not isinstance(branch.body[0], ast.Assign)
            or not isinstance(branch.body[1], ast.For)
            or not isinstance(branch.body[1].target, ast.Name)
            or branch.body[1].target.id != 'alias'
            or not isinstance(branch.body[1].iter, ast.Name)
            or branch.body[1].iter.id != aliases_name or len(branch.body[1].body) != 4):
        return None
    generated = branch.body[1]
    method_name = generated.body[0].targets[0].id if (
        isinstance(generated.body[0], ast.Assign) and len(generated.body[0].targets) == 1
        and isinstance(generated.body[0].targets[0], ast.Name)) else None
    if (method_name is None or not isinstance(generated.body[0].value, ast.Call)
            or ast.unparse(generated.body[0].value.func) != 'make_alias'
            or ast.unparse(generated.body[0].value.args[0]) != 'prefix + ' + prop_name
            or not isinstance(generated.body[1], ast.Assign)
            or ast.unparse(generated.body[1].targets[0]) != method_name + '.__name__'
            or ast.unparse(generated.body[1].value) != 'prefix + alias'
            or not isinstance(generated.body[2], ast.Assign)
            or ast.unparse(generated.body[2].targets[0]) != method_name + '.__doc__'
            or not (ast.unparse(generated.body[2].value) ==
                    "'Alias for ' + prefix + " + prop_name
                    or ast.unparse(generated.body[2].value) ==
                    "'Alias for `{}`.'.format(prefix + " + prop_name + ')')
            or not isinstance(generated.body[3], ast.Expr)
            or not isinstance(generated.body[3].value, ast.Call)
            or ast.unparse(generated.body[3].value.func) != 'setattr'
            or len(generated.body[3].value.args) != 3
            or ast.unparse(generated.body[3].value.args[0]) != 'cls'
            or ast.unparse(generated.body[3].value.args[1]) != 'prefix + alias'
            or ast.unparse(generated.body[3].value.args[2]) != method_name):
        return None

    if (not isinstance(missing.test, ast.UnaryOp) or not isinstance(missing.test.op, ast.Not)
            or not isinstance(missing.test.operand, ast.Name)
            or missing.test.operand.id != 'exists'):
        return None
    exception = missing.body[0].exc
    if not isinstance(exception, ast.Call) or ast.unparse(exception.func) != 'ValueError':
        return None
    # This template has only the intended class writes: generated alias
    # descriptors and the literal alias map. Any extra call or write makes the
    # source proof inapplicable.
    # 此模板只包含预期的类写入：生成的别名描述符和字面量别名映射；其他调用或写入会使证明不适用。
    if full_alias_map and (ast.unparse(body[2].body[0]) !=
            'return {*d, *(alias for aliases in d.values() for alias in aliases)}'
            or ast.unparse(body[3]) != "preexisting_aliases = getattr(cls, '_alias_map', {})"
            or ast.unparse(body[4]) !=
            'conflicting = get_aliased_and_aliases(preexisting_aliases) & get_aliased_and_aliases(alias_d)'
            or not isinstance(body[5].test, ast.Name) or body[5].test.id != 'conflicting'
            or len(body[5].body) != 1 or not isinstance(body[5].body[0], ast.Raise)
            or ast.unparse(body[5].body[0].exc.func) != 'NotImplementedError'
            or not isinstance(body[6].targets[0], ast.Attribute)
            or not isinstance(body[6].targets[0].value, ast.Name)
            or body[6].targets[0].value.id != late_parameter
            or body[6].targets[0].attr != '_alias_map'
            or ast.unparse(body[6].value) != '{**preexisting_aliases, **alias_d}'):
        return None
    if not full_alias_map and (not body[2].targets
            or not isinstance(body[2].targets[0], ast.Attribute)
            or not isinstance(body[2].targets[0].value, ast.Name)
            or body[2].targets[0].value.id != late_parameter
            or body[2].targets[0].attr != '_alias_map'
            or not isinstance(body[2].value, ast.Name)
            or body[2].value.id != 'alias_d'):
        return None
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    allowed = {'getattr', 'vars', 'setattr', 'ValueError', 'NotImplementedError',
                'make_alias', 'get_aliased_and_aliases', 'partial', 'wraps', 'alias_d.items',
                'getattr(self, name)', 'functools.partial', 'functools.wraps', 'get_aliased_and_aliases(preexisting_aliases)',
                'get_aliased_and_aliases(alias_d)', 'd.values'}
    for call in calls:
        name = ast.unparse(call.func)
        if name not in allowed and name != 'functools.wraps' and not (
                isinstance(call.func, ast.Attribute) and call.func.attr == 'format'
                and isinstance(call.func.value, ast.Constant)
                and type(call.func.value.value) is str):
            return None
    if any(analyzer._builtin_name_status(owner, function, name) != 'confirmed_builtin'
           for name in ('getattr', 'vars', 'setattr', 'ValueError', 'NotImplementedError')):
        return None
    imports = analyzer.imports.get(owner.module, {})
    partial_bound = (factory_binding.get('kind') == 'source_partial_class_decorator'
            and factory_binding.get('status') == 'source_bound'
            and factory_binding.get('function') == asdict(owner))
    wraps_imported = (imports.get('wraps') == 'functools.wraps'
            and analyzer._stable_import_name(owner.module + '.wraps')
            or any(imports.get(name) == 'functools'
                   and analyzer._stable_import_name(owner.module + '.' + name)
                   for name in ('functools',)))
    if not partial_bound or not wraps_imported:
        return None

    for base_ref, base in analyzer._class_mro(ref.module, ref.qualname) or ():
        if '_alias_map' in statement_scope_facts(base.body).bound:
            return None
    if any('_alias_map' in fact.get('attributes', ()) for fact in prior_decorations):
        return None
    generated_members, attributes = [], []
    for prop, aliases in mapping.items():
        if not prop.isidentifier() or any(not alias.isidentifier() for alias in aliases):
            return None
        accessors = []
        for prefix in ('get_', 'set_'):
            name = prefix + prop
            matches = [member for member in cls.body
                       if name in statement_scope_facts([member]).bound]
            if matches:
                if (len(matches) != 1 or not isinstance(matches[0], ast.FunctionDef)
                        or matches[0].name != name or matches[0].decorator_list):
                    return None
                accessors.append(name)
                for alias in aliases:
                    alias_name = prefix + alias
                    generated_members.append({'attribute': alias_name,
                        'kind': 'source_alias_method', 'target_method': name,
                        'wrapper_body': 'forward_same_arguments_to_target_method',
                        'function_metadata': 'functools_wraps_then_alias_name_and_doc',
                        'evidence': _span(ref, matches[0])})
                    if alias_name not in attributes:
                        attributes.append(alias_name)
        if not accessors:
            return None
    attributes.append('_alias_map')
    return {'kind': 'source_class_alias_decoration', 'status': 'source_bound',
        'basis': 'source_snapshot', 'receiver_class': asdict(ref),
        'decorator': asdict(owner), 'parameter': late_parameter,
        'identity_status': 'preserved', 'completion': 'normal_return_only',
        'runtime_identity_confirmed': False,
        'preserved_scope': 'other_class_attributes', 'attributes': attributes,
        'generated_class_members': generated_members,
        'alias_mapping': mapping, 'factory_binding': factory_binding,
        'decorator_evidence': _span(ref, cls.decorator_list[0]),
            'return_evidence': _span(owner, body[-1]),
        'evidence': [_span(owner, function)],
        'source_hashes': {path: analyzer.hashes[path]
                          for path in sorted({ref.file_path, owner.file_path})},
        'assumptions': ['source_snapshot_bindings_hold', 'source_module_fresh_class_prefix',
            'source_literal_alias_map', 'source_direct_accessor_bindings',
            'standard_functools_wraps_protocol', 'standard_builtin_namespace_preserved',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']}


## Prove a source callable decorator that changes only object documentation.
## 证明源码可调用对象装饰器仅修改对象文档。
#
#  @param analyzer Analyzer providing source classes, imports, and builtin facts.
#  @param target Decorated source class and its identity.
#  @param expression Decorator expression selecting the imported callable class.
#  @return Identity-preserving metadata fact, or None when extra effects are possible.
def _source_metadata_instance_decorator(analyzer, target, expression):
    ref, cls = target
    if not isinstance(expression, ast.Attribute) or not isinstance(expression.value, ast.Name):
        return None
    module_alias, attribute = expression.value.id, expression.attr
    imported = analyzer.imports.get(ref.module, {}).get(module_alias)
    if not imported or not analyzer._stable_import_name(ref.module + '.' + module_alias):
        return None
    bindings = analyzer.import_binding_facts.get(imported, [])
    if len(bindings) != 1:
        return None
    statements = bindings[0].get(attribute, [])
    if len(statements) != 1 or not isinstance(statements[0], (ast.Assign, ast.AnnAssign)):
        return None
    assignment = statements[0]
    value = assignment.value
    targets = (assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target])
    names = [item.id for item in targets if isinstance(item, ast.Name)]
    if (attribute not in names or len(names) != len(targets)
            or not isinstance(value, ast.Call) or value.args or value.keywords
            or not isinstance(value.func, ast.Name)):
        return None
    decorator_target = analyzer._definition_index.resolve_name(
        imported, '', value.func.id, analyzer.imports, kind='class')
    if decorator_target is None:
        return None
    decorator_class, decorator_node = decorator_target
    if (decorator_class.module != imported
            or not analyzer._ordinary_construction(decorator_class,
                                                   allow_bounded_decorations=True)):
        return None
    class_ref = decorator_class
    if not isinstance(decorator_node, ast.ClassDef):
        return None
    hierarchy = analyzer._class_mro(class_ref.module, class_ref.qualname)
    if not hierarchy or len(hierarchy) < 2:
        return None
    methods = [item for item in decorator_node.body
        if isinstance(item, ast.FunctionDef) and item.name == '__call__']
    if len(methods) != 1 or methods[0].decorator_list:
        return None
    call = methods[0]
    args = call.args.posonlyargs + call.args.args
    body = [item for item in call.body if not (
        isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
        and isinstance(item.value.value, str))]
    if (len(args) != 2 or len({item.arg for item in args}) != 2
            or call.args.defaults or call.args.kwonlyargs or call.args.vararg or call.args.kwarg
            or len(body) != 3 or not isinstance(body[0], ast.Expr)
            or not isinstance(body[0].value, ast.Call)
            or not isinstance(body[1], ast.If)
            or len(body[1].body) != 1 or not isinstance(body[1].body[0], ast.Expr)
            or body[1].orelse or not isinstance(body[2], ast.Return)
            or not isinstance(body[2].value, ast.Name)):
        return None
    receiver_name, object_name = [item.arg for item in args]

    class_call = body[0].value
    if (not isinstance(class_call.func, ast.Attribute)
            or class_call.func.attr != '__call__'
            or not isinstance(class_call.func.value, ast.Call)
            or not isinstance(class_call.func.value.func, ast.Name)
            or class_call.func.value.func.id != 'super'
            or class_call.func.value.args or class_call.func.value.keywords
            or len(class_call.args) != 1 or class_call.keywords):
        return None

    ## Normalize selected local names before structural AST comparison.
    ## 结构化比较 AST 前统一选定的局部名称。
    #
    #  @param node Expression or statement subtree to copy and normalize.
    #  @param names Mapping from source-local names to canonical names.
    #  @return Deep-copied AST node with matching names renamed.
    def normalized(node, names):
        renamed = copy.deepcopy(node)

        ## Rename Name nodes according to the supplied canonical mapping.
        ## 根据给定的规范名称映射重命名 Name 节点。
        class Rename(ast.NodeTransformer):
            ## Replace one identifier while preserving its AST context.
            ## 替换单个标识符并保留其 AST 上下文。
            #
            #  @param item Name node visited by the transformer.
            #  @return Renamed Name node, or the original node when unmatched.
            def visit_Name(self, item):
                if item.id in names:
                    item.id = names[item.id]
                return item

        return Rename().visit(renamed)

    expected_super_call = ast.parse('super().__call__(obj)', mode='eval').body
    if ast.dump(normalized(class_call, {object_name: 'obj'}), include_attributes=False) != \
            ast.dump(expected_super_call, include_attributes=False):
        return None
    test = normalized(body[1].test, {object_name: 'obj'})
    expected_test = ast.parse(
        'isinstance(obj, type) and obj.__init__ != object.__init__', mode='eval').body
    invoke = normalized(body[1].body[0].value,
                        {receiver_name: 'self', object_name: 'obj'})
    expected_invoke = ast.parse('self(obj.__init__)', mode='eval').body
    returned = body[2].value.id == object_name
    if (ast.dump(test, include_attributes=False)
            != ast.dump(expected_test, include_attributes=False)
            or ast.dump(invoke, include_attributes=False)
            != ast.dump(expected_invoke, include_attributes=False)
            or not returned):
        return None

    base_matches = []
    for base_ref, base_node in hierarchy[1:]:
        members = [item for item in base_node.body
            if '__call__' in statement_scope_facts([item]).bound]
        if members:
            if len(members) != 1 or not isinstance(members[0], ast.FunctionDef):
                return None
            base_matches = [(base_ref, members[0])]
            break
    if len(base_matches) != 1:
        return None
    base_call_ref, base_call = base_matches[0]
    base_args = base_call.args.posonlyargs + base_call.args.args
    base_body = [item for item in base_call.body if not (
        isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
        and isinstance(item.value.value, str))]
    if (len(base_args) != 2 or len({item.arg for item in base_args}) != 2
            or base_call.decorator_list or base_call.args.defaults or base_call.args.kwonlyargs
            or base_call.args.vararg or base_call.args.kwarg or len(base_body) != 2
            or not isinstance(base_body[0], ast.If)
            or len(base_body[0].body) != 1 or not isinstance(base_body[0].body[0], ast.Assign)
            or len(base_body[0].body[0].targets) != 1
            or not isinstance(base_body[1], ast.Return)
            or not isinstance(base_body[1].value, ast.Name)):
        return None
    base_receiver_name, function_name = [item.arg for item in base_args]
    base_names = {base_receiver_name: 'self', function_name: 'func'}
    imports = analyzer.imports.get(base_call_ref.module, {})
    inspect_names = [name for name, target in imports.items() if target == 'inspect']
    if (len(inspect_names) != 1 or not analyzer._stable_import_name(
            base_call_ref.module + '.' + inspect_names[0])):
        return None
    base_names[inspect_names[0]] = 'inspect'
    condition = normalized(base_body[0].test, base_names)
    expected_condition = ast.parse('func.__doc__', mode='eval').body
    assignment = base_body[0].body[0]
    assignment_target = normalized(assignment.targets[0], base_names)
    expected_target = ast.parse('func.__doc__ = None').body[0].targets[0]
    value = assignment.value
    value = normalized(value, base_names)
    if (not isinstance(value, ast.BinOp) or not isinstance(value.right, ast.Attribute)
            or not isinstance(value.right.value, ast.Name)
            or value.right.value.id != 'self'):
        return None
    state_attribute = value.right.attr
    expected_value = ast.parse(
        'inspect.cleandoc(func.__doc__) % self.' + state_attribute, mode='eval').body
    if (ast.dump(condition, include_attributes=False)
            != ast.dump(expected_condition, include_attributes=False)
            or ast.dump(assignment_target, include_attributes=False)
            != ast.dump(expected_target, include_attributes=False)
            or ast.dump(value, include_attributes=False)
            != ast.dump(expected_value, include_attributes=False)
            or base_body[1].value.id != function_name):
        return None
    if (analyzer._resolve_class(class_ref, 'type') is not None
            or analyzer._resolve_class(class_ref, 'object') is not None
            or analyzer._builtin_name_status(class_ref, call, 'isinstance') != 'confirmed_builtin'
            or analyzer._builtin_name_status(class_ref, call, 'type') != 'confirmed_builtin'
            or analyzer._builtin_name_status(class_ref, call, 'object') != 'confirmed_builtin'
            or analyzer._builtin_name_status(class_ref, call, 'super') != 'confirmed_builtin'):
        return None
    return {'kind': 'source_metadata_instance_class_decoration', 'status': 'source_bound',
        'basis': 'source_snapshot', 'receiver_class': asdict(ref),
        'decorator': asdict(class_ref), 'decorator_instance_class': asdict(decorator_class),
        'base_call': asdict(base_call_ref), 'parameter': object_name,
        'identity_status': 'preserved', 'completion': 'normal_return_only',
        'preserved_scope': 'other_class_attributes', 'attributes': [],
        'metadata_attributes': ['__doc__'],
        'runtime_identity_confirmed': False, 'decorator_evidence': _span(ref, expression),
        'instance_binding_evidence': _span(ref, assignment),
        'return_evidence': _span(class_ref, body[2]),
        'evidence': [_span(ref, assignment), _span(class_ref, call),
            _span(base_call_ref, base_call)],
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(
            {ref.file_path, class_ref.file_path, decorator_class.file_path,
             base_ref.file_path, base_call_ref.file_path})},
        'protocol': 'source_metadata_instance_class_decorator',
        'assumptions': ['source_snapshot_bindings_hold', 'source_module_singleton_binding',
            'source_metadata_instance_decorator', 'source_docstring_base_method_binding',
            'builtin_type_class_creation_protocol', 'builtin_type_attribute_writes',
            'standard_builtin_namespace_preserved', 'no_external_frame_introspection',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']}


## Bound class-decoration writes relevant to one ordinary instance lookup.
## 有界地记录与普通实例查找相关的类装饰器写入。
#
#  @param analyzer Fixed source snapshot and bounded decoration machinery.
#  @param hierarchy Exact source MRO, including the class being instantiated.
#  @param protected Attribute names whose binding/layout must survive decoration.
#  @return Ordered decoration records, or None for open or affected bindings.
def member_preservation(analyzer, hierarchy, protected):
    records = []
    for target in hierarchy:
        facts = constructor_decorations(analyzer, target)
        if facts is None or any(set(fact['attributes']) & set(protected) for fact in facts):
            return None
        records.extend(facts)
    return records


## Bound direct class-decorator writes without proving decoration completion.
## 有界地记录类装饰器的直接写入，但不证明装饰已完成。
#
#  @param analyzer Snapshot lookup machinery and query-local effect budget.
#  @param target Exact source class definition and identity.
#  @return Ordered source effect records, or None outside the bounded grammar.
def constructor_decorations(analyzer, target):
    ref, cls = target
    if not cls.decorator_list:
        return []
    if ref in analyzer._class_decoration_cache:
        return copy.deepcopy(analyzer._class_decoration_cache[ref])
    analyzer._class_decoration_cache[ref] = None
    if len(cls.decorator_list) > 8:
        return None
    records = []
    # Each decorator receives the same class only after the inner decorator's
    # proven identity return. Source writes are a union, never a restored slot.
    # 每层装饰器仅在内层已证明返回原类后才接收同一个类对象；源码写入按并集累计，不假定槽位恢复。
    for expression in reversed(cls.decorator_list):
        probe = copy.copy(cls)
        probe.decorator_list = [expression]
        selected = analyzer._decorator_definition((ref, probe))
        factory_binding, string_literals, late_parameter = None, {}, None
        if selected is None:
            metadata_fact = _source_metadata_instance_decorator(analyzer, target, expression)
            if metadata_fact is not None:
                records.append(metadata_fact)
                continue
        if selected is None:
            partial = bind_partial(analyzer, target, expression)
            if partial is not None:
                selected, late_parameter, string_literals, factory_binding = partial
        if selected is None or not isinstance(selected[1], ast.FunctionDef):
            return None
        owner, function = selected
        alias_fact = (_literal_alias_decorator(analyzer, target, selected,
            late_parameter, factory_binding, records) if late_parameter is not None else None)
        if alias_fact is not None:
            records.append(alias_fact)
            continue
        loop_expansion = None
        if factory_binding is not None:
            specialized = literal_class_loops(analyzer, selected, factory_binding)
            if specialized is not None:
                function, loop_expansion = specialized
        args = function.args
        parameters = args.posonlyargs + args.args
        if ('.' in owner.qualname or factory_binding is None and (len(parameters) != 1 or args.defaults)
                or args.kwonlyargs or args.vararg or args.kwarg
                or parameters[0].annotation is not None or function.returns is not None):
            return None
        nodes = []
        for item in ast.walk(function):
            analyzer._class_effect_fact_steps -= 1
            if len(nodes) >= 2000 or analyzer._class_effect_fact_steps < 0:
                return None
            nodes.append(item)
        parameter = late_parameter or parameters[0].arg
        immediate = list(execution_nodes(function))
        if (not function.body or not isinstance(function.body[-1], ast.Return)
                or not isinstance(function.body[-1].value, ast.Name)
                or function.body[-1].value.id != parameter
                or any(isinstance(item, ast.Return) and item is not function.body[-1]
                       for item in immediate)
                or parameter in statement_scope_facts(function.body).bound):
            return None
        prepared = deferred_class_functions(analyzer, (owner, function), parameter, target, records)
        if prepared is None:
            return None
        function, deferred = prepared
        body = copy.copy(function)
        body.body = function.body[:-1]

        ## Charge class-attribute traversal to the shared effect budget.
        ## 将类属性遍历工作量计入共享效果预算。
        #
        #  @param count Number of visited syntax nodes.
        #  @return None; the shared remaining budget is reduced in place.
        def charge(count):
            analyzer._class_effect_fact_steps -= count

        # The returned class is the only admitted escape. The remaining body
        # uses the same alias/reflective-write rules as ordinary class effects.
        # 仅允许返回的类对象发生逃逸；其余函数体使用与普通类效果相同的别名和反射写入规则。
        try:
            proof = class_attribute_writes(body, parameter,
                lambda name: analyzer._builtin_name_status(owner, function, name)
                    == 'confirmed_builtin', lambda value: False,
                max_nodes=min(2000, max(0, analyzer._class_effect_fact_steps)), charge=charge,
                string_literals=string_literals)
        except _ClassEffectLimit:
            return None
        if proof is None:
            return None
        records.append({'kind': 'source_class_decoration', 'status': 'source_bound',
            'basis': 'source_snapshot', 'receiver_class': asdict(ref),
            'decorator': asdict(owner), 'parameter': parameter,
            'identity_status': 'preserved', 'completion': 'normal_return_only',
            'preserved_scope': 'other_class_attributes',
            'attributes': list(proof.attributes), 'runtime_identity_confirmed': False,
            'decorator_evidence': _span(ref, expression),
            'return_evidence': _span(owner, function.body[-1]),
            'evidence': [_span(owner, item) for item in proof.evidence],
            'source_hashes': {path: analyzer.hashes[path]
                              for path in sorted({ref.file_path, owner.file_path})},
            'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_attribute_writes',
                            'no_external_monkeypatch_or_import_hook',
                            'no_unmodeled_indirect_class_mutation',
                            'no_external_frame_introspection']})
        if factory_binding is not None:
            records[-1]['factory_binding'] = factory_binding
            records[-1]['source_hashes'].update(factory_binding['source_hashes'])
            records[-1]['assumptions'].extend(factory_binding['assumptions'])
        if loop_expansion is not None:
            records[-1]['literal_loop_expansion'] = loop_expansion
            records[-1]['assumptions'].extend(loop_expansion['assumptions'])
        if deferred['declarations']:
            records[-1]['deferred_functions'] = deferred
            records[-1]['source_hashes'].update(deferred['source_hashes'])
            records[-1]['assumptions'].extend(deferred['assumptions'])
    analyzer._class_decoration_cache[ref] = records
    return copy.deepcopy(records)
