#!/usr/bin/python3
import datetime
import math
import json

class Vote:
    def __init__(self, voter = "", candidate = "", election_id = "", eround = 1, timestamp = math.floor(datetime.datetime.now().timestamp())):
        self.voter = voter
        self.candidate = candidate
        self.election_id = election_id
        self.timestamp = timestamp
        self.eround = eround

    def get(self):
        vote = {}
        vote['voter'] = self.voter
        vote['candidate'] = self.candidate
        vote['election_id'] = self.election_id
        vote['timestamp'] = self.timestamp
        vote['round'] = self.eround
        return json.dumps(vote)
