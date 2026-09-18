## @package pcresolve.module_mapper
#  Provide bidirectional mapping between file paths and Python module names.
#
#  The ModuleMapper class scans a project directory or selects one file and builds lookup
#  dictionaries that convert absolute file paths to dotted module names
#  (e.g. "pkg.sub.module") and vice versa.

import os
from .scanner import FileScanner
from .source_snapshot import ModuleIndex, module_name_for_path, OWNERSHIP_MODULES


## Bidirectional file-path-to-module-name mapper.
#
#  Scans a project root or selects one .py/.pyi file, and builds
#  dictionaries for translating between file paths and Python module paths.
class ModuleMapper:
    ## Initialize the mapper for a project directory or one Python source file.
    #  @param project_root Path to the project directory or a .py/.pyi file.
    def __init__(self, project_root):
        path = os.path.abspath(project_root)
        self._source_file = path if os.path.isfile(path) else None
        self.project_root = path
        if self._source_file:
            if not path.endswith(('.py', '.pyi')):
                raise ValueError('Source must be a .py or .pyi file: %s' % path)
            self.project_root = os.path.dirname(path)
            # Retain regular-package names without adding their other sources.
            while (os.path.isfile(os.path.join(self.project_root, '__init__.py'))
                   or os.path.isfile(os.path.join(self.project_root, '__init__.pyi'))):
                parent = os.path.dirname(self.project_root)
                if parent == self.project_root:
                    break
                self.project_root = parent
        self.file_to_module = {}
        self.module_to_file = {}
        self.package_modules = set()
        self._scanner = FileScanner()
        self._index = ModuleIndex.build((), [self.project_root], OWNERSHIP_MODULES)

    ## Discover selected sources and build the file <-> module mapping.
    #  @return List of discovered .py/.pyi file paths.
    def scan_project(self):
        py_files = ([self._source_file] if self._source_file
                    else self._scanner.scan(self.project_root))
        py_files = [f for f in py_files if f.endswith('.py') or f.endswith('.pyi')]
        self._index = ModuleIndex.build(py_files, [self.project_root], OWNERSHIP_MODULES)
        for entry in self._index.entries:
            self.file_to_module[entry.file_path] = entry.module_name
            self.module_to_file[entry.module_name] = entry.file_path
        self.package_modules.update(self._index.package_modules)
        return py_files

    ## Convert an absolute file path to a dotted module path.
    #  @param file_path Absolute path to a .py or .pyi file.
    #  @return Dotted module name, or empty string on failure.
    def _file_path_to_module_path(self, file_path):
        try:
            return module_name_for_path(file_path, [self.project_root], OWNERSHIP_MODULES)
        except Exception as e:
            raise ValueError(f"Failed to convert file path {file_path}: {e}")

    ## Get the module path for a given file path.
    #  @param file_path Absolute file path.
    #  @return Dotted module name, or empty string if not found.
    def get_module_path(self, file_path):
        return self.file_to_module.get(file_path, "")

    ## Get the file path for a given module path.
    #  @param module_path Dotted module name.
    #  @return Absolute file path, or empty string if not found.
    def get_file_path(self, module_path):
        return self.module_to_file.get(module_path, "")

    ## Return all known module paths.
    #  @return List of dotted module name strings.
    def get_all_modules(self):
        return list(self.module_to_file.keys())

    ## Return all known file paths.
    #  @return List of absolute file path strings.
    def get_all_files(self):
        return list(self.file_to_module.keys())

    ## Check whether a module path corresponds to a package (__init__.py).
    #  @param module_path Dotted module name.
    #  @return True if the module is a package.
    def is_package(self, module_path):
        return module_path in self.package_modules

    ## Resolve a simple module name to its full dotted name within the project.
    #
    #  When a package module imports a sibling via 'import data',
    #  the AST records only "data", but the full module name is "pkg.data".
    #  This method uses the context module's package prefix to find the
    #  full name in the known module set.
    #  @param name The simple module name (e.g. "data").
    #  @param context_module The full dotted name of the module where the
    #         import appears (e.g. "pkg.main").
    #  @return Full dotted module name if resolved, or the original name.
    def resolve_module_name(self, name, context_module=None):
        if not isinstance(name, str) or '.' in name:
            return name
        all_modules = self.get_all_modules()
        if name in all_modules:
            return name
        if context_module:
            parts = context_module.split('.')
            for i in range(len(parts) - 1, -1, -1):
                candidate = '.'.join(parts[:i + 1] + [name])
                if candidate in all_modules:
                    return candidate
        return name

    ## Clear all mappings and scanner state so the mapper can be reused.
    def clear(self):
        self.file_to_module.clear()
        self.module_to_file.clear()
        self.package_modules.clear()
        self._scanner.clc()
        self._index = ModuleIndex.build((), [self.project_root], OWNERSHIP_MODULES)
