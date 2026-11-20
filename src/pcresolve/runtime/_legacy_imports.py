## @package pcresolve.runtime._legacy_imports
#  Support legacy module imports.
#
#
#  Resolve previous flat module paths only when a caller imports them.
#  仅在调用方导入旧模块路径时解析历史平铺模块名。



from importlib import import_module, machinery
from importlib.abc import Loader, MetaPathFinder
import sys


_MOVED_MODULES = {
    'facts': (
        'call_resolution', 'effect_facts', 'import_facts', 'program_facts',
        'return_resolution', 'scope_facts', 'star_imports',
    ),
    'frontend': ('module_mapper', 'scanner', 'source_snapshot', 'source_syntax'),
    'ownership': (
        'builtin_ownership', 'call_graph', 'classification', 'decorator_provenance',
        'diagnostics', 'fact_versions', 'ir', 'library_usage', 'mapping_facts',
        'ownership_contracts', 'ownership_model', 'scope', 'source_resolution',
        'sources', 'symbol_table', 'types', 'views',
    ),
    'ownership.collect': (
        'single_file', 'single_file_argparse', 'single_file_assignment',
        'single_file_binding_resolution', 'single_file_builtins',
        'single_file_call_collection', 'single_file_container_shapes',
        'single_file_control_flow', 'single_file_definitions',
        'single_file_method_resolution', 'single_file_parameter_dependency',
        'single_file_receiver_resolution', 'single_file_returns',
        'single_file_source_resolution',
    ),
    'ownership.resolve': (
        'call_result_resolution', 'container_resolution', 'instance_method_resolution',
        'project_call_classification', 'project_call_context', 'project_local_classes',
        'project_method_ownership', 'project_result_binding', 'project_source_tracing',
    ),
    'flow.proofs': ('class_attribute_effects', 'entry_alias', 'syntax_facts'),
}

_RENAMED_MODULES = {
    'analysis_limits': 'runtime.limits',
    'cross_file': 'ownership.analyzer',
}

_NESTED_MOVES = {
    'flow.proofs.' + name: 'flow.proofs.containers.' + name
    for name in ('container_predicates', 'mapping_attribute_transfer', 'mapping_key_access',
                 'mapping_remainders', 'mapping_return_transfer')
}
_NESTED_MOVES.update({
    'flow.proofs.' + name: 'flow.proofs.classes.' + name
    for name in ('_class_creation', '_class_creation_calls', '_class_decoration',
                 '_class_deferred', '_class_definition', '_class_effect_attributes',
                 '_class_function_reads', '_class_identity', '_class_literal_loops',
                 '_class_metadata_read', '_class_name_binding', '_class_observer_input',
                 '_class_partial', '_class_read_binding', '_class_type_tests')
})
_PROOF_MOVES = {
    '_callable_instance_binding': 'callables',
    '_constructor_binding': 'callables', '_constructor_entry': 'callables',
    '_constructor_retention': 'callables', '_fresh_member_checks': 'callables',
    '_fresh_receiver': 'callables', '_function_factory': 'callables',
    '_function_metadata': 'callables', '_function_metadata_formation': 'callables',
    '_function_observation': 'callables',
    '_decorator_effects': 'callables.decorators',
    '_decorator_exceptions': 'callables.decorators',
    '_decorator_imports': 'callables.decorators', '_decorator_text': 'callables.decorators',
    '_fresh_decoration': 'callables.decorators',
    'conditional_constructor': 'callables.dispatch', 'entry_alias': 'callables.dispatch',
    'finite_dispatch': 'callables.dispatch', 'keyword_validation': 'callables.dispatch',
    '_metadata_calls': 'namespaces.metadata', '_metadata_creation': 'namespaces.metadata',
    '_metadata_entry': 'namespaces.metadata', '_metadata_namespace': 'namespaces.metadata',
    '_metadata_observer': 'namespaces.metadata', '_metadata_queries': 'namespaces.metadata',
    '_metadata_signature': 'namespaces.metadata',
    '_export_lists': 'namespaces.modules',
    '_module_class_effects': 'namespaces.modules',
    '_module_class_effects_core': 'namespaces.modules',
    '_module_class_prefix': 'namespaces.modules', '_module_getattr': 'namespaces.modules',
    '_function_namespace': 'namespaces',
    '_source_bindings': 'namespaces.source',
    '_source_callable_metadata': 'namespaces.source',
    '_source_dependencies': 'namespaces.source',
    '_cached_imports': 'protocols', '_caller_inputs': 'protocols',
    '_contextmanager_instance_effects': 'protocols', '_contextmanager_namespace': 'protocols',
    '_native_class_protocol': 'protocols', '_property_namespace': 'protocols',
    '_runtime_namespace': 'protocols', '_source_protocols': 'protocols',
    '_stdlib_function_decorators': 'protocols', '_stub_iterability': 'protocols',
    'capture_rejection_guard': 'protocols', 'class_attribute_effects': 'protocols',
    'syntax_facts': 'protocols',
}
_NESTED_MOVES.update({
    'flow.proofs.' + name: 'flow.proofs.' + folder + '.' + name
    for name, folder in _PROOF_MOVES.items()
})


## Map every supported old module name to its current implementation path.
## 将每个受支持的旧模块名映射到当前实现路径。
#
#  @param package_name Name of the loaded PCResolve package.
#  @return Mapping of fully qualified old names to relative target paths.
def _targets(package_name):
    targets = dict(_RENAMED_MODULES)
    targets.update(_NESTED_MOVES)
    for namespace, names in _MOVED_MODULES.items():
        targets.update((name, namespace + '.' + name) for name in names)
    return {package_name + '.' + old: target
            for old, target in targets.items() if old != target}


## Serve a legacy module name from its current implementation path.
## 从当前实现路径提供旧模块名。
class _LegacyLoader(Loader):
    ## Configure the loader for one legacy name and its target.
    ## 为单个旧模块名及其目标配置加载器。
    #
    #  @param package_name Root package used for the relative target import.
    #  @param target Relative implementation path that provides the module.
    #  @return None
    def __init__(self, package_name, target):
        self.package_name = package_name
        self.target = target

    ## Import the current implementation instead of the legacy module.
    ## 导入当前实现，而不是旧模块本身。
    #
    #  @param spec Module specification supplied by the import system; not inspected.
    #  @return Imported implementation module.
    def create_module(self, spec):
        return import_module('.' + self.target, self.package_name)

    ## Skip execution because the target module was already imported.
    ## 跳过执行，因为目标模块已经被导入。
    #
    #  @param module Module created from the target; no code is executed again.
    #  @return None
    def exec_module(self, module):
        return None


## Resolve legacy module names to their current implementations.
## 将旧模块名解析到当前实现。
class _LegacyFinder(MetaPathFinder):
    ## Configure the finder for one loaded PCResolve package.
    ## 为单个已加载的 PCResolve 包配置查找器。
    #
    #  @param package_name Root package whose old module names are aliased.
    #  @return None
    def __init__(self, package_name):
        self.package_name = package_name

    ## Build a spec only when the requested name has a legacy alias.
    ## 仅当请求的名称存在旧别名时构建模块规范。
    #
    #  @param fullname Fully qualified module name requested by the import system.
    #  @param path Parent package path supplied by the import system; not used.
    #  @param target Module object being reloaded; not used for alias lookup.
    #  @return Module spec backed by the legacy loader, or None for other names.
    def find_spec(self, fullname, path=None, target=None):
        destination = _targets(self.package_name).get(fullname)
        if destination is None:
            return None
        loader = _LegacyLoader(self.package_name, destination)
        return machinery.ModuleSpec(fullname, loader, is_package=False)


## Install lazy aliases for old module paths.
## 为旧模块路径安装延迟别名。
#
#  @param package_name Name of the loaded PCResolve package.
#  @return None
def register_legacy_imports(package_name):
    if not any(isinstance(finder, _LegacyFinder) and finder.package_name == package_name
               for finder in sys.meta_path):
        sys.meta_path.insert(0, _LegacyFinder(package_name))


## Find the implementation path for one old top-level module attribute.
## 查找一个旧顶层模块属性对应的实现路径。
#
#  @param package_name Name of the loaded PCResolve package.
#  @param name Attribute requested from the package.
#  @return Relative implementation path, or None when the name is not an alias.
def legacy_target_for(package_name, name):
    return _targets(package_name).get(package_name + '.' + name)


## List old module attributes supported at the package root.
## 列出包根目录支持的旧模块属性名。
#
#  @param package_name Name of the loaded PCResolve package.
#  @return Sorted top-level alias names.
def legacy_names_for(package_name):
    return sorted(fullname.rpartition('.')[2]
                  for fullname in _targets(package_name)
                  if fullname.count('.') == package_name.count('.') + 1)
