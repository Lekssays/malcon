#!/usr/bin/python3
import flask
import helper

from environs import Env
from flask import request

app = flask.Flask(__name__)
app.config["DEBUG"] = True

env = Env()
env.read_env()

@app.route('/', methods=['GET'])
def home():
    return "Welcome to MALCON peer client!"

@app.route('/tokens', methods=['POST'])
def receive_tokens():
    if not helper.isRegistred():
        helper.register_target_peer()

    data = request.json
    tokens = data['tokens']
    election_id = data['election_id']
    issuer = data['issuer']
    res = helper.validate_tokens(tokens=tokens)
    if res:
        strategy_id = helper.get_strategy(election_id=election_id)
        tx_hash = helper.broadcast_execution(strategy_id=strategy_id, issuer=issuer)
        output = helper.execute_stategy(strategy_id=strategy_id)
        return 200, {
            'message': output,
            'tx_hash': tx_hash
        }

    return 400, {
        'message': 'failure' 
    }

app.run(host='0.0.0.0', port=env.int("CORE_PEER_PORT"))
