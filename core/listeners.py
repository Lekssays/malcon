#!/usr/bin/python3
import asyncio
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
    message = "Listening on MALCONREQ tag..."
    print(message)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils.send_log(message))
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="REQ"):
            election = utils.read_transaction(tx_hash=tx_hash)
            utils.store_election(election_id=election['election_id'], tx_hash=tx_hash)
            message = "MALCONREQ: Sending vote..."
            print(message)
            loop.run_until_complete(utils.send_log(message))
            candidates = utils.get_voting_peers()
            candidate = candidates[random.randint(0, len(candidates) - 1)]
            utils.send_vote(candidate=candidate, election_id=election['election_id'], eround=1)
            message = "MALCONREQ: Peer {} voted successfully on candidate {} in election {} round 1".format(env("CORE_PEER_ID"), candidate, election['election_id'])
            print(message)
            loop.run_until_complete(utils.send_log(message))

def votes():
    socket = utils.get_socket_connection()
    message = "Listening on MALCONVOTE tag..."
    print(message)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils.send_log(message))
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
                        utils.save_elec_winner(election_id=vote['election_id'], eround=vote['round'], votes_count=winners[0][1], winner=winners[0][0])
                        if winners[0][0] == env("CORE_PEER_ID"):
                            message = "MALCONVOTE: Peer {} claiming executor after winning election {}".format(env("CORE_PEER_ID"), vote['election_id'])
                            print(message)
                            loop.run_until_complete(utils.send_log(message))        
                            utils.claim_executor(election_id=vote['election_id'], eround=vote['round'], votes=winners[0][1], core_id=env("CORE_PEER_ID"))
                    else:
                        candidates = []
                        for winner in winners:
                            if winner[0] != env("CORE_PEER_ID"):
                                candidates.append(winner[0])
                        candidate = candidates[random.randint(0, len(candidates) - 1)]

                        if total_votes == (len(utils.get_voting_peers()) + 1) and total_votes != 0:
                            elections_rounds[vote['election_id']] += 1
                            message = "MALCONVOTE: Peer {} voted successfully on candidate {} in election {} round {}".format(env("CORE_PEER_ID"), candidate, vote['election_id'], str(elections_rounds[vote['election_id']]))
                            print(message)
                            loop.run_until_complete(utils.send_log(message))
                            utils.send_vote(candidate=candidate, election_id=vote['election_id'], eround=elections_rounds[vote['election_id']])

def executors():
    socket = utils.get_socket_connection()
    message = "Listening on MALCONEXEC tag..."
    print(message)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils.send_log(message))
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EXEC"):
            executor = utils.read_transaction(tx_hash=tx_hash)
            if utils.verify_executor(election_id=executor['election_id'], executor=executor['core_id'], eround=int(executor['round']), votes_count=int(executor['votes'])):
                if executor['core_id'] != env("CORE_PEER_ID"):
                    message = "MALCONEXEC: Sending {}'s token to {}".format(env("CORE_PEER_ID"), executor['core_id'])
                    print(message)
                    loop.run_until_complete(utils.send_log(message))
                    response = utils.send_token(executor=executor['core_id'], election_id=executor['election_id'])
                    if response.status == 200:
                        message = "MALCONEXEC: token has been sent"
                        print(message)
                        loop.run_until_complete(utils.send_log(message))
                else:
                    token, signature = utils.generate_token()
                    with open(env("CORE_MAIN_PATH") + "/" + env("CORE_PEER_ID") + "_public_key.pem", "r") as f:
                        public_key = f.read()
                    payload = {"token": token, "signature": signature, "issuer": env("CORE_PEER_ID"), "election_id": executor['election_id'], "public_key": public_key}
                    utils.store_token(token=payload, election_id=executor['election_id'])
                    message = "MALCONEXEC: token has been generated"
                    print(message)
                    loop.run_until_complete(utils.send_log(message))

def emergency():
    socket = utils.get_socket_connection()
    message = "Listening on MALCONEMERG tag..."
    print(message)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils.send_log(message))
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EMERG"):
            emergency = utils.read_transaction(tx_hash=tx_hash)
            neighbors = utils.get_neighbors()
            if emergency['issuer'] in neighbors:
                message = "MALCONEMERG: Executing emergency strategy..."
                print(message)
                loop.run_until_complete(utils.send_log(message))
                response = utils.execute_strategy(ports=emergency['ports'])
                message = "MALCONEMERG: Execution Code = {}".format(str(response))
                print(message)
                loop.run_until_complete(utils.send_log(message))

def broadcasts():
    socket = utils.get_socket_connection()
    message = "Listening on MALCONEXECUTION tag..."
    print(message)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(utils.send_log(message))
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash = data[1].decode()
        if utils.parse_tag(tag=data[12].decode()) == utils.get_tag(resource="EXECUTION"):
            execution = utils.read_transaction(tx_hash=tx_hash)
            message = "MALCONEXECUTION: " + str(execution)
            print(message)
            loop.run_until_complete(utils.send_log(message))
