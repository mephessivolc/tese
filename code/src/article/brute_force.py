import itertools

def tsp_bruteforce(dist):
    n = len(dist)
    vertices = list(range(1, n))
    best_cost = float('inf')
    best_path = None

    for perm in itertools.permutations(vertices):
        path = (0,) + perm + (0,)
        cost = 0

        for i in range(len(path) - 1):
            cost += dist[path[i]][path[i + 1]]

        if cost < best_cost:
            best_cost = cost
            best_path = path

    return best_cost, best_path

if __name__ == "__main__":
    from graphs import GraphBuilder
    n = 4
    graph = GraphBuilder(n)
    best_cost, best_path = tsp_bruteforce(graph.matrix)
    print(f"Best Cost:{best_cost}\tBest Path: {best_path}")