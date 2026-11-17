## @package pcresolve.frontend.source_snapshot
#  Internal source versions, read-only AST snapshots, and module naming facts.
#  Call-target resolution and propagation policies belong to the consumers.
#  保存源码版本、只读语法树快照和模块命名事实；调用解析由使用方负责。

import ast
import hashlib
import os
import tokenize
from dataclasses import dataclass
from types import MappingProxyType
from pcresolve.frontend.source_syntax import parse_python_source


## Decode policy retained by the existing public analysis adapters.
## 现有公开分析适配器使用的源码解码策略。
@dataclass(frozen=True)
class SourceReadPolicy:
    ## Encoding name, or 'tokenize' for Python's declared source encoding.
    encoding: str
    legacy_keyword_attributes: bool = False


OWNERSHIP_SOURCE = SourceReadPolicy('utf-8')
FLOW_SOURCE = SourceReadPolicy('utf-8-sig', legacy_keyword_attributes=True)
OWNERSHIP_MODULES = 'ownership_compatibility'
FLOW_MODULES = 'flow_compatibility'


## One decoded file version and its parse result, independent of analysis summaries.
## 单个文件的解码版本及解析结果，独立于分析摘要。
#  AST nodes are read-only by convention; visitors must never annotate or modify them.
@dataclass(frozen=True)
class SourceDocument:
    file_path: str
    text: object = None
    sha256: str = ''
    tree: object = None
    error: object = None
    error_stage: str = ''
    syntax_features: tuple = ()


## Captured source set; later reads do not change its documents or AST versions.
## 已捕获的源码集合；后续读取不会改变其中的文档和语法树版本。
@dataclass(frozen=True)
class SourceSnapshot:
    files: tuple
    documents: object
    policy: SourceReadPolicy


## Session-local source reader and parser cache, with no process-global state.
## 会话内源码读取器和解析缓存，不使用进程全局状态。
#  Every capture rereads content. Size and mtime cannot establish source identity.
#  Only the latest requested version per file is cached; previous snapshots retain
#  their own document references. Equal decoded text can reuse ASTs across policies.
class SourceStore:
    ## Initialize an empty source cache.
    ## 初始化空的源码缓存。
    #
    #  @return None
    def __init__(self):
        self._cache = {}
        self._cache_policies = {}

    ## Capture files in caller-selected order without discovering extra sources.
    ## 按调用方选定的顺序捕获文件，不额外发现源码。
    #
    #  @param files Source paths chosen by the consumer's input policy.
    #  @param policy Decode policy; text-mode universal newlines remain unchanged.
    #  @param budget Optional cooperative resource checks during reads.
    #  @return Read-only snapshot, including read and syntax failures per file.
    def snapshot(self, files, policy, budget=None):
        paths = tuple(files)
        documents, next_cache = {}, {}
        for path in paths:
            document = self.read_document(path, policy, budget)
            documents[path] = document
            if document.error_stage != 'read':
                next_cache[path] = document

        # Retain only the latest selected set; older snapshots keep their documents.
        # 缓存仅保留本次选定集合；旧快照仍持有各自的文档。
        self._cache = next_cache
        self._cache_policies = {path: policy for path in next_cache}
        return SourceSnapshot(paths, MappingProxyType(documents), policy)

    ## Read one document without changing the caller's selected source set.
    ## 读取单个文档，不改变调用方选定的源码集合。
    #
    #  @param path Absolute source path; consumers retain their own scope policy.
    #  @param policy Explicit decoding and historical syntax compatibility policy.
    #  @param budget Optional cooperative resource checks, including on cache hits.
    #  @return SourceDocument refreshed by content, with a reusable read-only AST.
    def read_document(self, path, policy, budget=None):
        if budget is not None:
            budget.checkpoint(force=True)
        try:
            reader = tokenize.open(path) if policy.encoding == 'tokenize' else open(
                path, encoding=policy.encoding)
            with reader as stream:
                text = stream.read()
            if budget is not None:
                budget.checkpoint(force=True)
        except (OSError, UnicodeError, SyntaxError) as error:
            self._cache.pop(path, None)
            self._cache_policies.pop(path, None)
            return SourceDocument(path, error=error.with_traceback(None), error_stage='read')

        # Reuse a tree only when both content and syntax compatibility permit it.
        # 仅在内容相同且语法策略兼容时复用语法树。
        cached = self._cache.get(path)
        reusable = (self._cache_policies.get(path) == policy
                    or cached is not None and cached.tree is not None
                    and (not cached.syntax_features or policy.legacy_keyword_attributes))
        if cached is not None and cached.text == text and reusable:
            document = cached
        else:
            digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
            try:
                # Keep the existing '<unknown>' parse filename in diagnostics.
                tree = ast.parse(text)
            except SyntaxError as error:
                document = SourceDocument(path, text, digest,
                                          error=error.with_traceback(None), error_stage='parse')
                if policy.legacy_keyword_attributes:
                    try:
                        tree = parse_python_source(text)
                    except SyntaxError:
                        pass
                    else:
                        document = SourceDocument(path, text, digest, tree,
                            syntax_features=('legacy_keyword_attributes',))
            else:
                document = SourceDocument(path, text, digest, tree)

        # A stricter syntax consumer can reject this same source version while
        # a historical-syntax consumer still owns a valid AST. Keep that AST's
        # identity for later compatible reads; return the strict failure as-is.
        # 严格策略可能拒绝旧语法；保留已有语法树供兼容策略复用。
        if (document.error is not None and cached is not None
                and cached.tree is not None and cached.text == text):
            return document
        self._cache[path] = document
        self._cache_policies[path] = policy
        return document


## Derive a module name without reading or importing the file.
## 不读取或导入文件，直接推导其模块名。
#  Compatibility policies preserve current root-package and stub naming behavior.
#
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

    # The flow adapter retains its separate root and package naming policy.
    # 数据流适配器保留独立的根目录和包命名策略。
    if policy != FLOW_MODULES:
        raise ValueError('Unknown module naming policy: ' + str(policy))
    root = os.path.dirname(path)
    for candidate in roots:
        try:
            contains = os.path.commonpath([candidate, path]) == candidate
        except ValueError:
            # Windows paths on different drives cannot have a common path.
            contains = False
        if contains:
            root = candidate
            break
    module = os.path.splitext(os.path.relpath(path, root))[0].replace(os.sep, '.')
    return module[:-9] if module.endswith('.__init__') else module


## One file-to-module candidate, including package syntax independently of imports.
## 单个文件到模块的候选映射及其包语法事实，不依赖导入解析。
@dataclass(frozen=True)
class ModuleSource:
    file_path: str
    module_name: str
    is_package: bool


## Read-only module facts retaining every candidate and the adapter's last-file lookup.
## 保留全部候选项及适配器末文件查找结果的只读模块事实。
#  This index supplies no callee identity or import-resolution judgment.
@dataclass(frozen=True)
class ModuleIndex:
    entries: tuple
    file_to_module: object
    module_to_file: object
    package_modules: frozenset

    ## Build facts for exactly the supplied files, preserving their order.
    ## 按给定顺序为所选文件构建模块事实。
    #
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
            # Preserve every entry above while the lookup retains the last collision.
            # 候选列表保留所有条目，查找表对同名项保留最后一个。
            module_to_file[module] = path
            if is_package:
                packages.add(module)
        return cls(tuple(entries), MappingProxyType(file_to_module),
                   MappingProxyType(module_to_file), frozenset(packages))
