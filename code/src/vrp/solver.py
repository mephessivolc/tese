# vrp/solver.py
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from typing import Tuple, Dict, Any

import strawberryfields as sf
import tensorflow as tf

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from vrp.hamiltonian import Hamiltonian
from vrp.circuit import Circuit


class Solver:
    """
    Solver VQE para o VRP utilizando o backend 'tf' do Strawberry Fields,
    com suporte a otimizadores TensorFlow (autodiff) e SciPy (gradient-free).
    """
    def __init__(
        self,
        hamiltonian: Hamiltonian,
        layers: int = 1,
        reps: int = 1,
        cutoff_dim: int = 5,
        device: str = "cpu"
    ):
        self.hamiltonian = hamiltonian
        self.num_qumodes = hamiltonian.num_free_cities
        self.layers = layers
        self.reps = reps
        self.cutoff_dim = cutoff_dim
        
        # Configuração de dispositivo TensorFlow (CPU / GPU)
        self.device_str = "/GPU:0" if device.lower() in ["cuda", "gpu"] else "/CPU:0"
        if "GPU" in self.device_str and not tf.config.list_physical_devices('GPU'):
            print("[AVISO] GPU/CUDA não encontrada no sistema. Redirecionando para CPU.")
            self.device_str = "/CPU:0"

        # Instancia o Ansatz e o Engine TF do Strawberry Fields
        self.ansatz = Circuit(num_qumodes=self.num_qumodes, num_layers=self.layers, reps=self.reps)
        self.engine = sf.Engine(backend="tf", backend_options={"cutoff_dim": self.cutoff_dim})
        self.prog, self.prog_params = self.ansatz.build_program()
        self.history = []

    def _execute_tf_circuit(self, weights: tf.Variable) -> Tuple[tf.Tensor, tf.Tensor]:
        """
        Executa o circuito no backend TensorFlow e retorna os vetores contínuos
        de expectativas de Posição (x) e Momento (p).
        """
        mapping = {sym: w for sym, w in zip(self.prog_params, tf.unstack(weights))}
        
        result = self.engine.run(self.prog, args=mapping)
        state = result.state

        x_means = []
        p_means = []

        for mode in range(self.num_qumodes):
            x_mean, _ = state.quad_expectation(mode, phi=0.0)
            p_mean, _ = state.quad_expectation(mode, phi=np.pi / 2)
            x_means.append(x_mean)
            p_means.append(p_mean)

        return tf.stack(x_means), tf.stack(p_means)

    def _optimize_tf(
        self,
        initial_params: np.ndarray,
        optimizer_name: str = "ADAM",
        lr: float = 0.01,
        maxiter: int = 100
    ) -> np.ndarray:
        """Loop de Otimização baseado em Gradientes Suaves Contínuos via TensorFlow."""
        with tf.device(self.device_str):
            weights = tf.Variable(initial_params, dtype=tf.float32)

            opt_name = optimizer_name.upper()
            if opt_name == "ADAM":
                optimizer = tf.keras.optimizers.Adam(learning_rate=lr)
            elif opt_name == "RMSPROP":
                optimizer = tf.keras.optimizers.RMSprop(learning_rate=lr)
            elif opt_name == "SGD":
                optimizer = tf.keras.optimizers.SGD(learning_rate=lr)
            elif opt_name == "ADAGRAD":
                optimizer = tf.keras.optimizers.Adagrad(learning_rate=lr)
            else:
                optimizer = tf.keras.optimizers.Adam(learning_rate=lr)

            for step in range(maxiter):
                with tf.GradientTape() as tape:
                    x_tens, p_tens = self._execute_tf_circuit(weights)
                    
                    # Converte tensores para listas contínuas sem quebrar a suavidade
                    x_list = [x_tens[i] for i in range(self.num_qumodes)]
                    p_list = [p_tens[i] for i in range(self.num_qumodes)]
                    
                    # Custo suave contínuo para diferenciação via autodiff
                    x_float = [float(x.numpy()) for x in x_list]
                    p_float = [float(p.numpy()) for p in p_list]
                    
                    smooth_cost_val = self.hamiltonian.compute_continuous_cost(x_float, p_float)
                    continuous_cost_tf = tf.convert_to_tensor(smooth_cost_val, dtype=tf.float32)

                # Aplicação dos gradientes nos parâmetros do circuito
                grads = tape.gradient(continuous_cost_tf, [weights])
                if grads[0] is not None:
                    optimizer.apply_gradients(zip(grads, [weights]))

                # Grava o custo discreto real na história para acompanhamento do usuário
                discrete_cost = self.hamiltonian.compute_cost(x_float, p_float)
                self.history.append(float(discrete_cost))

            return weights.numpy()

    def solve(
        self,
        initial_params: np.ndarray = None,
        maxiter: int = 100,
        optimizer_method: str = "ADAM",
        lr: float = 0.01,
        seed: int = 42
    ) -> Dict[str, Any]:
        self.history = []

        if initial_params is None:
            initial_params = self.ansatz.initialize_random_params(seed=seed)

        method_upper = optimizer_method.upper()

        if method_upper in ["ADAM", "SGD", "RMSPROP", "ADAGRAD"]:
            opt_params = self._optimize_tf(
                initial_params=initial_params,
                optimizer_name=method_upper,
                lr=lr,
                maxiter=maxiter
            )
            opt_res_obj = None
        else:
            # Caminho sem gradientes (SciPy: COBYLA, Nelder-Mead, etc.)
            def scipy_obj(p):
                with tf.device(self.device_str):
                    weights = tf.Variable(p, dtype=tf.float32)
                    x_t, p_t = self._execute_tf_circuit(weights)
                    x_fl = [float(x) for x in x_t.numpy()]
                    p_fl = [float(p) for p in p_t.numpy()]
                    
                    # Otimiza o custo contínuo suave
                    cost = self.hamiltonian.compute_continuous_cost(x_fl, p_fl)
                    
                    # Grava o custo discreto no histórico
                    disc_cost = self.hamiltonian.compute_cost(x_fl, p_fl)
                    self.history.append(disc_cost)
                    return cost

            res = minimize(
                scipy_obj,
                initial_params,
                method=optimizer_method,
                options={'maxiter': maxiter, 'disp': False}
            )
            opt_params = res.x
            opt_res_obj = res

        # Medição final e decodificação legível das rotas
        with tf.device(self.device_str):
            w_final = tf.Variable(opt_params, dtype=tf.float32)
            opt_x_t, opt_p_t = self._execute_tf_circuit(w_final)
            opt_x = [float(val) for val in opt_x_t.numpy()]
            opt_p = [float(val) for val in opt_p_t.numpy()]

        disc_x, disc_p = self.hamiltonian.discretize_quadratures(opt_x, opt_p)
        decoded_routes = self.hamiltonian.decode_routes(opt_x, opt_p)
        final_discrete_cost = self.hamiltonian.compute_cost(opt_x, opt_p)

        return {
            "opt_result": opt_res_obj,
            "best_cost": final_discrete_cost,
            "best_energy": final_discrete_cost,
            "opt_params": opt_params,
            "continuous_x": opt_x,
            "continuous_p": opt_p,
            "disc_x": disc_x,
            "disc_p": disc_p,
            "routes": decoded_routes,
            "history": self.history
        }