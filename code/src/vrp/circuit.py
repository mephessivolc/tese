# vrp/circuit.py
from typing import Tuple, List
import numpy as np
import strawberryfields as sf
from strawberryfields import ops


class Circuit:
    """
    Ansatz de Variáveis Contínuas (CV) integrado ao Strawberry Fields para o VRP.
    Suporta camadas variacionais compostas por Squeezing, Beam Splitter, 
    Displacement e Kerr Gates para explorar o espaço de fase (x, p).
    """

    def __init__(self, num_qumodes: int, num_layers: int = 1, reps: int = 1):
        self.num_qumodes = num_qumodes
        self.num_layers = num_layers
        self.reps = reps
        self.num_params = self._calculate_total_params()

    def _calculate_total_params(self) -> int:
        """Calcula o total de parâmetros variacionais independentes do circuito."""
        sgate_params = 2 * self.num_qumodes
        bs_pairs = (self.num_qumodes * (self.num_qumodes - 1)) // 2
        bs_params = 2 * bs_pairs
        dgate_params = 2 * self.num_qumodes
        kgate_params = 1 * self.num_qumodes

        params_per_block = sgate_params + bs_params + dgate_params + kgate_params
        return params_per_block * self.num_layers * self.reps

    def build_program(self) -> Tuple[sf.Program, Tuple]:
        """
        Constrói o programa simbólico do Strawberry Fields.
        Retorna o objeto Program e a tupla de variáveis de parâmetros simbólicos.
        """
        prog = sf.Program(self.num_qumodes)
        
        with prog.context as q:
            # Cria os parâmetros simbólicos declarados no motor do Strawberry Fields
            params_sym = prog.params(*[f"theta_{i}" for i in range(self.num_params)])
            param_idx = 0

            for layer in range(self.num_layers):
                for rep in range(self.reps):

                    # 1. Squeezing Gate S(r, phi) - Controla a incerteza do espaço de fase
                    for i in range(self.num_qumodes):
                        ops.Sgate(params_sym[param_idx], params_sym[param_idx + 1]) | q[i]
                        param_idx += 2

                    # 2. Beam Splitter Gate BS(theta, phi) - Cria emaranhamento entre qumodes
                    for i in range(self.num_qumodes):
                        for j in range(i + 1, self.num_qumodes):
                            ops.BSgate(params_sym[param_idx], params_sym[param_idx + 1]) | (q[i], q[j])
                            param_idx += 2

                    # 3. Displacement Gate D(r, phi) - Desloca a média de (x, p)
                    for i in range(self.num_qumodes):
                        ops.Dgate(params_sym[param_idx], params_sym[param_idx + 1]) | q[i]
                        param_idx += 2

                    # 4. Kerr Gate K(kappa) - Aplica transformação não-linear no espaço de fase
                    for i in range(self.num_qumodes):
                        ops.Kgate(params_sym[param_idx]) | q[i]
                        param_idx += 1

        return prog, params_sym

    def initialize_random_params(self, seed: int = 42) -> np.ndarray:
        rng = np.random.default_rng(seed)
        params = np.zeros(self.num_params, dtype=np.float32)

        param_idx = 0
        for _ in range(self.num_layers * self.reps):
            # Squeezing r pequeno
            for _ in range(self.num_qumodes):
                params[param_idx] = rng.normal(0.0, 0.02)
                params[param_idx + 1] = rng.uniform(0, 2 * np.pi)
                param_idx += 2

            # Beam Splitter
            bs_pairs = (self.num_qumodes * (self.num_qumodes - 1)) // 2
            for _ in range(bs_pairs):
                params[param_idx] = rng.uniform(0, np.pi / 8)
                params[param_idx + 1] = rng.uniform(0, 2 * np.pi)
                param_idx += 2

            # Displacement magnitude r ~ 1.5 para posicionar as quadraturas na faixa útil [1, N]
            for _ in range(self.num_qumodes):
                params[param_idx] = rng.normal(1.5, 0.1)
                params[param_idx + 1] = np.pi / 4  # Ângulo de 45 deg para empurrar tanto x quanto p
                param_idx += 2

            # Kerr kappa muito pequeno para evitar instabilidade numéica
            for _ in range(self.num_qumodes):
                params[param_idx] = rng.normal(0.0, 0.005)
                param_idx += 1

        return params