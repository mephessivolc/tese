"""
    Model class for solution of TSP using MTZ method
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, List, Optional, Tuple

import networkx as nx
import pulp


@dataclass
class TSPSolution:
    tour: List[Hashable]  # cyclic order starting at `start`, ends with start repeated
    cost: float
    y: Dict[Tuple[Hashable, Hashable], int]
    u: Dict[Hashable, int]


def solve_tsp_mtz_ilp(
    G: nx.DiGraph | nx.Graph,
    start: Optional[Hashable] = None,
    weight: str = "weight",
    time_limit_s: Optional[int] = None,
    msg: bool = False,
) -> TSPSolution:
    """
    Solve TSP via ILP with MTZ constraints (position u_i and edges y_ij)

    Requisitos:
      - G deve ter custo para todo par i!=j (grafo completo dirigido ou não-dirigido com custos).
      - Pesos em G[u][v][weight] (default: 'weight').

    Retorna:
      - tour cíclico: [start, ..., start]
      - custo total
      - dicionários de y_ij e u_i (valores inteiros)
    """
    if G.number_of_nodes() < 2:
        nodes = list(G.nodes())
        if not nodes:
            return TSPSolution(tour=[], cost=0.0, y={}, u={})
        return TSPSolution(tour=[nodes[0], nodes[0]], cost=0.0, y={}, u={nodes[0]: 1})

    nodes = list(G.nodes())
    n = len(nodes)

    if start is None:
        start = nodes[0]
    if start not in G:
        raise ValueError("`start` não está no grafo.")

    other_nodes = [v for v in nodes if v != start]

    def edge_cost(i: Hashable, j: Hashable) -> float:
        """Retorna o custo c_ij. Exige aresta/custo para todo par i!=j."""
        if i == j:
            raise ValueError("Custo c(i,i) não é definido.")
        if G.has_edge(i, j):
            data = G.get_edge_data(i, j)
            if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)):
                return float(min(attrs.get(weight, 1.0) for attrs in data.values()))
            return float(data.get(weight, 1.0))
        # Para Graph (não-direcionado), pode estar armazenado como (j,i)
        if isinstance(G, nx.Graph) and G.has_edge(j, i):
            data = G.get_edge_data(j, i)
            if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)):
                return float(min(attrs.get(weight, 1.0) for attrs in data.values()))
            return float(data.get(weight, 1.0))
        raise ValueError(
            f"Falta aresta/custo para o par ({i},{j}). "
            "O modelo requer grafo completo (custos para todos i!=j)."
        )

    # -----------------------
    # Modelagem ILP (MTZ)
    # -----------------------
    prob = pulp.LpProblem("TSP_MTZ", pulp.LpMinimize)

    # y_ij binárias
    y: Dict[Tuple[Hashable, Hashable], pulp.LpVariable] = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            y[(i, j)] = pulp.LpVariable(f"y_{i}_{j}", lowBound=0, upBound=1, cat=pulp.LpBinary)

    # u_i inteiras (posição). Fixamos u[start]=1.
    u: Dict[Hashable, pulp.LpVariable] = {}
    u[start] = pulp.LpVariable(f"u_{start}", lowBound=1, upBound=1, cat=pulp.LpInteger)
    for v in other_nodes:
        u[v] = pulp.LpVariable(f"u_{v}", lowBound=2, upBound=n, cat=pulp.LpInteger)

    # Objetivo
    prob += pulp.lpSum(edge_cost(i, j) * y[(i, j)] for i in nodes for j in nodes if i != j)

    # Grau: 1 saída de cada i
    for i in nodes:
        prob += pulp.lpSum(y[(i, j)] for j in nodes if j != i) == 1, f"out_{i}"

    # Grau: 1 entrada em cada j
    for j in nodes:
        prob += pulp.lpSum(y[(i, j)] for i in nodes if i != j) == 1, f"in_{j}"

    # MTZ: elimina subtours (aplica apenas para i,j != start)
    # u_i - u_j + n*y_ij <= n-1  para i!=j, i,j ∈ V\{start}
    for i in other_nodes:
        for j in other_nodes:
            if i == j:
                continue
            prob += u[i] - u[j] + n * y[(i, j)] <= n - 1, f"mtz_{i}_{j}"

    # Solver
    solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit_s)
    status = prob.solve(solver)
    status_name = pulp.LpStatus.get(status, str(status))

    if status_name not in ("Optimal", "Feasible", "Integer Feasible"):
        raise RuntimeError(f"Solver status: {status_name}")

    # -----------------------
    # Extração robusta (evita None)
    # -----------------------
    y_sol: Dict[Tuple[Hashable, Hashable], int] = {}
    for (i, j), var in y.items():
        val = var.value()
        if val is None:
            raise RuntimeError(
                f"Variável y[{i},{j}] sem valor (None). Status={status_name}. "
                f"Use msg=True para ver o log do solver."
            )
        y_sol[(i, j)] = int(round(val))

    u_sol: Dict[Hashable, int] = {}
    for v, var in u.items():
        val = var.value()
        if val is None:
            # caso típico: variável fixada (u[start]) pode vir sem varValue
            if v == start:
                val = 1
            else:
                raise RuntimeError(
                    f"Variável u[{v}] sem valor (None). Status={status_name}. "
                    f"Use msg=True para ver o log do solver."
                )
        u_sol[v] = int(round(val))

    # -----------------------
    # Reconstrução do tour via sucessor
    # -----------------------
    succ: Dict[Hashable, Hashable] = {}
    for i in nodes:
        nxt = None
        for j in nodes:
            if i == j:
                continue
            if y_sol[(i, j)] == 1:
                nxt = j
                break
        if nxt is None:
            raise RuntimeError(f"Não encontrou sucessor para {i}.")
        succ[i] = nxt

    tour = [start]
    cur = start
    for _ in range(n):
        cur = succ[cur]
        tour.append(cur)

    if tour[-1] != start:
        raise RuntimeError("Tour não fechou em start; verifique o grafo/modelo.")

    # custo total do tour
    total_cost = 0.0
    for k in range(n):
        total_cost += edge_cost(tour[k], tour[k + 1])

    return TSPSolution(tour=tour, cost=total_cost, y=y_sol, u=u_sol)
