## @package pcresolve.flow.proofs.protocols._native_class_protocol
#  Describe native class proof premises.
#
#
#  Versioned source-helper predicates for an independently proved native type input.
#  为独立证明的原生类型输入提供版本化源码辅助谓词。



import ast
import copy

from pcresolve.flow.proofs.callables._function_factory import _canonical
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.namespaces.source._source_bindings import SourceBindingResolver
from pcresolve.flow.proofs.namespaces.source._source_dependencies import register
from pcresolve.flow.proofs.protocols._source_protocols import SourceProtocolResolver
from pcresolve.facts.scope_facts import statement_scope_facts


## Resolve a public helper re-export using bounded source import paths.
## 使用有界源码导入路径解析公开辅助函数的重新导出。
#
#  @param reader Source resolver containing the import snapshot and documents.
#  @param module Module that publicly exposes the helper.
#  @param name Public helper name to resolve.
#  @return Re-export evidence for a unique source binding, or None.
def _public_helper_export(reader, module, name):
    binding_reader = SourceBindingResolver(reader.roots, budget=reader.budget)
    binding = binding_reader.resolve(module, name)
    if (binding is None or binding.get('status') != 'unique_declaration_when_lookup_succeeds'
            or not binding.get('paths') or not binding.get('export_constructions')):
        return None
    target = binding['target']
    wildcard_modules = {item['imported_module'] for path in binding['paths']
                        for item in path.get('imports', ()) if item.get('wildcard')}
    exports = {item.get('module'): set(item.get('values', ()))
               for item in binding['export_constructions']}
    if any(module_name not in exports or name not in exports[module_name]
           for module_name in wildcard_modules):
        return None
    conditions = [condition for path in binding['paths']
                  for condition in path.get('conditions', ())]
    assumptions = set(binding['assumptions'])
    if binding.get('may_be_unbound'):
        if not conditions:
            return None

        # Pair conditional import paths with a narrowly recognized fallback guard.
        # 将条件导入路径与严格识别的回退保护条件配对。
        guards = []
        defaults = []
        for path in binding['source_hashes']:
            document = next((item for item in binding_reader.documents.values()
                             if item.file_path == path), None)
            if document is None or document.tree is None:
                continue
            referenced_conditions = [
                condition for condition in conditions
                if condition.get('branch') == 'else'
                and condition.get('evidence', {}).get('file_path') == path]
            for condition in referenced_conditions:
                line = condition.get('evidence', {}).get('lineno')
                guards.extend((path, node) for node in ast.walk(document.tree)
                    if isinstance(node, ast.If) and node.lineno == line
                    and isinstance(node.test, ast.Name))
            for node in document.tree.body:
                if (isinstance(node, ast.Try) and len(node.body) == 1
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Name)
                        and len(node.handlers) == 1
                        and isinstance(node.handlers[0].type, ast.Name)
                        and node.handlers[0].type.id == 'NameError'
                        and node.handlers[0].name is None and len(node.handlers[0].body) == 1
                        and isinstance(node.handlers[0].body[0], ast.Assign)
                        and len(node.handlers[0].body[0].targets) == 1
                        and isinstance(node.handlers[0].body[0].targets[0], ast.Name)
                        and node.handlers[0].body[0].targets[0].id
                        == node.body[0].value.id
                        and isinstance(node.handlers[0].body[0].value, ast.Constant)
                        and node.handlers[0].body[0].value.value is False
                        and not node.orelse and not node.finalbody):
                    defaults.append((path, node.body[0].value.id, node))
        if len(guards) != 1:
            return None
        guard_path, guard = guards[0]
        guard_name = guard.test.id
        matching_defaults = [node for path, name, node in defaults
                             if path == guard_path and name == guard_name]
        document = next(item for item in binding_reader.documents.values()
                        if item.file_path == guard_path)
        if len(matching_defaults) != 1:
            return None
        default = matching_defaults[0]
        prefix = document.tree.body[:document.tree.body.index(default)] if default in document.tree.body else ()
        if (default not in document.tree.body or guard not in document.tree.body
                or document.tree.body.index(default) + 1 != document.tree.body.index(guard)
                or any(guard_name in statement_scope_facts([statement]).bound
                    for statement in document.tree.body if statement is not default)
                or any('NameError' in statement_scope_facts([statement]).bound for statement in prefix)
                or any(not (isinstance(statement, ast.Import)
                    or isinstance(statement, ast.ImportFrom)
                        and all(alias.name != '*' for alias in statement.names)
                    or isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))
                    for statement in prefix)):
            return None

        # Preserve both sides of the guard as explicit binding evidence.
        # 将保护条件的两个分支都保留为显式绑定证据。
        guard_span = {'file_path': guard_path, 'lineno': guard.test.lineno,
            'col_offset': guard.test.col_offset, 'end_lineno': guard.test.end_lineno,
            'end_col_offset': guard.test.end_col_offset}
        unbound = binding.get('unbound_paths')
        if (not isinstance(unbound, list) or not unbound
                or any(not any(item.get('branch') == 'if' and item.get('evidence') == guard_span
                               for item in path.get('conditions', ())) for path in unbound)
                or any(not any(item.get('branch') == 'else' and item.get('evidence') == guard_span
                               for item in path.get('conditions', ())) for path in binding['paths'])):
            return None
        assumptions.add('no_external_module_global_injection')
    return {'kind': 'source_module_function_reexport', 'status': 'source_bound',
        'basis': 'source_snapshot', 'public_binding': module + '.' + name,
        'target': target['module'] + '.' + target['qualname'],
        'runtime_binding_confirmed': False, 'binding': binding,
        'source_hashes': dict(binding['source_hashes']),
        'assumptions': sorted(assumptions | {'standard_module_attribute_lookup'})}


## Resolve an iterability predicate without asserting the actual argument's kind.
## 解析可迭代性谓词，但不据此断言实际参数的类型。
#
#  @param analyzer Fixed primary snapshot and explicit dependency protocol option.
#  @param caller Exact lexical source definition containing the helper reference.
#  @param expression Actual helper callee expression.
#  @return Canonical name and conditional source protocol, or None.
def iterability_query(analyzer, caller, expression):
    canonical = _canonical(analyzer, caller[0], caller[1], expression)
    if not canonical:
        return None
    key = canonical
    cache = analyzer._native_class_protocol_cache
    if key not in cache:
        # Mark the key before recursive source resolution to prevent re-entry.
        # 在递归解析源码前标记该键，避免重复进入同一查询。
        cache[key] = None
        module, _, name = canonical.rpartition('.')
        # A dependency absent from the primary snapshot has its own source
        # binding and mutation audit below; the primary index cannot establish
        # that helper's freshness by itself.
        if (analyzer._definition_index.find(module, name)
                and not unmodified(analyzer, canonical)):
            return None
        ambient = [(owner, analyzer._source_snapshot.documents[path])
                   for owner, bodies in analyzer.module_bodies.items() for path, _ in bodies]
        reader = SourceProtocolResolver(analyzer.roots, budget=analyzer._analysis_budget,
            analyzer_factory=type(analyzer), ambient_documents=ambient)
        export = None
        if not analyzer._definition_index.find(module, name):
            reader.documents, reader.module_names = {}, {}
            reader.remaining = reader.limits.get('max_nodes', 1000000)
            export = _public_helper_export(reader, module, name)
        target_module, target_name = module, name
        if export is not None:
            target_module, target_name = export['target'].rsplit('.', 1)
        proof = reader.iterability(target_module, target_name)
        if analyzer.support_source_protocols:
            register(analyzer, {path: document.sha256 for path, document in reader.documents.items()
                                if document.sha256})
        if proof is not None and export is not None:
            proof['public_export_binding'] = export
            proof['source_hashes'].update(export['source_hashes'])
            proof['assumptions'] = sorted(set(proof['assumptions'] + export['assumptions']))
        if proof is not None and register(analyzer, proof['source_hashes']):
            cache[key] = proof
    proof = cache[key]
    return (canonical, copy.deepcopy(proof)) if proof is not None else None
