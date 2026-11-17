## @package pcresolve.ownership.resolve.target_metadata
#  Source-backed metadata for one local call target.


from pcresolve.ownership.sources import SourceSet, normalize_source


def edge_callable_names(edge, normalize):
    # These names select candidates only; they do not prove a target.
    names = set()
    callee_name = getattr(edge, 'callee_name', '') or ''
    if callee_name:
        names.add(callee_name.rsplit('.', 1)[-1])
    source = normalize(getattr(edge, 'callee_source', None))
    sources = source.sources if isinstance(source, SourceSet) else (source,)
    for item in sources:
        normalized = normalize(item)
        if isinstance(normalized, str):
            names.add(normalized.rsplit('.', 1)[-1])
    return names


class TargetMetadataMixin:
    def _edge_callable_names(self, edge):
        return edge_callable_names(edge, normalize_source)

    ## Describe one local function, constructor, or method target.
    ## 描述一个局部函数、构造函数或方法目标。
    #
    #  @param target_module Target definition's module.
    #  @param scope_name Qualified function or method name.
    #  @return Target metadata tuple, or None when its module is unavailable.
    def _local_target_metadata(
            self, target_module, scope_name
            ):
        cg = getattr(self, 'project_cg', None)
        target_cg = cg.modules.get(target_module) if cg is not None else None
        if target_cg is None:
            return None
        parts = scope_name.split('.')
        class_name = parts[-2] if len(parts) >= 2 else ''
        target_name = parts[-1]
        is_constructor = target_name == '__init__' and class_name in target_cg.classes
        is_method = (not is_constructor and class_name in target_cg.classes
                     and target_name in target_cg.classes[class_name].methods)
        return target_cg, class_name, target_name, is_constructor, is_method
