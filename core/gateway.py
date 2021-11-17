#!/usr/bin/python3
import asyncio
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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Register Peers
    if not r.smembers(env("CORE_PEER_ID")):
        endpoint = env("CORE_PEER_ENDPOINT")
        core_id = env("CORE_PEER_ID")
        with open(core_id + "_public_key.pem", "r") as f:
            pubkey = f.read()
        iota_addr = utils.MYADDRESS
        register_peer_tx = utils.register_peer(endpoint=endpoint, public_key=pubkey, core_id=core_id, address=iota_addr)
        r.sadd(env("CORE_PEER_ID"), str(register_peer_tx))
        message = "Peer {} registered! Tx hash: {}".format(core_id, register_peer_tx)
        print(message)
        loop.run_until_complete(utils.send_log(message))
    # store voting peers locally
    if not r.exists('voting_peers'):
        utils.store_voting_peers(origin=env("CORE_PEER_ID"))

    # initiate strategies
    # change this boolean to check if its a simulation or real life deployment
    initiate_strategies = False
    if initiate_strategies:
        strategies = utils.load_strategies()
        for strategy in strategies:
            utils.add_strategy(name=strategy['name'], commands=strategy['commands'], isFinal=strategy['isFinal'], system=strategy['system'])

    # Start all listeners
    elec_thread = threading.Thread(target=listeners.elections)
    votes_thread = threading.Thread(target=listeners.votes)
    exec_thread = threading.Thread(target=listeners.executors)
    emerg_thread = threading.Thread(target=listeners.emergency)
    broad_thread = threading.Thread(target=listeners.broadcasts)
    elec_thread.start()
    votes_thread.start()
    exec_thread.start()
    emerg_thread.start()
    broad_thread.start()

if __name__ == "__main__":
    main()
