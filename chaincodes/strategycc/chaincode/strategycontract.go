package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract defines the structure of a smart contract
type SmartContract struct {
	contractapi.Contract
}

// Strategy defines the structure of a strategy entry
type Strategy struct {
	ID        string `json:"ID"`
	Content   string `json:"content"`
	Timestamp string `json:"detection_time"`
}

// InitLedger adds a base set of strategy entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	strategies := []Strategy{
		{
			ID:        "file_0.1",
			Content:   "#!/bin/bash\nsudo rm *.exe",
			Timestamp: "1600437396",
		},
		{
			ID:        "net_0.2",
			Content:   "#!/bin/bash\nsudo sudo ufw disallow 5698",
			Timestamp: "1600437413",
		},
		{
			ID:        "sys_1.3",
			Content:   "#!/bin/bash\nsudo reboot",
			Timestamp: "1600437419",
		},
	}

	for _, strategy := range strategies {
		strategyJSON, err := json.Marshal(strategy)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(strategy.ID, strategyJSON)
		if err != nil {
			return fmt.Errorf("failed to put to world state. %v", err)
		}
	}

	return nil
}

// CreateStrategy issues a new strategy entry to the world state with given details.
func (s *SmartContract) CreateStrategy(ctx contractapi.TransactionContextInterface, id string, content string, timestamp string) error {
	exists, err := s.StrategyExists(ctx, id)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("the strategy %s already exists", id)
	}

	strategy := Strategy{
		ID:        id,
		Content:   content,
		Timestamp: timestamp,
	}
	strategyJSON, err := json.Marshal(strategy)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, strategyJSON)
}

// ReadStrategy returns the strategy entry stored in the world state with given id.
func (s *SmartContract) ReadStrategy(ctx contractapi.TransactionContextInterface, id string) (*Strategy, error) {
	strategyJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if strategyJSON == nil {
		return nil, fmt.Errorf("the strategy %s does not exist", id)
	}

	var strategy Strategy
	err = json.Unmarshal(strategyJSON, &strategy)
	if err != nil {
		return nil, err
	}

	return &strategy, nil
}

// StrategyExists returns true when a strategy entry with given ID exists in world state
func (s *SmartContract) StrategyExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	strategyJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read from world state: %v", err)
	}

	return strategyJSON != nil, nil
}

// GetAllStrategies returns all strategy found in world state
func (s *SmartContract) GetAllStrategies(ctx contractapi.TransactionContextInterface) ([]*Strategy, error) {
	// range query with empty string for startKey and endKey does an
	// open-ended query of all strategy in the chaincode namespace.
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var strategies []*Strategy
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var strategy Strategy
		err = json.Unmarshal(queryResponse.Value, &strategy)
		if err != nil {
			return nil, err
		}
		strategies = append(strategies, &strategy)
	}

	return strategies, nil
}
