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
    return "Welcome to MALCON peer client <b>{}</b>!".format(env("CORE_PEER_PORT"))

@app.route('/tokens', methods=['POST'])
def receive_tokens():
    data = request.json
    tokens = data['tokens']
    election_id = data['election_id']
    issuer = data['issuer']
    # TODO: Validate Tokens
    return {
        'tokens': tokens,
        'election_id': election_id,
        'issuer': issuer
    }, 200

try:
    app.run(host='0.0.0.0', port=env.int("CORE_PEER_PORT"))
except Exception as e:
    app.run(host='0.0.0.0', port=5000)