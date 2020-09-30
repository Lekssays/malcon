package main

import (
	"log"

	"github.com/Lekssays/malcon/chaincodes/actioncc/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	malwareChaincode, err := contractapi.NewChaincode(&chaincode.SmartContract{})
	if err != nil {
		log.Panicf("Error creating action chaincode: %v", err)
	}

	if err := malwareChaincode.Start(); err != nil {
		log.Panicf("Error starting action chaincode: %v", err)
	}
}
