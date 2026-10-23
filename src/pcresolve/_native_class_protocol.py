## @package pcresolve._native_class_protocol
#  Versioned source-helper predicates for an independently proved native type input.

import ast
import copy

from ._function_factory import _canonical
from ._runtime_namespace import unmodified
from ._source_bindings import SourceBindingResolver
from ._source_dependencies import register
from ._source_protocols import SourceProtocolResolver


def _public_helper_export(reader, module, name):
    """Resolve a re-export only when its source import paths are bounded."""
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
        # NumPy's ordinary import branch is selected by a fresh module global
        # initialized to False when it is absent. Other conditional exports
        # remain open until their guards have an independent value proof.
        if module != 'numpy' or name != 'iterable' or not conditions:
            return None
        module_path = next((path for path in binding['source_hashes']
                            if path.endswith('numpy/__init__.py') or path.endswith('numpy\\__init__.py')),
                           None)
        document = next((item for item in binding_reader.documents.values()
                         if item.file_path == module_path), None)
        if document is None:
            return None
        guards = [node for node in ast.walk(document.tree) if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Name) and node.test.id == '__NUMPY_SETUP__'
                  and any(condition.get('branch') == 'else'
                          and condition.get('evidence', {}).get('lineno') == node.test.lineno
                          for condition in conditions)]
        setup_defaults = [node for node in document.tree.body if isinstance(node, ast.Try)
            and len(node.body) == 1 and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Name)
            and node.body[0].value.id == '__NUMPY_SETUP__' and len(node.handlers) == 1
            and isinstance(node.handlers[0].type, ast.Name)
            and node.handlers[0].type.id == 'NameError' and node.handlers[0].name is None
            and len(node.handlers[0].body) == 1
            and isinstance(node.handlers[0].body[0], ast.Assign)
            and len(node.handlers[0].body[0].targets) == 1
            and isinstance(node.handlers[0].body[0].targets[0], ast.Name)
            and node.handlers[0].body[0].targets[0].id == '__NUMPY_SETUP__'
            and isinstance(node.handlers[0].body[0].value, ast.Constant)
            and node.handlers[0].body[0].value.value is False
            and not node.orelse and not node.finalbody]
        if len(guards) != 1 or len(setup_defaults) != 1:
            return None
        assumptions.add('no_external_module_global_injection')
    return {'kind': 'source_module_function_reexport', 'status': 'source_bound',
        'basis': 'source_snapshot', 'public_binding': module + '.' + name,
        'target': target['module'] + '.' + target['qualname'],
        'runtime_binding_confirmed': False, 'binding': binding,
        'source_hashes': dict(binding['source_hashes']),
        'assumptions': sorted(assumptions | {'standard_module_attribute_lookup'})}


## Resolve an iterability predicate without asserting the actual argument's kind.
#  @param analyzer Fixed primary snapshot and explicit dependency protocol option.
#  @param caller Exact lexical source definition containing the helper reference.
#  @param expression Actual helper callee expression.
#  @return Canonical name and conditional source protocol, or None.
def iterability_query(analyzer, caller, expression):
    canonical = _canonical(analyzer, caller[0], caller[1], expression)
    if not canonical or not unmodified(analyzer, canonical):
        return None
    key = canonical
    cache = analyzer._native_class_protocol_cache
    if key not in cache:
        cache[key] = None
        module, _, name = canonical.rpartition('.')
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
