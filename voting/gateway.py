#!/usr/bin/python3
import listeners
import time
import threading
import random
import utils

from environs import Env

env = Env()
env.read_env()

def main():
    print("malware containment project")

    # Register Peers
    endpoint = env("CORE_PEER_ENDPOINT")
    core_id = env("CORE_PEER_ID")
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
