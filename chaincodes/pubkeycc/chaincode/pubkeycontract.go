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

// PubKey defines the structure of a pubkey entry
type PubKey struct {
	ID        string `json:"ID"`
	Org       string `json:"org"`
	Content   string `json:"content"`
	Timestamp string `json:"detection_time"`
}

// InitLedger adds a base set of pubkey entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	pubkeys := []PubKey{
		{
			ID:        "org1_pubk",
			Org:       "org1",
			Content:   "-----BEGIN PUBLIC KEY----- MIIBIjANBgkqhkiG9w0BAQEFAA -----END PUBLIC KEY-----",
			Timestamp: "1600437396",
		},
		{
			ID:        "org2_pubk",
			Org:       "org2",
			Content:   "-----BEGIN PUBLIC KEY----- gkqhkiGMIIBIjANB9w0BAQEFAA -----END PUBLIC KEY-----",
			Timestamp: "1600437413",
		},
		{
			ID:        "org3_pubk",
			Org:       "org3",
			Content:   "-----BEGIN PUBLIC KEY----- 9w0BAQEFAAMIIBIjANBgkqhkiG -----END PUBLIC KEY-----",
			Timestamp: "1600437419",
		},
	}

	for _, pubkey := range pubkeys {
		pubkeyJSON, err := json.Marshal(pubkey)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(pubkey.ID, pubkeyJSON)
		if err != nil {
			return fmt.Errorf("failed to put to world state. %v", err)
		}
	}

	return nil
}

// CreatePubKey issues a new pubkey entry to the world state with given details.
func (s *SmartContract) CreatePubKey(ctx contractapi.TransactionContextInterface, id string, content string, timestamp string) error {
	exists, err := s.PubKeyExists(ctx, id)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("the pubkey %s already exists", id)
	}

	pubkey := PubKey{
		ID:        id,
		Content:   content,
		Timestamp: timestamp,
	}
	pubkeyJSON, err := json.Marshal(pubkey)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, pubkeyJSON)
}

// ReadPubKey returns the pubkey entry stored in the world state with given id.
func (s *SmartContract) ReadPubKey(ctx contractapi.TransactionContextInterface, id string) (*PubKey, error) {
	pubkeyJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if pubkeyJSON == nil {
		return nil, fmt.Errorf("the pubkey %s does not exist", id)
	}

	var pubkey PubKey
	err = json.Unmarshal(pubkeyJSON, &pubkey)
	if err != nil {
		return nil, err
	}

	return &pubkey, nil
}

// PubKeyExists returns true when a pubkey entry with given ID exists in world state
func (s *SmartContract) PubKeyExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	pubkeyJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read from world state: %v", err)
	}

	return pubkeyJSON != nil, nil
}

// GetAllPubkeys returns all pubkey found in world state
func (s *SmartContract) GetAllPubkeys(ctx contractapi.TransactionContextInterface) ([]*PubKey, error) {
	// range query with empty string for startKey and endKey does an
	// open-ended query of all pubkey in the chaincode namespace.
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var pubkeys []*PubKey
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var pubkey PubKey
		err = json.Unmarshal(queryResponse.Value, &pubkey)
		if err != nil {
			return nil, err
		}
		pubkeys = append(pubkeys, &pubkey)
	}

	return pubkeys, nil
}
