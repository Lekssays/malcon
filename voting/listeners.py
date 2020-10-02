#!/usr/bin/python3
import configparser
import time
import random
import urllib3
import utils

def elections_listener():
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
                print("MALCONELEC: Sending election requests with id {}".format(tx['election_id']))
                utils.send_request(tx_id=tx_hash, issuer=utils.MYADDRESS, election_id=tx['election_id'])
        print("MALCONELEC: Sleeping for 5 seconds...")
        time.sleep(5)

def requests_listener():
    config = configparser.ConfigParser()
    config.read('config.ini')
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
                utils.send_vote(candidate=candidate, election_id=tx['election_id'])
                print('MALCONREQ: Peer {} voted successfully on candidate {} in election {}'.format(config['PEER']['CORE_ID'], candidate, tx['election_id']))
        print("MALCONREQ: Sleeping for 5 seconds...")
        time.sleep(5)    

def votes_listener():
    print("Listening on MALCONVOTE tag...")
    while True:
        transactions = utils.get_transactions_by_tag(tag="MALCONVOTE")
        for tx_hash in transactions:
            if utils.ismember(label="votes", txhash=tx_hash):
                continue
            else:
                print("MALCONVOTE: Storing tx {} locally...".format(tx_hash))
                utils.store_hash(label="votes", txhash=tx_hash)
                tx = utils.read_transaction(tx_hash=tx_hash)
                print(tx)
                # TODO: Count votes and issue other votes in case of ties
        print("MALCONVOTE: Sleeping for 5 seconds...")
        time.sleep(5)  
