#!/usr/bin/python3
import jwt

from base64 import b64encode, b64decode
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

PUBKEYS = "./pubkeys/"

def get_pubkey(org: str):
    # TODO: get public key from the ledger
    with open (PUBKEYS + org + "_pubkey.pem", "r") as myfile:
        public_key = myfile.read()
        return public_key    

def verify_token(access_token: str, org: str) -> bool:
    public_key = get_pubkey(org=org)
    try:
        decoded = jwt.decode(access_token, public_key, algorithms='RS256')
        if decoded['org']:
            return True
        return False
    except Exception as e:
        print("Error: " + str(e))
        return False

def get_file(hash: str):
    # TODO: Get the file from the ledger
    print('get file from the ledger')
    commands_file = ''
    return commands_file

def execute_commands(file: str):
    # TODO: execute commands in the file
    print("execute commands")

def get_tokens(access_token: str) -> list:
    payload = jwt.decode(access_token, verify=False)
    tokens = []
    for key in payload['tokens']:
        ok = verify_token(access_token=payload[key], org=key)
        if ok:
            tokens.append(payload[key])
    return tokens

def get_organizations():
    # TODO: get how many organizations are there from the ledger
    orgs = 0
    return orgs
