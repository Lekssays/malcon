#!/usr/bin/python3
import json
import redis
import subprocess
import os.path
import urllib3

from iota import Iota
from iota import ProposedTransaction
from iota import Address
from iota import Tag
from iota import TryteString

from models import Vote, Peer, Request

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

def send_vote(election_id: str, candidate: str):
    VOTETAG = "MALCONVOTE"
    vote = Vote()
    vote.voter = MYADDRESS
    vote.election_id = election_id
    vote.candidate = candidate
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
