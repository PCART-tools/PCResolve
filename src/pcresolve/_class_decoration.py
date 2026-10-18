## @package pcresolve._class_decoration
#  Constructor-slot preservation for bounded, identity-returning class decorators.

import ast
import copy
from dataclasses import asdict

from .class_attribute_effects import class_attribute_writes, _ClassEffectLimit


def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Bound direct class-decorator writes without proving decoration completion.
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
    for expression in reversed(cls.decorator_list):
        probe = copy.copy(cls)
        probe.decorator_list = [expression]
        selected = analyzer._decorator_definition((ref, probe))
        if selected is None or not isinstance(selected[1], ast.FunctionDef):
            return None
        owner, function = selected
        args = function.args
        parameters = args.posonlyargs + args.args
        if ('.' in owner.qualname or len(parameters) != 1 or args.defaults
                or args.kwonlyargs or args.vararg or args.kwarg
                or parameters[0].annotation is not None or function.returns is not None):
            return None
        nodes = []
        for item in ast.walk(function):
            analyzer._class_effect_fact_steps -= 1
            if len(nodes) >= 2000 or analyzer._class_effect_fact_steps < 0:
                return None
            nodes.append(item)
        parameter = parameters[0].arg
        if (not function.body or not isinstance(function.body[-1], ast.Return)
                or not isinstance(function.body[-1].value, ast.Name)
                or function.body[-1].value.id != parameter
                or any(isinstance(item, ast.Return) and item is not function.body[-1]
                       for item in nodes)
                or any(isinstance(item, ast.Name) and item.id == parameter
                       and isinstance(item.ctx, (ast.Store, ast.Del)) for item in nodes)):
            return None
        body = copy.copy(function)
        body.body = function.body[:-1]

        def charge(count):
            analyzer._class_effect_fact_steps -= count

        # The returned class is the only admitted escape. The remaining body
        # uses the same alias/reflective-write rules as ordinary class effects.
        try:
            proof = class_attribute_writes(body, parameter,
                lambda name: analyzer._builtin_name_status(owner, function, name)
                    == 'confirmed_builtin', lambda value: False,
                max_nodes=min(2000, max(0, analyzer._class_effect_fact_steps)), charge=charge)
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
    analyzer._class_decoration_cache[ref] = records
    return copy.deepcopy(records)
