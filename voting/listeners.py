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
TIME = 2

def get_tag(resource: str):
    return "MALCON" + resource.upper() + env("VERSION")

def elections():
    print("Listening on MALCONELEC tag...")
    while True:
        transactions = list(set(utils.get_transactions_by_tag(tag=get_tag("ELEC"))) ^ set(utils.get_members_by_label(label="processed")))
        utils.synchronize(transactions=transactions, label="processed")
        for tx_hash in transactions:
            election = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if cur_timestamp - int(election['timestamp']) >= 300:
                continue
            else:
                response = utils.broadcast_request(election_id=election['election_id'])
                if response:
                    print("MALCONELEC: Registering election request with id {} LOCALLY".format(election['election_id']))
                    isInitiated = utils.initiateElec(election_id=election['election_id'])
                    if isInitiated:
                        print("MALCONELEC: Registering election request with id {} on BLOCKCHAIN".format(election['election_id']))
                        utils.send_request(tx_id=tx_hash, issuer=utils.MYADDRESS, election_id=election['election_id'])
        time.sleep(TIME)

def requests():
    print("Listening on MALCONREQ tag...")
    while True:
        transactions = list(set(utils.get_transactions_by_tag(tag=get_tag("REQ"))) ^ set(utils.get_members_by_label(label="requests")))
        utils.synchronize(transactions=transactions, label="requests")
        for tx_hash in transactions:
            request = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if cur_timestamp - int(request['timestamp']) >= 300:
                continue
            else:
                print("MALCONREQ: Sending vote...")
                candidates = utils.get_voting_peers()
                candidate = candidates[random.randint(0, len(candidates) - 1)]
                utils.send_vote(candidate=candidate.decode(), election_id=request['election_id'], eround=1)
                print('MALCONREQ: Peer {} voted successfully on candidate {} in election {} round 1'.format(env("CORE_PEER_ID"), candidate.decode(), request['election_id']))
            time.sleep(TIME)    

def votes():
    print("Listening on MALCONVOTE tag...")
    eround = 1
    while True:
        transactions = list(set(utils.get_transactions_by_tag(tag=get_tag("VOTE"))) ^ set(utils.get_members_by_label(label="votes")))
        utils.synchronize(transactions=transactions, label="votes")
        for tx_hash in transactions:
            vote = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if cur_timestamp - int(vote['timestamp']) >= 300:
                continue
            else:
                votes = utils.get_current_votes(election_id=vote['election_id'])
                if votes % (len(utils.get_voting_peers()) + 1) != 0:
                    continue
                else:
                    winners = utils.isElecFinal(election_id=vote['election_id'])
                    if len(winners) == 1:
                        winner = utils.get_election_winner(election_id=vote['election_id'])
                        if winner == env("CORE_PEER_ID"):
                            votes = utils.get_votes(election_id=vote['election_id'], address=env("CORE_PEER_ID"))
                            print("MALCONVOTE: Peer {} claiming executor after winning election {}".format(env("CORE_PEER_ID"), vote['election_id']))
                            utils.claim_executor(election_id=vote['election_id'], eround=eround, votes=votes, core_id=env("CORE_PEER_ID"))
                        eround = 1
                    else:
                        candidates = list(set(winners))
                        candidate = candidates[random.randint(0, len(candidates) - 1)]
                        eround += 1
                        print('MALCONVOTE: Peer {} voted successfully on candidate {} in election {} round {}'.format(env("CORE_PEER_ID"), candidate, vote['election_id'], str(eround)))
                        utils.send_vote(candidate=candidate, election_id=vote['election_id'], eround=eround)

            time.sleep(TIME)

def executors():
    print("Listening on MALCONEXEC tag...")
    while True:
        transactions = list(set(utils.get_transactions_by_tag(tag=get_tag("EXEC"))) ^ set(utils.get_members_by_label(label="executors")))
        utils.synchronize(transactions=transactions, label="executors")
        for tx_hash in transactions:
            executor = utils.read_transaction(tx_hash=tx_hash)
            cur_timestamp = math.floor(datetime.datetime.now().timestamp())
            if cur_timestamp - int(executor['timestamp']) >= 300:
                continue
            else:
                if utils.verify_executor(election_id=executor['election_id'], executor=executor['core_id']):
                    print("MALCONEXEC: Sending {}'s token to {}".format(env("CORE_PEER_ID"), executor['core_id']))
                    utils.send_token(executor=executor['core_id'], election_id=executor['election_id'])
        time.sleep(TIME)
