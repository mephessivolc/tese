# vrp/solver.py
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from typing import Tuple, List, Dict, Any

# --- AJUSTE DE PATH PARA ACESSAR A RAIZ DO PROJETO ---
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Imports dos módulos do projeto
from graphs import GraphBuilder
from vrp.hamiltonian import Hamiltonian


class Solver:
    """
    Solver VQE para o VRP usando o Modelo de Variáveis Contínuas (CV) no espaço de fase (x, p).
    """
    def __init__(self, hamiltonian: Hamiltonian):
        self.hamiltonian = hamiltonian
        self.num_qumodes = hamiltonian.num_free_cities
        self.history = []

    def execute_circuit(self, params: np.ndarray) -> Tuple[List[float], List[float]]:
        """
        Simula a medição/expectativa das quadraturas (x, p) a partir do vetor de parâmetros.
        """
        x_vals = params[:self.num_qumodes]
        p_vals = params[self.num_qumodes:]
        return x_vals, p_vals

    def objective_function(self, params: np.ndarray) -> float:
        """
        Função de custo chamada a cada iteração do otimizador clássico (ex: COBYLA).
        """
        x_vals, p_vals = self.execute_circuit(params)
        cost = self.hamiltonian.compute_cost(x_vals, p_vals)
        return cost

    def _callback(self, xk: np.ndarray):
        """
        Salva o histórico da função de custo a cada iteração do otimizador.
        """
        current_cost = self.objective_function(xk)
        self.history.append(current_cost)

    def solve(
        self,
        initial_params: np.ndarray = None,
        maxiter: int = 300,
        optimizer_method: str = "COBYLA",
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Executa a otimização variacional do VQE para o VRP.
        """
        self.history = []
        
        if seed is not None:
            np.random.seed(seed)

        if initial_params is None:
            init_x = np.random.uniform(1.0, self.hamiltonian.max_steps, self.num_qumodes)
            init_p = np.random.uniform(1.0, self.hamiltonian.num_vehicles, self.num_qumodes)
            initial_params = np.concatenate([init_x, init_p])

        res = minimize(
            self.objective_function,
            initial_params,
            method=optimizer_method,
            callback=self._callback,
            options={'maxiter': maxiter, 'disp': False}
        )

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
            "solution_vector": decoded_routes,  # Dicionário {veiculo_id: [0, c1, ..., 0]}
            "routes": decoded_routes,
            "probability": 1.0,
            "history": self.history if self.history else [float(res.fun)]
        }

# --- TESTE UNITÁRIO: VALIDAÇÃO FUNCIONAL DO VQE ---
if __name__ == "__main__":
    print("=" * 60)
    print("      TESTE UNITÁRIO: EXECUÇÃO FUNCIONAL DO VQE (CV) - VRP    ")
    print("=" * 60)

    # 1. Configuração de um problema pequeno para teste rápido
    N_free_cities = 3  # Depósito (0) + Cidades 1, 2, 3
    num_vehicles = 2   # 2 Veículos
    seed = 42

    gb = GraphBuilder(n=N_free_cities + 1, seed=seed)
    dist_matrix = gb.matrix

    print("\n[1] Inicializando o Hamiltoniano VRP e o Solver VQE...")
    hamiltonian = Hamiltonian(dist_matrix, num_vehicles=num_vehicles, lmbda=100.0)
    solver = Solver(hamiltonian)

    # 2. Execução do VQE com poucas iterações para validação rápida
    max_test_iters = 50
    print(f"\n[2] Executando o VQE por {max_test_iters} iterações...")
    vqe_result = solver.solve(maxiter=max_test_iters, seed=seed)

    # 3. Asserções e Validações Unitárias
    print("\n[3] Verificando Saídas do Algoritmo...")
    
    # Validação 1: O dicionário de resultados contém as chaves necessárias
    required_keys = ["opt_result", "best_cost", "disc_x", "disc_p", "history", "solution_vector"]
    for key in required_keys:
        assert key in vqe_result, f"ERRO: Chave '{key}' ausente na saída do VQE."
    print("  ✓ Estrutura de retorno válida.")

    # Validação 2: Dimensão dos vetores decodificados
    assert len(vqe_result["disc_x"]) == N_free_cities, "ERRO: Vetor x com dimensão incorreta."
    assert len(vqe_result["disc_p"]) == N_free_cities, "ERRO: Vetor p com dimensão incorreta."
    print("  ✓ Dimensões das quadraturas decodificadas corretas.")

    # Validação 3: Limites dos valores discretizados
    assert all(1 <= x <= N_free_cities for x in vqe_result["disc_x"]), "ERRO: Valor de tempo x fora do intervalo [1, T]."
    assert all(1 <= p <= num_vehicles for p in vqe_result["disc_p"]), "ERRO: Atribuição de veículo p fora do intervalo [1, V]."
    print("  ✓ Limites das quadraturas válidos.")

    # Validação 4: Evolução da Otimização (Custo inicial vs Custo final)
    initial_cost = vqe_result["history"][0]
    final_cost = vqe_result["best_cost"]
    print(f"\n  -> Custo Inicial : {initial_cost:.4f}")
    print(f"  -> Custo Final   : {final_cost:.4f}")
    print(f"  -> Rotas Finais  : {vqe_result['solution_vector']}")
    
    assert final_cost <= initial_cost, "ERRO: O otimizador não reduziu (ou manteve) o custo."
    print("  ✓ Otimizador reduziu a função de custo com sucesso.")

    print("\n" + "=" * 60)
    print(" STATUS: TESTE UNITÁRIO PASSOU COM SUCESSO! ")
    print("=" * 60)