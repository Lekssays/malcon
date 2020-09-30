package chaincode

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	. "github.com/iotaledger/iota.go/api"
	"github.com/iotaledger/iota.go/bundle"
	"github.com/iotaledger/iota.go/converter"
	"github.com/iotaledger/iota.go/trinary"
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

// Election defines the structure of a election entry
type Election struct {
	ID        string `json:"ID"`
	ActionID  string `json:"action_id"`
	Timestamp string `json:"timestamp"`
}

// Action defines the structure of action entry
type Action struct {
	ID         string `json:"ID"`
	StrategyID string `json:"strategy_id"`
	MalwareID  string `json:"malware_id"`
	Timestamp  string `json:"timestamp"`
}

// InitLedger adds a base set of malware entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	actions := []Action{
		{
			ID:         "AC_11252234",
			StrategyID: "1b3df8db0cba04400af1",
			MalwareID:  "peer0/1",
			Timestamp:  "0c1675bf83c5031b3df8db0cba04400af169d9a6",
		},
		{
			ID:         "AC_69523699",
			StrategyID: "675bf83c5031b3df8db0",
			MalwareID:  "peer0/1",
			Timestamp:  "0c1675bf83c5031b3df8db0cba04400af169d9a6",
		},
		{
			ID:         "AC_04723774",
			StrategyID: "0c1675bf83c5031b3df8d",
			MalwareID:  "peer0/1",
			Timestamp:  "0c1675bf83c5031b3df8d",
		},
	}

	for _, action := range actions {
		actionJSON, err := json.Marshal(action)
		if err != nil {
			return err
		}

		err = ctx.GetStub().PutState(action.ID, actionJSON)
		if err != nil {
			return fmt.Errorf("failed to put to world state. %v", err)
		}
	}

	return nil
}

// CreateElection initiates an election
func CreateElection(electionID string, actionID string, timestamp string) (string, bool) {
	backend := logging.NewLogBackend(os.Stderr, "", 0)
	backendFormatter := logging.NewBackendFormatter(backend, format)
	logging.SetBackend(backend, backendFormatter)

	const node = "https://nodes.devnet.iota.org"
	api, err := ComposeAPI(HTTPClientSettings{URI: node})

	if err != nil {
		log.Error(err)
		return "", false
	}

	const depth = 3
	const minimumWeightMagnitude = 9
	const tag = "MALCONELEC"
	// Just a dummy address and a seed that is not used since the transaction is has zero value (expected by iota)
	const address = trinary.Trytes("ZLGVEQ9JUZZWCZXLWVNTHBDX9G9KZTJP9VEERIIFHY9SIQKYBVAHIMLHXPQVE9IXFDDXNHQINXJDRPFDXNYVAPLZAW")
	const seed = trinary.Trytes("JBN9ZRCOH9YRUGSWIQNZWAIFEZUBDUGTFPVRKXWPAUCEQQFS9NHPQLXCKZKRHVCCUZNF9CZZWKXRZVCWQ")
	var data = fmt.Sprintf("{'election_id' : '%s', 'action_id': '%s', 'timestamp': '%s'}", electionID, actionID, timestamp)
	message, err := converter.ASCIIToTrytes(data)

	if err != nil {
		log.Error(err)
		return "", false
	}

	transfers := bundle.Transfers{
		{
			Address: address,
			Value:   0,
			Message: message,
			Tag:     tag,
		},
	}

	trytes, err := api.PrepareTransfers(seed, transfers, PrepareTransfersOptions{})

	if err != nil {
		log.Error(err)
		return "", false
	}

	myBundle, err := api.SendTrytes(trytes, depth, minimumWeightMagnitude)
	if err != nil {
		log.Error(err)
		return "", false
	}

	log.Infof("Transaction hash: %s", bundle.TailTransactionHash(myBundle))
	return bundle.TailTransactionHash(myBundle), true
}

// RandInt is a helper function that generate random integers
func RandInt(min int, max int) int {
	return min + rand.Intn(max-min)
}

// RandomNumber is a helper function that generates a random string
func RandomNumber(l int) string {
	bytes := make([]byte, l)
	for i := 0; i < l; i++ {
		bytes[i] = byte(RandInt(48, 57))
	}
	return string(bytes)
}

// CreateAction issues a new action taken after evaluating the available strategies
func (s *SmartContract) CreateAction(ctx contractapi.TransactionContextInterface, malwareID string) (string, error) {
	// TODO: add logic to choose a strategy
	strategyID := "OLGSLZJTSPRXLNNCKERMB"
	timestamp := fmt.Sprintf("%d", time.Now().Unix())

	rand.Seed(time.Now().UTC().UnixNano())
	ra := RandomNumber(10)
	id := fmt.Sprintf("AC_%s", ra)

	rand.Seed(time.Now().UTC().UnixNano())
	re := RandomNumber(10)
	electionID := fmt.Sprintf("ELEC_%s", re)

	action := Action{
		ID:         id,
		StrategyID: strategyID,
		MalwareID:  malwareID,
		Timestamp:  timestamp,
	}

	actionJSON, err := json.Marshal(action)
	log.Infof("Action object: %s", string(actionJSON))

	if err != nil {
		return "", err
	}

	txid, isSubmitted := CreateElection(electionID, id, timestamp)
	if isSubmitted == false {
		return "", fmt.Errorf("CreateElection failed")
	}
	err = ctx.GetStub().PutState(id, actionJSON)
	return txid, err
}

// ReadAction returns the action entry stored in the world state with given id.
func (s *SmartContract) ReadAction(ctx contractapi.TransactionContextInterface, id string) (*Action, error) {
	actionJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if actionJSON == nil {
		return nil, fmt.Errorf("the action %s does not exist", id)
	}

	var action Action
	err = json.Unmarshal(actionJSON, &action)
	if err != nil {
		return nil, err
	}

	return &action, nil
}

// GetAllActions returns all actions found in world state
func (s *SmartContract) GetAllActions(ctx contractapi.TransactionContextInterface) ([]*Action, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var actions []*Action
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var action Action
		err = json.Unmarshal(queryResponse.Value, &action)
		if err != nil {
			return nil, err
		}
		actions = append(actions, &action)
	}

	return actions, nil
}
