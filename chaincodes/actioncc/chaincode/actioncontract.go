package chaincode

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"github.com/hyperledger/fabric/common/util"
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
	ID         string   `json:"ID"`
	ActionID   string   `json:"action_id"`
	Timestamp  string   `json:"timestamp"`
	Target     string   `json:"target"`
	Strategies []string `json:"strategies"`
}

// Action defines the structure of action entry
type Action struct {
	ID        string `json:"ID"`
	MalwareID string `json:"malware_id"`
	Timestamp string `json:"timestamp"`
}

// InitLedger adds a base set of malware entries to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	actions := []Action{
		{
			ID:        "AC_11252234",
			MalwareID: "peer0/1",
			Timestamp: "0c1675bf83c5031b3df8db0cba04400af169d9a6",
		},
		{
			ID:        "AC_69523699",
			MalwareID: "peer0/1",
			Timestamp: "0c1675bf83c5031b3df8db0cba04400af169d9a6",
		},
		{
			ID:        "AC_04723774",
			MalwareID: "peer0/1",
			Timestamp: "0c1675bf83c5031b3df8d",
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
func CreateElection(electionID string, timestamp string, target string, strategies []string) (string, bool) {
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
	const tag = "MALCONELECVT"
	// Just a dummy address and a seed that is not used since the transaction has zero value (expected by iota)
	const address = trinary.Trytes("ZLGVEQ9JUZZWCZXLWVNTHBDX9G9KZTJP9VEERIIFHY9SIQKYBVAHIMLHXPQVE9IXFDDXNHQINXJDRPFDXNYVAPLZAW")
	const seed = trinary.Trytes("JBN9ZRCOH9YRUGSWIQNZWAIFEZUBDUGTFPVRKXWPAUCEQQFS9NHPQLXCKZKRHVCCUZNF9CZZWKXRZVCWQ")

	for i := range strategies {
		strategies[i] = "\"" + strategies[i] + "\""
	}
	printableStrategies := strings.Join(strategies, ",")

	var data = fmt.Sprintf("{\"election_id\" : \"%s\", \"timestamp\": \"%s\", \"target\": \"%s\", \"strategies\": [%+v], \"ports\": []}", electionID, timestamp, target, printableStrategies)
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

// UnionStrategies unions two sets of strategies
func UnionStrategies(a map[string]bool, b map[string]bool) map[string]bool {
	healingStrategies := map[string]bool{}
	for k := range a {
		healingStrategies[k] = true
	}
	for k := range b {
		healingStrategies[k] = true
	}
	return healingStrategies
}

// IntersectStrategies intersects two sets of strategies
func IntersectStrategies(a map[string]bool, b map[string]bool) map[string]bool {
	strategies := map[string]bool{}
	for k := range a {
		if b[k] {
			strategies[k] = true
		}
	}
	return strategies
}

// GetStrategies contains the process and malware matrices
func GetStrategies(actions []string, propagates bool, replicated bool, formatting bool, rebooting bool) []string {
	actionsMappings := map[string]int{
		"EF": 0,
		"DF": 1,
		"CR": 2,
		"M":  3,
		"SR": 4,
		"OP": 5,
	}

	existsMappings := map[bool]int{
		true:  0,
		false: 1,
	}

	malwareMatrix := [2][6][]string{
		{[]string{"F"}, []string{"DF", "CP"}, []string{"DF", "R", "CP"}, []string{"DF", "CP"}, []string{"DF", "CP", "R"}, []string{"DF", "CP"}},
		{[]string{"F"}, []string{"DF"}, []string{"DF", "R"}, []string{"DF", "CP"}, []string{"DF", "CP", "R"}, []string{"DF", "CP"}},
	}

	processMatrix := [3][]string{
		[]string{"F", "R", "DF", "CP"}, []string{"R", "DF", "CP"}, []string{"DF", "CP"},
	}

	malwareStrategies := map[string]bool{}
	for _, action := range actions {
		tmpStrategies := malwareMatrix[existsMappings[propagates]][actionsMappings[action]]
		for _, strategy := range tmpStrategies {
			malwareStrategies[strategy] = true
		}
	}

	processStrategies := map[string]bool{}
	if replicated || formatting {
		for _, strategy := range processMatrix[0] {
			processStrategies[strategy] = true
		}
	}

	if (!replicated || !formatting) && rebooting {
		for _, strategy := range processMatrix[1] {
			processStrategies[strategy] = true
		}
	}

	if !replicated && !formatting && !rebooting {
		for _, strategy := range processMatrix[2] {
			processStrategies[strategy] = true
		}
	}

	healingStrategies := UnionStrategies(malwareStrategies, processStrategies)
	finalStrategies := []string{}
	if propagates {
		emergencyStrategies := map[string]bool{"CP": true, "DF": true}
		finalStrategiesMap := IntersectStrategies(healingStrategies, emergencyStrategies)
		for k := range finalStrategiesMap {
			finalStrategies = append(finalStrategies, k)
		}
	} else {
		for k := range healingStrategies {
			finalStrategies = append(finalStrategies, k)
		}
	}
	return finalStrategies
}

// CreateAction issues a new action taken after evaluating the available strategies
func (s *SmartContract) CreateAction(ctx contractapi.TransactionContextInterface, malwareID string) (string, error) {
	// TODO: get malware info with malwareID QueryChaincode
	maliciousActions := []string{"M"}
	propagates := false

	log.Infof("MALWARE_ID: %s", malwareID)
	chainCodeArgs := util.ToChaincodeArgs("ReadMalware", malwareID)
	response := ctx.GetStub().InvokeChaincode("malware", chainCodeArgs, "mychannel")
	log.Infof("Query chaincode: %s", string(response.Payload))

	// TODO: get peer info (detector) QueryChaincode
	// peerID (target) and neighbors
	// get process info from the peer
	replicated := false
	formatting := false
	rebooting := false

	strategies := GetStrategies(maliciousActions, propagates, replicated, formatting, rebooting)

	timestamp := fmt.Sprintf("%d", time.Now().Unix())

	target := "peer1.org1.example.com"

	rand.Seed(time.Now().UTC().UnixNano())
	ra := RandomNumber(10)
	id := fmt.Sprintf("AC_%s", ra)

	rand.Seed(time.Now().UTC().UnixNano())
	re := RandomNumber(10)
	electionID := fmt.Sprintf("ELEC_%s", re)

	action := Action{
		ID:        id,
		MalwareID: malwareID,
		Timestamp: timestamp,
	}

	actionJSON, err := json.Marshal(action)

	if err != nil {
		return "", err
	}

	txid, isSubmitted := CreateElection(electionID, timestamp, target, strategies)
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
