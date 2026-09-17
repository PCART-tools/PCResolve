## @package pcresolve.source_snapshot
#  Internal source versions, read-only AST snapshots, and module naming facts.
#  Call-target resolution and propagation policies belong to the consumers.

import ast
import hashlib
import os
from dataclasses import dataclass
from types import MappingProxyType


## Decode policy retained by the existing public analysis adapters.
@dataclass(frozen=True)
class SourceReadPolicy:
    encoding: str


OWNERSHIP_SOURCE = SourceReadPolicy('utf-8')
FLOW_SOURCE = SourceReadPolicy('utf-8-sig')
OWNERSHIP_MODULES = 'ownership_compatibility'
FLOW_MODULES = 'flow_compatibility'


## One decoded file version and its parse result, independent of analysis summaries.
#  AST nodes are read-only by convention; visitors must never annotate or modify them.
@dataclass(frozen=True)
class SourceDocument:
    file_path: str
    text: object = None
    sha256: str = ''
    tree: object = None
    error: object = None
    error_stage: str = ''


## Captured source set; later reads do not change its documents or AST versions.
@dataclass(frozen=True)
class SourceSnapshot:
    files: tuple
    documents: object
    policy: SourceReadPolicy


## Session-local source reader and parser cache, with no process-global state.
#  Every capture rereads content. Size and mtime cannot establish source identity.
#  Only the latest requested version per file is cached; previous snapshots retain
#  their own document references. Equal decoded text can reuse ASTs across policies.
class SourceStore:
    ## Initialize an empty source cache.
    def __init__(self):
        self._cache = {}

    ## Capture files in caller-selected order without discovering extra sources.
    #  @param files Source paths chosen by the consumer's input policy.
    #  @param policy Decode policy; text-mode universal newlines remain unchanged.
    #  @return Read-only snapshot, including read and syntax failures per file.
    def snapshot(self, files, policy):
        paths = tuple(files)
        documents, next_cache = {}, {}
        for path in paths:
            try:
                with open(path, encoding=policy.encoding) as stream:
                    text = stream.read()
            except (OSError, UnicodeError) as error:
                documents[path] = SourceDocument(path, error=error.with_traceback(None),
                                                 error_stage='read')
                continue
            cached = self._cache.get(path)
            if cached is not None and cached.text == text:
                document = cached
            else:
                digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
                try:
                    # Keep the existing '<unknown>' parse filename in diagnostics.
                    tree = ast.parse(text)
                except SyntaxError as error:
                    document = SourceDocument(path, text, digest,
                                              error=error.with_traceback(None), error_stage='parse')
                else:
                    document = SourceDocument(path, text, digest, tree)
            documents[path] = next_cache[path] = document
        self._cache = next_cache
        return SourceSnapshot(paths, MappingProxyType(documents), policy)


## Derive a module name without reading or importing the file.
#  Compatibility policies preserve current root-package and stub naming behavior.
#  @param path Source file path.
#  @param roots Ordered import roots; flow falls back to the file's directory.
#  @param policy Existing adapter's module naming policy.
#  @return Dotted module name, or empty for ownership's omitted root package.
def module_name_for_path(path, roots, policy):
    if policy == OWNERSHIP_MODULES:
        relative = os.path.relpath(path, roots[0])
        if relative == os.path.basename(path):
            name = relative.replace('.py', '').replace('.pyi', '')
            return name if name != '__init__' else ''
        directory = os.path.dirname(relative)
        name = os.path.basename(relative).replace('.py', '').replace('.pyi', '')
        module = directory.replace(os.sep, '.')
        if name != '__init__':
            module += '.' + name
        if os.altsep:
            module = module.replace(os.altsep, '.')
        return module
    if policy != FLOW_MODULES:
        raise ValueError('Unknown module naming policy: ' + str(policy))
    root = next((r for r in roots if os.path.commonpath([r, path]) == r), os.path.dirname(path))
    module = os.path.splitext(os.path.relpath(path, root))[0].replace(os.sep, '.')
    return module[:-9] if module.endswith('.__init__') else module


## One file-to-module candidate, including package syntax independently of imports.
@dataclass(frozen=True)
class ModuleSource:
    file_path: str
    module_name: str
    is_package: bool


## Read-only module facts retaining every candidate and the adapter's last-file lookup.
#  This index supplies no callee identity or import-resolution judgment.
@dataclass(frozen=True)
class ModuleIndex:
    entries: tuple
    file_to_module: object
    module_to_file: object
    package_modules: frozenset

    ## Build facts for exactly the supplied files, preserving their order.
    #  @param files Selected Python sources, already normalized by the caller.
    #  @param roots Ordered import roots.
    #  @param policy Existing module naming policy.
    #  @return Index with immutable lookups and all nonempty module candidates.
    @classmethod
    def build(cls, files, roots, policy):
        entries, file_to_module, module_to_file, packages = [], {}, {}, set()
        for path in files:
            module = module_name_for_path(path, roots, policy)
            if not module:
                continue
            name = os.path.basename(path)
            is_package = (name == '__init__.py' if policy == OWNERSHIP_MODULES
                          else name.startswith('__init__.'))
            entries.append(ModuleSource(path, module, is_package))
            file_to_module[path] = module
            module_to_file[module] = path
            if is_package:
                packages.add(module)
        return cls(tuple(entries), MappingProxyType(file_to_module),
                   MappingProxyType(module_to_file), frozenset(packages))
