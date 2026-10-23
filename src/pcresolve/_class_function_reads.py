## @package pcresolve._class_function_reads
#  Plain function metadata lookup at a bounded source class-decorator prefix.

import ast
import copy
from dataclasses import asdict

from ._class_definition import namespace_issues, _namespace_syntax
from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts
from ._class_creation import creation_effects, written_attributes
from ._function_metadata_formation import metadata_formation


## Prepare lazy lookup proofs without inferring execution of the selected method.
#  @param analyzer Fixed source snapshot and query budget.
#  @param target Protected source class identity and declaration.
#  @param decorations Inner class decorations already proved at this prefix.
#  @return Provider taking an attribute, lookup expression and prior write set.
def function_reads(analyzer, target, decorations=()):
    checked, hierarchy, hooks = [False], [], []

    def stable():
        if checked[0] is not False:
            return checked[0] is True
        checked[0] = None
        if target is None or analyzer.index_boundaries:
            return False
        ref, _ = target
        sources = analyzer._class_mro(ref.module, ref.qualname)
        if not sources or len(sources) > 64:
            return False
        if any(cls.keywords or analyzer.definition_conditions.get(owner)
                or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
                or owner != ref and cls.decorator_list
                for owner, cls in sources):
            return False
        creation = creation_effects(analyzer, target)
        if creation is None:
            return False
        hooks.extend(creation)
        count = 0
        for _, cls in sources:
            for _ in _namespace_syntax(cls):
                count += 1
                analyzer._class_effect_fact_steps -= 1
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                if count > 2000 or analyzer._class_effect_fact_steps < 0:
                    return False
        try:
            if namespace_issues(analyzer, sources, assumptions=set()):
                return False
        except _ClassEffectLimit:
            return False
        hierarchy.extend(sources)
        checked[0] = True
        return True

    def unescaped():
        writes, truncated = analyzer._class_binding_writes(include_escapes=True)
        return not truncated and not any(any(written == owner for owner, _ in hierarchy)
                                          for written, _, _, _, _ in writes)

    def intact(attribute, dirty):
        if (type(attribute) is not str or not attribute or attribute.startswith('__')
                or attribute == 'mro' or not stable()):
            return False
        affected = {attribute, '*', '__class__', '__bases__'}
        if affected & (dirty | written_attributes(hooks)) or any(
                affected & set(fact['attributes']) for fact in decorations):
            return False
        # A saved method may be represented by its declaring class in the
        # neutral escape scanner. Any such write can change function metadata,
        # not just the class slot with the original method name.
        return unescaped()

    def namespace(dirty, absent=None):
        if not stable():
            return None
        if absent is not None and (not intact(absent, dirty) or any(
                absent in statement_scope_facts(cls.body).bound for _, cls in hierarchy)):
            return None
        affected = {'*', '__class__', '__bases__', '__dict__'}
        if (affected & (dirty | written_attributes(hooks)) or any(
                affected & set(fact['attributes']) for fact in decorations) or not unescaped()):
            return None
        assumptions = ['source_snapshot_bindings_hold', 'builtin_type_class_namespace_mapping',
                       'no_unmodeled_indirect_class_mutation',
                       'no_external_monkeypatch_or_import_hook']
        for hook in hooks:
            assumptions.extend(hook['assumptions'])
        hashes = {**analyzer.hashes, **analyzer._supporting_source_hashes}
        for fact in decorations:
            assumptions.extend(fact['assumptions'])
            hashes.update(fact['source_hashes'])
        return {'kind': 'source_native_class_namespace_query', 'status': 'source_bound',
            'operation': 'absent_attribute_fallback' if absent is not None else 'native_string_key_membership',
            'attribute': absent, 'receiver_class': asdict(target[0]),
            'lookup_scope': 'source_class_decoration_prefix',
            'class_creation_hooks': copy.deepcopy(hooks), 'prior_class_writes': sorted(dirty),
            'inner_class_decorations': copy.deepcopy(decorations),
            'runtime_lookup_confirmed': False, 'completion': 'normal_read_only',
            'source_hashes': dict(sorted(hashes.items())),
            'assumptions': sorted(set(assumptions))}

    def read(attribute, expression, dirty):
        if not intact(attribute, dirty):
            return None
        for owner, cls in hierarchy:
            members = [node for node in cls.body if attribute in statement_scope_facts([node]).bound]
            if not members:
                continue
            if (len(members) != 1 or not isinstance(members[0], (ast.FunctionDef, ast.AsyncFunctionDef))
                    or members[0].name != attribute):
                return None
            matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + attribute)
            if len(matches) != 1 or matches[0][1] is not members[0]:
                return None
            function_ref, function = matches[0]
            formation = None
            try:
                formation = metadata_formation(analyzer, matches[0])
            except _ClassEffectLimit:
                return None
            if function.decorator_list and formation is None:
                return None
            assumptions = ['source_snapshot_bindings_hold',
                'builtin_type_lookup_and_function_descriptor',
                'no_unmodeled_indirect_class_mutation',
                'no_external_monkeypatch_or_import_hook']
            for hook in hooks:
                assumptions.extend(hook['assumptions'])
            if formation is not None:
                assumptions.extend(formation['assumptions'])
            result = {'kind': 'source_plain_class_function_read', 'status': 'source_bound',
                'completion': 'normal_read_only', 'attribute': attribute,
                'lookup_scope': 'source_class_decoration_prefix', 'target': asdict(function_ref),
                'receiver_class': asdict(target[0]),
                'hierarchy': [asdict(ref) for ref, _ in hierarchy],
                'prior_class_writes': sorted(dirty),
                'class_creation_hooks': copy.deepcopy(hooks),
                'method_namespace': 'no_visible_writes_or_escapes',
                'function_evidence': {'file_path': owner.file_path, 'lineno': function.lineno,
                    'col_offset': function.col_offset, 'end_lineno': function.end_lineno,
                    'end_col_offset': function.end_col_offset},
                'source_hashes': dict(sorted(analyzer.hashes.items())),
                'assumptions': sorted(set(assumptions))}
            if formation is not None:
                result['metadata_formation'] = formation
                result['source_hashes'].update(formation['source_hashes'])
                result['source_hashes'] = dict(sorted(result['source_hashes'].items()))
            return result
        return None

    read.namespace = namespace
    return read
