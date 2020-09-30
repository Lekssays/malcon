package main

import (
	"log"

	"github.com/Lekssays/malcon/chaincodes/strategycc/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	strategyChaincode, err := contractapi.NewChaincode(&chaincode.SmartContract{})
	if err != nil {
		log.Panicf("Error creating strategy chaincode: %v", err)
	}

	if err := strategyChaincode.Start(); err != nil {
		log.Panicf("Error starting strategy chaincode: %v", err)
	}
}
