import networkx as nx
import numpy as np 
import matplotlib.pyplot as plt

from pathlib import Path


def get_path():
    """
    Retorna o diretório onde as imagens serão armazenadas.

    O diretório é criado automaticamente caso não exista.

    Returns
    -------
    Path
        Caminho absoluto para a pasta "images" dentro do diretório atual.
    """
    current_path = Path.cwd()
    img_path = current_path / "images"

    img_path.mkdir(exist_ok=True)

    return img_path


class GraphBuilder:
    """
    Constrói e manipula grafos ponderados a partir de matrizes aleatórias.

    A classe gera uma matriz de adjacência simétrica de tamanho `n x n`,
    cria um grafo não-direcionado utilizando NetworkX e permite visualizar
    o grafo com os pesos das arestas.

    Parameters
    ----------
    n : int
        Número de vértices do grafo.
    intergers_number : bool, optional
        Define se os pesos das arestas serão inteiros ou números reais
        aleatórios. Se True, gera inteiros entre 1 e 9. Caso contrário,
        gera números reais entre 0 e 1.

    Attributes
    ----------
    n : int
        Número de vértices do grafo.
    integers_numbers : bool
        Indica se os pesos são inteiros ou reais.
    _G : networkx.Graph
        Objeto de grafo criado a partir da matriz de adjacência.
    _matrix : numpy.ndarray
        Matriz de adjacência simétrica usada para construir o grafo.
    """

    def __init__(self, n, intergers_number=True):
        """
        Inicializa o construtor de grafos.

        Parameters
        ----------
        n : int
            Número de vértices do grafo.
        intergers_number : bool, optional
            Se True, utiliza pesos inteiros; caso contrário,
            utiliza valores reais aleatórios.
        """
        self.n = n
        self.integers_numbers = intergers_number
        self._G = self._build()
        self._matrix = self._matrix()

    def _matrix(self):
        """
        Gera uma matriz de adjacência simétrica aleatória.

        A matriz possui diagonal principal igual a zero
        (sem auto-laços) e pesos simétricos, garantindo
        um grafo não-direcionado.

        Returns
        -------
        numpy.ndarray
            Matriz de adjacência de dimensão (n, n).
        """
        matrix = np.random.random((self.n, self.n))

        if self.integers_numbers:
            matrix = np.random.randint(low=1, high=10, size=(self.n, self.n))

        for i in range(self.n):
            for j in range(i, self.n):
                if i == j:
                    matrix[i, i] = 0
                else:
                    matrix[j, i] = matrix[i, j]

        return matrix

    @property
    def matrix(self):
        """
        Retorna a matriz de adjacência do grafo.

        Returns
        -------
        numpy.ndarray
            Matriz de adjacência armazenada no objeto.
        """
        return self._matrix

    def _build(self) -> nx.Graph:
        """
        Constrói o grafo a partir da matriz de adjacência.

        Returns
        -------
        networkx.Graph
            Grafo não-direcionado criado a partir da matriz.
        """
        matrix = self._matrix()

        G = nx.from_numpy_array(matrix)

        return G

    @property
    def graph(self):
        """
        Retorna o grafo construído.

        Returns
        -------
        networkx.Graph
            Instância do grafo NetworkX.
        """
        return self._G

    def draw(self, figsize=(8, 6), figname=None) -> None:
        """
        Desenha o grafo utilizando matplotlib.

        O grafo é exibido com os rótulos dos vértices e
        os pesos das arestas. Opcionalmente a figura pode
        ser salva em arquivo.

        Parameters
        ----------
        figsize : tuple, optional
            Tamanho da figura (largura, altura).
        figname : str, optional
            Nome do arquivo para salvar a imagem. Caso
            seja None, a imagem não será salva.
        """
        pos = nx.spring_layout(self._G, seed=7, k=0.5, iterations=100)

        plt.figure(figsize=figsize)
        color_map = ["blue"]

        nx.draw(
            self._G,
            pos,
            node_color=color_map,
            with_labels=True,
            node_size=500,
            font_size=8,
        )

        edge_labels = nx.get_edge_attributes(self._G, 'weight')

        nx.draw_networkx_edge_labels(
            self._G,
            pos,
            edge_labels=edge_labels,
            font_color='red'
        )

        if figname is not None:
            name_file = f"{figname}"
            path = get_path()

            plt.savefig(path / name_file)

        plt.show()