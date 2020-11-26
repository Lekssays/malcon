#!/usr/bin/python3
import datetime
import math
import json

class Strategy:
    def __init__(self, name = "", commands = "", isFinal = False, system = "", timestamp = str(math.floor(datetime.datetime.now().timestamp()))):
        self.name = name
        self.commands = commands
        self.isFinal = isFinal
        self.system = system
        self.timestamp = timestamp

    def get(self):
        strategy = {}
        strategy['name'] = self.name
        strategy['commands'] = self.commands
        strategy['isFinal'] = self.isFinal
        strategy['timestamp'] = self.timestamp
        strategy['system'] = self.system
        return json.dumps(strategy)
