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

// Neighbor defines the structure of a neighbor of a device
type Neighbor struct {
	IP string `json:"IP"`
}

// Malware defines the structure of a malware entry
type Malware struct {
	ID            string     `json:"ID"`
	Filename      string     `json:"filename"`
	Family        string     `json:"family"`
	Checksum      string     `json:"checksum"`
	DetectionTime string     `json:"detection_time"`
	Neighbors     []Neighbor `json:"neighbors"`
}

// InitLedger adds a base set of malware entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	malwares := []Malware{
		{
			ID:            "peer0/1",
			Filename:      "download.sh",
			Family:        "Mirai",
			Checksum:      "0c1675bf83c5031b3df8db0cba04400af169d9a6",
			DetectionTime: "300",
			Neighbors: []Neighbor{
				{
					IP: "192.168.5.11",
				},
				{
					IP: "192.168.55.11",
				},
			},
		},
		{
			ID:            "peer0/2",
			Filename:      "ads.sh",
			Family:        "Torii",
			Checksum:      "d3ae921b9687f1a4a0cb04e1bd4b064a407e723b",
			DetectionTime: "400",
			Neighbors: []Neighbor{
				{
					IP: "192.168.5.22",
				},
				{
					IP: "192.168.55.22",
				},
			},
		},
		{
			ID:            "peer0/3",
			Filename:      "update.sh",
			Family:        "Muhstik",
			Checksum:      "36eae9b881af69cb92e1129608866825085742be",
			DetectionTime: "500",
			Neighbors: []Neighbor{
				{
					IP: "192.168.5.33",
				},
				{
					IP: "192.168.55.33",
				},
			},
		},
	}

	for _, malware := range malwares {
		malwareJSON, err := json.Marshal(malware)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(malware.ID, malwareJSON)
		if err != nil {
			return fmt.Errorf("failed to put to world state. %v", err)
		}
	}

	return nil
}

// CreateMalware issues a new malware entry to the world state with given details.
func (s *SmartContract) CreateMalware(ctx contractapi.TransactionContextInterface, id string, filename string, family string, checksum string, detectionTime string, neighbors []Neighbor) error {
	exists, err := s.MalwareExists(ctx, id)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("the asset %s already exists", id)
	}

	malware := Malware{
		ID:            id,
		Filename:      filename,
		Family:        family,
		Checksum:      checksum,
		DetectionTime: detectionTime,
		Neighbors:     neighbors,
	}
	malwareJSON, err := json.Marshal(malware)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, malwareJSON)
}

// ReadMalware returns the malware entry stored in the world state with given id.
func (s *SmartContract) ReadMalware(ctx contractapi.TransactionContextInterface, id string) (*Malware, error) {
	malwareJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if malwareJSON == nil {
		return nil, fmt.Errorf("the asset %s does not exist", id)
	}

	var malware Malware
	err = json.Unmarshal(malwareJSON, &malware)
	if err != nil {
		return nil, err
	}

	return &malware, nil
}

// MalwareExists returns true when a malware entry with given ID exists in world state
func (s *SmartContract) MalwareExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	malwareJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read from world state: %v", err)
	}

	return malwareJSON != nil, nil
}

// GetAllMalware returns all malware found in world state
func (s *SmartContract) GetAllMalware(ctx contractapi.TransactionContextInterface) ([]*Malware, error) {
	// range query with empty string for startKey and endKey does an
	// open-ended query of all malware in the chaincode namespace.
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var malwares []*Malware
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var malware Malware
		err = json.Unmarshal(queryResponse.Value, &malware)
		if err != nil {
			return nil, err
		}
		malwares = append(malwares, &malware)
	}

	return malwares, nil
}
