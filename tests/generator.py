#!/usr/bin/python3
import argparse
import json
import random

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
    # TODO: check for collisions
    peers_ports = []
    for peer in peers:
        peer_dict = {
            'peer': peer,
            'ports': {
                'redis': random.randint(11000, 22000),
                'web': random.randint(33000, 44000),
                'gossip': int("1" + get_org_id(peer=peer) + "51") if is_admin(peer=peer) else random.randint(8000, 10999),
                'operations': random.randint(33000, 44000)
            }
        }
        peers_ports.append(peer_dict)
    return peers_ports

def save(peers_ports: list):
    with open('peers_ports.json', 'w') as f:
        json.dump(peers_ports , f)

def get_redis_port(peer: str, peers_ports: list):
    port = ""
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

def generate_docker_configs(peers_ports: list) -> list:
    # TODO: generate neighbors
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

    peers_list = generate_peers(orgs=orgs, peers=peers)
    peers_ports = generate_ports(peers=peers_list)
    save(peers_ports=peers_ports)

    generate_redis_config(peers_ports=peers_ports)
    configs, peers = generate_docker_configs(peers_ports=peers_ports)
    generate_docker_compose(configs=configs, peers=peers)

if __name__ == "__main__":
    main()