#!/usr/bin/python3
import datetime
import math
import json

class Peer:
    def __init__(self, endpoint = "", public_key = "", core_id = "", address = "", timestamp = str(math.floor(datetime.datetime.now().timestamp()))):
        self.endpoint = endpoint
        self.public_key = public_key
        self.core_id = core_id
        self.address = address
        self.timestamp = timestamp

    def get(self):
        peer = {}
        peer['endpoint'] = self.endpoint
        peer['public_key'] = self.public_key
        peer['core_id'] = self.core_id
        peer['address'] = self.address
        peer['timestamp'] = self.timestamp
        return json.dumps(peer)
