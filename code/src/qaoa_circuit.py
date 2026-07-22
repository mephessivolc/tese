from typing import List
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import Dgate, Rgate, BSgate


class QAOACircuit:
    """
    Monta, desenha e executa o circuito variacional CV-QAOA no Strawberry Fields
    para um Hamiltoniano codificado na base de Fock, utilizando a dualidade
    Posição-Momento (x <-> p) na camada de mistura.
    """
    def __init__(self, hamiltonian_builder):
        """
        Parameters
        ----------
        hamiltonian_builder : Hamiltonian
            Instância da classe Hamiltonian contendo as matrizes e o cutoff.
        """
        self.hb = hamiltonian_builder
        self.N = hamiltonian_builder.N
        self.cutoff_dim = hamiltonian_builder.cutoff_dim
        _, _, self.H_total_matrix = self.hb.get_hamiltonian_matrices()

    def cost_hamiltonian(self, q: sf.Program, gamma: float) -> None:
        """
        Aplica o operador unitário da Camada de Custo: U(H_C, gamma) = e^{-i gamma H_C(x)}
        no espaço de Posição (x).
        """
        # Rotações de fase individuais em cada qumode
        for k in range(self.N):
            Rgate(gamma) | q[k]

        # Acoplamento de custo entre qumodes vizinhos (ciclo/adjacência)
        for k in range(self.N - 1):
            BSgate(gamma * 0.5, 0.0) | (q[k], q[k + 1])

    def mixer_hamiltonian(self, q: sf.Program, beta: float) -> None:
        """
        Aplica o operador unitário da Camada de Mistura: U(H_M, beta) = e^{-i beta H_M(p)}
        utilizando a Transformada de Fourier / Dualidade Posição-Momento (x <-> p).
        """
        # 1. Mapeamento para o espaço de Momento (x -> p)
        for k in range(self.N):
            Rgate(np.pi / 2) | q[k]

        # 2. Mistura/Difusão de estados via Beam Splitter no espaço p
        for k in range(self.N):
            for j in range(k + 1, self.N):
                BSgate(beta, 0.0) | (q[k], q[j])

        # 3. Retorno ao espaço de Posição (p -> x)
        for k in range(self.N):
            Rgate(-np.pi / 2) | q[k]

    def build_circuit(
        self, 
        gamma_params: List[float], 
        beta_params: List[float], 
        alpha_init: float = 0.8
    ) -> sf.Program:
        """
        Orquestra a preparação do estado inicial e a aplicação alternada
        das camadas de Custo e Mistura para p-steps de CV-QAOA.
        """
        p = len(gamma_params)
        prog = sf.Program(self.N)

        with prog.context as q:
            # 1. PREPARAÇÃO DO ESTADO INICIAL |psi_0>
            for k in range(self.N):
                Dgate(alpha_init) | q[k]

            # 2. APLICAÇÃO DAS P CAMADAS VARIACIONAIS
            for layer in range(p):
                gamma = gamma_params[layer]
                beta = beta_params[layer]

                # Executa o Hamiltoniano de Custo (em x)
                self.cost_hamiltonian(q, gamma)

                # Executa o Hamiltoniano de Mistura (em p)
                self.mixer_hamiltonian(q, beta)

        return prog

    def draw_circuit(
        self, 
        p_layers: int = 1, 
        filename: str = None,
    ) -> sf.Program:
        """
        Gera a representação do circuito quântico e exporta para formato LaTeX/TeX.

        Parameters
        ----------
        p_layers : int, optional
            Número de camadas (p) para desenhar o circuito.
        filename : str, optional
            Caminho do arquivo de saída (ex: "images/qaoa_circuit.tex").

        Returns
        -------
        sf.Program
            O programa montado que foi visualizado.
        """
        # Usa parâmetros simbólicos/fictícios apenas para visualização
        gamma_params = [0.5] * p_layers
        beta_params = [0.5] * p_layers

        prog = self.build_circuit(gamma_params, beta_params)

        print("\n=== ESTRUTURA DO CIRCUITO QUÂNTICO (Strawberry Fields) ===")
        prog.print()
        print("==========================================================\n")

        # Exporta o circuito em formato LaTeX (Circuitikz)
        if filename:
            try:
                # Tenta utilizar a API nativa de exportação LaTeX do Strawberry Fields
                from strawberryfields.circuit_drawer import circuit_drawer
                tex_code = circuit_drawer(prog)
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(tex_code)
                    
                print(f"[OK] Código TeX/LaTeX do circuito exportado para: {filename}")
            except Exception as e:
                # Fallback caso a função de desenho nativa varie entre versões
                try:
                    prog.draw_circuit(tex_dir=filename)
                    print(f"[OK] Desenho do circuito exportado para: {filename}")
                except Exception as e2:
                    print(f"[Aviso] Não foi possível exportar a imagem em TeX: {e2}")

        return prog
    
    def get_solution_vector(self, opt_params: np.ndarray, p_layers: int = 1) -> dict:
        """
        Executa o circuito final com os parâmetros otimizados e extrai 
        o vetor de estado (distribuição de fótons nos qumodes) mais provável.
        """
        prog = self.build_circuit(opt_params[:p_layers], opt_params[p_layers:])
        engine = sf.Engine(backend="fock", backend_options={"cutoff_dim": self.cutoff_dim})
        state = engine.run(prog).state

        # Extrai o vetor de probabilidades do estado final (Fock space)
        probs = state.all_fock_probs()
        
        # Encontra a combinação de estados com maior probabilidade
        max_idx = np.unravel_index(np.argmax(probs), probs.shape)
        max_prob = probs[max_idx]

        return {
            "state_vector": list(max_idx), # Vetor de ocupação de fótons por qumode
            "probability": max_prob
        }

    def evaluate_energy(
        self, 
        params: np.ndarray, 
        p_layers: int, 
        backend_options: dict = None
    ) -> float:
        """
        Executa o circuito no backend 'fock' e calcula o valor esperado <H_total>.
        """
        gamma_params = params[:p_layers]
        beta_params = params[p_layers:]

        prog = self.build_circuit(gamma_params, beta_params)

        if backend_options is None:
            backend_options = {"cutoff_dim": self.cutoff_dim}

        engine = sf.Engine(backend="fock", backend_options=backend_options)
        
        results = engine.run(prog)
        state = results.state

        if state.is_pure:
            ket = state.ket().flatten()
            
            if len(ket) != self.H_total_matrix.shape[0]:
                raise ValueError(
                    f"Incompatibilidade de Cutoff: O estado simulado tem dimensão {len(ket)}, "
                    f"mas o Hamiltoniano espera {self.H_total_matrix.shape[0]}."
                )
                
            expectation_value = np.real(np.vdot(ket, self.H_total_matrix @ ket))
        else:
            rho = state.dm()
            dim_total = self.H_total_matrix.shape[0]
            rho_2d = rho.reshape((dim_total, dim_total))
            expectation_value = np.real(np.trace(rho_2d @ self.H_total_matrix))

        return float(expectation_value)


if __name__ == "__main__":
    from hamiltonian import Hamiltonian
    from graphs import GraphBuilder
    from get_paths import get_images_path

    print("--- TESTANDO VISUALIZAÇÃO E DESENHO DO CIRCUITO ---")
    
    # 1. Instancia Grafo e Hamiltoniano
    N_cities = 3
    graph_builder = GraphBuilder(n=N_cities, seed=42)
    hamiltonian_builder = Hamiltonian(graph_builder.matrix, lmbda=50.0)

    # 2. Instancia o Circuito
    circuit = QAOACircuit(hamiltonian_builder)

    # 3. Testa o método draw_circuit salvando na pasta de imagens do projeto
    output_tex = get_images_path() / "qaoa_circuit.tex"
    circuit.draw_circuit(p_layers=1) #, filename=str(output_tex))

    print("[SUCESSO] Teste do método de desenho concluído!")