import itertools
from typing import List, Tuple, Dict
import numpy as np


def tsp_bruteforce_all(dist: np.ndarray) -> Tuple[float, List[Tuple[int, ...]], Dict[Tuple[int, ...], float]]:
    """
    Executa a busca exaustiva (CA) para o TSP e mapeia todo o espaço de soluções.

    Parameters
    ----------
    dist : np.ndarray
        Matriz de adjacência/distâncias do grafo (n x n).

    Returns
    -------
    best_cost : float
        Custo mínimo absoluto (energia fundamental real).
    optimal_paths : List[Tuple[int, ...]]
        Lista com TODAS as rotas que atingem o custo mínimo.
    all_solutions : Dict[Tuple[int, ...], float]
        Dicionário mapeando cada rota possível ao seu respetivo custo (espectro de energia).
    """
    n = len(dist)
    vertices = list(range(1, n))
    
    best_cost = float('inf')
    optimal_paths = []
    all_solutions = {}

    # Percorre as (N-1)! permutações das cidades intermediárias
    for perm in itertools.permutations(vertices):
        path = (0,) + perm + (0,)
        
        # Calcula o custo total da rota
        cost = sum(dist[path[i]][path[i + 1]] for i in range(len(path) - 1))
        
        all_solutions[path] = cost

        # Atualiza conjunto de melhores soluções
        if cost < best_cost:
            best_cost = cost
            optimal_paths = [path]  # Reinicia a lista com a nova melhor rota
        elif np.isclose(cost, best_cost):
            optimal_paths.append(path)  # Adiciona rotas empatadas no custo mínimo

    return best_cost, optimal_paths, all_solutions


if __name__ == "__main__":
    from graphs import GraphBuilder

    n = 4
    graph = GraphBuilder(n, seed=42)

    print("--- MATRIZ DE ADJACÊNCIA ---")
    print(graph.matrix)
    print("----------------------------\n")

    best_cost, optimal_paths, all_solutions = tsp_bruteforce_all(graph.matrix)

    print(f"Custo Mínimo (E0): {best_cost}")
    print(f"Quantidade de Rotas Ótimas: {len(optimal_paths)}")
    print("Rotas Ótimas Encontradas:")
    for path in optimal_paths:
        print(f"  -> {path}")

    print("\n--- ESPECTRO COMPLETO DE SOLUÇÕES (Ranking) ---")
    # Ordena o dicionário de soluções pelo custo crescente
    sorted_solutions = sorted(all_solutions.items(), key=lambda x: x[1])
    for path, cost in sorted_solutions:
        print(f"Rota: {path} | Custo: {cost}")