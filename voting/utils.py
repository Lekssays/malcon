#!/usr/bin/python3
import json
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
    return json.dumps(results, indent=1, sort_keys=True)

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
    return message.decode()

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

def register_peer(endpoint: str, public_key: str, core_id: str):
    PEERTAG = "MALCONPEER"
    peer = Peer()
    peer.endpoint = endpoint
    peer.public_key = public_key
    peer.core_id = core_id
    peer.address = get_address()
    address, message = build_transaction(payload=peer.get())
    return send_transaction(address=address, message=message, tag=PEERTAG)
