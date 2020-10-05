#!/usr/bin/python3
import datetime
import math
import json

class Executor:
    def __init__(self, address = "", election_id = "", eround = 0, votes = [], timestamp = str(math.floor(datetime.datetime.now().timestamp()))):
        self.election_id = election_id
        self.timestamp = timestamp
        self.eround = eround
        self.votes = votes
        self.address = address

    def get(self):
        executor = {}
        executor['votes'] = self.votes
        executor['election_id'] = self.election_id
        executor['timestamp'] = self.timestamp
        executor['round'] = self.eround
        executor['address'] = self.address
        return json.dumps(executor)
