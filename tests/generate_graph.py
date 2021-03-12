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

def get_label(peer: str) -> str:
    tmp = peer.split(".")
    pid = tmp[0]
    oid = tmp[1]

    label = ""
    if len(pid) == 5:
        label += pid[-1]
    elif len(pid) == 6:
        label += pid[4:5]
    
    label += "/"

    if len(oid) == 4:
        label += oid[-1]
    elif len(pid) == 5:
        label += pid[3:4]

    return label    

def generate_labels(peers: list) -> dict:
    labels = {}
    for peer in peers:
        labels[peer] = get_label(peer=peer)
    return labels

def generate_graph(neighbors: list):
    peers = list(neighbors.keys())
    labels = generate_labels(peers=peers)
    admins = []
    normal = []
    for peer in peers:
        if "peer0" in peer:
            admins.append(peer)
        else:
            normal.append(peer)

    G = nx.Graph()
    G.add_nodes_from(peers)

    edges = get_edges(neighbors=neighbors)

    G.add_edges_from(edges)
    pos = nx.planar_layout(G)
    options = {"node_size": 50, "alpha": 0.8}
    
    nx.draw_networkx_nodes(G, pos, nodelist=admins, node_color="r", **options)
    nx.draw_networkx_nodes(G, pos, nodelist=normal, node_color="y", **options)
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
    nx.draw_networkx_labels(G,pos, labels, font_size=8, font_color='b')

    #plt.savefig("network.png")
    plt.show()

def main():
    neighbors = load_neighbors()
    generate_graph(neighbors=neighbors)

if __name__ == '__main__':
    main()
