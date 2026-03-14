import networkx as nx
import numpy as np 
import matplotlib.pyplot as plt

class GraphBuilder:

    def __init__(self, n, intergers_number = True):
        self.n = n
        self.integers_numbers = intergers_number
        self._G = self._build()
    
    def _matrix(self):
        if self.integers_numbers:
            return np.random.randint(low=1, high=10, size=(self.n, self.n))
        return np.random.random((self.n, self.n))
    
    def _build(self) -> nx.Graph:

        # matrix = np.ones((n,n))
        matrix = self._matrix()
        print(matrix)

        for i in range(self.n):
            for j in range(i, self.n):
                if i == j:
                    matrix[i,i] = 0
                else:
                    matrix[j,i] = matrix[i,j]
        
        G = nx.from_numpy_array(matrix)

        return G
    
    @property
    def graph(self):
        return self._G

    def draw(self, figsize=(8,6)) -> None:
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

        nx.draw_networkx_edge_labels(self._G, 
            pos, 
            edge_labels=edge_labels, 
            font_color='red'
        )

        plt.show()