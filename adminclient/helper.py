#!/usr/bin/python3
import json
import math
import redis
import urllib3

from environs import Env
from iota import Iota

ENDPOINT = 'https://nodes.devnet.iota.org:443'
API = Iota(ENDPOINT, testnet = True)
r = redis.Redis()
env = Env()
env.read_env()

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

def read_transaction( tx_hash: str):
    bundle = API.get_bundles(tx_hash)
    message = bundle['bundles'][0].tail_transaction.signature_message_fragment
    message = message.decode().replace("\'", "\"")
    return json.loads(message)

def get_peers():
    peers = []
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        peers.append(peer)
    return set(peers)

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
    transactions = get_transactions_by_tag(tag="MALCONELEC")
    for tx_hash in transactions:
        election = read_transaction(tx_hash=tx_hash)
        if election_id == election['election_id']:
            target_peer_id = election['target']
            peers = get_transactions_by_tag('MALCONTARPEER')
            for peer in peers:
                if peer['core_id'] == target_peer_id:
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