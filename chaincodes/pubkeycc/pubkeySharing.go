package main

import (
	"log"

	"github.com/Lekssays/malcon/chaincodes/pubkeycc/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	pubkeyChaincode, err := contractapi.NewChaincode(&chaincode.SmartContract{})
	if err != nil {
		log.Panicf("Error creating pubkey chaincode: %v", err)
	}

	if err := pubkeyChaincode.Start(); err != nil {
		log.Panicf("Error starting pubkey chaincode: %v", err)
	}
}
