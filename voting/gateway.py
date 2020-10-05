#!/usr/bin/python3
import configparser
import listeners
import time
import threading
import random
import utils

def main():
    print("malware containment project")
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Register Peers
    endpoint = config['PEER']['ENDPOINT']
    core_id = config['PEER']['CORE_ID']
    with open("public_key.pem", "r") as f:
        pubkey = f.read()
    iota_addr = utils.MYADDRESS
    register_peer_tx = utils.register_peer(endpoint=endpoint, public_key=pubkey, core_id=core_id, address=iota_addr)
    print("Peer {} registered! Tx hash: {}".format(core_id, register_peer_tx))

    # Store Peers Locally
    peers = utils.get_transactions_by_tag('MALCONPEER')
    utils.store_peers(peers=peers['hashes'])

    # Start all listeners
    elec_thread = threading.Thread(target=listeners.elections)
    reqs_thread = threading.Thread(target=listeners.requests)
    votes_thread = threading.Thread(target=listeners.votes)
    exec_thread = threading.Thread(target=listeners.executors)
    elec_thread.start()
    reqs_thread.start()
    votes_thread.start()
    exec_thread.start()



if __name__ == "__main__":
    main()
