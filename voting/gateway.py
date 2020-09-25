#!/usr/bin/python3
import time
import utils

def main():
    print("malware containment project")

    # TODO: Get the following variable from ELECTION CHANNEL (shared by Fabric SC)
    candidate = ""
    election_id = ""
    issuer = ""
    tx_id = ""

    tx1 = utils.send_request(tx_id=tx_id, issuer=issuer, election_id=election_id)
    print(tx1)
    time.sleep(4)
    tx2 = utils.send_vote(election_id=election_id, candidate=candidate)
    print(tx2)
    
    time.sleep(4)
    print(utils.get_transactions_by_tag(tag="MALCONVOTE"))

    time.sleep(3)
    tx3 = utils.register_peer(endpoint="0.0.0.0:8556", public_key="some pk", core_id="peer0.org1.example.com")
    print(tx3)


if __name__ == "__main__":
    main()
