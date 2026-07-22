import numpy as np
import strawberryfields as sf
from strawberryfields.ops import Dgate, Rgate, BSgate
from scipy.optimize import minimize

from graphs import GraphBuilder
from brute_force import tsp_bruteforce


def n_params_ansatz(n_qumodes):
    """Número de parâmetros independentes em uma camada do ansatz."""
    return 3 * n_qumodes + 2 * (n_qumodes - 1) + 3 * n_qumodes


def vqe_ansatz_layer(q, n_qumodes, params):
    """
    Camada VQE CV:
    - deslocamento + rotação em cada qumode
    - beam splitters entre vizinhos
    - deslocamento + rotação final em cada qumode
    """
    expected = n_params_ansatz(n_qumodes)
    if len(params) < expected:
        raise ValueError(f"Foram recebidos {len(params)} parâmetros, mas são necessários {expected}.")

    idx = 0

    # 1. Bloco local inicial
    for i in range(n_qumodes):
        Dgate(params[idx], params[idx + 1]) | q[i]
        Rgate(params[idx + 2]) | q[i]
        idx += 3

    # 2. Bloco de emaranhamento
    for i in range(n_qumodes - 1):
        BSgate(params[idx], params[idx + 1]) | (q[i], q[i + 1])
        idx += 2

    # 3. Bloco local final
    for i in range(n_qumodes):
        Dgate(params[idx], params[idx + 1]) | q[i]
        Rgate(params[idx + 2]) | q[i]
        idx += 3

    return idx


def estado_valido_tsp(fock_state, fix_start=True):
    """
    Codificação usada:
    fock_state[cidade] = instante em que a cidade é visitada.

    Para N=4, os instantes válidos são 0, 1, 2, 3.
    Exemplo:
        fock_state = (0, 2, 1, 3)
        rota = 0 -> 2 -> 1 -> 3 -> 0
    """
    N = len(fock_state)
    esperado = set(range(N))

    if set(fock_state) != esperado:
        return False

    if fix_start and fock_state[0] != 0:
        return False

    return True


def decodificar_rota(fock_state):
    """Converte estado de Fock em rota fechada."""
    rota = tuple(np.argsort(fock_state))
    return rota + (rota[0],)


def custo_rota(rota, d_matrix):
    """Calcula o custo de uma rota fechada."""
    return sum(d_matrix[rota[i], rota[i + 1]] for i in range(len(rota) - 1))


def hamiltoniano_classico_tsp(fock_state, d_matrix, lambda_penalty, fix_start=True):
    """
    Hamiltoniano clássico associado à amostra de Fock.

    Estados válidos são permutações de 0, ..., N-1.
    Estados inválidos recebem penalidade.
    """
    N = len(fock_state)
    fock_state = tuple(int(s) for s in fock_state)

    if not estado_valido_tsp(fock_state, fix_start=fix_start):
        n_unicos = len(set(fock_state))
        repeticao = N - n_unicos
        penalidade_repeticao = lambda_penalty * (repeticao + 1) ** 2
        penalidade_inicio = lambda_penalty if fix_start and fock_state[0] != 0 else 0.0
        return penalidade_repeticao + penalidade_inicio

    rota = decodificar_rota(fock_state)
    return custo_rota(rota, d_matrix)


def analisar_circuito(
    params,
    n_qumodes,
    d_matrix,
    lambda_penalty,
    cutoff_dim,
    prob_min=1e-6,
    top_k=10,
    fix_start=True,
):
    """
    Executa o circuito e retorna diagnóstico útil para o VQE.

    A energia é calculada com normalização pela massa de probabilidade
    dentro do cutoff e com penalidade para vazamento fora do cutoff.
    """
    prog = sf.Program(n_qumodes)

    with prog.context as q:
        vqe_ansatz_layer(q, n_qumodes, params)

    eng = sf.Engine(
        backend="fock",
        backend_options={"cutoff_dim": cutoff_dim},
    )

    result = eng.run(prog)
    probs = result.state.all_fock_probs()

    prob_total = float(np.sum(probs))

    if prob_total <= 1e-14:
        return {
            "energia": 10.0 * lambda_penalty,
            "prob_total": prob_total,
            "vazamento": 1.0,
            "melhor_por_custo": None,
            "melhor_por_probabilidade": None,
            "top_estados": [],
        }

    energia_bruta = 0.0
    registros = []

    for fock_state, prob in np.ndenumerate(probs):
        if prob <= 0.0:
            continue

        custo = hamiltoniano_classico_tsp(
            fock_state,
            d_matrix,
            lambda_penalty,
            fix_start=fix_start,
        )

        energia_bruta += float(prob) * custo

        prob_norm = float(prob) / prob_total
        valido = estado_valido_tsp(fock_state, fix_start=fix_start)
        rota = decodificar_rota(fock_state) if valido else None

        if prob_norm >= prob_min:
            registros.append(
                {
                    "estado": tuple(int(s) for s in fock_state),
                    "rota": rota,
                    "custo": float(custo),
                    "probabilidade": prob_norm,
                    "valido": valido,
                }
            )

    # Energia condicional dentro do cutoff + penalidade de vazamento.
    energia_condicional = energia_bruta / prob_total
    vazamento = max(0.0, 1.0 - prob_total)
    energia = energia_condicional + lambda_penalty * vazamento

    registros_validos = [r for r in registros if r["valido"]]

    melhor_por_custo = None
    melhor_por_probabilidade = None

    if registros_validos:
        melhor_por_custo = min(registros_validos, key=lambda r: r["custo"])
        melhor_por_probabilidade = max(registros_validos, key=lambda r: r["probabilidade"])

    top_estados = sorted(
        registros,
        key=lambda r: r["probabilidade"],
        reverse=True,
    )[:top_k]

    return {
        "energia": float(energia),
        "prob_total": prob_total,
        "vazamento": vazamento,
        "melhor_por_custo": melhor_por_custo,
        "melhor_por_probabilidade": melhor_por_probabilidade,
        "top_estados": top_estados,
    }


def objective_function(params, n_qumodes, d_matrix, lambda_penalty, cutoff_dim):
    diagnostico = analisar_circuito(
        params,
        n_qumodes,
        d_matrix,
        lambda_penalty,
        cutoff_dim,
        prob_min=0.0,
        top_k=0,
        fix_start=True,
    )
    return diagnostico["energia"]


def otimizar_multistart(N, distancias, penalidade, fock_cutoff, n_restarts=5):
    """Executa várias inicializações e retorna o melhor resultado."""
    n_params = n_params_ansatz(N)
    bounds = [(-1.0, 1.0)] * n_params

    melhor_resultado = None

    for seed in range(n_restarts):
        rng = np.random.default_rng(seed)
        params_iniciais = rng.uniform(-0.1, 0.1, n_params)

        resultado = minimize(
            objective_function,
            params_iniciais,
            args=(N, distancias, penalidade, fock_cutoff),
            method="Powell",
            bounds=bounds,
            options={"maxiter": 300, "disp": False},
        )

        if melhor_resultado is None or resultado.fun < melhor_resultado.fun:
            melhor_resultado = resultado

        print(f"Restart {seed}: energia = {resultado.fun:.8f}")

    return melhor_resultado


if __name__ == "__main__":
    N = 3
    fock_cutoff = N
    penalidade = 500.0

    graph = GraphBuilder(N)
    distancias = graph.matrix

    print(f"Matriz de adjacencia:\n{distancias}")

    print("=== brute force ===")
    best_cost, best_path = tsp_bruteforce(distancias)
    print(f"Best Cost: {best_cost}\tBest Path: {best_path}")

    print("=== VQE ===")
    resultado_otimizacao = otimizar_multistart(
        N,
        distancias,
        penalidade,
        fock_cutoff,
        n_restarts=5,
    )

    diagnostico = analisar_circuito(
        resultado_otimizacao.x,
        N,
        distancias,
        penalidade,
        fock_cutoff,
        prob_min=1e-6,
        top_k=10,
        fix_start=True,
    )

    print("\nParâmetros ótimos encontrados:")
    print(resultado_otimizacao.x)

    print("\nEnergia esperada mínima encontrada <H>:")
    print(diagnostico["energia"])

    print("\nProbabilidade total dentro do cutoff:")
    print(diagnostico["prob_total"])

    print("\nVazamento fora do cutoff:")
    print(diagnostico["vazamento"])

    print("\nMelhor rota válida por custo entre estados relevantes:")
    print(diagnostico["melhor_por_custo"])

    print("\nRota válida mais provável:")
    print(diagnostico["melhor_por_probabilidade"])

    print("\nTop estados medidos:")
    for item in diagnostico["top_estados"]:
        print(item)
