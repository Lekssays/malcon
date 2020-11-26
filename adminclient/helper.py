#!/usr/bin/python3
import datetime
import json
import math
import os
import redis
import subprocess
import urllib3

from collections import defaultdict
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

def get_peers():
    peers = set()
    tx_peers = get_transactions_by_tag(tag=get_tag("PEER"), hashes=[], returnAll=True)
    for peer in tx_peers:
        peers.add(peer['core_id'])
    return list(peers)

def store_token(token: str, election_id: str):
    r.sadd(election_id, token)

def get_tokens(election_id: str):
    return r.smembers(election_id)

def prepare_payload(election_id: str):
    tokens = get_tokens(election_id=election_id)
    issuer = env("CORE_PEER_ID")
    payload = {
        'tokens': tokens,
        'election_id': election_id,
        'issuer': issuer
    }
    return json.dumps(payload)

def get_target_peer(election_id: str):
    elections = get_transactions_by_tag(tag=get_tag("ELEC"), hashes=[], returnAll=True)
    target_peer = ""
    for election in elections:
        if election_id == election['election_id']:
            target_peer = election['target']
            break
    
    peers = get_transactions_by_tag(get_tag("TARPEER"), hashes=[], returnAll=True)
    for peer in peers:
        if peer['core_id'] == target_peer:
            return peer

def enough_tokens(election_id: str):
    tokens = len(get_tokens(election_id=election_id))
    peers = len(get_peers)
    if tokens < math.ceil(peers/2):
        return True
    return False

def execute_strategy(endpoint: str, election_id: str):
    payload = prepare_payload(election_id=election_id)
    http = urllib3.PoolManager()
    response = http.request(
        'POST', endpoint,
        headers={'Content-Type': 'application/json'},
        body=payload
    )
    return json.loads(response.data.decode('utf-8'))

def store_election_initiation(election_id: str):
    if not r.exists(election_id + "_init"):
        r.sadd(election_id + "_init", 1)
    return r.exists(election_id + "_init")
 