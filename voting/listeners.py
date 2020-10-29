#!/usr/bin/python3
import datetime
import math
import time
import random
import urllib3
import utils

from environs import Env

env = Env()
env.read_env()

def get_tag(resource: str):
    return "MALCON" + resource.upper() + env("VERSION")

def elections():
    print("Listening on MALCONELEC tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag=get_tag("ELEC"))
        for tx_hash in transactions:
            election = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if utils.ismember(label="processed", txhash=tx_hash) or cur_timestamp - int(election['timestamp']) >= 300:
                continue
            else:
                print("MALCONELEC: storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="processed", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)
                print("MALCONELEC: Broadcasting election request with id {} resigration..".format(tx['election_id']))
                response = utils.broadcast_request(election_id=tx['election_id'])
                if response:
                    print("MALCONELEC: Registering election request with id {} LOCALLY".format(tx['election_id']))
                    isInitiated = utils.initiateElec(election_id=tx['election_id'])
                    if isInitiated:
                        print("MALCONELEC: Registering election request with id {} on BLOCKCHAIN".format(tx['election_id']))
                        utils.send_request(tx_id=tx_hash, issuer=utils.MYADDRESS, election_id=tx['election_id'])
        print("MALCONELEC: Sleeping for 5 seconds...")
        time.sleep(5)

def requests():
    print("Listening on MALCONREQ tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag=get_tag("REQ"))
        for tx_hash in transactions:
            request = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if utils.ismember(label="requests", txhash=tx_hash) or cur_timestamp - int(request['timestamp']) >= 300:
                continue
            else:
                print("MALCONREQ: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="requests", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)
                print("MALCONREQ: Sending vote...")
                candidates = utils.get_voting_peers(origin=env("CORE_PEER_ID"))
                candidate = candidates[random.randint(0, len(candidates) - 1)]
                utils.send_vote(candidate=candidate, election_id=tx['election_id'], eround=1)
                print('MALCONREQ: Peer {} voted successfully on candidate {} in election {} round 1'.format(env("CORE_PEER_ID"), candidate, tx['election_id']))
        print("MALCONREQ: Sleeping for 5 seconds...")
        time.sleep(5)    

def votes():
    print("Listening on MALCONVOTE tag...")
    eround = 1
    while True:
        transactions = utils.get_transactions_by_tag(tag=get_tag("VOTE"))
        for tx_hash in transactions:
            vote = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if utils.ismember(label="votes", txhash=tx_hash) or cur_timestamp - int(vote['timestamp']) >= 300:
                continue
            else:
                print("MALCONVOTE: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="votes", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)

                isFinal, winners = utils.isElecFinal(election_id=tx['election_id'])
                if not isFinal:
                    candidates = list(set(utils.get_voting_peers(origin=env("CORE_PEER_ID"))) & set(winners))
                    candidate = candidates[random.randint(0, len(candidates) - 1)]
                    eround += 1
                    print('MALCONVOTE: Peer {} voted successfully on candidate {} in election {} round {}'.format(env("CORE_PEER_ID"), candidate, tx['election_id'], str(eround)))
                    utils.send_vote(candidate=candidate, election_id=tx['election_id'], eround=eround)                     
                else:
                    winner = utils.get_election_winner(election_id=tx['election_id'])
                    if winner == env("CORE_PEER_ID"):
                        votes = utils.get_votes(election_id=tx['election_id'], address=env("CORE_PEER_ID"))
                        print("MALCONVOTE: Peer {} claiming executor after winning election {}".format(env("CORE_PEER_ID"), tx['election_id']))
                        utils.claim_executor(election_id=tx['election_id'], eround=eround, votes=votes, core_id=env("CORE_PEER_ID"))
                    eround = 1
        print("MALCONVOTE: Sleeping for 5 seconds...")
        time.sleep(5)

def executors():
    print("Listening on MALCONEXEC tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag=get_tag("EXEC"))
        for tx_hash in transactions:
            executor = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if utils.ismember(label="executors", txhash=tx_hash) or cur_timestamp - int(executor['timestamp']) >= 300:
                continue
            else:
                print("MALCONEXEC: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="executors", txhash=tx_hash)
                executor = utils.read_transaction(tx_hash=tx_hash)
                if utils.verify_executor(election_id=executor['election_id'], executor=executor['core_id']):
                    print("MALCONEXEC: Sending {}'s token to {}".format(env("CORE_PEER_ID"), executor['address']))
                    utils.send_token(executor=executor['core_id'], election_id=executor['election_id'])
        print("MALCONEXEC: Sleeping for 5 seconds...")
        time.sleep(5)
