#!/usr/bin/python3

import datetime
import json
import math
import subprocess
import os.path
import redis
import urllib3

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

def get_transactions_by_tag(tag: str):
    http = urllib3.PoolManager()
    command = json.dumps({"command": "findTransactions", "tags": [tag]})

    response = http.request(
        'POST', ENDPOINT,
        headers={'Content-Type': 'application/json', 'X-IOTA-API-Version': '1'},
        body=command
    )
    results = json.loads(response.data.decode('utf-8'))
    return results['hashes']

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

def read_transaction( tx_hash: str):
    bundle = API.get_bundles(tx_hash)
    message = bundle['bundles'][0].tail_transaction.signature_message_fragment
    message = message.decode().replace("\'", "\"")
    return json.loads(message)

def verify_token(token: str, signature: float, issuer: str):
    # Check if the token is already used
    if r.sismember("tokens", token):
        return False
    else:
        r.sadd("tokens", token)
    
    # Check if the token is not expired
    token = token.split("_")
    current_timestamp = int(datetime.datetime.now().timestamp())
    token_timestamp = int(token[1])
    if current_timestamp - token_timestamp > 500:
        return False
    
    # Check if the signature is correct
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['core_id'] == issuer:
            pubkey = RSA.importKey(peer['public_key'].encode())
            thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
            hashFromSignature = pow(signature, pubkey.e, pubkey.n)
            return thash == hashFromSignature
    return False

def get_peers():
    peers = []
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        peers.append(peer)
    return set(peers)

def validate_tokens(tokens: list):
    npeers = len(get_peers())
    valid_tokens = 0
    for entry in tokens:
        is_valid = verify_token(token=entry['token'], signature=entry['signature'], issuer=entry['core_id'])
        if is_valid:
            valid_tokens += 1
    
    # Check if the number of tokens is strictly greater than 50%
    if valid_tokens < math.ceil(npeers/2):
        return False

    return True

def get_strategy(election_id: str):
    # TODO: this can be also done with Fabric
    transactions = get_transactions_by_tag(tag="MALCONELEC")
    for election in transactions:
        if election['election_id'] == election_id:
            return election['strategy_id']

def execute_stategy(strategy_id: str):
    # TODO: wait for confirmation of the majority
    transactions = get_transactions_by_tag(tag="MALCONSTRAT")
    for strategy in transactions:
        if strategy['strategy_id'] == strategy_id:
            command = subprocess.check_output(strategy, shell=True)
            return command.decode()

def broadcast_execution(strategy_id: str, issuer: str):
    EXECUTIONTAG= "MALCONEXECUTION"
    execution = {
        'strategy_id': strategy_id,
        'issuer': issuer
    }
    address, message = build_transaction(payload=json.dumps(execution))
    return send_transaction(address=address, message=message, tag=EXECUTIONTAG)

def register_target_peer():
    TARGETPEERTAG = "MALCONTARPEER"
    target_peer = {
        'endpoint': env("CORE_PEER_ENDPOINT"),
        'address': get_address(),
        'core_id': env("CORE_PEER_ID")
    }
    address, message = build_transaction(payload=json.dumps(target_peer))
    r.sadd("registred", "yes")
    return send_transaction(address=address, message=message, tag=TARGETPEERTAG)

def isRegistred():
    return len(r.smembers("registred")) == 1