#!/usr/bin/python3
 
import datetime
import json
import math
import subprocess
import threading
import os.path
import redis
import urllib3
import websockets

from Crypto.PublicKey import RSA
from environs import Env
from hashlib import sha512
from iota import Iota
from iota import ProposedTransaction
from iota import Address
from iota import Tag
from iota import TryteString

ENDPOINT = 'https://nodes.devnet.iota.org:443'
API = Iota(ENDPOINT, testnet = True)
env = Env()
env.read_env()
r = redis.Redis(host="0.0.0.0", port=env.int("CORE_PEER_REDIS_PORT"))

async def send_log(message: str):
    uri = "ws://172.17.0.1:7777"
    now = datetime.datetime.now()
    dt = now.strftime("%d/%m/%Y %H:%M:%S")
    message = dt + " - [" + env("CORE_PEER_ID") + "] " + message
    async with websockets.connect(uri) as websocket:
        await websocket.send(message)

def get_tag(resource: str):
    return "MALCON" + resource.upper() + env("VERSION")

def generate_address():
    seed = subprocess.check_output("cat /dev/urandom |tr -dc A-Z9|head -c${1:-81}", shell=True)
    filename = "seed.txt"
    out = open(filename, "w")
    out.write(seed.decode())
    out.close()
    seed = seed.decode()
    
    api = Iota(ENDPOINT, seed, testnet = True)
    security_level = 2
    address = api.get_new_addresses(index=0, count=1, security_level = security_level)['addresses'][0]
    os.environ['IOTA_ADDRESS'] = str(address)
    filename = "address.txt"
    out = open(filename, "w")
    out.write(str(address))
    out.close()
    return str(address)

def get_address():
    if os.path.isfile("address.txt"):
        with open("address.txt") as f:
            return f.readline()
    else:
        return generate_address()

MYADDRESS = get_address()

def get_transactions_by_tag(tag: str, hashes: list, returnAll: bool):
    results = API.find_transaction_objects(tags=[tag])
    if returnAll:
        return results['transactions']
    else:
        transactions = []
        for tx in results['transactions']:
            for tx_hash in hashes:
                cur_timestamp = math.floor(datetime.datetime.now().timestamp())
                if tx_hash == str(tx.hash) and cur_timestamp - int(tx.timestamp) < 300:
                    transactions.append(tx)    
        return transactions

def send_transaction(address: str, message: TryteString, tag: str) -> str:
    tx = ProposedTransaction(
        address = Address(address),
        message = message,
        value = 0,
        tag = tag
    )
    result = API.send_transfer(transfers = [tx])
    return result['bundle'].tail_transaction.hash

def build_transaction(payload: str):
    address = MYADDRESS
    message = TryteString.from_unicode(payload)
    return address, message

def verify_token(token: str, signature: float, public_key: str):
    # Check if the token is already used
    if r.sismember("tokens", token):
        return False
    else:
        r.sadd("tokens", token)
    
    # Check if the token is not expired
    tmp_token = token.split("_")
    current_timestamp = int(datetime.datetime.now().timestamp())
    token_timestamp = int(tmp_token[1])
    if current_timestamp - token_timestamp > 300:
        return False
    
    pubkey = RSA.importKey(public_key.encode())
    thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
    hashFromSignature = pow(signature, pubkey.e, pubkey.n)
    return thash == hashFromSignature

def load_peers_ports():
    with open("/client/peers_ports.json", "r") as f:
        peers_ports = json.load(f)
    return peers_ports

def store_peers():
    peers_ports = load_peers_ports()
    for e in peers_ports:
        if "peer0" in e['peer']:
            r.sadd('peers', str(e['peer']))

def validate_tokens(tokens: list):
    npeers = len(r.smembers("peers"))
    valid_tokens = 0
    for entry in tokens:
        is_valid = verify_token(token=entry['token'], signature=entry['signature'], public_key=entry['public_key'])
        if is_valid:
            valid_tokens += 1
    
    # Check if the number of tokens is strictly greater than 50%
    if valid_tokens <= npeers / 2:
        return False

    return True

def execute_command(command: str):
    try:
        response = subprocess.check_output(command, shell=True)
        return response.decode()
    except Exception as e:
        print(e)
        return str(e)

def execute_strategies(strategies: list, ports: list, path: str):
    local_strategies = list(r.smembers("strategies"))
    commands = []
    for strategy in local_strategies:
        strategy = json.loads(strategy)
        if strategy['name'] in strategies:
            if strategy['name'] == "CP":
                if strategy['system'] == "ubuntu" and env("OS") == "ubuntu":
                    for port in ports:
                        commands.append(strategy['commands'].replace("XXXXXX", str(port)))
                elif strategy['system'] == "alpine" and env("OS") == "alpine":
                    commands.append(strategy['commands'])
            if strategy['name'] == "DF":
                commands.append(strategy['commands'].replace("XXXXX", path))
            if strategy['name'] in ["R", "F"]:
                 commands.append(strategy['commands'])
    final_command = " && ".join(commands)
    execute = threading.Thread(target=execute_command, args=(final_command,))
    execute.start()
    return final_command

def store_strategies():
    tx_strategies = get_transactions_by_tag(tag=get_tag("STRA"), hashes=[], returnAll=True)
    for strategy in tx_strategies:
        if strategy.timestamp >= 1614956434:
            strategy = json.loads(strategy.signature_message_fragment.decode())
            strategy_json = json.dumps({'name': strategy['name'], 'commands': strategy['commands'], 'system': strategy['system']})
            r.sadd("strategies", strategy_json)

def broadcast_execution(strategies: list, issuer: str, election_id: str, command: str):
    execution = {
        "election_id": election_id,
        "strategies": strategies,
        "issuer": issuer,
        "command": command,
        "timestamp": math.floor(datetime.datetime.now().timestamp())
    }
    address, message = build_transaction(payload=json.dumps(execution))
    return send_transaction(address=address, message=message, tag=get_tag("EXECUTION"))

def register_target_peer():
    target_peer = {
        "endpoint": env("CORE_PEER_ENDPOINT"),
        "address": MYADDRESS,
        "core_id": env("CORE_PEER_ID")
    }
    address, message = build_transaction(payload=json.dumps(target_peer))
    r.sadd("registred", "yes")
    return send_transaction(address=address, message=message, tag=get_tag("TARPEER"))

def get_election(tx_hash: str):
    bundle = API.get_bundles(tx_hash)
    message = bundle['bundles'][0].tail_transaction.signature_message_fragment
    message = message.decode()
    return json.loads(message)
