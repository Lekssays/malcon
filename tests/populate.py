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

base = 'peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile {path}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:1151 --tlsRootCertFiles {path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '.format(path=base_path)

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
    _tmp = path.split("/")
    _id = "MAL_" + str(random.randint(10000, 999999))
    _name = _tmp[-1]
    _path = path
    _type = "bot"
    _checksum = hashlib.md5(path.encode()).hexdigest()
    _timestamp = str(math.floor(datetime.datetime.now().timestamp()))
    _target = env("CORE_PEER_ID")
    _propagates = "false"
    _mal_actions = '"[\\"M\\"]"'
    _ports = "[1337]"
    return {
        "id": _id,
        "name": _name,
        "path": _path,
        "type": _type,
        "checksum": _checksum,
        "timestamp": _timestamp,
        "target": _target,
        "propagates": _propagates,
        "mal_actions": _mal_actions,
        "ports": _ports
    }

def share_malware(path: str):
    malware_info = get_malware_info(path=path)
    
    t = Template('{"function":"CreateMalware","Args":["$id", "$name", "$path", "$type", "$checksum", "$timestamp", "$target", "$propagates", $mal_actions, "$ports"]}')
    
    create_malware = t.substitute(id=malware_info['id'], name=malware_info['name'], path=malware_info['path'], type=malware_info['type'], checksum=malware_info['checksum'], timestamp=malware_info['timestamp'], target=malware_info['target'], propagates=malware_info['propagates'], mal_actions=malware_info['mal_actions'], ports=malware_info['ports'])
    
    print(create_malware)
    command = base + "'{}'".format(create_malware)
    print(command)
    execute(command=command)

def get_peer_info(neighbors: dict, name: str):
    _id = "PID_" + str(random.randint(10000, 999999))
    _name = name
    _timestamp = str(math.floor(datetime.datetime.now().timestamp()))
    _replica = "true" if random.randint(0, 1) == 1 else "false"
    _reboot = "true" if random.randint(0, 1) == 1 else "false"
    _format = "true" if random.randint(0, 1) == 1 or _reboot == "true" else "false"
    _neighbors = neighbors[name]
    return {
        "id": _id,
        "name": _name,
        "timestamp": _timestamp,
        "replica": _replica,
        "format": _format, 
        "reboot": _reboot,
        "neighbors": _neighbors
    }

def share_peer(neighbors: dict, name: str):
    peer_info = get_peer_info(neighbors=neighbors, name=name)
    
    t = Template('{"function":"CreatePeer","Args":["$name", "$neighbors", "$timestamp", "$id", "$replica", "$reboot", "$format"]}')
    
    neighbors = str(peer_info['neighbors'])
    neighbors = neighbors.replace('\'', '\\"')
    
    create_peer = t.substitute(id=peer_info['id'], name=peer_info['name'], timestamp=peer_info['timestamp'], neighbors=neighbors, replica=peer_info['replica'], reboot=peer_info['reboot'], format=peer_info['format'])
    
    command = base + "'{}'".format(create_peer)
    print("[*] INFO:",create_peer)
    execute(command=command)

def populate_peers(neighbors: dict):
    peers = list(neighbors.keys())
    for peer in peers:
        share_peer(neighbors=neighbors, name=peer)

def main():
    print("Populate Blockchain")
    neighbors = load_neighbors()
    
    populate_peers(neighbors=neighbors)

    share_malware(path="/home/ahmed/workspace/malcon/core/kitkat.dark.mal")

if __name__ == "__main__":
    main()