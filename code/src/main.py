# main.py (na raiz do projeto)
from tsp.main import run as run_tsp
from vrp.main import run as run_vrp

def main():
    print("=== INICIANDO BATCH DE EXPERIMENTOS CV-VQE ===")

    # 1. Executa TSP com 4 cidades
    res_tsp = run_tsp(
        n_cities=4,
        maxiter=60,
        optimizer_method="COBYLA",
        seed=42
    )

    # 2. Executa VRP com 4 cidades e 2 veículos
    res_vrp = run_vrp(
        n_cities=4,
        num_vehicles=2,
        maxiter=60,
        optimizer_method="COBYLA",
        seed=42
    )

    # Exemplo de acesso direto aos resultados sem reescrever nada
    print(f"\n[Resumo Final]")
    print(f"Custo TSP (VQE): {res_tsp['quantum_cost']:.4f}")
    print(f"Custo VRP (VQE): {res_vrp['quantum_cost']:.4f}")

if __name__ == "__main__":
    main()