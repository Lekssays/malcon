# malcon
A Malware Containment Solution based on Blockchain

## Prerequisites
* Install Golang 1.16.3
* Install Docker
* Install Python 3.9.5

## Getting Started
* In one terminal, run `python3 ./logs/server.py` and a log file will be generated automatically in the same folder. It allows you to see all the steps of MalCon containment.
* To start the system, run `./system.sh up`
* To populate the blockchain with data, run `python3 ./tests/populate.py -c a`

## Structure