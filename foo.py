import networkx as nx
import matplotlib.pyplot as plt

# Criando um grafo direcionado
grafo = nx.DiGraph()

# Adicionando nós
grafo.add_node("Cep")
grafo.add_node("Verificar_Cep")
grafo.add_node("C")

# Adicionando arestas
grafo.add_edge("Cep", "Verificar_Cep")
grafo.add_edge("Verificar_Cep", "C")
grafo.add_edge("C", "Cep")
grafo.add_edge("Cep", "C")

# Função para traçar caminhos específicos
def listar_caminhos(grafo, origem, destino):
    caminhos = list(nx.all_simple_paths(grafo, source=origem, target=destino))
    print(f"Caminhos de {origem} para {destino}:")
    for caminho in caminhos:
        print(" -> ".join(caminho))
    return caminhos

# Traçando os caminhos
listar_caminhos(grafo, "C", "Cep")
listar_caminhos(grafo, "Cep", "C")
listar_caminhos(grafo, "C", "Cep")
listar_caminhos(grafo, "Cep", "Verificar_Cep")

# Visualizando o grafo
nx.draw(grafo, with_labels=True, node_color='lightblue', font_weight='bold')
plt.show()
