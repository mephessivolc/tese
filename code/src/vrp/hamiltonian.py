import tensorflow as tf
import numpy as np
from typing import Tuple, List, Dict

class Hamiltonian:
    def __init__(
        self, 
        dist_matrix: np.ndarray, 
        num_vehicles: int = 2, 
        lmbda: float = 100.0,
        lmbda_empty: float = 150.0
    ):
        self.dist_matrix = np.array(dist_matrix, dtype=np.float32)
        self.num_nodes = len(dist_matrix)
        self.num_vehicles = num_vehicles
        self.num_free_cities = self.num_nodes - 1
        self.lmbda = lmbda
        self.lmbda_empty = lmbda_empty
        self.max_steps = self.num_free_cities
        self.cutoff_dim = self.num_free_cities

    def compute_continuous_cost_tf(self, x_tens: tf.Tensor, p_tens: tf.Tensor) -> tf.Tensor:
        """
        Calcula o custo contínuo mantendo 100% das operações no Grafo de Autodiff do TensorFlow.
        Isso garante que tape.gradient() calcule gradientes reais e não-nulos.
        """
        # 1. Penalidade por extrapolação dos limites [1, max_steps] e [1, num_vehicles]
        out_x = tf.reduce_sum(tf.square(tf.maximum(0.0, 1.0 - x_tens)) + tf.square(tf.maximum(0.0, x_tens - float(self.max_steps))))
        out_p = tf.reduce_sum(tf.square(tf.maximum(0.0, 1.0 - p_tens)) + tf.square(tf.maximum(0.0, p_tens - float(self.num_vehicles))))
        
        # 2. Penalidade Suave de Colisão (Gaussiana suave)
        col_penalty = 0.0
        for i in range(self.num_free_cities):
            for j in range(i + 1, self.num_free_cities):
                diff_p = p_tens[i] - p_tens[j]
                diff_x = x_tens[i] - x_tens[j]
                # Atrai se estiverem no mesmo veículo e mesmo instante
                col_penalty += tf.exp(-0.5 * (tf.square(diff_p) + tf.square(diff_x)))

        # 3. Penalidade Suave por Veículo Ocioso
        empty_penalty = 0.0
        for v in range(1, self.num_vehicles + 1):
            coverage = tf.reduce_sum(tf.exp(-0.5 * tf.square(p_tens - float(v))))
            empty_penalty += tf.exp(-2.0 * coverage)

        # 4. Custo Estável de Distância Contínua (Relaxamento)
        dist_cost = 0.0
        for i in range(self.num_free_cities):
            city_id = i + 1
            d_depot = float(self.dist_matrix[0, city_id] + self.dist_matrix[city_id, 0])
            dist_cost += 0.5 * d_depot * tf.square(x_tens[i])

        # Custo Total como Tensor Diferenciável
        total_loss = 20.0 * (out_x + out_p) + self.lmbda * col_penalty + self.lmbda_empty * empty_penalty + 0.1 * dist_cost
        return total_loss

    def discretize_quadratures(self, x_vals: List[float], p_vals: List[float]) -> Tuple[List[int], List[int]]:
        x_disc = [int(np.clip(np.round(x), 1, self.max_steps)) for x in x_vals]
        p_disc = [int(np.clip(np.round(p), 1, self.num_vehicles)) for p in p_vals]
        return x_disc, p_disc

    def decode_routes(self, x_vals: List[float], p_vals: List[float]) -> Dict[int, List[int]]:
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        routes = {}
        for v in range(1, self.num_vehicles + 1):
            vehicle_cities = [(i + 1, x_disc[i]) for i in range(self.num_free_cities) if p_disc[i] == v]
            if not vehicle_cities:
                routes[v] = [0, 0]
                continue
            vehicle_cities.sort(key=lambda item: item[1])
            routes[v] = [0] + [city_id for city_id, _ in vehicle_cities] + [0]
        return routes

    def compute_cost(self, x_vals: List[float], p_vals: List[float]) -> float:
        x_disc, p_disc = self.discretize_quadratures(x_vals, p_vals)
        cost_dist, penalty_col, penalty_empty = 0.0, 0.0, 0.0

        for i in range(self.num_free_cities):
            for j in range(i + 1, self.num_free_cities):
                if p_disc[i] == p_disc[j] and x_disc[i] == x_disc[j]:
                    penalty_col += self.lmbda

        vehicles_used = set(p_disc)
        for v in range(1, self.num_vehicles + 1):
            if v not in vehicles_used:
                penalty_empty += self.lmbda_empty

        routes = self.decode_routes(x_vals, p_vals)
        for v, route in routes.items():
            if route != [0, 0]:
                for k in range(len(route) - 1):
                    cost_dist += self.dist_matrix[route[k], route[k + 1]]

        return float(cost_dist + penalty_col + penalty_empty)