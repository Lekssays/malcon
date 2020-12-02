package main

import (
	"log"

	"github.com/Lekssays/malcon/chaincodes/peercc/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	peerChaincode, err := contractapi.NewChaincode(&chaincode.SmartContract{})
	if err != nil {
		log.Panicf("Error creating peer chaincode: %v", err)
	}

	if err := peerChaincode.Start(); err != nil {
		log.Panicf("Error starting peer chaincode: %v", err)
	}
}
