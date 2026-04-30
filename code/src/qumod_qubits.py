import numpy as np
import qutip as qt

def edge_to_idx(i, j, N):
    if i == j:
        raise ValueError("Não existe modo para i == j")

    idx = 0
    for u in range(N):
        for v in range(N):
            if u != v:
                if u == i and v == j:
                    return idx
                idx += 1


def calcular_hamiltoniano_tsp(d_ij, alpha=100, beta=100, gamma=100, dim=5, incluir_p=False):
    N = d_ij.shape[0]
    Numero_qmodes = N * (N - 1)

    # operadores de destruição
    a_lista = [
        qt.tensor(*[
            qt.qeye(dim) if j != i else qt.destroy(dim)
            for j in range(Numero_qmodes)
        ])
        for i in range(Numero_qmodes)
    ]

    # operadores número
    n_lista = [a.dag() * a for a in a_lista]

    # Custo: soma d_ij * n_ij
    C = 0
    for i in range(N):
        for j in range(N):
            if i != j:
                idx = edge_to_idx(i, j, N)
                C += d_ij[i, j] * n_lista[idx]

    # H1: força ocupações binárias 0 ou 1
    H1 = 0
    for idx in range(Numero_qmodes):
        n = n_lista[idx]
        H1 += alpha * (n * (n - 1))**2
        # também funciona bem para zerar em n=0,1 e penalizar n>=2

    # H2: exatamente uma saída por vértice
    H2 = 0
    for i in range(N):
        soma_saida = 0
        for j in range(N):
            if i != j:
                idx = edge_to_idx(i, j, N)
                soma_saida += n_lista[idx]
        H2 += beta * (soma_saida - 1)**2

    # H3: exatamente uma entrada por vértice
    H3 = 0
    for j in range(N):
        soma_entrada = 0
        for i in range(N):
            if i != j:
                idx = edge_to_idx(i, j, N)
                soma_entrada += n_lista[idx]
        H3 += gamma * (soma_entrada - 1)**2

    H_final = C + H1 + H2 + H3

    if incluir_p:
        p = sum(((1j * np.sqrt(1/2) * (a.dag() - a))**2) / 2 for a in a_lista)
        H_final += p

    return H_final

def indices_para_matriz_x(indices, N):
    """
    Converte a tupla 'indices' em uma matriz X de arestas selecionadas.
    X[i,j] = 1 se a aresta i->j foi escolhida.
    """
    X = np.zeros((N, N), dtype=int)

    idx = 0
    for i in range(N):
        for j in range(N):
            if i != j:
                occ = indices[idx]

                # só aceitamos estados binários para representar solução combinatória
                if occ not in (0, 1):
                    return None

                X[i, j] = occ
                idx += 1

    return X

def matriz_x_para_caminho(X):
    """
    Recebe uma matriz binária X de arestas dirigidas.
    Retorna um ciclo (0, ..., 0) se X representar um único tour válido.
    Senão retorna None.
    """
    N = X.shape[0]

    # uma saída por vértice
    if not np.all(X.sum(axis=1) == 1):
        return None

    # uma entrada por vértice
    if not np.all(X.sum(axis=0) == 1):
        return None

    caminho = [0]
    atual = 0
    visitados = set([0])

    for _ in range(N - 1):
        proxs = np.where(X[atual] == 1)[0]
        if len(proxs) != 1:
            return None

        prox = int(proxs[0])

        if prox in visitados:
            return None

        caminho.append(prox)
        visitados.add(prox)
        atual = prox

    # precisa voltar ao 0
    proxs = np.where(X[atual] == 1)[0]
    if len(proxs) != 1 or int(proxs[0]) != 0:
        return None

    caminho.append(0)

    if len(visitados) != N:
        return None

    return tuple(caminho)

def custo_path(dist, path):
    cost = 0
    for i in range(len(path) - 1):
        cost += dist[path[i]][path[i + 1]]
    return cost

