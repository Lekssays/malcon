#!/usr/bin/python3
import asyncio
import datetime
import json
import math
import os.path
import random
import redis
import subprocess
import threading
import urllib3
import websockets
import zmq

from collections import defaultdict
from Crypto.PublicKey import RSA
from environs import Env
from hashlib import sha512
from iota import Iota
from iota import ProposedTransaction
from iota import Address
from iota import Tag
from iota import TryteString

from models import Vote, Peer, Request, Executor, Strategy

ENDPOINT = 'https://nodes.devnet.iota.org:443'
API = Iota(ENDPOINT, testnet = True)
env = Env()
env.read_env()
r = redis.Redis(host="0.0.0.0", port=env.int("CORE_PEER_REDIS_PORT"))

async def send_log(message: str):
    uri = "ws://172.17.0.1:7777"
    now = datetime.datetime.now()
    dt = now.strftime("%d/%m/%Y %H:%M:%S")
    message = dt + " - [" + env("CORE_PEER_ID") + "] " + message
    async with websockets.connect(uri) as websocket:
        await websocket.send(message)

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
    filename = env("CORE_PEER_ID") + "_address.txt"
    out = open(filename, "w")
    out.write(str(address))
    out.close()
    return str(address)

def get_address():
    if os.path.isfile(env("CORE_PEER_ID") + "_address.txt"):
        with open(env("CORE_PEER_ID") + "_address.txt") as f:
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
    message = message.decode()
    return json.loads(message)

def initiate_elec(election_id: str):
    if not r.exists(election_id + "_init"):
        r.sadd(election_id + "_init", 1)
        return True
    return False

def send_request(tx_hash: str, election_id: str):
    request = Request()
    request.tx_hash = tx_hash
    request.issuer = env("CORE_PEER_ID")
    request.election_id = election_id
    address, message = build_transaction(payload=request.get())
    return send_transaction(address=address, message=message, tag=get_tag("REQ"))

def send_vote(election_id: str, candidate: str, eround: int):
    vote = Vote()
    vote.voter = env("CORE_PEER_ID")
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

def store_vote(vote: dict, election_id: str, eround: int):
    r.sadd("votes_" + election_id + "_" + str(eround), json.dumps(vote))

def get_votes(election_id: str, eround: int):
    votes = r.smembers("votes_" + election_id + "_" + str(eround))
    return list(map(lambda x: json.loads(x.decode()), votes))

def get_peer_endpoint(peer: str):
    if env("CORE_PEER_PORT"):
        return "http://" + peer + ":" + env("CORE_PEER_PORT")
    endpoints = list(r.smembers("endpoints"))
    for endpoint in endpoints:
        endpoint = endpoint.decode()
        core_id = endpoint.split(":")
        core_id = core_id[0]
        if core_id == peer:
            return "http://" + endpoint

def store_voting_peers(origin: str):
    peers_ports = load_peers_ports()
    for e in peers_ports:
        if e['peer'] != origin and "peer0" in e['peer']:
            r.sadd('voting_peers', str(e['peer']))
            r.sadd('endpoints', str(e['peer'] + ":" + str(e['ports']['web'])))

def get_voting_peers():
    return list(map(lambda x: x.decode(), r.smembers('voting_peers')))

def claim_executor(election_id: str, eround: int, votes: int, core_id: str):
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

def save_elec_winner(election_id: str, eround: int, votes_count: int, winner: str):
    key = election_id + "_" + str(eround) + "_" + str(votes_count)
    r.set(key, winner)

def get_elec_winner(election_id: str, eround: int, votes_count: int):
    key = election_id + "_" + str(eround) + "_" + str(votes_count)
    winner = r.get(key)
    return winner.decode()

def verify_executor(election_id: str, executor: str, eround: int, votes_count: int):
    winner = get_elec_winner(election_id=election_id, eround=eround, votes_count=votes_count)
    if executor == winner:
        return True
    return False

def get_peer_tx_hash():
    tx_hash = list(r.smembers(env("CORE_PEER_ID")))
    return tx_hash[0]

def get_peer_public_key(tx_hash: str):
    peer = read_transaction(tx_hash=tx_hash)
    return peer['public_key']

def send_token(executor: str, election_id: str):
    peer_public_key = get_peer_public_key(tx_hash=get_peer_tx_hash())
    token, signature = generate_token()
    endpoint = get_peer_endpoint(peer=executor)
    http = urllib3.PoolManager()
    payload = json.dumps({"token": token, "signature": signature, "issuer": env("CORE_PEER_ID"), "election_id": election_id, "public_key": peer_public_key})
    response = http.request(
        'POST', endpoint + "/tokens",
        headers={'Content-Type': 'application/json'},
        body=payload
    )
    return response

def store_token(token: str, election_id: str):
    r.sadd(election_id + "_token", str(token))

def is_elec_final(election_id: str, eround: int):
    votes = get_votes(election_id=election_id, eround=eround)
    leaderboard = defaultdict(lambda : 0)
    
    for vote in votes:
        if election_id == vote['election_id'] and eround == vote['round']:
            leaderboard[vote['candidate']] += 1
    
    max_votes = max(leaderboard.values())
    total_votes = 0
    winners = []

    for candidate in leaderboard:
        total_votes += leaderboard[candidate]
        if leaderboard[candidate] == max_votes:
            winners.append((candidate, max_votes))
    
    message = "MALCONVOTE: {}/{} - WINNERS = {} - TOTAL_VOTES = {}".format(election_id, str(eround), str(winners), str(total_votes))
    print(message)
    asyncio.get_event_loop().run_until_complete(send_log(message))
    if len(winners) == 1 and total_votes == (len(get_voting_peers()) + 1):
        r.sadd(election_id, eround)
    
    return winners, total_votes

def get_peer_id(peer: str):
    _id = ""
    for c in peer:
        if c.isdigit():
            _id += c
    return _id[::-1]

def load_peers_ports():
    with open("/core/peers_ports.json", "r") as f:
        peers_ports = json.load(f)
    return peers_ports

def broadcast_request(election_id: str):
    voting_peers = get_voting_peers()
    count = 0
    peers_ports = load_peers_ports()
    for e in peers_ports:
        if e['peer'] in voting_peers: 
            rr = redis.Redis(host=e['peer'], port=e['ports']['redis'])
            if not rr.exists(election_id + "_init"):
                rr.sadd(election_id + "_init", 1)
                count += 1
    if count == len(voting_peers):
        return True
    return False

def load_strategies():
    strategies = []
    with open("/core/strategies.csv") as f:
        content = f.readlines()
        for line in content:
            line = line.strip().split(",")
            strategy = {}
            strategy['name'] = line[0]
            strategy['commands'] = line[1]
            strategy['isFinal'] = bool(line[2])
            strategy['system'] = line[3]
            strategies.append(strategy)
    return strategies

def add_strategy(name: str, commands: str, isFinal: bool, system: str):
    strategy = Strategy()
    strategy.name = name
    strategy.commands = commands
    strategy.isFinal = isFinal
    strategy.system = system
    address, message = build_transaction(payload=strategy.get())
    return send_transaction(address=address, message=message, tag=get_tag("STRA"))

def get_neighbors():
    neighbors = env("CORE_PEER_NEIGHBORS")
    if "None" not in neighbors:
        return neighbors.split(",")
    return ""

def execute_command(command: str):
    response = subprocess.check_output(command, shell=True)
    return response.decode()

def execute_strategy(ports: list):
    commands = []
    command = "ufw disallow XXXXXX"
    for port in ports:
        commands.append(command.replace("XXXXXX", str(port)))
    final_command = " && ".join(commands)
    execute = threading.Thread(target=execute_command, args=(final_command,))
    execute.start()
    return final_command

def get_socket_connection():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://zmq.devnet.iota.org:5556')
    socket.subscribe('tx')
    return socket

def get_tags() -> list:
    resources = ["VOTE", "EXECUTION", "EXEC", "ELEC", "REQ", "EMERG"]
    tags = []
    for resource in resources:
        tags.append(get_tag(resource=resource))
    return tags

def parse_tag(tag: str) -> str:
    tag = tag.split("9")
    return tag[0]

def store_election(election_id: str, tx_hash: str):
    r.sadd(election_id + "_hash", str(tx_hash))
