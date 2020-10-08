#!/usr/bin/python3
import json
import listeners
import time
import threading
import random
import redis
import utils

from environs import Env

env = Env()
env.read_env()
r = redis.Redis(host="0.0.0.0", port=env.int("CORE_PEER_REDIS_PORT"))

def main():
    print("malware containment project")

    # Register Peers
    if not r.smembers(env("CORE_PEER_ID")):
        endpoint = env("CORE_PEER_ENDPOINT")
        core_id = env("CORE_PEER_ID")
        with open(core_id + "_public_key.pem", "r") as f:
            pubkey = f.read()
        iota_addr = utils.MYADDRESS
        register_peer_tx = utils.register_peer(endpoint=endpoint, public_key=pubkey, core_id=core_id, address=iota_addr)
        r.sadd("registred", "yes")
        print("Peer {} registered! Tx hash: {}".format(core_id, register_peer_tx))

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
