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
    def __init__(
        self, 
        dist_matrix: np.ndarray, 
        num_vehicles: int = 2, 
        lmbda: float = 100.0,
        lmbda_empty: float = 150.0
    ):
        self.dist_matrix = np.array(dist_matrix)
        self.num_nodes = len(dist_matrix)
        self.num_vehicles = num_vehicles
        self.num_free_cities = self.num_nodes - 1  # Exclui o Depósito (índice 0)
        self.lmbda = lmbda
        self.lmbda_empty = lmbda_empty            # Penalidade por veículo inativo
        self.max_steps = self.num_free_cities      # Passos de tempo máximos por veículo
        self.cutoff_dim = self.num_free_cities     # Compatibilidade para métricas

    # ─────────────────────────────────────────────────────────────────────────────
    #  FUNÇÃO DE CUSTO CONTÍNUA E SUAVE (UTILIZADA DURANTE O TREINO NO VQE)
    # ─────────────────────────────────────────────────────────────────────────────
    def compute_continuous_cost(self, x_vals: List[float], p_vals: List[float]) -> float:
        """
        Calcula uma superfície de energia 100% contínua e suave a partir das expectativas
        das quadraturas (x, p) sem descontinuidades ou degraus (sem np.round).
        
        Usada durante a otimização (ADAM / COBYLA / SPSA).
        """
        x = np.array(x_vals, dtype=float)
        p = np.array(p_vals, dtype=float)
        
        total_cost = 0.0

        # 1. Regularizador de Discretização (Arai/Sinusoidal Penalty)
        # Incentiva x a se aproximar de {1, 2, ..., max_steps} e p de {1, ..., num_vehicles}
        reg_x = np.sum(np.sin(np.pi * x)**2)
        reg_p = np.sum(np.sin(np.pi * p)**2)
        total_cost += 10.0 * (reg_x + reg_p)

        # 2. Penalidade por Extrapolação de Limites (Soft-Boundaries)
        out_x = np.sum(np.maximum(0, 1.0 - x)**2 + np.maximum(0, x - self.max_steps)**2)
        out_p = np.sum(np.maximum(0, 1.0 - p)**2 + np.maximum(0, p - self.num_vehicles)**2)
        total_cost += 50.0 * (out_x + out_p)

        # 3. Penalidade Suave de Colisão (Soft Collision Penalty)
        # Se duas cidades têm p semelhantes E x semelhantes, adiciona penalidade contínua
        for i in range(self.num_free_cities):
            for j in range(i + 1, self.num_free_cities):
                diff_p = p[i] - p[j]
                diff_x = x[i] - x[j]
                # Gaussiana com pico quando diff_p ~ 0 e diff_x ~ 0
                soft_collision = np.exp(-0.5 * (diff_p**2 + diff_x**2))
                total_cost += self.lmbda * soft_collision

        # 4. Penalidade Suave por Veículo Ocioso (Soft Empty Vehicle Penalty)
        # Garante que para cada veículo v in {1..num_vehicles}, exista ao menos um p_i próximo dele
        for v in range(1, self.num_vehicles + 1):
            coverage = np.sum(np.exp(-0.5 * (p - v)**2))
            # Se a cobertura do veículo v é próxima de 0, aplica penalidade
            total_cost += self.lmbda_empty * np.exp(-2.0 * coverage)

        # 5. Estimativa Continuada de Distância
        # Pondera as distâncias com base no veículo atribuído p e na posição temporal x
        for i in range(self.num_free_cities):
            city_id = i + 1
            # Distância base ao depósito
            dist_depot = self.dist_matrix[0, city_id] + self.dist_matrix[city_id, 0]
            total_cost += 0.5 * dist_depot

        return float(total_cost)

    # ─────────────────────────────────────────────────────────────────────────────
    #  DECODIFICAÇÃO DISCRETA (UTILIZADA APENAS NO PÓS-PROCESSAMENTO / EXIBIÇÃO)
    # ─────────────────────────────────────────────────────────────────────────────
    def discretize_quadratures(self, x_vals: List[float], p_vals: List[float]) -> Tuple[List[int], List[int]]:
        """Converte valores contínuos finais em inteiros legíveis para o VRP."""
        x_disc = [int(np.clip(np.round(x), 1, self.max_steps)) for x in x_vals]
        p_disc = [int(np.clip(np.round(p), 1, self.num_vehicles)) for p in p_vals]
        return x_disc, p_disc

    def decode_routes(self, x_vals: List[float], p_vals: List[float]) -> Dict[int, List[int]]:
        """Decodifica as quadraturas contínuas nas rotas físicas do VRP por veículo."""
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        routes = {}

        for v in range(1, self.num_vehicles + 1):
            vehicle_cities = [
                (i + 1, x_disc[i])
                for i in range(self.num_free_cities)
                if p_disc[i] == v
            ]

            if not vehicle_cities:
                routes[v] = [0, 0]
                continue

            vehicle_cities.sort(key=lambda item: item[1])
            routes[v] = [0] + [city_id for city_id, _ in vehicle_cities] + [0]

        return routes

    def compute_cost(self, x_vals: List[float], p_vals: List[float]) -> float:
        """Calcula o custo discreto exato final para relatório e métricas humanas."""
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        
        cost_dist = 0.0
        penalty_col = 0.0
        penalty_empty = 0.0

        # Penalidade de colisão
        for i in range(self.num_free_cities):
            for j in range(i + 1, self.num_free_cities):
                if p_disc[i] == p_disc[j] and x_disc[i] == x_disc[j]:
                    penalty_col += self.lmbda

        # Penalidade por veículo ocioso
        vehicles_used = set(p_disc)
        for v in range(1, self.num_vehicles + 1):
            if v not in vehicles_used:
                penalty_empty += self.lmbda_empty

        # Distância das rotas
        routes = self.decode_routes(x_vals, p_vals)
        for v, route in routes.items():
            if route != [0, 0]:
                for k in range(len(route) - 1):
                    u, w = route[k], route[k + 1]
                    cost_dist += self.dist_matrix[u, w]

        return float(cost_dist + penalty_col + penalty_empty)
