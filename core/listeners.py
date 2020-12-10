#!/usr/bin/python3
import datetime
import json
import math
import time
import random
import urllib3
import utils

from collections import defaultdict
from environs import Env

env = Env()
env.read_env()
TIME = 0

def get_tag(resource: str):
    return "MALCON" + resource.upper() + env("VERSION")

def elections():
    print("Listening on MALCONELEC tag...")
    while True:
        hashes = list(set(utils.get_transactions_hashes_by_tag(tag=get_tag("ELEC"))) ^ set(utils.get_members_hashes_by_label(label="processed")))
        utils.synchronize_hashes(hashes=hashes, label="processed")
        elections = utils.get_transactions_by_tag(tag=get_tag("ELEC"), hashes=hashes, returnAll=False)
        for election in elections:
            tx_hash = str(election.hash)
            election = json.loads(election.signature_message_fragment.decode().replace("\'", "\""))
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
        hashes = list(set(utils.get_transactions_hashes_by_tag(tag=get_tag("REQ"))) ^ set(utils.get_members_hashes_by_label(label="requests")))
        utils.synchronize_hashes(hashes=hashes, label="requests")
        requests = utils.get_transactions_by_tag(tag=get_tag("REQ"), hashes=hashes, returnAll=False)
        for request in requests:
            request = json.loads(request.signature_message_fragment.decode().replace("\'", "\""))
            print("MALCONREQ: Sending vote...")
            candidates = utils.get_voting_peers()
            candidate = candidates[random.randint(0, len(candidates) - 1)]
            utils.send_vote(candidate=candidate, election_id=request['election_id'], eround=1)
            print('MALCONREQ: Peer {} voted successfully on candidate {} in election {} round 1'.format(env("CORE_PEER_ID"), candidate, request['election_id']))
        time.sleep(TIME)

def votes():
    print("Listening on MALCONVOTE tag...")
    elections_rounds = defaultdict(lambda : 1)
    finalized_elections = defaultdict(lambda : False)
    while True:
        hashes = list(set(utils.get_transactions_hashes_by_tag(tag=get_tag("VOTE"))) ^ set(utils.get_members_hashes_by_label(label="votes")))
        if len(hashes) > (len(utils.get_voting_peers()) + 1) / 2 and len(hashes) > 0:
            utils.synchronize_hashes(hashes=hashes, label="votes")
            votes = utils.get_transactions_by_tag(tag=get_tag("VOTE"), hashes=hashes, returnAll=False)
            for vote in votes:
                vote = json.loads(vote.signature_message_fragment.decode().replace("\'", "\""))
                if not finalized_elections[vote['election_id']]:
                    winners = utils.isElecFinal(election_id=vote['election_id'], eround=int(vote['round']))
                    if len(winners) == 1:
                        finalized_elections[vote['election_id']] = True
                        if winners[0][0] == env("CORE_PEER_ID") and winners[0][1] > (len(utils.get_voting_peers()) + 1) / 2:
                            print("MALCONVOTE: Peer {} claiming executor after winning election {}".format(env("CORE_PEER_ID"), vote['election_id']))
                            utils.claim_executor(election_id=vote['election_id'], eround=int(vote['round']), votes=winners[0][1], core_id=env("CORE_PEER_ID"))
                    else:
                        candidates = []
                        for winner in winners:
                            if winner[0] != env("CORE_PEER_ID"):
                                candidates.append(winner[0])
                        candidate = candidates[random.randint(0, len(candidates) - 1)]
                        if utils.is_round_finalized(election_id=vote['election_id'], eround=elections_rounds[vote['election_id']]):
                            elections_rounds[vote['election_id']] += 1
                            print('MALCONVOTE: Peer {} voted successfully on candidate {} in election {} round {}'.format(env("CORE_PEER_ID"), candidate, vote['election_id'], str(elections_rounds[vote['election_id']])))
                            utils.send_vote(candidate=candidate, election_id=vote['election_id'], eround=elections_rounds[vote['election_id']])
        time.sleep(TIME)

def executors():
    print("Listening on MALCONEXEC tag...")
    while True:
        hashes = list(set(utils.get_transactions_hashes_by_tag(tag=get_tag("EXEC"))) ^ set(utils.get_members_hashes_by_label(label="executors")))
        utils.synchronize_hashes(hashes=hashes, label="executors")
        executors = utils.get_transactions_by_tag(tag=get_tag("EXEC"), hashes=hashes, returnAll=False)
        for executor in executors:
            executor = json.loads(executor.signature_message_fragment.decode().replace("\'", "\""))
            if utils.verify_executor(election_id=executor['election_id'], executor=executor['core_id'], eround=int(executor['round']), votes_count=int(executor['votes'])):
                if executor['core_id'] != env("CORE_PEER_ID"):
                    print("MALCONEXEC: Sending {}'s token to {}".format(env("CORE_PEER_ID"), executor['core_id']))
                    response = utils.send_token(executor=executor['core_id'], election_id=executor['election_id'])
                    if response.status == 200:
                        print("MALCONEXEC: Token Sent - Response ", response.data.decode('utf-8'))
                else:
                    token, signature = utils.generate_token()
                    with open(env("CORE_MAIN_PATH") + "/" + env("CORE_PEER_ID") + "_public_key.pem", "r") as f:
                        public_key = f.read()
                    payload = {"token": token, "signature": signature, "issuer": env("CORE_PEER_ID"), "election_id": executor['election_id'], "public_key": public_key}
                    utils.store_token(token=payload, election_id=executor['election_id'])
                    print("MALCONEXEC: Generated token - Token = ", payload)
        time.sleep(TIME)

def emergency():
    print("Listening on MALCONEMERG tag...")
    while True:
        hashes = list(set(utils.get_transactions_hashes_by_tag(tag=get_tag("EMERG"))) ^ set(utils.get_members_hashes_by_label(label="executors")))
        utils.synchronize_hashes(hashes=hashes, label="emergency")
        emergencies = utils.get_transactions_by_tag(tag=get_tag("EMERG"), hashes=hashes, returnAll=False)
        for emergency in emergencies:
            emergency = json.loads(emergency.signature_message_fragment.decode().replace("\'", "\""))
            neighbors = utils.get_neighbors()
            if emergency['issuer'] in neighbors:
                print("MALCONEMERG: Executing emergency strategy...")
                response = utils.execute_strategy(ports=emergency['ports'])
                print("MALCONEMERG: Execution Code = {}".format(str(response)))
        time.sleep(TIME)    