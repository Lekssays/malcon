# MalCon
A Blockchain-based Malware Containment Framework

## Prerequisites
* Install Golang 1.16.3
* Install Docker
* Install Python 3.9.5
* Install pip3
* Install Hyperledger Fabric 2.2 and the binaries to your `$PATH`.

## Getting Started
* Install dependencies: `pip3 install -r requirements.txt`
* In one terminal, run `python3 ./logs/server.py` and a log file will be generated automatically in the same folder. It allows you to see all the steps of MalCon containment.
* To start the system, run `./system.sh up`
* To populate the blockchain with data, run `python3 ./tests/populate.py -c a`
* To add a new malware entry, run `python3 ./tests/populate.py -c m`
* To add a new peer entry, run `python3 ./tests/populate.py -c p`

## Bugs
For any bugs, please create an issue and we will work to fix it.