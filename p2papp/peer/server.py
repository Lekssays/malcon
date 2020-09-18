#!/usr/bin/python3

import utils

from flask import Flask
from flask import json, current_app, request

app = Flask(__name__)

@app.route('/')
def hello():
    return 'MalCon - Peer Server'

@app.route('/commands', methods=['POST'])
def send_commands():
    payload = request.get_json()
    file_hash = payload['hash']
    access_token = payload['access_token']
    org = 'org' + str(payload['org'])
    if utils.verify_token(access_token=access_token, org=org):
        tokens = utils.get_tokens(access_token=access_token)
        orgs = utils.get_organizations()
        commands_file = utils.get_file(hash=file_hash)
        if commands_file and len(tokens) > len(orgs) // 2.0:
            utils.execute_commands(file=commands_file)
            return{
                'status': 'success'
            }
        else:
            return {
                'status': 'error',
                'message': 'Invalid hash or not enough agreements.'
            }
    else:
        return {
            'status': 'error',
            'message': 'Forbidden.'
        }, 403