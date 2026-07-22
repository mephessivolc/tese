import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from pathlib import Path

from get_paths import get_images_path


class GraphBuilder:
    def __init__(self, n: int = 3, seed: int = 42):
        self.n = n
        self.seed = seed
        self.matrix = self._generate_matrix()

    def _generate_matrix(self) -> np.ndarray:
        np.random.seed(self.seed)
        # Matriz simétrica com diagonal zero (sem laços)
        adj = np.random.uniform(1.0, 10.0, size=(self.n, self.n))
        adj = (adj + adj.T) / 2.0
        np.fill_diagonal(adj, 0.0)
        return np.round(adj, 2)

    def _convert_qaoa_vector_to_route(self, vector) -> list:
        """
        Converte qualquer formato de entrada (tupla, lista simples [0, 1, 2]
        ou vetor binário N^2 do QAOA) em uma lista Python simples de nós.
        """
        # Se for uma tupla ou numpy array, garante a conversão inicial para lista
        if isinstance(vector, (tuple, np.ndarray)):
            vector = list(vector)

        # Se for um vetor de estados do QAOA de tamanho N^2
        if len(vector) == self.n ** 2:
            matrix_form = np.array(vector).reshape((self.n, self.n))
            route = []
            for step in range(self.n):
                city = int(np.argmax(matrix_form[:, step]))
                route.append(city)
            return route

        # Retorna como lista simples de cidades
        return list(vector)

    def plot_graph_and_route(self, solution_vector = None, prefix: str = "tsp") -> tuple:
        """
        Gera duas imagens na pasta de imagens:
        1. Grafo completo original (com pesos das arestas).
        2. Grafo com o trajeto da solução destacado em vermelho com setas.

        Parameters
        ----------
        solution_vector : list, tuple or np.ndarray, optional
            Vetor/Rota de solução (ex: (0, 1, 2) do CA ou estado binário do QAOA).
        prefix : str
            Prefixo para nomear as imagens geradas.

        Returns
        -------
        tuple
            (Path do grafo original, Path do grafo com trajeto)
        """
        images_dir = get_images_path()
        
        # Cria o grafo completo não-direcionado
        G = nx.Graph()
        for i in range(self.n):
            G.add_node(i, label=f"Cidade {i}")
            for j in range(i + 1, self.n):
                G.add_edge(i, j, weight=self.matrix[i, j])

        # Posições fixas dos nós usando layout baseado na seed
        pos = nx.spring_layout(G, seed=self.seed)

        # -------------------------------------------------------------
        # 1. GERAR IMAGEM DO GRAFO ORIGINAL
        # -------------------------------------------------------------
        plt.figure(figsize=(7, 6))
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=700)
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        nx.draw_networkx_edges(G, pos, edge_color='gray', width=1.5, alpha=0.7)

        labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=10)

        plt.title(f"Grafo Original do TSP (N={self.n} Cidades)", fontsize=12)
        plt.axis('off')

        orig_path = images_dir / f"{prefix}_graph_original.png"
        plt.savefig(orig_path, dpi=300, bbox_inches='tight')
        plt.close()

        # -------------------------------------------------------------
        # 2. GERAR IMAGEM DO GRAFO COM O TRAJETO DESTACADO
        # -------------------------------------------------------------
        route_path = None
        if solution_vector is not None:
            # Trata e converte a entrada para lista simples
            route = self._convert_qaoa_vector_to_route(solution_vector)
            
            # Fecha o ciclo do TSP voltando para a cidade inicial
            full_cycle = route + [route[0]]

            # Cria grafo direcionado para desenhar as setas do trajeto
            G_directed = nx.DiGraph()
            for i in range(self.n):
                G_directed.add_node(i)

            route_edges = []
            for i in range(len(full_cycle) - 1):
                u, v = full_cycle[i], full_cycle[i + 1]
                G_directed.add_edge(u, v, weight=self.matrix[u, v])
                route_edges.append((u, v))

            plt.figure(figsize=(7, 6))
            
            # Desenha fundo suave (arestas não utilizadas no ciclo)
            nx.draw_networkx_edges(G, pos, edge_color='lightgray', width=1.0, style='dashed', alpha=0.5)

            # Desenha nós
            nx.draw_networkx_nodes(G, pos, node_color='lightgreen', node_size=750)
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')

            # Desenha trajeto em vermelho com setas direcionais
            nx.draw_networkx_edges(
                G_directed, pos, 
                edgelist=route_edges, 
                edge_color='crimson', 
                width=3.0, 
                arrowstyle='->', 
                arrowsize=20
            )

            # Rótulos das distâncias
            nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=10)

            plt.title(f"Trajeto Destacado do TSP: {' -> '.join(map(str, full_cycle))}", fontsize=11)
            plt.axis('off')

            route_path = images_dir / f"{prefix}_graph_route.png"
            plt.savefig(route_path, dpi=300, bbox_inches='tight')
            plt.close()

        return orig_path, route_path

    def draw(self, filename: str = "graph.png") -> Path:
        """Método de conveniência para salvar a visualização do grafo original."""
        orig_path, _ = self.plot_graph_and_route(prefix=filename.replace(".png", ""))
        return orig_path


if __name__ == "__main__":
    graph = GraphBuilder(6)

    print("Matriz utilizada:")
    print(graph.matrix)

    print("\nSalvando imagem do grafo...")
    saved_path = graph.draw("teste.png")
    print(f"[OK] Grafo salvo com sucesso em: {saved_path}")

    # Exemplo de teste com um vetor de solução em tupla
    print("\nSalvando rota de teste...")
    _, route_path = graph.plot_graph_and_route(solution_vector=(0, 2, 4, 1, 5, 3), prefix="teste_rota")
    print(f"[OK] Rota salva com sucesso em: {route_path}")