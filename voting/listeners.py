#!/usr/bin/python3
import configparser
import time
import random
import urllib3
import utils

config = configparser.ConfigParser()
config.read('config.ini')

def elections():
    print("Listening on MALCONELEC tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag="MALCONELEC")
        for tx_hash in transactions:
            if utils.ismember(label="processed", txhash=tx_hash):
                continue
            else:
                print("MALCONELEC: storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="processed", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)
                if not utils.isElecInitiated(election_id=tx['election_id']):
                    print("MALCONELEC: Sending election requests with id {}".format(tx['election_id']))
                    utils.send_request(tx_id=tx_hash, issuer=utils.MYADDRESS, election_id=tx['election_id'])
        print("MALCONELEC: Sleeping for 5 seconds...")
        time.sleep(5)

def requests():
    print("Listening on MALCONREQ tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag="MALCONREQ")
        for tx_hash in transactions:
            if utils.ismember(label="requests", txhash=tx_hash):
                continue
            else:
                print("MALCONREQ: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="requests", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)
                print("MALCONREQ: Sending vote...")
                candidates = utils.get_voting_peers(origin=config['PEER']['CORE_ID'])
                candidate = candidates[random.randint(0, len(candidates))]
                utils.send_vote(candidate=candidate, election_id=tx['election_id'], eround=1)
                print('MALCONREQ: Peer {} voted successfully on candidate {} in election {}'.format(config['PEER']['CORE_ID'], candidate, tx['election_id']))
        print("MALCONREQ: Sleeping for 5 seconds...")
        time.sleep(5)    

def votes():
    print("Listening on MALCONVOTE tag...")
    eround = 1
    while True:
        transactions = utils.get_transactions_by_tag(tag="MALCONVOTE")
        for tx_hash in transactions:
            if utils.ismember(label="votes", txhash=tx_hash):
                continue
            else:
                print("MALCONVOTE: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="votes", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)

                isFinal, winners = utils.isElecFinal(election_id=tx['election_id'])
                if not isFinal:
                    candidates = list(set(utils.get_voting_peers(origin=config['PEER']['CORE_ID'])) & set(winners))
                    candidate = candidates[random.randint(0, len(candidates))]
                    utils.send_vote(candidate=candidate, election_id=tx['election_id'], eround=eround+1)                     
                else:
                    winner = utils.get_election_winner(election_id=tx['election_id'])
                    if winner == utils.MYADDRESS:
                        votes = utils.get_votes(election_id=tx['election_id'], address=utils.MYADDRESS)
                        print("MALCONVOTE: Peer {} claiming executor after winner election {}".format(config['PEER']['CORE_ID'], tx['election_id']))
                        utils.claim_executor(election_id=tx['election_id'], eround=eround, votes=votes)
                    eround = 1
        print("MALCONVOTE: Sleeping for 5 seconds...")
        time.sleep(5)

def executors():
    print("Listening on MALCONEXEC tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag="MALCONEXEC")
        for tx_hash in transactions:
            if utils.ismember(label="executors", txhash=tx_hash):
                continue
            else:
                print("MALCONEXEC: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="executors", txhash=tx_hash)
                executor = utils.read_transaction(tx_hash=tx_hash)
                if utils.verify_executor(election_id=executor['election_id'], executor_address=executor['address']):
                    print("MALCONEXEC: Sending {}'s token to {}".format(config['PEER']['CORE_ID'], executor['address']))
                    utils.send_token(executor_address=executor['address'])
        print("MALCONEXEC: Sleeping for 5 seconds...")
        time.sleep(5)
