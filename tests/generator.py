#!/usr/bin/python3
import argparse
import json
import random

from collections import defaultdict

REDIS_PORTS = []
WEB_PORTS = []
OPERATIONS_PORTS = []
GOSSIP_PORTS = []

def generate_random_ports():
    for i in range(8000, 13000):
        GOSSIP_PORTS.append(i)

    for i in range(13001, 33000):
        REDIS_PORTS.append(i)

    for i in range(33001, 48000):
        WEB_PORTS.append(i)

    for i in range(48001, 58000):
        OPERATIONS_PORTS.append(i)    

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-o', '--orgs',
                        dest = "orgs",
                        help = "Orgs Number",
                        default = 3,
                        required = True)
    parser.add_argument('-p', '--peers',
                        dest = "peers",
                        help = "Number of Peers per Org",
                        default = 2,
                        required = True)
    return parser.parse_args()

def generate_peers(orgs: int, peers: int) -> list:
    peers_list = []
    for org in range(1, orgs + 1):
        for peer in range(0, peers):
            peers_list.append("peer{}.org{}.example.com".format(str(peer), str(org)))
    return peers_list

def get_org_id(peer: str):
    org = peer.split(".")
    org = org[1].split("org")
    return org[1][-1]

def is_admin(peer: str):
    peer = peer.split(".")
    peer = peer[0]
    if len(peer) == 5 and peer[-1] == "0":
        return True
    return False

def generate_ports(peers: list) -> list:
    peers_ports = []
    for peer in peers:
        redis_port = REDIS_PORTS[random.randint(0, len(REDIS_PORTS) - 1)]
        REDIS_PORTS.remove(redis_port)
        web_port = WEB_PORTS[random.randint(0, len(WEB_PORTS) - 1)]
        WEB_PORTS.remove(web_port)
        gossip_port = GOSSIP_PORTS[random.randint(0, len(GOSSIP_PORTS) - 1)]
        GOSSIP_PORTS.remove(gossip_port)
        operations_port = OPERATIONS_PORTS[random.randint(0, len(OPERATIONS_PORTS) - 1)]
        OPERATIONS_PORTS.remove(operations_port)
        peer_dict = {
            'peer': peer,
            'ports': {
                'redis': redis_port,
                'web': web_port,
                'gossip': int("1" + get_org_id(peer=peer) + "51") if is_admin(peer=peer) else gossip_port,
                'operations': operations_port
            }
        }
        peers_ports.append(peer_dict)
    return peers_ports

def save(peers_ports: list):
    with open('peers_ports.json', 'w') as f:
        json.dump(peers_ports , f)

def get_redis_port(peer: str, peers_ports: list):
    for e in peers_ports:
        if e['peer'] == peer:
            return str(e['ports']['redis'])

def write(filename: str, content: str):
    writing_file = open(filename, "w")
    writing_file.write(content)
    writing_file.close()

def generate_redis_config(peers_ports: list):
    base_filename = "../adminclient/redis.conf"
    for e in peers_ports:
        peer = e['peer']
        port = str(e['ports']['redis'])
        reading_file = open(base_filename, "r")
        content = reading_file.read()
        content = content.replace("XXXXX", port)
        reading_file.close()
        filename = "../adminclient/" + peer + ".rd.conf" if is_admin(peer=peer) else "../peerclient/" + peer + ".rd.conf" 
        write(filename=filename, content=content)

def get_org(peer: str):
    org = peer.split(".")
    return org[1]

def get_org_msp(peer: str):
    org = get_org(peer=peer)
    org = org.capitalize() + "MSP"
    return org

def get_orgs_peers(peers: list) -> defaultdict:
    org_peers = defaultdict(list)
    for peer in peers:
        p_org = get_org(peer=peer)
        org_peers[p_org].append(peer)
    return org_peers

def generate_neighbors(peers: list, topology: str, org_peers: defaultdict):
    neighbors = defaultdict(list)
    bucket = peers
    if topology == "SR":
        for peer in peers:
            org = get_org(peer=peer)
            admin = "peer0." + org + ".example.com"
            if admin == peer:
                continue
            neighbors[peer].append(admin)
    elif topology == "FC":
        orgs = list(org_peers.keys())
        for org in orgs:
            for peer in org_peers[org]:
                neighbors[peer] = org_peers[org]

    elif topology == "M":
        for peer in peers:
            for i in range(1, random.randint(1, 7)):
                t_peer = bucket[random.randint(0, len(bucket) - 1)]
                neighbors[peer].append(t_peer)
                neighbors[t_peer].append(peer)
                bucket.remove(t_peer)
    return neighbors

def generate_docker_configs(peers_ports: list, neighbors: defaultdict) -> list:
    configs = []
    peers = []
    base_filename = "./templates/peer_template.yaml"
    for e in peers_ports:
        config_file = open(base_filename, "r")
        content = config_file.read()
        content = content.replace("gossip_port", str(e['ports']['gossip']))
        content = content.replace("core_id", e['peer'])
        content = content.replace("redis_port", str(e['ports']['redis']))
        content = content.replace("web_port", str(e['ports']['web']))
        content = content.replace("operations_port", str(e['ports']['operations']))
        content = content.replace("org_id", get_org(peer=e['peer']))
        content = content.replace("org_msp", get_org_msp(peer=e['peer']))
        content = content.replace("neighbors", ",".join(neighbors[e['peer']]))
        if is_admin(peer=e['peer']):
            content = content.replace("client_path", "adminclient")
            content = content.replace("core_path", "core")
        else:
            content = content.replace("client_path", "peerclient")
        config_file.close()
        configs.append(content)
        peers.append(e['peer'])
    return configs, peers

def generate_docker_compose(configs: list, peers: list):
    main_config = ""
    base_file = open("./templates/base_template.yaml", "r")
    base = base_file.read()
    base_file.close()

    main_config = base + "\n"

    for config in configs:
        main_config += config + "\n"

    cli_file = open("./templates/cli_template.yaml", "r")
    cli = cli_file.read()
    cli_file.close()    

    main_config += cli + "\n"

    for peer in peers:
        main_config += "    - {}\n".format(peer)

    write(filename="docker_compose_test.yml", content=main_config)

def main():
    print("Config generator for malcon experiments")
    orgs = int(parse_args().orgs)
    peers = int(parse_args().peers)

    generate_random_ports()

    peers_list = generate_peers(orgs=orgs, peers=peers)
   
    neighbors = generate_neighbors(peers=peers_list, org_peers=get_orgs_peers(peers=peers_list), topology="M")
    
    peers_ports = generate_ports(peers=peers_list)
    save(peers_ports=peers_ports)

    generate_redis_config(peers_ports=peers_ports)
    configs, peers = generate_docker_configs(peers_ports=peers_ports, neighbors=neighbors)
    generate_docker_compose(configs=configs, peers=peers)

if __name__ == "__main__":
    main()