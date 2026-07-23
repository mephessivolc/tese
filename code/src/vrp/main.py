# vrp/main.py
import sys
from pathlib import Path

# --- RESOLUÇÃO DE IMPORTS (Adiciona o diretório 'src/' ao sys.path) ---
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import time
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# Importações da raiz (src/)
from graphs import GraphBuilder
from brute_force import BruteForce
from metrics import ExperimentResult
from logger import ExperimentLogger
from utils import format_timespan, print_experiment_summary
from path import get_images_path, get_results_path

# Módulos específicos do VRP
from vrp.hamiltonian import Hamiltonian
from vrp.solver import Solver as VqeSolver


def run(
    n_cities: int = 3,
    num_vehicles: int = 2,
    lmbda: float = 100.0,
    layers: int = 1,
    maxiter: int = 100,
    optimizer_method: str = "COBYLA",
    seed: int = 42,
    save_outputs: bool = True
) -> dict:
    """
    Orquestrador e ponto de entrada para execução dos experimentos do VRP.
    Pode ser importado por outros scripts (ex: main principal da raiz).
    """
    logger = ExperimentLogger(problem_type="VRP")
    logger.info(f"Iniciando Experimento VRP (N={n_cities}, V={num_vehicles}, Layers={layers}, Seed={seed})")

    # 1. GERAÇÃO DO GRAFO (Inclui o depósito como nó 0)
    logger.info("1. Gerando matriz de adjacência do grafo (Depósito + Cidades)...")
    total_nodes = n_cities + 1
    gb = GraphBuilder(n=total_nodes, seed=seed, logger=logger)

    # 2. GROUND TRUTH (Força Bruta Clássica)
    logger.info("2. Executando Busca Exaustiva Clássica (Ground Truth)...")
    t0 = time.time()
    solver_exato = BruteForce(gb.matrix, num_vehicles=num_vehicles)
    exact_cost, exact_route = solver_exato.solve()
    t_exact = time.time() - t0
    logger.info(f"   ► Custo Exato: {exact_cost:.4f} | Tempo: {format_timespan(t_exact)}")

    # 3. CONSTRUÇÃO DO HAMILTONIANO
    logger.info("3. Construindo operadores do Hamiltoniano CV para VRP...")
    hamiltonian = Hamiltonian(gb.matrix, num_vehicles=num_vehicles, lmbda=lmbda)
    
    # Energia fundamental do ground truth
    e0_exact = exact_cost
    logger.info(f"   ► Custo de Referência H_total (E0): {e0_exact:.4f}")

    # 4. EXECUÇÃO DO SOLVER VQE
    logger.info(f"4. Executando CV-VQE Solver ({optimizer_method})...")
    t0 = time.time()
    vqe_solver = VqeSolver(hamiltonian)
    vqe_res = vqe_solver.solve(
        maxiter=maxiter,
        optimizer_method=optimizer_method,
        seed=seed
    )
    t_vqe = time.time() - t0

    vqe_cost = float(vqe_res["best_energy"])
    nfev = len(vqe_res["history"])
    prob = float(vqe_res.get("probability", 1.0))
    approx_ratio = float(exact_cost / vqe_cost) if vqe_cost != 0 else 0.0

    logger.info(f"   ► VQE Custo Otimizado: {vqe_cost:.4f} | Tempo: {format_timespan(t_vqe)}")

    # 5. ESTRUTURAÇÃO DO RESULTADO (ExperimentResult)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_id = f"VRP_N{n_cities}_V{num_vehicles}_s{seed}_{now_str}"

    opt_params = vqe_res.get("opt_params", None)
    if isinstance(opt_params, np.ndarray):
        opt_params = opt_params.tolist()

    experiment_res = ExperimentResult(
        # Metadados
        experiment_id=exp_id,
        problem_type="VRP",
        timestamp=now_str,
        seed=seed,
        
        # Parâmetros de Entrada
        n_cities=n_cities,
        num_vehicles=num_vehicles,
        p_layers=layers,
        max_iter=maxiter,
        momentum_mass=1.0,  # Valor padrão do operador momento contínuo
        lmbda=lmbda,

        # Solução Exata
        exact_cost=exact_cost,
        exact_route=exact_route,
        exact_time_sec=t_exact,
        ground_state_energy=e0_exact,

        # Solução Quântica
        solver_name="CV-VQE",
        quantum_cost=vqe_cost,
        quantum_route=vqe_res["solution_vector"],
        quantum_time_sec=t_vqe,
        approx_ratio=approx_ratio,
        success_probability=prob,
        evaluations_count=nfev,

        # Históricos
        optimal_params=opt_params,
        cost_history=vqe_res["history"]
    )

    # Exibe resumo formatado no terminal
    print_experiment_summary(
        problem_type="vrp",
        n_cities=n_cities,
        exact_cost=exact_cost,
        exact_time=t_exact,
        quantum_cost=vqe_cost,
        quantum_time=t_vqe,
        evals=nfev
    )

    # 6. SALVAMENTO DE ARTEFATOS E GRÁFICOS (result/vrp/)
    if save_outputs:
        figures_dir = Path(logger.get_figures_dir("VRP"))

        # a) Salva via ExperimentLogger (JSON e registro no CSV acumulativo)
        logger.save_experiment(experiment_res)

        # b) Plot do Grafo e Rotas do VRP
        gb.plot_graph_and_route(
            solution_vector=vqe_res["solution_vector"],
            prefix=f"vqe_N{n_cities}_V{num_vehicles}_s{seed}"
        )

        # c) Plot e Salvamento da Curva de Convergência
        plt.figure(figsize=(8, 4.5))
        plt.axhline(y=exact_cost, color='r', linestyle='--', label=f'Ground Truth Exato ({exact_cost:.2f})')
        plt.plot(vqe_res["history"], label=f'Convergência CV-VQE ({optimizer_method})', color='green', marker='o', alpha=0.7)
        plt.title(f"Convergência VQE - VRP (N={n_cities}, V={num_vehicles}, Camadas={layers})")
        plt.xlabel("Avaliações de Custo (Iterações)")
        plt.ylabel("Energia Esperada <H_total>")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(figures_dir / f"convergence_N{n_cities}_V{num_vehicles}_s{seed}.png", dpi=300)
        plt.close()

        logger.info("Artefatos salvos com sucesso na pasta 'result/vrp/'")

    return experiment_res.to_dict()


if __name__ == "__main__":
    run(
        n_cities=3,
        num_vehicles=2,
        lmbda=100.0,
        layers=1,
        maxiter=50,
        optimizer_method="COBYLA",
        seed=42,
        save_outputs=True
    )