## @package pcresolve.flow.proofs.classes.deferred._class_deferred_metadata
#  Track generated function metadata.
#
#
#  Formation and invalidation of generated function metadata evidence.
#  新建函数元数据证据的形成与失效管理。



import copy
import ast


## Record a stored function metadata snapshot when formation is proven.
## 仅在元数据形成得到证明时记录函数存储快照。
#
#  @param name Stored class metadata attribute.
#  @param value Local binding containing the fresh function.
#  @param state Current local helper/function bindings.
#  @param statement Assignment providing source evidence.
#  @param generated_members Mutable evidence destination.
#  @param published_tokens Tokens already stored in the protected class.
#  @param source_span Source coordinate query.
#  @return None; appends a complete formation fact when supported.
def store_metadata_member(name, value, state, statement, generated_members,
                          published_tokens, source_span):
    payload = state[value][2] if len(state[value]) == 3 else None
    if payload is None or payload['formation'] is None or name is None:
        return
    fact = copy.deepcopy(payload['formation'])
    if any(fact['metadata_shapes'][key] is None
           for key in ('documentation', 'name', 'qualname')):
        return
    generated_members.append({'attribute': name, 'metadata_formation': fact,
                              'store_evidence': source_span(statement),
                              '_token': payload['token']})
    published_tokens.add(payload['token'])


## Update aliases and invalidate stale metadata snapshots after a write.
## 元数据后续写入后更新别名并使过期快照失效。
#
#  @param name Local function binding being updated.
#  @param field Metadata field such as __doc__ or __name__.
#  @param value Assigned metadata expression.
#  @param state Current helper/function bindings.
#  @param values Known literal strings used for specialization.
#  @param statement Assignment providing source evidence.
#  @param generated_members Mutable metadata evidence destination.
#  @param published_tokens Tokens already stored in the protected class.
#  @param token_nodes Function nodes associated with proof tokens.
#  @param source_span Source coordinate query.
#  @param string_value Bounded string expression evaluator.
#  @return None; updates aliases and invalidates stale snapshots in place.
def update_metadata_write(name, field, value, state, values, statement,
                          generated_members, published_tokens, token_nodes,
                          source_span, string_value):
    current = state[name]
    payload = current[2] if len(current) == 3 else None
    if payload is None:
        # A branch join can lose metadata precision while retaining the native
        # function. Invalidate any possibly aliased store too.
        generated_members[:] = [record for record in generated_members
                                if token_nodes.get(record['_token']) is not current[1]]
        return
    token = payload['token']
    if token in published_tokens:
        generated_members[:] = [record for record in generated_members
                                if record['_token'] != token]
    updated = copy.deepcopy(payload)
    fact = updated['formation']
    if fact is not None:
        shape = ['str'] if string_value(value, values) is not None else (
            ['NoneType'] if isinstance(value, ast.Constant) and value.value is None
            and field == '__doc__' else None)
        fact['metadata_shapes'][{'__doc__': 'documentation', '__name__': 'name',
                                 '__qualname__': 'qualname'}[field]] = shape
        fact['metadata_writes'].append(source_span(statement))
    for alias, item in list(state.items()):
        other = item[2] if len(item) == 3 else None
        if other is not None and other['token'] == token:
            state[alias] = (item[0], item[1], updated)
