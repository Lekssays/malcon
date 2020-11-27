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

def read_transaction( tx_hash: str):
    bundle = API.get_bundles(tx_hash)
    message = bundle['bundles'][0].tail_transaction.signature_message_fragment
    message = message.decode().replace("\'", "\"")
    return json.loads(message)

def get_latest_peer(entries: list): 
	entries.sort(key = lambda x: x[0], reverse=True) 
	return entries[0] 

def get_peer_publickey(issuer: str):
    # TODO: radical refactoring
    peers = []
    tx_peers = get_transactions_by_tag(tag=get_tag("PEER"), hashes=[], returnAll=True)
    for peer in tx_peers:
        peer = json.loads(peer.signature_message_fragment.decode().replace("\'", "\""))
        if peer['core_id'] == issuer:
            peers.append((peer['timestamp'], peer))
    
    latest_entry = get_latest_peer(entries=peers)
    publickey = read_transaction(tx_hash=latest_entry[1])
    return publickey

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
    tx_peers = get_transactions_by_tag(tag=get_tag("PEER"), hashes=[], returnAll=True)
    for peer in tx_peers:
        peer = json.loads(peer.signature_message_fragment.decode().replace("\'", "\""))
        if peer['core_id'] == issuer:
            publickey = get_peer_publickey(issuer=peer['core_id'])
            pubkey = RSA.importKey(publickey.encode())
            thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
            hashFromSignature = pow(signature, pubkey.e, pubkey.n)
            return thash == hashFromSignature
    return False

def get_peers():
    peers = set()
    tx_peers = get_transactions_by_tag(tag=get_tag("PEER"), hashes=[], returnAll=True)
    for peer in tx_peers:
        peer = json.loads(peer.signature_message_fragment.decode().replace("\'", "\""))
        peers.add(peer['core_id'])
    return list(peers)

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
    tx_elections = get_transactions_by_tag(tag=get_tag("ELEC"), hashes=[], returnAll=True)
    for election in tx_elections:
        election = json.loads(election.signature_message_fragment.decode().replace("\'", "\""))
        if election['election_id'] == election_id:
            return election['strategy_id']

def execute_stategy(strategy_id: str):
    # TODO: wait for confirmation of the majority
    tx_strategies = get_transactions_by_tag(tag=get_tag("STRA"), hashes=[], returnAll=True)
    for strategy in tx_strategies:
        strategy = json.loads(strategy.signature_message_fragment.decode().replace("\'", "\""))
        if strategy['strategy_id'] == strategy_id:
            command = subprocess.check_output(strategy, shell=True)
            return command.decode()

def broadcast_execution(strategy_id: str, issuer: str):
    execution = {
        'strategy_id': strategy_id,
        'issuer': issuer
    }
    address, message = build_transaction(payload=json.dumps(execution))
    return send_transaction(address=address, message=message, tag=get_tag("EXECUTION"))

def register_target_peer():
    target_peer = {
        'endpoint': env("CORE_PEER_ENDPOINT"),
        'address': MYADDRESS,
        'core_id': env("CORE_PEER_ID")
    }
    address, message = build_transaction(payload=json.dumps(target_peer))
    r.sadd("registred", "yes")
    return send_transaction(address=address, message=message, tag=get_tag("TARPEER"))
