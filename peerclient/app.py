#!/usr/bin/python3
import flask
import helper
import threading
import redis

from environs import Env
from flask import request

env = Env()
env.read_env()
r = redis.Redis(host="0.0.0.0", port=env.int("CORE_PEER_REDIS_PORT"))

app = flask.Flask(__name__)
app.config["DEBUG"] = True

env = Env()
env.read_env()

if len(r.smembers("registred")) == 0:
    helper.register_target_peer()

if len(r.smembers("peers")) == 0:
    helper.store_peers()

if len(r.smembers("strategies")) == 0:
    helper.store_strategies()

@app.route('/', methods=['GET'])
def home():
    return {
        "message": "success",
        "type": "client",
        "peer_id": env("CORE_PEER_ID")
    }, 200

@app.route('/tokens', methods=['POST'])
def receive_tokens():
    data = request.json
    areValid = helper.validate_tokens(tokens=data['tokens'])
    election = helper.get_election(tx_hash=data['election_hash'])
    if areValid:
        final_command = helper.execute_strategies(strategies=election['strategies'], ports=election['ports'], path=election['path'])
        execution_tx = helper.broadcast_execution(strategies=election['strategies'], issuer=data['issuer'], election_id=data['election_id'], command=final_command)
        print(final_command, execution_tx)
        return {
            "message": "initialized strategies execution!",
            "broadcast_tx": str(execution_tx),
            "command": final_command,
            "election_id": data['election_id'],
            "issuer": data['issuer']
        }, 200

    return {
        "message": "invalid tokens!"
    }

try:
    app.run(host='0.0.0.0', port=env.int("CORE_PEER_PORT"))
except Exception as e:
    app.run(host='0.0.0.0', port=5000)