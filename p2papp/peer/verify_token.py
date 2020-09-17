#!/usr/bin/python3
import jwt

from base64 import b64encode, b64decode
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA


def get_organization(access_token: str) -> int:
    decoded = jwt.decode(access_token, verify=False)
    return decoded['org']

def verify(access_token: str) -> bool:
    with open ("public_key.pem", "r") as myfile:
        public_key = myfile.read()

    try:
        decoded = jwt.decode(access_token, public_key, algorithms='RS256')
        if decoded['org']:
            return True
        return False
    except Exception as e:
        print("Error: " + str(e))
        return False

def main():
    # TODO: communicate access token to verify using Flask
    access_token = ''
    verify(access_token=access_token)

if __name__ == '__main__':
    main()
