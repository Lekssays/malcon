#!/usr/bin/python3
import datetime
import json
import os.path
import random
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

from models import Vote, Peer, Request, Executor

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

def send_request(tx_id: str, issuer: str, election_id: str):
    request = Request()
    request.tx_id = tx_id
    request.issuer = MYADDRESS
    request.election_id = election_id
    address, message = build_transaction(payload=request.get())
    return send_transaction(address=address, message=message, tag=get_tag("REQ"))

def send_vote(election_id: str, candidate: str, eround: int):
    vote = Vote()
    vote.voter = MYADDRESS
    vote.election_id = election_id
    vote.candidate = candidate
    vote.eround = eround
    address, message = build_transaction(payload=vote.get())
    return send_transaction(address=address, message=message, tag=get_tag("VOTE"))

def register_peer(endpoint: str, public_key: str, core_id: str, address: str):
    peer = Peer()
    peer.endpoint = endpoint
    peer.public_key = public_key
    peer.core_id = core_id
    peer.address = address
    address, message = build_transaction(payload=peer.get())
    return send_transaction(address=address, message=message, tag=get_tag("PEER"))

def store_hash(label: str, txhash: str):
    r.sadd(label, txhash)

def ismember(label: str, txhash: str):
    return r.sismember(label, txhash)

def store_voting_peers(origin: str):
    voters = []
    transactions = get_transactions_by_tag(tag=get_tag("PEER"))
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['core_id'] != origin:
            voters.append(peer['core_id'])
    r.sadd('voting_peers', *set(voters))

def get_voting_peers():
    return list(r.smembers('voting_peers'))

def claim_executor(election_id: str, eround: int, votes: list, core_id: str):
    executor = Executor()
    executor.election_id = election_id
    executor.eround = eround
    executor.votes = votes
    executor.core_id = core_id
    address, message = build_transaction(payload=executor.get())
    return send_transaction(address=address, message=message, tag=get_tag("EXEC"))

def generate_token():
    timestamp = datetime.datetime.now() + datetime.timedelta(seconds=500)
    timestamp = str(timestamp.timestamp())
    nonce = str(random.randint(100000, 999999))
    token = nonce + "_" + timestamp
    token = token.split(".")
    token = token[0]

    with open(env("CORE_PEER_ID") + "_private_key.pem", "rb") as k:
        privatekey = RSA.importKey(k.read())
    
    thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
    signature = pow(thash, privatekey.d, privatekey.n)
    return token, signature

def get_votes(election_id: str, address: str):
    transactions = get_transactions_by_tag(tag=get_tag("VOTE"))
    leaderboard = defaultdict(lambda : 0)
    for tx_hash in transactions:
        vote = read_transaction(tx_hash=tx_hash)
        if election_id == vote['election_id']:
            leaderboard[vote['candidate']] += 1
    return leaderboard[address]

def get_election_winner(election_id: str):
    transactions = get_members_by_label(label="votes")
    leaderboard = defaultdict(lambda : 0)
    for tx_hash in transactions:
        vote = read_transaction(tx_hash=tx_hash)
        if election_id == vote['election_id']:
            leaderboard[vote['candidate']] += 1
    
    max_votes = -1
    winner = ""
    for candidate in leaderboard:
        if leaderboard[candidate] >= max_votes:
            max_votes = leaderboard[candidate]
            winner = candidate
    return winner

def verify_executor(election_id: str, executor: str):
    winner = get_election_winner(election_id=election_id)
    if winner == executor:
        return True
    return False

def send_token(executor: str, election_id: str):
    transactions = get_transactions_by_tag(tag=get_tag("PEER"))
    token, signature = generate_token()
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['core_id'] == executor:
            http = urllib3.PoolManager()
            payload = json.dumps({"token": token, "signature": signature, "issuer": env("CORE_PEER_ID"), "election_id": election_id})
            response = http.request(
                'POST', peer['endpoint'],
                headers={'Content-Type': 'application/json'},
                body=payload
            )
            return response


def initiateElec(election_id: str):
    if not r.exists(election_id + "_init"):
        r.sadd(election_id + "_init", 1)
        return True
    return False

def update(tag: str, label: str):
    remote = get_transactions_by_tag(tag=tag)
    for tx in remote:
        store_hash(label=label, txhash=tx)

def get_current_votes(election_id: str):
    return len(list(get_members_by_label(label="votes")))

def isElecFinal(election_id: str):
    transactions = get_members_by_label(label="votes")
    leaderboard = defaultdict(lambda : 0)
    votes = 0
    for tx_hash in transactions:
        vote = read_transaction(tx_hash=tx_hash)
        if election_id == vote['election_id']:
            votes += 1
            leaderboard[vote['candidate']] += 1
    
    max_votes = -1
    winners = []
    for candidate in leaderboard:
        if leaderboard[candidate] >= max_votes:
            max_votes = leaderboard[candidate]
            winners.append(candidate)

    return  winners

def get_peer_id(peer: str):
    _id = ""
    for c in peer:
        if c.isdigit():
            _id += c
    return _id[::-1]

def broadcast_request(election_id: str):
    # TODO: In Prod, PORT 5000 shall be changed to the appropriate port of devices
    peers = get_voting_peers()
    count = 0
    for peer in peers:
        port = "110" + get_peer_id(peer=peer.decode())
        rr = redis.Redis(host=peer.decode(), port=port)
        if not rr.exists(election_id + "_init"):
            rr.sadd(election_id + "_init", 1)
            count += 1
    if count == len(peers):
        return True
    return False

def get_members_by_label(label: str):
    return map(lambda x: x.decode(), r.smembers(label))


def synchronize(label: str, transactions: list):
    for tx_hash in transactions:
        store_hash(label=label, txhash=tx_hash)