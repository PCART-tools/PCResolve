## @package tests.test_shared_layer_boundaries
#  Architectural dependency direction for the shared program-fact layer.

import ast
from pathlib import Path


PACKAGE = Path(__file__).parents[1] / 'src' / 'pcresolve'
SHARED_MODULES = frozenset([
    'program_facts', 'source_snapshot', 'call_resolution', 'scope_facts',
    'return_resolution', 'effect_facts', 'import_facts',
])
OWNERSHIP_ADAPTERS = (
    'single_file.py', 'cross_file.py', 'mapping_facts.py',
    'single_file_method_resolution.py', 'single_file_call_collection.py',
    'single_file_assignment.py', 'single_file_source_resolution.py',
    'single_file_control_flow.py', 'single_file_definitions.py',
    'single_file_container_shapes.py', 'call_result_resolution.py',
    'instance_method_resolution.py', 'container_resolution.py',
    'project_call_context.py', 'project_result_binding.py',
    'project_source_tracing.py', 'project_method_ownership.py',
    'project_local_classes.py', 'project_call_classification.py',
)


def _local_imports(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            modules.add(node.module.split('.')[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('pcresolve.'):
                    modules.add(alias.name.split('.')[1])
    return modules


def test_shared_fact_modules_do_not_depend_on_analyzer_adapters():
    for module in SHARED_MODULES:
        imports = _local_imports(PACKAGE / (module + '.py'))
        assert imports <= SHARED_MODULES, (module, imports - SHARED_MODULES)


def test_analyzers_consume_the_shared_layer_through_explicit_imports():
    flow_imports = _local_imports(PACKAGE / 'flow.py')
    ownership_imports = set().union(*(
        _local_imports(PACKAGE / name)
        for name in OWNERSHIP_ADAPTERS))
    assert SHARED_MODULES <= flow_imports
    assert SHARED_MODULES <= ownership_imports
