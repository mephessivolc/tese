# vrp/solver.py
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from typing import Tuple, List, Dict, Any

import strawberryfields as sf

# --- AJUSTE DE PATH PARA ACESSAR A RAIZ DO PROJETO ---
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Imports dos módulos do projeto
from graphs import GraphBuilder
from vrp.hamiltonian import Hamiltonian
from vrp.circuit import Circuit


class Solver:
    """
    Solver VQE para o VRP utilizando circuito quântico CV (Strawberry Fields)
    e extração de valores esperados das quadraturas <x> e <p>.
    """
    def __init__(
        self,
        hamiltonian: Hamiltonian,
        layers: int = 1,
        cutoff_dim: int = 5,
        backend: str = "fock"
    ):
        self.hamiltonian = hamiltonian
        self.num_qumodes = hamiltonian.num_free_cities
        self.layers = layers
        self.cutoff_dim = cutoff_dim
        self.backend = backend
        
        # Instancia o Ansatz e calcula o número de parâmetros necessários
        self.ansatz = Circuit(num_qumodes=self.num_qumodes, num_layers=self.layers)
        self.engine = sf.Engine(backend=self.backend, backend_options={"cutoff_dim": self.cutoff_dim})
        self.history = []

    def execute_circuit(self, params: np.ndarray) -> Tuple[List[float], List[float]]:
        """
        Executa o circuito quântico variacional no Strawberry Fields
        e extrai os valores esperados das quadraturas <x> e <p> para cada qumode.
        """
        # Constrói o programa do Strawberry Fields a partir dos parâmetros do otimizador
        prog = self.ansatz.build_program(params)
        
        # Executa no simulador quântico
        result = self.engine.run(prog)
        state = result.state

        x_vals = []
        p_vals = []

        # Extrai os valores esperados das quadraturas para cada cidade livre
        for mode in range(self.num_qumodes):
            x_mean, _ = state.quad_expectation(mode, phi=0.0)         # Quadratura X (Tempo de visita)
            p_mean, _ = state.quad_expectation(mode, phi=np.pi/2)     # Quadratura P (Veículo atribuído)
            
            x_vals.append(x_mean)
            p_vals.append(p_mean)

        return x_vals, p_vals

    def objective_function(self, params: np.ndarray) -> float:
        """
        Função de custo chamada pelo otimizador clássico (COBYLA, Nelder-Mead, etc.).
        """
        x_vals, p_vals = self.execute_circuit(params)
        cost = self.hamiltonian.compute_cost(x_vals, p_vals)
        return cost

    def _callback(self, xk: np.ndarray):
        """
        Registra o histórico de energia no VQE.
        """
        current_cost = self.objective_function(xk)
        self.history.append(current_cost)

    def solve(
        self,
        initial_params: np.ndarray = None,
        maxiter: int = 100,
        optimizer_method: str = "COBYLA",
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Executa o loop variacional do VQE para encontrar as rotas ótimas do VRP.
        """
        self.history = []

        # Inicializa parâmetros aleatórios do Ansatz se não fornecidos
        if initial_params is None:
            initial_params = self.ansatz.initialize_random_params(seed=seed)

        # Otimização Variacional Clássica
        res = minimize(
            self.objective_function,
            initial_params,
            method=optimizer_method,
            callback=self._callback,
            options={'maxiter': maxiter, 'disp': False}
        )

        # Medição final com o melhor conjunto de parâmetros otimizados
        opt_x, opt_p = self.execute_circuit(res.x)
        disc_x, disc_p = self.hamiltonian.discretize_quadratures(opt_x, opt_p)
        decoded_routes = self.hamiltonian.decode_routes(opt_x, opt_p)

        return {
            "opt_result": res,
            "best_cost": float(res.fun),
            "best_energy": float(res.fun),
            "opt_params": res.x,
            "disc_x": disc_x,
            "disc_p": disc_p,
            "solution_vector": decoded_routes,
            "routes": decoded_routes,
            "probability": 1.0,
            "history": self.history if self.history else [float(res.fun)]
        }


# --- TESTE UNITÁRIO COM CIRCUITOS QUÂNTICOS DE VERDADE ---
if __name__ == "__main__":
    print("=" * 60)
    print("    TESTE UNITÁRIO: VQE COM STRAWBERRY FIELDS (VRP)    ")
    print("=" * 60)

    N_free_cities = 2  # 2 cidades livres (2 qumodes) + 1 depósito
    num_vehicles = 2   # 2 veículos
    seed = 42

    gb = GraphBuilder(n=N_free_cities + 1, seed=seed)
    dist_matrix = gb.matrix

    print("\n[1] Inicializando Hamiltoniano e Solver com Circuit...")
    hamiltonian = Hamiltonian(dist_matrix, num_vehicles=num_vehicles, lmbda=100.0)
    solver = Solver(hamiltonian, layers=1, cutoff_dim=4)

    print(f"  ► Qumodes no circuito: {solver.num_qumodes}")
    print(f"  ► Parâmetros variacionais a otimizar: {solver.ansatz.num_params}")

    print("\n[2] Executando VQE no Strawberry Fields...")
    vqe_result = solver.solve(maxiter=15, optimizer_method="COBYLA", seed=seed)

    print("\n[3] Resultados Obtidos:")
    print(f"  ► Custo Inicial : {vqe_result['history'][0]:.4f}")
    print(f"  ► Custo Final   : {vqe_result['best_cost']:.4f}")
    print(f"  ► Rotas Otimizadas : {vqe_result['solution_vector']}")
    print("\n STATUS: TESTE COM CIRCUITO QUÂNTICO CONCLUÍDO COM SUCESSO!")