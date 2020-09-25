#!/usr/bin/python3
import datetime
import math
import json

class Vote:
    def __init__(self, voter = "", candidate = "", election_id = "", timestamp = str(math.floor(datetime.datetime.now().timestamp()))):
        self.voter = voter
        self.candidate = candidate
        self.election_id = election_id
        self.timestamp = timestamp
    
    def get(self):
        vote = {}
        vote['voter'] = self.voter
        vote['candidate'] = self.candidate
        vote['election_id'] = self.election_id
        vote['timestamp'] = self.timestamp
        return json.dumps(vote)
