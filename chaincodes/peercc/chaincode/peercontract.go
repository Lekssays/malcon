package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("example")

// Example format string. Everything except the message has a custom color
// which is dependent on the log level. Many fields have a custom output
// formatting too, eg. the time returns the hour down to the milli second.
var format = logging.MustStringFormatter(
	`%{color}%{time:15:04:05.000} %{shortfunc} ▶ %{level:.4s} %{id:03x}%{color:reset} %{message}`,
)

// SmartContract defines the structure of a smart contract
type SmartContract struct {
	contractapi.Contract
}

// Process defines the structure of the most critical process a peer runs
type Process struct {
	PID        string `json:"ID"`
	Replicated bool   `json:"replicated"`
	Rebooting  bool   `json:"rebooting"`
}

// Peer defines the structure of a peer entry
type Peer struct {
	ID         string  `json:"ID"`
	LastUpdate string  `json:"last_update"`
	Process    Process `json:"critical_process"`
}

// InitLedger adds a base set of peer entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	peers := []Peer{
		{
			ID:         "peerX.org1.example.com",
			LastUpdate: "1622359874",
			Process: Process{
				PID:        "temperature.sh",
				Replicated: true,
				Rebooting:  true,
			},
		},
		{
			ID:         "peerZ.org3.example.com",
			LastUpdate: "16223598589",
			Process: Process{
				PID:        "pressure.exe",
				Replicated: false,
				Rebooting:  false,
			},
		},
	}

	for _, peer := range peers {
		peerJSON, err := json.Marshal(peer)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(peer.ID, peerJSON)
		if err != nil {
			return fmt.Errorf("failed to put to world state. %v", err)
		}
	}

	return nil
}

// CreatePeer issues a new peer entry to the world state with given details.
func (s *SmartContract) CreatePeer(ctx contractapi.TransactionContextInterface, id string, lastUpdate string, pid string, replicated bool, rebooting bool) error {
	exists, err := s.PeerExists(ctx, id)
	if err != nil {
		return err
	}

	if exists {
		return fmt.Errorf("the peer %s already exists", id)
	}

	peer := Peer{
		ID:         id,
		LastUpdate: lastUpdate,
		Process: Process{
			PID:        pid,
			Replicated: replicated,
			Rebooting:  rebooting,
		},
	}
	peerJSON, err := json.Marshal(peer)

	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, peerJSON)
}

// ReadPeer returns the peer entry stored in the world state with given id.
func (s *SmartContract) ReadPeer(ctx contractapi.TransactionContextInterface, id string) (*Peer, error) {
	peerJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if peerJSON == nil {
		return nil, fmt.Errorf("the peer %s does not exist", id)
	}

	var peer Peer
	err = json.Unmarshal(peerJSON, &peer)
	if err != nil {
		return nil, err
	}

	return &peer, nil
}

// PeerExists returns true when a peer entry with given ID exists in world state
func (s *SmartContract) PeerExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	peerJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read from world state: %v", err)
	}

	return peerJSON != nil, nil
}

// GetAllPeers returns all peer found in world state
func (s *SmartContract) GetAllPeers(ctx contractapi.TransactionContextInterface) ([]*Peer, error) {
	// range query with empty string for startKey and endKey does an
	// open-ended query of all peer in the chaincode namespace.
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var peers []*Peer
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var peer Peer
		err = json.Unmarshal(queryResponse.Value, &peer)
		if err != nil {
			return nil, err
		}
		peers = append(peers, &peer)
	}

	return peers, nil
}
