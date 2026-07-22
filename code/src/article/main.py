import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize, dual_annealing

# Módulos do Projeto
from get_paths import get_images_path, get_results_path
from utils import format_timespan, Logger
from graphs import GraphBuilder
from ca_bruteforce import tsp_bruteforce_all
from hamiltonian import Hamiltonian
from qaoa_circuit import QAOACircuit


def run_experiment(
    N_cities: int = 3, 
    p_layers: int = 1, 
    max_iter: int = 50, 
    seed: int = 42,
    optimizer_method: str = "COBYLA",
    save_outputs: bool = True
) -> dict:
    """
    Orquestra o experimento CV-QAOA salvando a saída no log .txt e 
    exibindo os VETORES DE SOLUÇÃO encontrados por CA e QAOA.
    """
    global_start_time = time.time()

    log_filename = f"experiment_N{N_cities}_p{p_layers}_{optimizer_method.lower()}.txt"
    log_path = get_results_path() / log_filename

    with Logger(log_path):
        print(f"===========================================================")
        print(f"=== INICIANDO EXPERIMENTO CV-QAOA ({N_cities} CIDADES) ===")
        print(f"=== Otimizador: {optimizer_method} | Camadas: {p_layers} | Seed: {seed} ===")
        print(f"===========================================================\n")

        # -------------------------------------------------------------
        # 1. SOLUÇÃO CLÁSSICA (CA - FORÇA BRUTA)
        # -------------------------------------------------------------
        t0_ca = time.time()
        gb = GraphBuilder(n=N_cities, seed=seed)
        print("[CA] Resolvendo por Força Bruta...")
        ca_cost, ca_paths, _ = tsp_bruteforce_all(gb.matrix)
        t_ca = time.time() - t0_ca

        print(f"  -> Custo Mínimo Exato (CA): {ca_cost:.4f}")
        print(f"  -> Vetor/Rota Ótima (CA):   {ca_paths}")
        print(f"  -> Tempo Algoritmo Clássico: {format_timespan(t_ca)}\n")

        # -------------------------------------------------------------
        # 2. CONSTRUÇÃO DO CIRCUITO QUÂNTICO (QA)
        # -------------------------------------------------------------
        t0_setup = time.time()
        hamiltonian_builder = Hamiltonian(gb.matrix, lmbda=50.0)
        qaoa_circuit = QAOACircuit(hamiltonian_builder)
        t_setup = time.time() - t0_setup

        n_qumodes = qaoa_circuit.N
        cutoff_dim = qaoa_circuit.cutoff_dim

        print(f"[QA] Circuito Montado ({n_qumodes} qumodes, cutoff={cutoff_dim}).")
        print(f"  -> Tempo de Inicialização do Circuito: {format_timespan(t_setup)}\n")

        # -------------------------------------------------------------
        # 3. OTIMIZAÇÃO VARIACIONAL DO QAOA
        # -------------------------------------------------------------
        np.random.seed(seed)
        initial_params = np.random.uniform(0, np.pi, 2 * p_layers)
        bounds = [(0, 2 * np.pi)] * (2 * p_layers)

        history = []
        iteration_times = []
        t0_optimization = time.time()

        def objective_function(params: np.ndarray) -> float:
            t0_iter = time.time()
            energy = qaoa_circuit.evaluate_energy(params, p_layers)
            t_iter = time.time() - t0_iter
            
            history.append(energy)
            iteration_times.append(t_iter)
            
            elapsed_so_far = time.time() - t0_optimization
            print(f"  Iteração {len(history):02d} | <H> = {energy:.4f} | Tempo Iter: {format_timespan(t_iter)} | Decorrido: {format_timespan(elapsed_so_far)}")
            return energy

        print(f"[QA] Iniciando Otimização ({optimizer_method})...")
        
        method_upper = optimizer_method.upper()

        if method_upper in ["COBYLA", "NELDER-MEAD", "POWELL"]:
            result = minimize(
                fun=objective_function,
                x0=initial_params,
                method=optimizer_method,
                options={"maxiter": max_iter}
            )
        elif method_upper in ["L-BFGS-B", "BFGS", "CG"]:
            result = minimize(
                fun=objective_function,
                x0=initial_params,
                method=optimizer_method,
                bounds=bounds if method_upper == "L-BFGS-B" else None,
                options={"maxiter": max_iter}
            )
        elif method_upper == "DUAL-ANNEALING":
            result = dual_annealing(
                func=objective_function,
                bounds=bounds,
                maxiter=max_iter,
                seed=seed
            )
        else:
            raise ValueError(f"Método '{optimizer_method}' não suportado.")

        t_optimization = time.time() - t0_optimization
        total_experiment_time = time.time() - global_start_time

        opt_energy = result.fun
        opt_params = result.x
        approx_ratio = ca_cost / opt_energy if opt_energy > 0 else 0.0
        avg_time_per_iter = np.mean(iteration_times) if iteration_times else 0.0

        # -------------------------------------------------------------
        # 4. EXTRAÇÃO DO VETOR DE ESTADO FINAL DO QAOA
        # -------------------------------------------------------------
        qaoa_solution = qaoa_circuit.get_solution_vector(opt_params, p_layers)
        qaoa_vector = qaoa_solution["state_vector"]
        qaoa_prob = qaoa_solution["probability"]

        # -------------------------------------------------------------
        # 5. EXIBIÇÃO E LOG DOS RESULTADOS E VETORES
        # -------------------------------------------------------------
        print("\n===========================================================")
        print("=== RELATÓRIO DE RESULTADOS E VETORES ENCONTRADOS ===")
        print(f"  -> Custo Mínimo Real (CA):          {ca_cost:.4f}")
        print(f"  -> Rota/Vetor de Solução (CA):      {ca_paths}")
        print("  ---------------------------------------------------------")
        print(f"  -> Energia Fundamental QAOA (QA):   {opt_energy:.4f}")
        print(f"  -> Vetor do Estado Medido (QAOA):   {qaoa_vector}")
        print(f"  -> Probabilidade do Estado (QAOA):  {qaoa_prob * 100:.2f}%")
        print(f"  -> Approximation Ratio (\u03b1):       {approx_ratio:.4f}")
        print("  ---------------------------------------------------------")
        print(f"  -> Tempo Algoritmo Clássico (CA):   {format_timespan(t_ca)}")
        print(f"  -> Tempo de Setup do Circuito (QA): {format_timespan(t_setup)}")
        print(f"  -> Tempo da Otimização Variacional: {format_timespan(t_optimization)}")
        print(f"  -> TEMPO TOTAL DO EXPERIMENTO:      {format_timespan(total_experiment_time)}")
        print("===========================================================\n")

        # -------------------------------------------------------------
        # 6. SALVAR GRÁFICOS E ARQUIVOS AUXILIARES
        # -------------------------------------------------------------
        if save_outputs:
            images_dir = get_images_path()

            plt.figure(figsize=(8, 5))
            plt.plot(range(1, len(history) + 1), history, marker='o', linewidth=2, label=f"QAOA ({optimizer_method})")
            plt.axhline(y=ca_cost, color='r', linestyle='--', label=f"Ótimo Clássico CA ({ca_cost:.2f})")
            plt.title(f"Convergência do CV-QAOA (N={N_cities}, p={p_layers})\nTempo Total: {format_timespan(total_experiment_time)}", fontsize=11)
            plt.xlabel("Avaliação da Função Objetivo", fontsize=10)
            plt.ylabel("Energia <H>", fontsize=10)
            plt.grid(True, linestyle=":", alpha=0.6)
            plt.legend()
            
            plot_path = images_dir / f"convergence_{optimizer_method.lower()}_N{N_cities}_p{p_layers}.png"
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"[OK] Log completo salvo em: {log_path}")
            print(f"[OK] Gráfico salvo em: {plot_path}")

            # Pega a primeira rota de menor custo do CA (ex: ca_paths[0])
            best_ca_route = ca_paths[0] if isinstance(ca_paths, list) else ca_paths

            orig_img, route_img = gb.plot_graph_and_route(
                solution_vector=best_ca_route,
                prefix=f"N{N_cities}"
            )
            print(f"[OK] Grafo original salvo em: {orig_img}")
            print(f"[OK] Grafo com rota gerado em: {route_img}")

    return {
        "N_cities": N_cities,
        "p_layers": p_layers,
        "optimizer": optimizer_method,
        "ca_cost": ca_cost,
        "ca_vector": ca_paths,
        "qaoa_energy": opt_energy,
        "qaoa_vector": qaoa_vector,
        "qaoa_probability": qaoa_prob,
        "approx_ratio": approx_ratio,
        "history": history,
        "time_total": format_timespan(total_experiment_time)
    }


if __name__ == "__main__":
    run_experiment(
        N_cities=3, 
        p_layers=1, 
        max_iter=15, 
        optimizer_method="COBYLA"
    )