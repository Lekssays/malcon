#!/usr/bin/python3
import datetime
import json
import math
import time
import random
import urllib3
import utils
import zmq

from collections import defaultdict
from environs import Env

env = Env()
env.read_env()
TIME = 0

def elections():
    socket = utils.get_socket_connection()
    print("Listening on MALCONELEC tag...")
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="ELEC"):
            election = utils.read_transaction(tx_hash=tx_hash)
            response = utils.broadcast_request(election_id=election['election_id'])
            if response:
                print("MALCONELEC: Registering election request with id {} LOCALLY".format(election['election_id']))
                is_initiated = utils.initiate_elec(election_id=election['election_id'])
                if is_initiated:
                    print("MALCONELEC: Registering election request with id {} on BLOCKCHAIN".format(election['election_id']))
                    utils.send_request(tx_hash=tx_hash, election_id=election['election_id'])

def requests():
    socket = utils.get_socket_connection()
    print("Listening on MALCONREQ tag...")
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="REQ"):
            request = utils.read_transaction(tx_hash=tx_hash)
            print("MALCONREQ: Sending vote...")
            candidates = utils.get_voting_peers()
            candidate = candidates[random.randint(0, len(candidates) - 1)]
            utils.send_vote(candidate=candidate, election_id=request['election_id'], eround=1)
            print('MALCONREQ: Peer {} voted successfully on candidate {} in election {} round 1'.format(env("CORE_PEER_ID"), candidate, request['election_id']))

def votes():
    socket = utils.get_socket_connection()
    print("Listening on MALCONVOTE tag...")
    elections_rounds = defaultdict(lambda : 1)
    finalized_elections = defaultdict(lambda : False)
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="VOTE"):
            vote = utils.read_transaction(tx_hash=tx_hash)
            utils.store_vote(vote=vote, election_id=vote['election_id'], eround=vote['round'])
            
            if len(utils.get_votes(election_id=vote['election_id'], eround=vote['round'])) == len(utils.get_voting_peers()) + 1:
                if not finalized_elections[vote['election_id']]:
                    winners, total_votes = utils.is_elec_final(election_id=vote['election_id'], eround=elections_rounds[vote['election_id']])

                    if len(winners) == 1 and total_votes > (len(utils.get_voting_peers()) + 1) / 2:
                        finalized_elections[vote['election_id']] = True
                        if winners[0][0] == env("CORE_PEER_ID") and winners[0][1] > (len(utils.get_voting_peers()) + 1) / 2:
                            print("MALCONVOTE: Peer {} claiming executor after winning election {}".format(env("CORE_PEER_ID"), vote['election_id']))
                            utils.claim_executor(election_id=vote['election_id'], eround=vote['round'], votes=winners[0][1], core_id=env("CORE_PEER_ID"))
                    else:
                        candidates = []
                        for winner in winners:
                            if winner[0] != env("CORE_PEER_ID"):
                                candidates.append(winner[0])
                        candidate = candidates[random.randint(0, len(candidates) - 1)]

                        if total_votes == (len(utils.get_voting_peers()) + 1) and total_votes != 0:
                            elections_rounds[vote['election_id']] += 1
                            print('MALCONVOTE: Peer {} voted successfully on candidate {} in election {} round {}'.format(env("CORE_PEER_ID"), candidate, vote['election_id'], str(elections_rounds[vote['election_id']])))
                            utils.send_vote(candidate=candidate, election_id=vote['election_id'], eround=elections_rounds[vote['election_id']])

def executors():
    socket = utils.get_socket_connection()
    print("Listening on MALCONEXEC tag...")
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EXEC"):
            executor = utils.read_transaction(tx_hash=tx_hash)
            if utils.verify_executor(election_id=executor['election_id'], executor=executor['core_id'], eround=int(executor['round']), votes_count=int(executor['votes'])):
                if executor['core_id'] != env("CORE_PEER_ID"):
                    print("MALCONEXEC: Sending {}'s token to {}".format(env("CORE_PEER_ID"), executor['core_id']))
                    response = utils.send_token(executor=executor['core_id'], election_id=executor['election_id'])
                    if response.status == 200:
                        print("MALCONEXEC: token has been sent")
                else:
                    token, signature = utils.generate_token()
                    with open(env("CORE_MAIN_PATH") + "/" + env("CORE_PEER_ID") + "_public_key.pem", "r") as f:
                        public_key = f.read()
                    payload = {"token": token, "signature": signature, "issuer": env("CORE_PEER_ID"), "election_id": executor['election_id'], "public_key": public_key}
                    utils.store_token(token=payload, election_id=executor['election_id'])
                    print("MALCONEXEC: token has been generated")

def emergency():
    socket = utils.get_socket_connection()
    print("Listening on MALCONEMERG tag...")
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EMERG"):
            emergency = utils.read_transaction(tx_hash=tx_hash)
            neighbors = utils.get_neighbors()
            if emergency['issuer'] in neighbors:
                print("MALCONEMERG: Executing emergency strategy...")
                response = utils.execute_strategy(ports=emergency['ports'])
                print("MALCONEMERG: Execution Code = {}".format(str(response)))

def broadcasts():
    socket = utils.get_socket_connection()
    print("Listening on MALCONEXECUTION tag...")
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EXECUTION"):
            execution = utils.read_transaction(tx_hash=tx_hash)
            print("MALCONEXECUTION: ", execution)
