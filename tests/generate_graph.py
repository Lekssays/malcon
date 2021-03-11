import json

import matplotlib.pyplot as plt
import networkx as nx

def load_neighbors():
    with open("neighbors.json", "r") as f:
        return json.load(f)

def get_edges(neighbors: list):
    peers = list(neighbors.keys())
    edges = []

    for peer in peers:
        for neighbor in neighbors[peer]:
            edges.append((peer, neighbor))
    return edges 

def generate_graph(neighbors: list):
    peers = list(neighbors.keys())

    G = nx.Graph()
    G.add_nodes_from(peers)

    edges = get_edges(neighbors=neighbors)

    G.add_edges_from(edges)

    nx.draw(G)
    plt.savefig("network.png")

def main():
    neighbors = load_neighbors()
    generate_graph(neighbors=neighbors)

if __name__ == '__main__':
    main()
