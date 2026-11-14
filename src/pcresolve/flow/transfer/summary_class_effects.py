## @package pcresolve.flow.transfer.summary_class_effects
## @brief Class Effects operations for query-local flow summaries.

from pcresolve.flow.transfer._summary_support import *


class ClassEffectsMixin:
    def class_attribute_effect(self, definition, call, captures, env, node):
        if (call.binding_status == 'invalid' or call.target != definition[0]
                or (definition[0].module, definition[0].qualname) in self.modified_return_callables
                or not getattr(definition[1], 'decorator_list', [])
                    and '.' not in definition[0].qualname
                    and not self.analyzer._stable_import_name(
                        definition[0].module + '.' + definition[0].qualname)
                or getattr(definition[1], 'decorator_list', []) and not any(
                    fact.get('status') == 'source_bound' for fact in call.class_method_bindings)):
            return []
        ordinary = {arg.arg for arg in definition[1].args.posonlyargs + definition[1].args.args
                    + definition[1].args.kwonlyargs}
        preserved = []
        for argument in call.argument_sources:
            parameter, values = argument.get('parameter'), argument.get('sources', [])
            if (parameter not in ordinary or argument.get('target_path') or not values
                    or not all(value.get('class_type') and value.get('relation') == 'direct'
                        and (value.get('kind') == 'class' or value.get('source_class_origin', {}).get(
                            'basis') == 'source_symbol')
                        and not any(value.get(flag) for flag in ('projection', 'output_path',
                            'value_incomplete', 'import_modified', 'import_incomplete',
                            'attribute_provenance')) for value in values)):
                continue
            identities = _unique(value['class_type'] for value in values)
            if len(identities) != 1:
                continue
            identity = identities[0]
            hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
            if not hierarchy or len(hierarchy) > 64 or any(cls.decorator_list or cls.keywords
                                                          for _, cls in hierarchy):
                continue
            owners = [asdict(ref) for ref, _ in hierarchy]
            other = [value for item in call.argument_sources if item is not argument
                     for value in item.get('sources', [])]
            other.extend(value for contents in captures.values() for value in contents)
            related = False
            for value in other + self.materialize(other, env):
                other_class = value.get('class_type')
                if not other_class:
                    continue
                other_mro = self.analyzer._class_mro(other_class['module'], other_class['qualname'])
                if (other_class in owners or other_mro is None
                        or any(asdict(ref) in owners for ref, _ in other_mro)):
                    related = True
            if related:
                continue
            records = [record for record in call.parameter_bindings
                       if record.get('parameter') == parameter]
            implicit = any(fact.get('status') == 'source_bound'
                and fact.get('implicit_binding', {}).get('parameter') == parameter
                for fact in call.class_method_bindings)
            if not (len(records) == 1 and records[0]['status'] == 'exact' or not records and implicit):
                continue
            args = definition[1].args
            uncertain = {arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs
                         + [arg for arg in (args.vararg, args.kwarg) if arg is not None]}
            uncertain.discard(parameter)
            uncertain.update(captures)
            string_literals, name_bindings = {}, []
            for item in call.argument_sources:
                literal = item.get('literal')
                if literal and literal.get('type') in ('str', 'int', 'float', 'bool', 'NoneType'):
                    uncertain.discard(item.get('parameter'))
                bindings = [record for record in call.parameter_bindings
                            if record.get('parameter') == item.get('parameter')]
                arguments = [argument for argument in call.argument_sources
                             if argument.get('parameter') == item.get('parameter')]
                if (literal and literal.get('type') == 'str' and type(literal.get('value')) is str
                        and item.get('parameter') in ordinary and item.get('parameter') != parameter
                        and not item.get('target_path') and len(arguments) == 1
                        and len(bindings) == 1 and bindings[0].get('status') == 'exact'
                        and bindings[0].get('argument') == item.get('argument')
                        and bindings[0].get('binding_kind') != 'default'):
                    string_literals[item['parameter']] = literal['value']
                    name_bindings.append({'parameter': item['parameter'],
                        'argument': copy.deepcopy(item['argument']), 'literal': copy.deepcopy(literal),
                        'evidence': copy.deepcopy(item.get('value_evidence', []))})
            defaults = {arg.arg: default for arg, default in zip(
                (args.posonlyargs + args.args)[-len(args.defaults):], args.defaults)}
            defaults.update({arg.arg: default for arg, default in zip(args.kwonlyargs, args.kw_defaults)
                             if default is not None})
            for record in call.parameter_bindings:
                default = defaults.get(record.get('parameter'))
                if (record.get('binding_kind') == 'default' and record.get('status') == 'exact'
                        and any(fact.get('status') == 'source_bound'
                            and fact.get('target') == asdict(definition[0])
                            for fact in call.class_method_bindings)
                        and isinstance(default, ast.Constant)
                        and type(default.value) in (str, int, float, bool, type(None))):
                    uncertain.discard(record['parameter'])
            ## Identify a name whose class write must remain protected.
            ## 判断名称是否属于必须保护的类写入范围。
            #
            #  @param source Name AST node.
            #  @return True when uncertain or within the receiver hierarchy.
            def protected(source):
                if source.id in uncertain:
                    return True
                match = self.analyzer._resolve_class(definition[0], source.id)
                return match is not None and asdict(match[0]) in owners

            ## Charge work against the shared class-effect budget.
            ## 将工作量计入共享类效果预算。
            #
            #  @param count Number of steps to charge.
            #  @return None
            def charge(count):
                self.analyzer._class_effect_fact_steps -= count

            metadata = []
            read_bindings = {}

            ## Obtain and cache an independent class-attribute read premise.
            ## 获取并缓存独立的类属性读取前提。
            #
            #  @param attribute Attribute name.
            #  @return True when the binding is source-bound.
            def class_read(attribute):
                if attribute not in read_bindings:
                    binding = source_class_read_binding(self, identity, definition, parameter, call, node, attribute)
                    read_bindings[attribute] = binding
                    if binding is not None and binding not in call.class_read_bindings:
                        call.class_read_bindings.append(copy.deepcopy(binding))
                binding = read_bindings[attribute]
                return binding is not None and binding.get('status') == 'source_bound'

            ## Obtain the independently proved source class-name literal.
            ## 获取独立证明的源码类名字面量。
            #
            #  @param source Name expression supplied by the effect scanner.
            #  @return Literal class name or None when unproven.
            def class_name(source):
                if not metadata:
                    binding = source_class_name_binding(self, identity, definition, parameter, call, node)
                    metadata.append(binding)
                    if binding is not None and binding not in call.class_metadata_bindings:
                        call.class_metadata_bindings.append(copy.deepcopy(binding))
                binding = metadata[0]
                return (binding.get('literal', {}).get('value') if binding is not None
                        and binding.get('status') == 'source_bound' else None)

            try:
                proof = class_attribute_writes(definition[1], parameter,
                    lambda name: self.analyzer._builtin_name_status(definition[0], definition[1], name)
                        == 'confirmed_builtin', protected,
                    self.analyzer._lexical_class_name(definition[0]),
                    min(2000, self.analyzer._class_effect_fact_steps), charge,
                    string_literals=string_literals, class_name=class_name, class_read=class_read)
            except _ClassEffectLimit:
                self.add_boundary('class_attribute_effect_budget', node, env, values, call_id=call.id)
                continue
            if proof is None:
                continue
            paths = {ref.file_path for ref, _ in hierarchy} | {
                definition[0].file_path, self.ref.file_path}
            if proof.metadata_evidence:
                paths.update(metadata[0]['source_hashes'])
            for attribute, _ in proof.read_evidence:
                paths.update(read_bindings[attribute]['source_hashes'])
            effect = {'kind': 'class_attribute_write_set', 'status': 'bounded',
                'preserved_scope': 'other_class_attributes', 'completion': 'normal_return',
                'value_completeness': 'unmodeled', 'receiver_class': copy.deepcopy(identity),
                'target': asdict(definition[0]), 'parameter': parameter,
                'attributes': list(proof.attributes), 'call_id': call.id,
                'call_evidence': self.evidence(node),
                'evidence': [self.evidence_at(definition[0], item) for item in proof.evidence],
                'source_hashes': {path: self.analyzer.hashes[path] for path in sorted(paths)
                                  if path in self.analyzer.hashes},
                'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_attribute_writes',
                    'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']}
            if name_bindings:
                effect['name_bindings'] = name_bindings
            if proof.read_evidence:
                effect['read_basis'] = 'source_class_attribute_invariant'
                effect['read_premises'] = [copy.deepcopy(read_bindings[name])
                    for name in _unique([name for name, _ in proof.read_evidence])]
                effect['read_evidence'] = [{'attribute': name, 'operation': 'hasattr',
                    'evidence': self.evidence_at(definition[0], source)} for name, source in proof.read_evidence]
            if proof.metadata_evidence:
                effect['name_basis'] = 'source_class_metadata'
                effect['name_metadata'] = copy.deepcopy(metadata[0])
                effect['name_evidence'] = [self.evidence_at(definition[0], item)
                                           for item in proof.metadata_evidence]
            call.effects.append(effect)
            self.register_class_lookup_effect(effect, env)
            preserved.append(identity)
        return preserved

    def class_origin_invalid(self, identity, env, exposed=()):
        if not exposed and not any(key.startswith('$class_origin_invalid:') for key in env):
            return False
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        owners = [asdict(ref) for ref, _ in hierarchy] if hierarchy else [identity]
        return any(owner in exposed or env.get(_class_origin_key(owner)) for owner in owners)

    def invalidate_class_origins(self, values, env, call=None):
        identities = [value['class_type'] for value in values + self.materialize(values, env)
                      if value.get('source_class_origin') and value.get('class_type')]
        if identities:
            if (getattr(self.analyzer, '_conditional_source_state', False) and call is not None
                    and self.condition_class_state(identities, values, env, call)):
                return
            for identity in _unique(identities):
                key = _class_origin_key(identity)
                env[key] = [{'kind': 'class_state', 'source': key,
                    'relation': 'direct', 'evidence': [], 'conditions': [],
                    'cause': 'unmodeled_call' if call is not None else 'write'}]
            for name, sources in env.items():
                env[name] = [dict(value, value_incomplete=True)
                    if value.get('class_type') and self.class_origin_invalid(
                        value['class_type'], env, identities) else value for value in sources]

    def condition_class_state(self, identities, values, env, call):
        # A state predicate describes a required source lookup, never an effect
        # proof or a runtime target. Explicit writes still use normal invalidation.
        if any(value.get('value_incomplete') for value in values if value.get('class_type')):
            return False
        if call.target is None:
            return False
        selected = self.analyzer._definition_index.find(call.target.module, call.target.qualname)
        if len(selected) != 1:
            return False
        function = selected[0][1]
        parameters = function.args.posonlyargs + function.args.args
        if not parameters:
            return False
        # Do not hide source-known writes to the method namespace or MRO.
        methods = {'__class__', '__bases__', '__dict__'}
        for identity in identities:
            hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
            if not hierarchy:
                return False
            for _, cls in hierarchy:
                for member in cls.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(member.name)
                        if member.name.startswith('__') and not member.name.endswith('__') and cls.name.lstrip('_'):
                            methods.add('_' + cls.name.lstrip('_') + member.name)
        for count, item in enumerate(ast.walk(function)):
            if count >= 2000 or self.analyzer._class_effect_fact_steps <= 0:
                self.result.boundaries.append({'call_id': call.id, 'reason': 'conditional_source_budget'})
                return False
            self.analyzer._class_effect_fact_steps -= 1
            if (isinstance(item, ast.Attribute) and isinstance(item.ctx, (ast.Store, ast.Del))
                    and item.attr in methods):
                return False
            if (isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                    and item.func.id in ('setattr', 'delattr') and len(item.args) >= 2):
                name = (class_write_name(item.args[1], function, item.args[0].id, None, item.lineno)
                        if isinstance(item.args[0], ast.Name) else None)
                if name in methods:
                    return False
        predicates = []
        for identity in _unique(identities):
            if self.class_origin_invalid(identity, env):
                return False
            predicate = {'kind': 'source_state_preserved', 'status': 'required',
                'runtime_confirmed': False, 'receiver_class': copy.deepcopy(identity),
                'effect_call': call.id, 'effect_target': asdict(call.target),
                'evidence': {'file_path': call.caller.file_path, 'lineno': call.lineno,
                    'col_offset': call.col_offset, 'end_lineno': call.end_lineno,
                    'end_col_offset': call.end_col_offset},
                'scope': 'subsequent_source_lookup', 'feasibility': 'not_proven'}
            predicates.append(predicate)
            self.result.boundaries.append({'call_id': call.id, 'reason': 'conditional_source_state',
                'boundary_kind': 'required_condition', 'condition': copy.deepcopy(predicate)})
        for name, sources in env.items():
            env[name] = [dict(value, conditions=_unique(value.get('conditions', []) +
                [copy.deepcopy(predicate) for predicate in predicates
                 if predicate['receiver_class'] == value.get('class_type')]))
                if value.get('class_type') else value for value in sources]
        return True

    def invalidate_instance_receivers(self, values, env):
        exposed = {(value.get('source'), repr(value['instance_type']))
                   for value in values + self.materialize(values, env)
                   if value.get('instance_type')}
        if exposed:
            for name, sources in env.items():
                env[name] = [dict(value, value_incomplete=True, instance_candidates=[])
                    if value.get('instance_type') and (value.get('source'),
                        repr(value['instance_type'])) in exposed else value for value in sources]

    def implicit_keyword_conflict(self, call, parameter, slot, positional_only):
        if parameter in positional_only:
            return False
        keyword = {'keyword': parameter}
        duplicates = [record for record in call.parameter_bindings
                      if record.get('argument') == keyword]
        if not duplicates:
            return False
        for record in duplicates:
            record.update(parameter=parameter, status='duplicate',
                          conflicts_with=slot, destination_kind='parameter')
            record.pop('target_path', None)
        for argument in call.argument_sources:
            if argument.get('argument') == keyword:
                argument['parameter'] = parameter
                argument.pop('target_path', None)
        for value in call.argument_flows + call.parameter_flows:
            if value.get('argument') == keyword:
                value.update(target_parameter=parameter, target_path=[])
        call.binding_status = 'invalid'
        call.binding_issues.append({'kind': 'duplicate_binding',
            'parameter': parameter, 'argument': keyword, 'conflicts_with': slot})
        self.result.boundaries.append({'call_id': call.id, 'reason': 'duplicate_argument_binding'})
        return True

    def class_method_binding(self, node, target, receiver):
        if not isinstance(node.func, ast.Attribute):
            return None
        classes = _unique([value['class_type'] for value in receiver if value.get('class_type')])
        receiver_ref = FunctionRef(**classes[0]) if len(classes) == 1 else None
        if receiver_ref is None and isinstance(node.func.value, (ast.Name, ast.Attribute)):
            match = self.analyzer._resolve_class(self.ref, ast.unparse(node.func.value))
            if match:
                receiver_ref = match[0]
        if target is None and receiver_ref:
            matches = self.analyzer._definition_index.find(receiver_ref.module,
                receiver_ref.qualname + '.' + node.func.attr)
            target = matches[0] if len(matches) == 1 else self.analyzer._inherited_method(
                receiver_ref.module, receiver_ref.qualname, node.func.attr)
        if target is None or not any(isinstance(decorator, ast.Name)
                and decorator.id == 'classmethod' for decorator in getattr(target[1], 'decorator_list', [])):
            return None
        ref, method = target
        owners = self.analyzer._definition_index.find(ref.module, ref.qualname.rpartition('.')[0], kind='class')
        owner_ref = owners[0][0] if len(owners) == 1 else None
        descriptor = self.analyzer._descriptor_kind(target)
        issues = []
        evidence = _unique([self.evidence(node)] + [item for value in receiver
            for item in value.get('evidence', [])] + [self.evidence_at(ref, method)])
        binding_evidence = [item for value in receiver for item in value.get('evidence', [])]
        first = ast.unparse(node.func.value).partition('.')[0]
        bodies = self.analyzer.module_bodies.get(self.ref.module, [])
        bindings = self.analyzer.import_binding_facts.get(self.ref.module, [])
        if len(bodies) == 1 and len(bindings) == 1:
            module_ref = FunctionRef(self.ref.module, '', bodies[0][0])
            binding_evidence.extend(self.evidence_at(module_ref, statement)
                                    for statement in bindings[0].get(first, [])
                                    if hasattr(statement, 'lineno'))

        ## Record a classmethod binding issue with optional source evidence.
        ## 记录类方法绑定问题及可选源码证据。
        #
        #  @param reason Issue reason code.
        #  @param source_ref Optional source identity.
        #  @param source_node Optional evidence AST node.
        #  @return None
        def issue(reason, source_ref=None, source_node=None):
            item = {'reason': reason}
            if source_node is not None:
                item['evidence'] = self.evidence_at(source_ref, source_node)
            issues.append(item)

        direct = (receiver_ref is not None and receiver and len(classes) == 1
            and isinstance(node.func.value, (ast.Name, ast.Attribute)) and all(
                (value.get('kind') == 'class' or value.get('source_class_origin', {}).get(
                    'basis') == 'source_symbol' and value.get('source_class_origin', {}).get(
                    'class') == value.get('class_type')) and value.get('relation') == 'direct'
                and not any(value.get(flag) for flag in ('projection', 'output_path',
                    'value_incomplete', 'import_modified', 'import_incomplete', 'attribute_provenance'))
                for value in receiver))
        if not direct:
            issue('receiver_origin_unconfirmed')
        mutations = _unique([effect for value in receiver
                            for effect in value.get('class_lookup_mutations', [])])
        if (any(effect.get('attributes') for effect in mutations)
                and node.func.attr.startswith('__') and not node.func.attr.endswith('__')):
            issue('private_lookup_after_class_write_unconfirmed')
        if self.class_lookup_affected(receiver, (node.func.attr, '__class__', '__bases__')):
            issue('class_lookup_write')
        if descriptor != 'classmethod':
            issue('descriptor_unconfirmed', ref, method)
        parts = ref.qualname.split('.')
        for length in range(1, len(parts) - 1):
            for enclosing_ref, enclosing in self.analyzer._definition_index.find(
                    ref.module, '.'.join(parts[:length])):
                if 'classmethod' in self.analyzer._scope_facts(enclosing).bound:
                    issue('descriptor_unconfirmed', enclosing_ref, enclosing)
        hierarchy = (self.analyzer._class_mro(receiver_ref.module, receiver_ref.qualname)
                     if receiver_ref else None)
        lookup = 'local_class_dictionary' if receiver_ref == owner_ref else 'source_mro'
        if lookup == 'source_mro' and hierarchy is None:
            issue('mro_unavailable')
        checked, pending, unresolved_bases = [], [receiver_ref] if receiver_ref else [], False
        while pending and len(checked) < 64:
            current = pending.pop(0)
            if current in checked:
                continue
            checked.append(current)
            matches = self.analyzer._definition_index.find(current.module, current.qualname, kind='class')
            if len(matches) != 1:
                issue('class_definition_unavailable')
                continue
            class_ref, cls = matches[0]
            if cls.decorator_list or cls.keywords:
                issue('class_lookup_customization', class_ref, cls)
            if current != receiver_ref and any('__init_subclass__' in
                    statement_scope_facts([statement]).bound for statement in cls.body):
                issue('class_creation_hook', class_ref, cls)
            members = [statement for statement in cls.body
                       if node.func.attr in statement_scope_facts([statement]).bound]
            if current == owner_ref:
                if members != [method]:
                    issue('method_member_binding_unconfirmed', class_ref, cls)
                preceding = cls.body[:cls.body.index(method)] if method in cls.body else cls.body
                if 'classmethod' in statement_scope_facts(preceding).bound:
                    issue('descriptor_unconfirmed', class_ref, cls)
            bases = self.analyzer._base_classes(current.module, current.qualname)
            if bases is None:
                unresolved_bases = True
            else:
                pending.extend(base[0] for base in bases)
        if pending:
            issue('class_binding_budget')
        if hierarchy:
            selected = next(((class_ref, cls) for class_ref, cls in hierarchy
                if any(node.func.attr in statement_scope_facts([statement]).bound
                       for statement in cls.body)), None)
            if selected and selected[0] != owner_ref:
                issue('method_lookup_conflict', selected[0], selected[1])
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            issue('class_binding_budget')
        identities = {(item.module, item.qualname) for item in checked}
        for written, attribute, reason, source_ref, source_node in writes:
            if ((written.module, written.qualname) in identities
                    and attribute in (node.func.attr, '*', '__bases__', '__class__')):
                issue(reason, source_ref, source_node)
                issues[-1]['reachability'] = 'not_proven'
        for previous in self.calls:
            if (previous.target_status not in (
                    'python_protocol', 'local_container_protocol', 'builtin_allocation')
                    and not (previous.target_status == 'builtin_boundary'
                             and previous.callee_name in ('isinstance', 'issubclass'))):
                if any((value.get('class_type', {}).get('module'),
                        value.get('class_type', {}).get('qualname')) in identities
                       for argument in previous.argument_sources
                       if argument['argument'] != {'receiver': True}
                       for value in argument['sources']) and not any(
                        effect.get('kind') == 'class_attribute_write_set'
                        and effect.get('status') == 'bounded'
                        and (effect['receiver_class']['module'],
                             effect['receiver_class']['qualname']) in identities
                        for effect in previous.effects):
                    issue('class_escape')
                    issues[-1]['evidence'] = {'file_path': previous.caller.file_path,
                        'lineno': previous.lineno, 'col_offset': previous.col_offset,
                        'callee_name': previous.callee_name}
        parameters = method.args.posonlyargs + method.args.args
        if not parameters:
            issue('implicit_receiver_parameter_missing', ref, method)
        assumptions = ['source_snapshot_bindings_hold', 'builtin_classmethod_and_type_lookup',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']
        if unresolved_bases:
            assumptions.append('unresolved_bases_use_standard_metaclass_lookup')
        fact = {'status': 'unconfirmed' if issues else 'source_bound',
            'basis': 'source_snapshot', 'runtime_target_confirmed': False,
            'receiver_class': asdict(receiver_ref) if receiver_ref else None,
            'definition_class': asdict(owner_ref) if owner_ref else None,
            'target': asdict(ref), 'lookup': lookup,
            'descriptor': {'kind': 'builtin_classmethod' if descriptor == 'classmethod' else 'unconfirmed',
                'evidence': [self.evidence_at(ref, decorator) for decorator in method.decorator_list]},
            'implicit_binding': {'parameter': parameters[0].arg if parameters else None,
                'argument': {'receiver': True},
                'status': 'unconfirmed' if issues else 'static_bound',
                'receiver_class': asdict(receiver_ref) if receiver_ref else None},
            'evidence': evidence, 'conditions': copy.deepcopy(self.conditions),
            'receiver_binding_evidence': _unique(binding_evidence),
            'source_hashes': {path: self.analyzer.hashes[path] for path in sorted(
                {item.file_path for item in checked} | {ref.file_path, self.ref.file_path})
                if path in self.analyzer.hashes},
            'assumptions': assumptions, 'issues': _unique(issues)}
        if mutations:
            fact['lookup_preservation'] = copy.deepcopy(mutations)
            fact['lookup_hierarchy'] = [asdict(owner) for owner, _ in hierarchy] if hierarchy else []
            for effect in mutations:
                fact['source_hashes'].update(effect.get('source_hashes', {}))
        return fact
