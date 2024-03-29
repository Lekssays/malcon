import argparse
import datetime
import hashlib
import json
import math
import random
import subprocess

from environs import Env
from string import Template

env = Env()
env.read_env()

base_path = "/home/ahmed/workspace/malcon"

init = "export CORE_PEER_TLS_ENABLED=true \
        export CORE_PEER_LOCALMSPID='Org1MSP' \
        export CORE_PEER_TLS_ROOTCERT_FILE={path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt \
        export CORE_PEER_MSPCONFIGPATH={path}/network/crypto-config/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp \
        export CORE_PEER_ADDRESS=0.0.0.0:1151 \
        export FABRIC_CFG_PATH={path}/network/config/".format(path=base_path)

base_peer = 'peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile {path}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:1151 --tlsRootCertFiles {path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '.format(path=base_path)
base_malware = 'peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile {path}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n malware  --peerAddresses 0.0.0.0:1151 --tlsRootCertFiles {path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '.format(path=base_path)

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--command',
                        dest = "command",
                        help = "Command to execute: a (all), p (peer), m (malware)",
                        default = "a",
                        required = True)
    return parser.parse_args()

def load_neighbors() -> dict:
    with open("neighbors.json", "r") as f:
        neighbors = json.load(f)
    return neighbors

def execute(command: str):
    try:
        output = subprocess.check_output(init + " && " + command, stderr=subprocess.STDOUT, shell=True, timeout=3, universal_newlines=True)
    except subprocess.CalledProcessError as exc:
        print("[-] ERROR: ", exc.returncode, exc.output)
    else:
        print("[*] INFO: {}".format(output))

def get_malware_info(path: str) -> dict:
    _id = "MAL_" + str(random.randint(10000, 999999))
    _path = path
    _timestamp = str(math.floor(datetime.datetime.now().timestamp()))
    _target = "peer1.org1.example.com"
    _propagates = "false"
    _mal_actions = '"[\\"M\\"]"'
    _ports = "[1337]"
    return {
        "id": _id,
        "path": _path,
        "timestamp": _timestamp,
        "target": _target,
        "propagates": _propagates,
        "mal_actions": _mal_actions,
        "ports": _ports
    }

def share_malware(path: str):
    malware_info = get_malware_info(path=path)
    
    t = Template('{"function":"CreateMalware","Args":["$id", "$path", "$timestamp", "$target", "$propagates", $mal_actions, "$ports"]}')
    
    create_malware = t.substitute(id=malware_info['id'], path=malware_info['path'], timestamp=malware_info['timestamp'], target=malware_info['target'], propagates=malware_info['propagates'], mal_actions=malware_info['mal_actions'], ports=malware_info['ports'])
    
    print(create_malware)
    command = base_malware + "'{}'".format(create_malware)
    print(command)
    execute(command=command)

def get_peer_info(name: str):
    _id = "PID_" + str(random.randint(10000, 999999))
    _name = name
    _timestamp = str(math.floor(datetime.datetime.now().timestamp()))
    _replica = "true" if random.randint(0, 1) == 1 else "false"
    _reboot = "true" if random.randint(0, 1) == 1 else "false"
    return {
        "id": _id,
        "name": _name,
        "timestamp": _timestamp,
        "replica": _replica,
        "reboot": _reboot,
    }

def share_peer(name: str):
    peer_info = get_peer_info(name=name)
    
    t = Template('{"function":"CreatePeer","Args":["$name", "$timestamp", "$id", "$replica", "$reboot"]}')
    
    create_peer = t.substitute(id=peer_info['id'], name=peer_info['name'], timestamp=peer_info['timestamp'], replica=peer_info['replica'], reboot=peer_info['reboot'])
    
    command = base_peer + "'{}'".format(create_peer)
    print("[*] INFO:",create_peer)
    execute(command=command)

def populate_peers(neighbors: dict):
    peers = list(neighbors.keys())
    for peer in peers:
        share_peer(name=peer)

def main():
    print("Populate Blockchain")
    command = parse_args().command
    neighbors = load_neighbors()
    
    if command == "a":
        populate_peers(neighbors=neighbors)
        share_malware(path="/client/kitkat.dark.mal")
    elif command == "p":
        populate_peers(neighbors=neighbors)
    elif command == "m":
        share_malware(path="/client/kitkat.dark.mal")
    else :
        print("Command not found :)")

if __name__ == "__main__":
    main()