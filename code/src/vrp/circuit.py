
import numpy as np
import strawberryfields as sf
from strawberryfields import ops


class Circuit:
    """
    Ansatz de Variáveis Contínuas (CV) integrado ao Strawberry Fields para o VRP.
    
    A arquitetura segue o modelo de Circuito Neural Quântico CV:
      1. Squeezing (Sgate): Ajusta flutuações e covariância nos qumodes.
      2. Interferômetro / Beam Splitters (BSgate): Emaranha as variáveis do VRP.
      3. Displacement (Dgate): Desloca a expectativa das variáveis no espaço de fase.
      4. Kerr Gate (Kgate): Introduz não-gaussianidade essencial para otimização NP-difícil.
    """

    def __init__(self, num_qumodes: int, num_layers: int = 1):
        self.num_qumodes = num_qumodes
        self.num_layers = num_layers
        self.num_params = self._calculate_total_params()

    def _calculate_total_params(self) -> int:
        """Calcula o total exato de parâmetros variacionais necessários."""
        # Por camada:
        # - Sgate: 2 parâmetros (r, phi) por qumode
        # - BSgate: 2 parâmetros (theta, phi) por par de qumodes
        # - Dgate: 2 parâmetros (r, phi) por qumode
        # - Kgate: 1 parâmetro (kappa) por qumode
        sgate_params = 2 * self.num_qumodes
        bs_pairs = (self.num_qumodes * (self.num_qumodes - 1)) // 2
        bs_params = 2 * bs_pairs
        dgate_params = 2 * self.num_qumodes
        kgate_params = 1 * self.num_qumodes

        params_per_layer = sgate_params + bs_params + dgate_params + kgate_params
        return params_per_layer * self.num_layers

    def build_program(self, params: np.ndarray) -> sf.Program:
        """
        Constrói o objeto `sf.Program` do Strawberry Fields pronto para execução.

        Args:
            params (np.ndarray): Vetor 1D de parâmetros variacionais otimizados pelo VQE.

        Returns:
            sf.Program: Programa Strawberry Fields configurado.
        """
        if len(params) != self.num_params:
            raise ValueError(
                f"Esperado {self.num_params} parâmetros, mas foram fornecidos {len(params)}."
            )

        prog = sf.Program(self.num_qumodes)
        param_idx = 0

        with prog.context as q:
            # Loop sobre as camadas (layers) do Ansatz
            for layer in range(self.num_layers):

                # 1. Camada de Squeezing (Sgate)
                for i in range(self.num_qumodes):
                    r = params[param_idx]
                    phi = params[param_idx + 1]
                    ops.Sgate(r, phi) | q[i]
                    param_idx += 2

                # 2. Camada de Emaranhamento Interferométrico (BSgate)
                for i in range(self.num_qumodes):
                    for j in range(i + 1, self.num_qumodes):
                        theta = params[param_idx]
                        phi_bs = params[param_idx + 1]
                        ops.BSgate(theta, phi_bs) | (q[i], q[j])
                        param_idx += 2

                # 3. Camada de Deslocamento (Dgate)
                for i in range(self.num_qumodes):
                    mag = params[param_idx]
                    phase = params[param_idx + 1]
                    ops.Dgate(mag, phase) | q[i]
                    param_idx += 2

                # 4. Camada Não-Gaussiana (Kgate)
                for i in range(self.num_qumodes):
                    kappa = params[param_idx]
                    ops.Kgate(kappa) | q[i]
                    param_idx += 1

        return prog

    def initialize_random_params(self, seed: int = 42) -> np.ndarray:
        """Gera valores iniciais pequenos para os parâmetros variacionais."""
        rng = np.random.default_rng(seed)
        # Valores pequenos evitam estouro numérico na simulação Fock
        return rng.normal(loc=0.0, scale=0.1, size=self.num_params)