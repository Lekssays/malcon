#!/usr/bin/python3
import zmq

from pprint import pprint 

def main():
    print("Listening on live transactions...")
    
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://zmq.devnet.iota.org:5556')
    socket.subscribe('sn')
    print ("Socket connected")
    
    address = "MTPSOKOWNDRQTU9HVGRVOIHAKCYSJUWTS9ZUOSKDDVHRYUBBVADWUSUTSRCNPQGGFZCMRCWKWVPJXAWZC"
    print ("Listening for live transaction on address ", address)
    while True:
        message = socket.recv()
        data = message.split()
        tx_hash =  data[2].decode()
        tx_address = data[3].decode()
        if address == tx_address:
            print("Transaction Hash: ", tx_hash)

if __name__ == "__main__":
    main()