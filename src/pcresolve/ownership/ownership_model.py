## @package pcresolve.ownership.ownership_model
#  Own one ownership analysis run.
#
#
#  Explicit internal state for one ownership analysis run.
#  单次归属分析运行使用的显式内部状态。



from collections import namedtuple
from functools import wraps

from pcresolve.ownership.call_graph import ProjectCallGraph
from pcresolve.ownership.ast_facts import AstFactIndex
from pcresolve.facts.call_resolution import DefinitionIndex, DefinitionRecord


## Work budget shared by mutually recursive ownership proof queries.
## 相互递归的归属证明查询共享的工作预算。
class OwnershipProofBudget:
    def __init__(self, max_queries=4096, max_depth=32, depth=0, queries=0, exhausted=False):
        ## Maximum query entries in one independent proof.
        self.max_queries = max_queries
        ## Maximum nested query entries, independent of Python's stack limit.
        self.max_depth = max_depth
        ## Current nesting depth.
        self.depth = depth
        ## Query entries consumed by the active proof.
        self.queries = queries
        ## Whether any part of the active proof exceeded its limits.
        self.exhausted = exhausted


## Bound cross-resolver work and discard proofs with incomplete candidates.
## 限制跨解析器工作量，并丢弃候选不完整的证明。
#
#  @param fallback Factory producing the query's conservative unknown result.
#  @return Decorator sharing one budget across nested ownership queries.


def bounded_ownership_query(fallback
                            ):
    ## Wrap a query with the shared proof budget.
    ## 使用共享证明预算包装查询。
    #
    #  @param query Ownership query to wrap.
    #  @return Budget-aware query.
    def decorate(query
                 ):
        ## Enforce budget limits across nested calls to the query.
        ## 在嵌套查询中执行共享预算限制。
        #
        #  @param args Positional arguments forwarded to the query.
        #  @param kwargs Keyword arguments forwarded to the query.
        #  @return Query result or conservative fallback after exhaustion.
        @wraps(query)
        def bounded(self, /, *args,
                    **kwargs):
            resources = getattr(self, '_analysis_budget', None)
            if resources is not None:
                resources.checkpoint()
            budget = self._ownership_proof_budget
            if budget.depth == 0:
                budget.queries = 0
                budget.exhausted = False
            if (budget.exhausted or budget.queries >= budget.max_queries
                    or budget.depth >= budget.max_depth):
                budget.exhausted = True
                return fallback()
            budget.depth += 1
            budget.queries += 1
            try:
                result = query(self, *args, **kwargs)
                # A cutoff in a nested candidate must invalidate the outer
                # proof too; a surviving subset cannot establish convergence.
                # 嵌套候选触及限制时，剩余子集无法证明整体收敛。
                return fallback() if budget.exhausted else result
            finally:
                budget.depth -= 1
        return bounded
    return decorate


## Immutable project inputs observed by one ownership analysis run.
## 单次归属分析运行观察到的不可变项目输入。
ProjectSnapshot = namedtuple(
    'ProjectSnapshot', ('modules', 'sources'))


## Mutable program facts assembled during one ownership analysis run.
## 单次归属分析运行中组装的可变程序事实。
class ProgramIndex:
    def __init__(self, module_tracers=None, call_graph=None):
        ## Per-module single-file analyzers, preserving discovery order.
        self.module_tracers = dict() if module_tracers is None else module_tracers
        ## Project call graph backed by the tracers' module summaries.
        self.call_graph = ProjectCallGraph() if call_graph is None else call_graph

    def add_module(self, module, tracer):
        self.module_tracers[module] = tracer
        graph = tracer.module_cg
        if (graph.functions or graph.classes or graph.edges
                or graph.iteration_bindings):
            self.call_graph.modules[module] = graph


class MethodResultIndex:
    def __init__(self, graph, generation, data):
        # Index validity depends on both graph identity and structural version.
        self.graph = graph
        self.generation = generation
        self.data = data


class OwnershipDefinitionIndex:
    def __init__(self, graph, generation, definitions, target_names):
        # Candidate names and definition records share one graph generation.
        self.graph = graph
        self.generation = generation
        self.definitions = definitions
        self.target_names = target_names


def build_ownership_definition_index(
        graph,
        metadata,
        ):
    # Definition records and name buckets are assembled for one graph version.
    generation = graph.version
    records = []
    for module, module_graph in graph.modules.items():
        for kind, summaries in (('function', module_graph.functions), ('class', module_graph.classes)):
            records.extend(DefinitionRecord(module, qualname, summary, kind, summary.definition_span)
                           for qualname, summary in summaries.items())
    definitions = DefinitionIndex(tuple(records))
    target_names = {}
    for ordinal, record in enumerate(definitions.records):
        if record.kind != 'function':
            continue
        target = metadata(record.module, record.qualname)
        if target is None:
            raise ValueError('definition module is missing from its call graph')
        _, class_name, name, constructor, _ = target
        target_names.setdefault(class_name if constructor else name, []).append(ordinal)
    if graph.version != generation:
        raise RuntimeError('call graph changed during definition indexing')
    return OwnershipDefinitionIndex(graph, generation, definitions, target_names)


class OwnershipEdgeIndex:
    def __init__(self, graph, generation, data, edge_names, ordinals, scopes, positions):
        # All buckets describe the same graph identity and structural generation.
        self.graph = graph
        self.generation = generation
        self.data = data
        self.edge_names = edge_names
        self.ordinals = ordinals
        self.scopes = scopes
        self.positions = positions


def build_ownership_edge_index(graph,
                               edge_names_for):
    # Retain the initial generation so a changed graph cannot reuse this index.
    generation = graph.version
    edges = []
    names = {}
    mapped = []
    sites = {}
    edge_names = {}
    ordinals = {}
    scopes = {}
    positions = {}
    for module, module_graph in graph.modules.items():
        for edge in module_graph.edges:
            ordinal = len(edges)
            edges.append((module, edge))
            ordinals[id(edge)] = ordinal
            edge_names[ordinal] = edge_names_for(edge)
            for name in edge_names[ordinal]:
                names.setdefault(name, set()).add(ordinal)
            is_mapped = getattr(edge, 'mapping_targets', None) is not None
            if is_mapped:
                mapped.append(ordinal)
            sites.setdefault((module, edge.call_lineno, edge.call_col_offset), []).append(edge)
            scopes.setdefault((module, edge.caller.qualname), []).append(edge)
            positions[ordinal] = (edge.caller.qualname, edge.call_lineno, edge.call_col_offset, is_mapped)
    if graph.version != generation:
        raise RuntimeError('call graph changed during edge indexing')
    return OwnershipEdgeIndex(graph, generation, (edges, names, mapped, sites),
                              edge_names, ordinals, scopes, positions)


class OwnershipCallableIndex:
    def __init__(self, graph, generation, static_classes=None, indexed_edges=None,
                 reverse_lookup=None):
        # Candidate cache and reverse index belong to one graph generation.
        self.graph = graph
        self.generation = generation
        self.static_classes = dict() if static_classes is None else static_classes
        self.indexed_edges = indexed_edges
        self.reverse_lookup = reverse_lookup


## Mutable orchestration state owned by one ProjectAnalyzer.analyze() call.
## 单次 ProjectAnalyzer.analyze() 调用拥有的可变编排状态。
class OwnershipRun:
    def __init__(self, snapshot, program=None, diagnostics=None, global_symbols=None,
                 symbol_chains=None, all_calls=None, python_shape_in_progress=None,
                 callable_field_in_progress=None, edge_target_in_progress=None,
                 proof_budget=None, analysis_budget=None, constructor_only_fields=None, method_result_index=None,
                 definition_index=None, edge_index=None, callable_index=None):
        ## Read-only AST lookup facts owned by this source generation.
        self.ast_facts = AstFactIndex()
        ## Completed readonly proofs; recursive failures are never memoized.
        self.readonly_proofs = set()
        ## Number of unmodified files whose pristine visitor facts were reused.
        self.source_facts_reused = 0
        ## Fixed module and source inputs for the run.
        self.snapshot = snapshot
        ## Cooperative budget shared by all phases of this analysis generation.
        self.analysis_budget = analysis_budget
        ## Tracers and project-wide indexes built from the snapshot.
        self.program = ProgramIndex() if program is None else program
        ## Diagnostics emitted while consuming the snapshot.
        self.diagnostics = list() if diagnostics is None else diagnostics
        ## Cross-file symbol lookup table built during resolution.
        self.global_symbols = dict() if global_symbols is None else global_symbols
        ## Explanation chains corresponding to global symbol resolutions.
        self.symbol_chains = dict() if symbol_chains is None else symbol_chains
        ## Classified call records grouped by module.
        self.all_calls = dict() if all_calls is None else all_calls
        ## Active Python-shape queries used to stop recursive resolution cycles.
        self.python_shape_in_progress = set() if python_shape_in_progress is None else python_shape_in_progress
        ## Active callable-field queries used to stop recursive resolution cycles.
        self.callable_field_in_progress = set() if callable_field_in_progress is None else callable_field_in_progress
        ## Active call-edge target queries, including receiver provenance lookup.
        self.edge_target_in_progress = set() if edge_target_in_progress is None else edge_target_in_progress
        ## Fresh cross-resolver proof limits for this analysis generation.
        self.proof_budget = OwnershipProofBudget() if proof_budget is None else proof_budget
        ## Lazily computed fields whose writes are confined to constructors.
        self.constructor_only_fields = constructor_only_fields
        ## Lazily built index whose lifetime is limited to this run.
        self.method_result_index = method_result_index
        ## Definition candidates indexed for this run's call graph.
        self.definition_index = definition_index
        ## Indexed call edges for this run's call graph.
        self.edge_index = edge_index
        ## Callable candidates and reverse lookup for this run's graph.
        self.callable_index = callable_index
