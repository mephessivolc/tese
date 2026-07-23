from typing import Tuple, List, Dict
import numpy as np

class Hamiltonian:
    """
    Hamiltoniano do VRP para Variáveis Contínuas (CV-VQE) no Espaço de Fase (x, p).
    
    Mapeamento:
    - 1 Qumode por Cidade Livre (N-1 qumodes, excluindo o Depósito 0).
    - Quadratura x (Posição): Passo de tempo / Ordem de visita (1..T).
    - Quadratura p (Momento): Identidade do Veículo (1..V).
    """
    def __init__(self, dist_matrix: np.ndarray, num_vehicles: int = 2, lmbda: float = 100.0):
        self.dist_matrix = np.array(dist_matrix)
        self.num_nodes = len(dist_matrix)
        self.num_vehicles = num_vehicles
        self.num_free_cities = self.num_nodes - 1  # Exclui o Depósito (índice 0)
        self.lmbda = lmbda
        self.max_steps = self.num_free_cities      # Passos de tempo máximos por veículo
        self.cutoff_dim = self.num_free_cities     # Propriedade de compatibilidade para métricas

    def discretize_quadratures(self, x_vals: List[float], p_vals: List[float]) -> Tuple[List[int], List[int]]:
        """
        Converte as amostras contínuas lidas nas detecções homódinas de Posição (x)
        e Momento (p) em valores inteiros discretos para o VRP.
        """
        x_disc = [int(np.clip(np.round(x), 1, self.max_steps)) for x in x_vals]
        p_disc = [int(np.clip(np.round(p), 1, self.num_vehicles)) for p in p_vals]
        return x_disc, p_disc

    def decode_routes(self, x_vals: List[float], p_vals: List[float]) -> Dict[int, List[int]]:
        """
        Converte as quadraturas contínuas (x, p) em um dicionário de rotas por veículo:
        {veiculo_id: [0, cidade_1, cidade_2, ..., 0]}
        """
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        routes = {}

        for v in range(1, self.num_vehicles + 1):
            # Obtém cidades atendidas pelo veículo v e seus respectivos tempos x
            vehicle_cities = [
                (i + 1, x_disc[i])  # (Cidade_ID no Grafo, Tempo x)
                for i in range(self.num_free_cities)
                if p_disc[i] == v
            ]

            if not vehicle_cities:
                routes[v] = [0, 0]  # Veículo que não realiza entregas (Depósito -> Depósito)
                continue

            # Ordena as paradas da rota em ordem cronológica de tempo x
            vehicle_cities.sort(key=lambda item: item[1])
            
            # Constrói o ciclo completo do veículo
            routes[v] = [0] + [city_id for city_id, _ in vehicle_cities] + [0]

        return routes

    def compute_cost(self, x_vals: List[float], p_vals: List[float]) -> float:
        """
        Avalia o custo do Hamiltoniano H_total = H_dist + H_penalty
        diretamente a partir das amostras/valores esperados medidos no circuito.
        """
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        
        cost_dist = 0.0
        penalty_col = 0.0

        # 1. PENALIDADE DE COLISÃO (H_penalty)
        # Dois qumodes não podem compartilhar o mesmo veículo (p) e mesmo tempo (x)
        for i in range(self.num_free_cities):
            for j in range(i + 1, self.num_free_cities):
                if p_disc[i] == p_disc[j] and x_disc[i] == x_disc[j]:
                    penalty_col += self.lmbda

        # 2. CUSTO DE DISTÂNCIA (H_dist)
        routes = self.decode_routes(x_vals, p_vals)
        for v, route in routes.items():
            for k in range(len(route) - 1):
                u, w = route[k], route[k + 1]
                cost_dist += self.dist_matrix[u, w]

        return float(cost_dist + penalty_col)


# Alias de compatibilidade
VRPCVHamiltonian = Hamiltonian


# --- BLOCO DE TESTES E VALIDAÇÃO ---
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # --- RESOLUÇÃO DE IMPORTS ---
    SRC_DIR = Path(__file__).resolve().parent.parent
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    from graphs import GraphBuilder

    num_free_cities = 3  # Depósito (0) + 3 Cidades Livres (1, 2, 3)
    gb = GraphBuilder(n=num_free_cities + 1, seed=42)

    print("--- TESTANDO HAMILTONIANO VRP (CV-SPACE) ---")
    print("Matriz de Adjacência do Grafo (0 é o Depósito):")
    print(gb.matrix)
    print("------------------------------------------------\n")

    # Instancia o Hamiltoniano VRP
    vrp_hamiltonian = Hamiltonian(gb.matrix, num_vehicles=2, lmbda=100.0)

    # Exemplo de teste manual de uma medição quântica contínua (x, p):
    sample_x = [1.02, 2.05, 1.10]  # C1 no tempo 1, C2 no tempo 2, C3 no tempo 1
    sample_p = [0.95, 1.01, 1.98]  # C1 no veículo 1, C2 no veículo 1, C3 no veículo 2

    custo_solucao = vrp_hamiltonian.compute_cost(sample_x, sample_p)
    rotas_decodificadas = vrp_hamiltonian.decode_routes(sample_x, sample_p)

    x_d, p_d = vrp_hamiltonian.discretize_quadratures(sample_x, sample_p)
    print(f"Valores discretizados obtidos: x (Tempos) = {x_d}, p (Veículos) = {p_d}")
    print(f"Rotas por Veículo: {rotas_decodificadas}")
    print(f"Custo total calculado: {custo_solucao:.4f}")