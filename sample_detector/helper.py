import datetime
import hashlib
import math
import random
import subprocess

from environs import Env
from string import Template

env = Env()
env.read_env()

detected = []
base_path = "/home/ahmed/workspace/malcon"

init = "export CORE_PEER_TLS_ENABLED=true \
        export CORE_PEER_LOCALMSPID='Org1MSP' \
        export CORE_PEER_TLS_ROOTCERT_FILE={path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt \
        export CORE_PEER_MSPCONFIGPATH={path}/network/crypto-config/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp \
        export CORE_PEER_ADDRESS=0.0.0.0:1151 \
        export FABRIC_CFG_PATH={path}/network/config/".format(path=base_path)

base = 'peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile {path}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:1151 --tlsRootCertFiles {path}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '.format(path=base_path)

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
    detected.append(_path)
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
    
    command = base + "'{}'".format(create_malware)

    try:
        output = subprocess.check_output(init + " && " + command, stderr=subprocess.STDOUT, shell=True, timeout=3, universal_newlines=True)
    except subprocess.CalledProcessError as exc:
        print("[-] ERROR:", exc.returncode, exc.output)
    else:
        print("[*] INFO: {}".format(output))
