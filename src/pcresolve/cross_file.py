## @package pcresolve.cross_file
#  Provide cross-file project-level API call chain analysis.
#
#  The ProjectAnalyzer class orchestrates scanning a project, parsing every
#  .py file, building per-file symbol tables, resolving symbols across files,
#  and collecting all API calls with their top-level library origins.

import ast
import os
import builtins
from .module_mapper import ModuleMapper
from .single_file import SingleFileAnalyzer
from .types import ProjectAnalysis, FileAnalysis, ApiCall


## Cross-file project analyzer that traces all API calls to their origins.
#
#  Steps:
#  1. Scan the project for all .py/.pyi files and map them to module names.
#  2. Parse each file and run SingleFileAnalyzer to build per-file symbol data.
#  3. Resolve cross-file symbol references across the project.
#  4. Classify every API call with its top-level library source.
class ProjectAnalyzer:
    ## Initialize the analyzer for a given project root.
    #  @param project_root Absolute path to the project root directory.
    def __init__(self, project_root):
        self.project_root = project_root
        self.module_mapper = ModuleMapper(project_root)
        self.global_symbols = {}
        self.symbol_chains = {}
        self.all_calls = {}

    ## Run the full analysis: scan, parse, resolve, and collect.
    #  @return ProjectAnalysis with all results.
    def analyze(self):
        self.module_mapper.scan_project()
        all_modules = self.module_mapper.get_all_modules()
        module_tracers = {}

        for module in all_modules:
            file_path = self.module_mapper.get_file_path(module)
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                tracer = SingleFileAnalyzer()
                tree = ast.parse(code)
                tracer.visit(tree)
                module_tracers[module] = tracer

        self.resolve_cross_file_symbols(module_tracers)
        self.get_calls(module_tracers)

        files = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            files.append(FileAnalysis(
                file_path=file_path,
                module_name=module,
                symbols=self.global_symbols.get(module, {}),
                chains=self.symbol_chains.get(module, {}),
                api_calls=[
                    ApiCall(
                        expression=c['api'],
                        top_library=c['top'],
                        base_symbol=str(c.get('base', '')),
                        chain=c.get('chain', []),
                    )
                    for c in self.all_calls.get(module, [])
                ],
            ))

        all_api_calls = []
        for module, calls in self.all_calls.items():
            for c in calls:
                all_api_calls.append(ApiCall(
                    expression=c['api'],
                    top_library=c['top'],
                    base_symbol=str(c.get('base', '')),
                    chain=c.get('chain', []),
                ))

        return ProjectAnalysis(
            project_root=self.project_root,
            files=files,
            all_api_calls=all_api_calls,
        )

    ## Check whether a module name belongs to the current project.
    #  @param module_name Dotted module name.
    #  @return True if the module is a local project module.
    def is_local(self, module_name):
        return module_name in self.module_mapper.get_all_modules()

    ## Collect all locally defined function names across all tracers.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Set of function names.
    def _total_defined_function_names(self, tracers):
        names = set()
        for t in tracers.values():
            names.update(getattr(t, "defined_functions", ()))
        return names

    ## Determine whether an API call should be classified as local.
    #
    #  A call is local if its base symbol or any link in its chain refers to
    #  a function defined within the project.
    #  @param module The module where the call appears.
    #  @param call_detail The call detail dict from the tracer.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return True if the call should be treated as local.
    def _ignore_api(self, module, call_detail, tracers):
        base = call_detail.get('base')
        tracer = tracers.get(module)
        if not tracer:
            return False
        if isinstance(base, tuple):
            return False
        all_local_funcs = self._total_defined_function_names(tracers)
        dn = call_detail.get('direct_name_callee')
        if dn:
            if dn in getattr(tracer, "defined_functions", set()):
                return True
            imp = tracer.import_from_symbols.get(dn)
            if imp and self.is_local(imp) and imp in tracers:
                src_tr = tracers[imp]
                if dn in getattr(src_tr, "defined_functions", set()):
                    return True
        if not isinstance(base, str):
            return False
        chain = self.symbol_chains.get(module, {}).get(base)
        if not chain:
            chain = call_detail.get("chain") or []
        for elem in chain:
            if isinstance(elem, str) and elem in all_local_funcs:
                return True
        return False

    ## Collect all API calls across all modules and resolve their top-level origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def get_calls(self, module_tracers):
        for module, tracer in module_tracers.items():
            self.all_calls[module] = []
            for call_detail in tracer.api_calls:
                if call_detail.get('top') == 'local':
                    self.all_calls[module].append({
                        'api': call_detail['api'],
                        'top': 'local',
                    })
                    continue
                if self._ignore_api(module, call_detail, module_tracers):
                    self.all_calls[module].append({
                        'api': call_detail['api'],
                        'top': 'local',
                    })
                    continue
                base = call_detail['base']
                if base in self.global_symbols.get(module, {}):
                    top_source = self.global_symbols[module][base]
                elif isinstance(base, tuple):
                    structured = self._resolve_structured_source(module, base, module_tracers)
                    if structured is not None:
                        _, src_module, src_symbol = structured
                        top_source = self._top_source(src_module, src_symbol, module_tracers)
                    else:
                        top_source = str(base)
                else:
                    top_source = self._top_source(module, base, module_tracers)
                call_record = {
                    'api': call_detail['api'],
                    'top': top_source
                }
                self.all_calls[module].append(call_record)

    ## Resolve cross-file symbol references across all modules.
    #
    #  For each symbol in each module, trace its source through imports
    #  and assignments to find the final origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def resolve_cross_file_symbols(self, module_tracers):
        for module, tracer in module_tracers.items():
            self.global_symbols[module] = {}
            self.symbol_chains[module] = {}
            for symbol, direct_source in tracer.symbols.direct.items():
                chain = self.trace_symbol(module, symbol, module_tracers, set())
                if chain:
                    final_source = self.extract_final_source(chain)
                    self.global_symbols[module][symbol] = final_source
                    self.symbol_chains[module][symbol] = chain

    ## Normalize a container index to its positive equivalent.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param key_idx Raw index (may be negative).
    #  @return Adjusted index.
    def _container_index(self, tracer, container_name, key_idx):
        if not isinstance(key_idx, int):
            return key_idx
        if key_idx >= 0:
            return key_idx
        n = tracer.container_lengths.get(container_name)
        if n is not None:
            return key_idx + n
        return key_idx

    ## Resolve a container item access to its source symbol.
    #
    #  Looks up the item in the current module's container_items, and falls
    #  back to cross-file import if not found locally.
    #  @param module The module where the access occurs.
    #  @param container_name Name of the container variable.
    #  @param key_idx The index/key being accessed.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_container_item(self, module, container_name, key_idx, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        container_idx = self._container_index(tracer, container_name, key_idx)
        item_key = (container_name, container_idx)
        if item_key in tracer.container_items:
            return (module, tracer.container_items[item_key])
        container_direct = tracer.symbols.direct.get(container_name)
        if self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            container_idx_src = self._container_index(src_tracer, container_name, key_idx)
            src_key = (container_name, container_idx_src)
            if src_key in src_tracer.container_items:
                return (src_module, src_tracer.container_items[src_key])
        return None

    ## Add a candidate to the list if not already visited.
    #  @param module The current module.
    #  @param src The source symbol.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param candidates List to append to.
    #  @param visited Set of already-visited origins.
    def _container_candidate(self, module, src, tracers, candidates, visited):
        if not src:
            return
        top_src = self._top_source(module, src, tracers)
        if top_src and top_src not in visited:
            visited.add(top_src)
            candidates.append(top_src)

    ## Collect all candidates for a container's iteration source.
    #  @param module The current module.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of candidate source symbols.
    def _collect_container_candidates(self, module, tracer, container_name, tracers):
        candidates = []
        visited = set()
        for (cont_name, idx), src in tracer.container_items.items():
            if cont_name == container_name:
                self._container_candidate(module, src, tracers, candidates, visited)
        for src in sorted(tracer.container_set_sources.get(container_name, set())):
            self._container_candidate(module, src, tracers, candidates, visited)
        return candidates

    ## Resolve an iteration over a container to its source(s).
    #  @param module The current module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, candidates_list) tuple, or None.
    def _resolve_container_iter(self, module, container_name, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        local_candidates = self._collect_container_candidates(module, tracer, container_name, tracers)
        if local_candidates:
            return (module, local_candidates)
        container_direct = tracer.symbols.direct.get(container_name)
        if isinstance(container_direct, str) and self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            src_candidates = self._collect_container_candidates(src_module, src_tracer, container_name, tracers)
            if src_candidates:
                return (src_module, src_candidates)
        return None

    ## Resolve a method call through class inheritance and cross-file imports.
    #
    #  Searches the class's method list, then recursively checks parent classes,
    #  following imports to other modules as needed.
    #  @param module The current module.
    #  @param class_symbol The class name.
    #  @param method_name The method being called.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, class, method) keys.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_method_symbol(self, module, class_symbol, method_name, tracers, visited):
        tracer = tracers.get(module)
        if not tracer:
            return None
        key = (module, class_symbol, method_name)
        if key in visited:
            return None
        visited.add(key)
        methods = tracer.class_methods.get(class_symbol, [])
        if method_name in methods:
            return (module, method_name)
        for base_symbol in tracer.class_bases.get(class_symbol, []):
            if base_symbol in tracer.class_methods:
                resolved = self._resolve_method_symbol(module, base_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            base_direct = tracer.symbols.direct.get(base_symbol)
            if isinstance(base_direct, str):
                if self.is_local(base_direct):
                    src_module = base_direct
                    resolved = self._resolve_method_symbol(src_module, base_symbol, method_name, tracers, visited)
                    if resolved:
                        return resolved
                else:
                    return (module, base_symbol)
        class_direct = tracer.symbols.direct.get(class_symbol)
        if isinstance(class_direct, str):
            if self.is_local(class_direct):
                src_module = class_direct
                resolved = self._resolve_method_symbol(src_module, class_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            else:
                return (module, class_symbol)
        return None

    ## Resolve a structured (tuple) source to its concrete origin.
    #
    #  Handles the three structured tuple kinds:
    #  - "container_item" for subscript access
    #  - "instance_method" for method calls
    #  - "container_iter" for iteration over containers
    #  @param module The current module.
    #  @param direct_source The structured tuple (kind, arg1, arg2).
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (display_name, src_module, src_symbol) tuple, or None.
    def _resolve_structured_source(self, module, direct_source, tracers):
        if not (isinstance(direct_source, tuple) and len(direct_source) == 3):
            return None
        kind, a, b = direct_source

        if kind == "container_item":
            resolved = self._resolve_container_item(module, a, b, tracers)
            if not resolved:
                return None
            src_module, src_symbol = resolved
            return (f"{a}[{b}]", src_module, src_symbol)

        if kind == "instance_method":
            tracer = tracers.get(module)
            if not tracer:
                return None
            class_symbol = tracer.symbols.direct.get(a)
            if a in tracer.class_methods and class_symbol == "local":
                class_symbol = a
            if not class_symbol:
                return None
            resolved = self._resolve_method_symbol(module, class_symbol, b, tracers, set())
            if not resolved:
                return None
            src_module, src_symbol = resolved
            return (f"{a}.{b}", src_module, src_symbol)

        if kind == "container_iter":
            resolved = self._resolve_container_iter(module, a, tracers)
            if not resolved:
                return None
            src_module, candidates = resolved
            if len(candidates) == 1:
                src_symbol = candidates[0]
            else:
                src_symbol = "[" + ",".join(candidates) + "]"
            return (f"{a}[*]", src_module, src_symbol)

        return None

    ## Recursively trace a symbol through cross-file imports to its origin.
    #
    #  Follows direct sources across module boundaries, handling
    #  structured sources (container items, instance methods, container iters)
    #  at each step.
    #  @param module The current module being traced from.
    #  @param symbol The symbol to trace.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, symbol) pairs.
    #  @return Ordered chain list from symbol to origin.
    def trace_symbol(self, module, symbol, tracers, visited):
        if (module, symbol) in visited:
            return []
        visited.add((module, symbol))
        tracer = tracers.get(module)
        if not tracer:
            return []
        direct_source = tracer.symbols.direct.get(symbol)
        if not direct_source:
            return [symbol]

        structured = self._resolve_structured_source(module, direct_source, tracers)
        if structured is not None:
            display_name, src_module, src_symbol = structured
            sub_chain = self.trace_symbol(src_module, src_symbol, tracers, visited)
            if sub_chain:
                return [symbol, display_name] + sub_chain
            return [symbol, display_name, src_symbol]

        if isinstance(direct_source, tuple):
            return [symbol, str(direct_source)]

        if self.is_local(direct_source):
            sub_chain = self.trace_symbol(direct_source, symbol, tracers, visited)
            if sub_chain:
                return [symbol, direct_source] + sub_chain
            else:
                return [symbol, direct_source]
        elif direct_source in tracer.symbols.direct:
            sub_chain = self.trace_symbol(module, direct_source, tracers, visited)
            if sub_chain:
                return [symbol] + sub_chain
            else:
                return [symbol, direct_source]
        else:
            return [symbol, direct_source]

    ## Extract the top-level name from a dotted name string.
    #  @param name Possibly dotted name.
    #  @return The first component before a dot.
    def _top_name(self, name):
        if isinstance(name, str) and "." in name:
            return name.split(".")[0]
        return name

    ## Resolve a symbol to its top-level source library.
    #
    #  Traces through the chain and returns the top-level name, or "python"
    #  for builtins.
    #  @param src_module The module where the symbol is referenced.
    #  @param symbol The symbol to resolve.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name (e.g. "requests", "python").
    def _top_source(self, src_module, symbol, tracers):
        if not symbol:
            return None
        if isinstance(symbol, str) and hasattr(builtins, symbol):
            return "python"
        chain = self.trace_symbol(src_module, symbol, tracers, set())
        if chain:
            return self.extract_final_source(chain)
        src_tracer = tracers.get(src_module)
        if src_tracer:
            top = src_tracer.symbols.get_top(symbol)
            if top:
                return self._top_name(top)
        return self._top_name(symbol)

    ## Extract the ultimate source from a resolution chain.
    #
    #  Walks the chain in reverse; the first non-local, non-builtin element
    #  is the top-level library.
    #  @param chain The resolution chain list.
    #  @return Final source string.
    def extract_final_source(self, chain):
        if not chain:
            return ""
        for item in reversed(chain):
            if isinstance(item, str) and hasattr(builtins, item):
                return "python"
            if isinstance(item, str) and not self.is_local(item):
                return self._top_name(item)
        return chain[-1]


## Analyze an entire project and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Absolute path to the project root directory.
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root):
    analyzer = ProjectAnalyzer(project_root)
    return analyzer.analyze()
