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
from hashlib import sha512
from iota import Iota
from iota import ProposedTransaction
from iota import Address
from iota import Tag
from iota import TryteString

from models import Vote, Peer, Request, Executor

ENDPOINT = 'https://nodes.devnet.iota.org:443'
API = Iota(ENDPOINT, testnet = True)
r = redis.Redis()

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
    REQUSTTAG = "MALCONREQ"
    request = Request()
    request.tx_id = tx_id
    request.issuer = MYADDRESS
    request.election_id = election_id
    address, message = build_transaction(payload=request.get())
    return send_transaction(address=address, message=message, tag=REQUSTTAG)

def send_vote(election_id: str, candidate: str, eround: int):
    VOTETAG = "MALCONVOTE"
    vote = Vote()
    vote.voter = MYADDRESS
    vote.election_id = election_id
    vote.candidate = candidate
    vote.eround = eround
    address, message = build_transaction(payload=vote.get())
    return send_transaction(address=address, message=message, tag=VOTETAG)

def register_peer(endpoint: str, public_key: str, core_id: str, address: str):
    PEERTAG = "MALCONPEER"
    peer = Peer()
    peer.endpoint = endpoint
    peer.public_key = public_key
    peer.core_id = core_id
    peer.address = address
    address, message = build_transaction(payload=peer.get())
    return send_transaction(address=address, message=message, tag=PEERTAG)

def store_hash(label: str, txhash: str):
    r.sadd(label, txhash)

def ismember(label: str, txhash: str):
    return r.sismember(label, txhash)

def store_peers(peers: list):
    for peer in peers:
        r.sadd("peers", peer)

def get_voting_peers(origin: str):
    voters = []
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['core_id'] != origin:
            voters.append(tx_hash)
    return voters

def claim_executor(election_id: str, eround: int, votes: list):
    EXECUTORTAG = "MALCONEXEC"
    executor = Executor()
    executor.election_id = election_id
    executor.eround = eround
    executor.votes = votes
    executor.address = MYADDRESS
    address, message = build_transaction(payload=executor.get())
    return send_transaction(address=address, message=message, tag=EXECUTORTAG)

def generate_token():
    timestamp = datetime.datetime.now() + datetime.timedelta(seconds=500)
    timestamp = str(timestamp.timestamp())
    nonce = str(random.randint(100000, 999999))
    token = nonce + "_" + timestamp
    token = token.split(".")
    token = token[0]

    with open("private_key.pem", "rb") as k:
        privatekey = RSA.importKey(k.read())
    
    thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
    signature = pow(thash, privatekey.d, privatekey.n)
    return token, signature

# FIXME: MOVE THIS TO CLIENT NOT ADMIN
def verify_token(token: str, signature: float, issuer_address: str):
    token = token.split("_")
    current_timestamp = int(datetime.datetime.now().timestamp())
    token_timestamp = int(token[1])
    if current_timestamp - token_timestamp > 500:
        return False
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['address'] == issuer_address:
            pubkey = RSA.importKey(peer['public_key'].encode())
            thash = int.from_bytes(sha512(token.encode()).digest(), byteorder='big')
            hashFromSignature = pow(signature, pubkey.e, pubkey.n)
            return thash == hashFromSignature
    return False

def get_votes(election_id: str, address: str):
    transactions = get_transactions_by_tag(tag="MALCONVOTE")
    leaderboard = defaultdict(lambda : 0)
    for tx_hash in transactions:
        vote = read_transaction(tx_hash=tx_hash)
        if election_id == vote['election_id']:
            leaderboard[vote['candidate']] += 1
    return leaderboard[address]

def get_election_winner(election_id: str):
    transactions = get_transactions_by_tag(tag="MALCONVOTE")
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

def verify_executor(election_id: str, executor_address: str):
    winner = get_election_winner(election_id=election_id)
    if winner == executor_address:
        return True
    return False

def send_token(executor_address: str):
    transactions = get_transactions_by_tag(tag="MALCONPEER")
    token, signature = generate_token()
    for tx_hash in transactions:
        peer = read_transaction(tx_hash=tx_hash)
        if peer['address'] == executor_address:
            http = urllib3.PoolManager()
            payload = json.dumps({"token": token, "signature": signature})
            response = http.request(
                'POST', peer['endpoint'],
                headers={'Content-Type': 'application/json'},
                body=payload
            )
            return response

def isElecInitiated(election_id: str):
    transactions = get_transactions_by_tag(tag="MALCONREQ")
    for tx_hash in transactions:
        request = read_transaction(tx_hash=tx_hash)
        if request['election_id'] == election_id:
            return True
    return False

def isElecFinal(election_id: str):
    transactions = get_transactions_by_tag(tag="MALCONVOTE")
    leaderboard = defaultdict(lambda : 0)
    for tx_hash in transactions:
        vote = read_transaction(tx_hash=tx_hash)
        if election_id == vote['election_id']:
            leaderboard[vote['candidate']] += 1
    
    max_votes = -1
    winners = []
    for candidate in leaderboard:
        if leaderboard[candidate] >= max_votes:
            max_votes = leaderboard[candidate]
            winners.append(candidate)
    if len(winners) > 1:
        return False, winners
    return True, winners