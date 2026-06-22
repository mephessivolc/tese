import strawberryfields as sf
from strawberryfields.ops import *
import numpy as np

def circuit(n_qumodes, d_matrix, params, lambda_penalty, p=1, r=1.5):
    # Supondo um problema com n qumodes (ex: 3 variáveis de rota do TSP)
    prog = sf.Program(n_qumodes)

    gamma = params["gamma"]
    beta = params["beta"]

    p = len(gamma)

    with prog.context as q:

        # ---- ESTADO INICIAL ----
        # Em CV-QAOA, costuma-se iniciar com estados de momento zero (altamente "squeezed" em p)
        for i in range(3):
            Sgate(r, 0) | q[i] # Squeezing inicial para espalhar a posição x

        for layer in range(p):
            # for (i,j), distance in np.ndenumerate(d_matrix):
            for i in range(n_qumodes):
                for j in range(i+1, n_qumodes):
                    # Custo
                    print(f"({i},{j}): {d_matrix[i,j]}, {-gamma[layer]*d_matrix[i,j]}")
                    CZgate(-gamma[layer] * d_matrix[i,j]) | (q[i], q[j])

            # Penalidade de restrição 
            for i in range(n_qumodes):
                Pgate(-2 * gamma[layer] *  lambda_penalty) | q[i]

            # Mixer
            for i in range(n_qumodes):
                Rgate(np.pi / 2) | q[i]
                Pgate(-2 * beta) | q[i]
                Rgate(-np.pi / 2) | q[i]

        return prog

# Para rodar o circuito (usando o simulador Fock ou Gaussiano dependendo se usar portas cúbicas)
n = 3
d_matrix = np.random.randn(n,n)
print(d_matrix)

params = {
    "gamma": [0.05, 0.05],
    "beta": [0.1, 0.1]
}

prog = circuit(n, d_matrix, params, 10)
eng = sf.Engine(backend="gaussian")
result = eng.run(prog)

print(result)