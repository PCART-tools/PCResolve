import time
import networkx as nx
import tsplib95
from memory_profiler import memory_usage

def christofides(graph):
    start = time.time()

    # minimum spanning tree
    minSpanTree = nx.minimum_spanning_tree(graph)

    # find nodes with odd degree in MST
    vertexDegrees = nx.degree(minSpanTree)
    oddDegreeVertices = [x[0] for x in vertexDegrees if vertexDegrees[x[0]] % 2 == 1]

    # create subgraph of odd degree nodes
    oddVertexSubgraph = nx.subgraph(graph, oddDegreeVertices)

    # find minimum weight matching
    minWeightMatching = list(nx.min_weight_matching(oddVertexSubgraph, maxcardinality=True))

    # combine MST and matching
    combinedGraph = nx.MultiGraph(minSpanTree)
    for edge in minWeightMatching:
        combinedGraph.add_edge(edge[0], edge[1], weight=graph[edge[0]][edge[1]]['weight'])

    # find Eulerian circuit
    eulerianCircuit = list(nx.eulerian_circuit(combinedGraph, source=1))
   
    visited = set()
    hamiltonianPath = []
    totalWeight = 0

    for u, v in eulerianCircuit:
        if u not in visited:
            hamiltonianPath.append(u)
            visited.add(u)
            if len(hamiltonianPath) > 1:
                totalWeight += graph[hamiltonianPath[-2]][u]['weight']

    # Fechando o ciclo e adicionando o peso da última aresta
    hamiltonianPath.append(hamiltonianPath[0])
    totalWeight += graph[hamiltonianPath[-2]][hamiltonianPath[-1]]['weight']

    end = time.time()
    executionTime = end - start

    return totalWeight, hamiltonianPath, executionTime

# tests
if __name__ == "__main__":
    problem = tsplib95.load('lib/eil51.tsp')
    graph = problem.get_graph()
    # mem_usage, retval= memory_usage((christofides, (graph,)), retval=True, max_usage=True)
    # peak_memory = mem_usage
    weight, path, executionTime = christofides(graph)
    print("Peso total:", weight)
    print("Caminho:", path)
    print("Tempo de execução:", executionTime)