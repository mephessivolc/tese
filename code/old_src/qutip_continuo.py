import qutip as qt
from itertools import product


def projector_k_a(k, a, N, dim):
    ops = []
    for m in range(N):
        if m == k:
            ops.append(qt.basis(dim, a) * qt.basis(dim, a).dag())
        else:
            ops.append(qt.qeye(dim))
    return qt.tensor(*ops)


def calcular_hamiltoniano_tsp_qudit(d_ij, lamb=100.0, dim=None):
    N = d_ij.shape[0]

    if dim is None:
        dim = N

    if dim < N:
        raise ValueError("É necessário ter dim >= N para representar todas as cidades.")

    P = {}
    for k in range(N):
        for a in range(N):
            P[(k, a)] = projector_k_a(k, a, N, dim)

    H_distance = 0
    for k in range(N):
        kp1 = (k + 1) % N
        for a in range(N):
            for b in range(N):
                H_distance += d_ij[a, b] * P[(k, a)] * P[(kp1, b)]

    H_penalty = 0
    for k in range(N):
        for l in range(k + 1, N):
            for a in range(N):
                H_penalty += P[(k, a)] * P[(l, a)]

    return H_distance + lamb * H_penalty


def indices_para_caminho(indices, N):
    if len(indices) != N:
        return None
    if any((x < 0 or x >= N) for x in indices):
        return None
    return tuple(indices) + (indices[0],)


def caminho_valido(indices, N):
    """
        Verifica se o caminho e os vértices encontrados são válidos

        Exemplo:
        tomando `N=4` => [0,1,2,3]
        se `indices=[2,3,0,1]` então `sorted(indices) == [0,1,2,3]` => True
        outros casos
            se `indices=[2,2,0,1]` então `sorted(indices) == [0,1,2,3]` => False
            se `indices=[2,3,0]` então `len(indices) == N` => False
    """
    if len(indices) != N:
        return False
    return sorted(indices) == list(range(N))


def custo_path(dist, path):
    cost = 0
    for i in range(len(path) - 1):
        cost += dist[path[i]][path[i + 1]]
    return cost

def analisar_estados_base_qudit(H_final_matriz, dist, N, dim=None):
    if dim is None:
        dim = N

    melhor_energia = float('inf')
    melhor_indices = None
    melhor_path = None
    resultados_validos = []

    for indices in product(range(dim), repeat=N):
        if not caminho_valido(indices, N):
            continue

        state = qt.tensor(*[qt.basis(dim, i) for i in indices])
        energia = qt.expect(H_final_matriz, state)
        path = indices_para_caminho(indices, N)
        custo = custo_path(dist, path)

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