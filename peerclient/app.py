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
    return "Welcome to MALCON peer client!"

@app.route('/tokens', methods=['POST'])
def receive_tokens():
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

app.run(host='0.0.0.0', port=int(config['PEER']['PORT']))
