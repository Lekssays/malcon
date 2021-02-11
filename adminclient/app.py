#!/usr/bin/python3
import flask
import helper

from environs import Env
from flask import request

app = flask.Flask(__name__)
app.config["DEBUG"] = True

env = Env()
env.read_env()

peers_count = len(helper.get_peers())

@app.route('/', methods=['GET'])
def home():
    return {
        "message": "success",
        "type": "admin",
        "peer_id": env("CORE_PEER_ID")
    }, 200

@app.route('/tokens', methods=['POST'])
def receive_tokens():
    data = request.json
    helper.store_token(token=data, election_id=data['election_id'])
    current_tokens = helper.current_tokens(election_id=data['election_id'])
    if data['election_id']:
        if current_tokens > (peers_count / 2):
            target_peer = helper.get_target_peer(election_id=data['election_id'])
            output = helper.execute_strategy(peer=target_peer, election_id=data['election_id'])
            return {
                'message': output
            }, 200
        return {
            'message': 'token received!'
        }, 200
    return {
        'message': 'failure' 
    }, 400

app.run(host='0.0.0.0', port=env.int("CORE_PEER_PORT"))
