#!/usr/bin/python3
import datetime
import json
import math
import os
import redis
import subprocess
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

def load_peers_ports():
    with open("/core/peers_ports.json", "r") as f:
        peers_ports = json.load(f)
    return peers_ports

def get_peers():
    peers = []
    peers_ports = load_peers_ports()
    for e in peers_ports:
        peers.append(e['peer'])
    return list(peers)

def store_token(token: str, election_id: str):
    r.sadd(election_id + "_token", str(token))

def get_tokens(election_id: str):
    return list(r.smembers(election_id + "_token"))

def get_election_hash(election_id: str):
    tx_hash = list(r.smembers(election_id + "_hash"))
    return tx_hash[0]

def prepare_payload(election_id: str):
    tokens = get_tokens(election_id=election_id)
    tokens = list(map(lambda x: json.loads(x.decode().replace("\'", "\"")), tokens))
    issuer = env("CORE_PEER_ID")
    election_hash = get_election_hash(election_id=election_id)
    payload = {
        "tokens": tokens,
        "election_id": election_id,
        "issuer": issuer,
        "election_hash": election_hash.decode()
    }
    return json.dumps(payload)

def get_election(tx_hash: str):
    bundle = API.get_bundles(tx_hash)
    message = bundle['bundles'][0].tail_transaction.signature_message_fragment
    message = message.decode()
    return json.loads(message)

def get_target_peer(election_id: str) -> str:
    tx_hash = get_election_hash(election_id=election_id)
    election = get_election(tx_hash=tx_hash)
    return election['target']

def current_tokens(election_id: str) -> int:
    return len(get_tokens(election_id=election_id))

def get_peer_endpoint(peer: str, internal: bool) -> str:
    # NOTE: the inter-container communication will use the original port 
    # where the container serves the app client 5000 and not the exposed port e.g. 10011
    if internal:
        return "http://" + peer + ":5000"
    else:
        endpoint = "http://" + peer + ":100"
        digits = ""
        for c in peer:
            if c.isdigit():
                digits += c
        return endpoint + digits[::-1]

def execute_strategy(peer: str, election_id: str):
    payload = prepare_payload(election_id=election_id)
    http = urllib3.PoolManager()
    # NOTE: Change internal to False if you are deploying in a prod env.
    endpoint = get_peer_endpoint(peer=peer, internal=True)
    response = http.request(
        'POST', endpoint + "/tokens",
        headers={'Content-Type': 'application/json'},
        body=payload
    )
    return response.data.decode('utf-8')
