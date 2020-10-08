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
    return "Welcome to MALCON admin client for <b>{}</b>!".format(env("CORE_PEER_ID"))

@app.route('/tokens', methods=['POST'])
def receive_tokens():
    data = request.json
    helper.store_token(token=data['token'], election_id=data['election_id'])
    target_peer = helper.get_target_peer(election_id=data['election_id'])
    if helper.enough_tokens:
        output = helper.execute_strategy(endpoint=target_peer['endpoint'], election_id=data['election_id'])
        return 200, {
            'message': output
        }
    return 400, {
        'message': 'failure' 
    }

app.run(host='0.0.0.0', port=env.int("CORE_PEER_PORT"))
