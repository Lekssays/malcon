#!/usr/bin/python3
import configparser
import flask
import helper

from flask import request

app = flask.Flask(__name__)
app.config["DEBUG"] = True

config = configparser.ConfigParser()
config.read('config.ini')

@app.route('/', methods=['GET'])
def home():
    return "Welcome to MALCON admin client!"

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

app.run(host='0.0.0.0', port=int(config['PEER']['PORT']))
