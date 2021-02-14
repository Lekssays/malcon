#!/usr/bin/python3
import datetime
import math
import json

class Request:
    def __init__(self, tx_hash = "", timestamp = math.floor(datetime.datetime.now().timestamp()), issuer = "", election_id = ""):
        self.tx_hash = tx_hash
        self.timestamp = timestamp
        self.issuer = issuer
        self.election_id = election_id
    
    def get(self):
        request = {}
        request['tx_hash'] = self.tx_hash
        request['timestamp'] = self.timestamp
        request['issuer'] = self.issuer
        request['election_id'] = self.election_id
        return json.dumps(request)
