## @package pcresolve.ownership.resolve.target_metadata
#  Describe source-backed local call targets.
#
#
#  Extracts candidate names and local function or constructor metadata without proving target identity.
#  提取候选名称以及本地函数或构造器元数据，候选名称本身不证明目标身份。



from pcresolve.ownership.sources import SourceSet, normalize_source


## Select candidate callable names for one source edge.
## 为一个源码边选择候选可调用名称。
#
#  @param edge Edge fact supplying the callee name and callee source.
#  @param normalize Normalizer applied to every candidate source value.
#  @return Candidate short names; membership does not prove the target.
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


## Mixin describing source-backed local call targets.
## 描述有源码依据的本地调用目标的混入类。
class TargetMetadataMixin:
    ## Select candidate callable names for one edge with the shared normalizer.
    ## 使用共享归一化器为一个边选择候选可调用名称。
    #
    #  @param edge Edge fact whose callee names are inspected.
    #  @return Candidate short names for the edge.
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
