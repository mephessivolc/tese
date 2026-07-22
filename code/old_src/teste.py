import numpy as np
import qutip as qt

import qutip_continuo as qtc

import itertools

import pandas as pd
import graphs
import time 


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

def analisar_estados_base(H_final_matriz, dist, N, dim):
    Numero_qmodes = N * (N - 1)

    melhor_energia = float('inf')
    melhor_indices = None
    melhor_X = None
    melhor_path = None

    resultados_validos = []

    cont = 0
    for indices in itertools.product(range(dim), repeat=Numero_qmodes):
        X = indices_para_matriz_x(indices, N)
        if X is None:
            continue

        path = matriz_x_para_caminho(X)
        if path is None:
            continue

        state = qt.tensor(*[qt.basis(dim, i) for i in indices])
        energia = qt.expect(H_final_matriz, state)
        custo = custo_path(dist, path)

        resultados_validos.append((energia, custo, path, indices))

        if energia < melhor_energia:
            melhor_energia = energia
            melhor_indices = indices
            melhor_X = X.copy()
            melhor_path = path

        cont += 1
        if cont % 10 == 0:
            print(f"{cont}: energia={energia}, custo={custo}, path={path}")

    return {
        "melhor_energia": melhor_energia,
        "melhor_indices": melhor_indices,
        "melhor_X": melhor_X,
        "melhor_path": melhor_path,
        "resultados_validos": resultados_validos,
    }

import itertools
import numpy as np
import pennylane as qml
from itertools import permutations

def edge_to_wire(i, j, N):
    if i == j:
        raise ValueError("Não existe aresta com i == j")

    w = 0
    for u in range(N):
        for v in range(N):
            if u != v:
                if u == i and v == j:
                    return w
                w += 1


def x_op(i, j, N):
    w = edge_to_wire(i, j, N)
    return 0.5 * (qml.Identity(w) - qml.PauliZ(w))


def build_tsp_hamiltonian_qubits(d_ij, beta=100.0, gamma=100.0):
    N = d_ij.shape[0]
    H = 0

    # custo
    for i in range(N):
        for j in range(N):
            if i != j:
                H = H + d_ij[i, j] * x_op(i, j, N)

    # uma saída por vértice
    for i in range(N):
        s_out = 0
        for j in range(N):
            if i != j:
                s_out = s_out + x_op(i, j, N)
        H = H + beta * (s_out - 1) @ (s_out - 1)

    # uma entrada por vértice
    for j in range(N):
        s_in = 0
        for i in range(N):
            if i != j:
                s_in = s_in + x_op(i, j, N)
        H = H + gamma * (s_in - 1) @ (s_in - 1)

    return H


def prepare_basis_state_from_bits(bits):
    for w, b in enumerate(bits):
        if b == 1:
            qml.PauliX(wires=w)


def make_energy_qnode(H, num_wires):
    dev = qml.device("default.qubit", wires=num_wires)

    @qml.qnode(dev)
    def energy_circuit(bits):
        prepare_basis_state_from_bits(bits)
        return qml.expval(H)

    return energy_circuit


def bits_to_adjacency(bits, N):
    X = np.zeros((N, N), dtype=int)
    idx = 0
    for i in range(N):
        for j in range(N):
            if i != j:
                X[i, j] = bits[idx]
                idx += 1
    return X


def adjacency_to_path(X):
    N = X.shape[0]

    if not np.all(X.sum(axis=1) == 1):
        return None
    if not np.all(X.sum(axis=0) == 1):
        return None

    path = [0]
    current = 0
    visited = {0}

    for _ in range(N - 1):
        nxt = np.where(X[current] == 1)[0]
        if len(nxt) != 1:
            return None

        nxt = int(nxt[0])
        if nxt in visited:
            return None

        path.append(nxt)
        visited.add(nxt)
        current = nxt

    back = np.where(X[current] == 1)[0]
    if len(back) != 1 or int(back[0]) != 0:
        return None

    path.append(0)

    if len(visited) != N:
        return None

    return tuple(path)


def cost_of_path(dist, path):
    return sum(dist[path[k], path[k+1]] for k in range(len(path) - 1))


def analyze_qubit_tsp_hamiltonian(d_ij, beta=100.0, gamma=100.0):
    N = d_ij.shape[0]
    num_wires = N * (N - 1)

    H = build_tsp_hamiltonian_qubits(d_ij, beta=beta, gamma=gamma)
    energy_qnode = make_energy_qnode(H, num_wires)

    best_energy = float("inf")
    best_bits = None
    best_path = None
    valid_results = []

    for bits in itertools.product([0, 1], repeat=num_wires):
        X = bits_to_adjacency(bits, N)
        path = adjacency_to_path(X)

        if path is None:
            continue

        energy = energy_qnode(bits)
        cost = cost_of_path(d_ij, path)

        valid_results.append((energy, cost, path, bits))

        if energy < best_energy:
            best_energy = energy
            best_bits = bits
            best_path = path

    return {
        "H": H,
        "best_energy": best_energy,
        "best_bits": best_bits,
        "best_path": best_path,
        "valid_results": valid_results,
    }

N = [3,4,5]
linhas_tabela = []

alpha = 100
beta = 100
gamma = 100
lamb = 100

i = 0
for city in N:
    start = time.perf_counter()
    gerador = graphs.GraphBuilder(n=city)
    d_ij = gerador.matrix
    dim = city

    best_cost_classico, best_path_classico = tsp_bruteforce(d_ij)

    H_n = qtc.calcular_hamiltoniano_tsp_qudit(d_ij, lamb=lamb, dim=dim)
    resultado_quantico = qtc.analisar_estados_base_qudit(H_n, d_ij, city, dim=dim)

    melhor_path_quantico = resultado_quantico["melhor_path"]
    similar = custo_path(d_ij, melhor_path_quantico) == best_cost_classico

    total = time.perf_counter() - start
    linhas_tabela.append(
        {
            "Numero de cidades": city,
            "Custo classico": best_cost_classico,
            "Caminho classico": " -> ".join(map(str, best_path_classico)),
            "Energia quantica": resultado_quantico["melhor_energia"],
            "Caminho quantico": " -> ".join(map(str, melhor_path_quantico)),
            "Solucao equivalente": "Sim" if similar else "Não",
            "tempo de execucao": total,
        }
    )

    print(f"{linhas_tabela[i]['Numero de cidades']}: C-{linhas_tabela[i]['Caminho classico']} | \
          Q-{linhas_tabela[i]['Caminho quantico']} | tempo {linhas_tabela[i]['tempo de execucao']}")
    i = i + 1
        
    df = pd.DataFrame(linhas_tabela)

    from pathlib import Path

    BASE_DIR = Path.cwd()
    OUTPUT_DIR = BASE_DIR / "code" / "src" / "resultados"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_pickle(OUTPUT_DIR / f"resultados_tsp_{city}.pkl")
    df.to_csv(OUTPUT_DIR / f"resultados_tsp_{city}.csv", index=False)

print("Finalizado")