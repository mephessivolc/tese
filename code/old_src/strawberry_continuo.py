import strawberryfields as sf
from strawberryfields.ops import Fock
import numpy as np
from itertools import product


def caminho_valido(indices, N):
    return len(indices) == N and sorted(indices) == list(range(N))


def indices_para_caminho(indices, N):
    if not caminho_valido(indices, N):
        return None
    return tuple(indices) + (indices[0],)


def custo_path(dist, path):
    return sum(dist[path[i], path[i+1]] for i in range(len(path)-1))


def energia_tsp_diagonal(indices, d_ij, lamb=100.0):
    """
    Equivalente ao Hamiltoniano do QuTiP avaliado num estado de base |indices>.
    """
    N = len(indices)

    # termo de distância
    H_distance = 0.0
    for k in range(N):
        kp1 = (k + 1) % N
        a = indices[k]
        b = indices[kp1]
        H_distance += d_ij[a, b]

    # termo de penalidade
    H_penalty = 0.0
    for k in range(N):
        for l in range(k + 1, N):
            if indices[k] == indices[l]:
                H_penalty += 1.0

    return H_distance + lamb * H_penalty


def analisar_tsp_strawberry(d_ij, lamb=100.0, cutoff=None):
    N = d_ij.shape[0]

    if cutoff is None:
        cutoff = N
    if cutoff < N:
        raise ValueError("É necessário cutoff >= N para representar todas as cidades.")

    melhor_energia = float("inf")
    melhor_indices = None
    melhor_path = None
    resultados_validos = []

    for indices in product(range(cutoff), repeat=N):
        if not caminho_valido(indices, N):
            continue

        prog = sf.Program(N)
        with prog.context as q:
            for k, i in enumerate(indices):
                Fock(i) | q[k]

        eng = sf.Engine("fock", backend_options={"cutoff_dim": cutoff})
        result = eng.run(prog)
        state = result.state

        # como o estado é exatamente |indices>, a energia é a diagonal correspondente
        energia = energia_tsp_diagonal(indices, d_ij, lamb=lamb)

        path = indices_para_caminho(indices, N)
        custo = custo_path(d_ij, path)

        resultados_validos.append((energia, custo, path, indices))

        if energia < melhor_energia:
            melhor_energia = energia
            melhor_indices = indices
            melhor_path = path

    return {
        "melhor_energia": melhor_energia,
        "melhor_indices": melhor_indices,
        "melhor_path": melhor_path,
        "resultados_validos": resultados_validos,
    }