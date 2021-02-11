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
API = Iota(ENDPOINT, testnet = True, local_pow = True)
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
        if peer.timestamp >= 1609455600:
            peer = json.loads(peer.signature_message_fragment.decode().replace("\'", "\""))
            peers.add(peer['core_id'])
    return list(peers)

def store_token(token: str, election_id: str):
    r.sadd(election_id + "_token", str(token))

def get_tokens(election_id: str):
    return list(r.smembers(election_id + "_token"))

def prepare_payload(election_id: str):
    tokens = get_tokens(election_id=election_id)
    tokens = list(map(lambda x: json.loads(x.decode().replace("\'", "\"")), tokens))
    issuer = env("CORE_PEER_ID")
    payload = {
        "tokens": tokens,
        "election_id": election_id,
        "issuer": issuer
    }
    return json.dumps(payload)

def get_target_peer(election_id: str):
    elections = get_transactions_by_tag(tag=get_tag("ELEC"), hashes=[], returnAll=True)
    target_peer = ""
    for election in elections:
        # New version of the election object
        if election.timestamp >= 1609455600:
            election = json.loads(election.signature_message_fragment.decode().replace("\'", "\""))
            if election_id == election['election_id']:
                target_peer = election['target']
                break

    peers = get_transactions_by_tag(get_tag("TARPEER"), hashes=[], returnAll=True)
    for peer in peers:
        if peer.timestamp >= 1609455600:
            peer = json.loads(peer.signature_message_fragment.decode().replace("\'", "\""))
            if peer['core_id'] == target_peer:
                return peer

def current_tokens(election_id: str):
    return len(get_tokens(election_id=election_id))

def get_peer_endpoint(peer: dict):
    if env("CORE_PEER_PORT"):
        return "http://" + peer['core_id'] + ":" + env("CORE_PEER_PORT")
    return "http://" + peer['endpoint']

def execute_strategy(peer: dict, election_id: str):
    payload = prepare_payload(election_id=election_id)
    http = urllib3.PoolManager()
    endpoint = get_peer_endpoint(peer=peer)
    response = http.request(
        'POST', endpoint + "/tokens",
        headers={'Content-Type': 'application/json'},
        body=payload
    )
    return response.data.decode('utf-8')
