#!/usr/bin/python3
import datetime
import math
import json

class Request:
    def __init__(self, tx_id = "", timestamp = math.floor(datetime.datetime.now().timestamp()), issuer = "", election_id = ""):
        self.tx_id = tx_id
        self.timestamp = timestamp
        self.issuer = issuer
        self.election_id = election_id
    
    def get(self):
        request = {}
        request['tx_id'] = self.tx_id
        request['timestamp'] = self.timestamp
        request['issuer'] = self.issuer
        request['election_id'] = self.election_id
        return json.dumps(request)
