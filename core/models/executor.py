#!/usr/bin/python3
import datetime
import math
import json

class Executor:
    def __init__(self, core_id = "", election_id = "", eround = 0, votes = 0, timestamp = math.floor(datetime.datetime.now().timestamp())):
        self.election_id = election_id
        self.timestamp = timestamp
        self.eround = eround
        self.votes = votes
        self.core_id = core_id

    def get(self):
        executor = {}
        executor['votes'] = self.votes
        executor['election_id'] = self.election_id
        executor['timestamp'] = self.timestamp
        executor['round'] = self.eround
        executor['core_id'] = self.core_id
        return json.dumps(executor)
