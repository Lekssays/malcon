#!/usr/bin/python3
import jwt
import random

from base64 import b64encode, b64decode
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

def get_nonce() -> str:
    return str(random.randint(10000, 999999))

def sign(org: int) -> bytes:
    private_key = False
    with open ("private_key.pem", "r") as myfile:
        private_key = myfile.read()
    nonce = get_nonce()
    access_token = jwt.encode({'org': org, 'nonce': nonce}, private_key, algorithm='RS256')
    return access_token

def main():
    # TODO: load organization from env variables
    org = 1
    access_token = sign(org=org)

if __name__ == '__main__':
    main()
