export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=${PWD}/network/crypto-config/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=0.0.0.0:7051
export FABRIC_CFG_PATH=${PWD}/network/config/

echo "Create peer peer1.org1.example.com"
peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreatePeer","Args":["peer1.org1.example.com", "[\"peer2.org1.example.com\"]", "1606834745", "PID_000001", "true", "true", "true"]}'

sleep 3

echo "Create peer peer1.org2.example.com"
peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreatePeer","Args":["peer1.org2.example.com", "[\"peer1.org1.example.com\"]", "1606834745", "PID_000001", "false", "true", "true"]}'

sleep 3

echo "Create malware MAL_000004"
peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n malware  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreateMalware","Args":["MAL_000004", "kitkat.dark.mal", "/client/kitkat.dark.mal", "bot", "4e4d6c332b6fe62a63afe56171fd3725", "1606834745", "peer1.org1.example.com", "false", "[\"M\"]", "[1337]"]}'
