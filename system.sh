#!/bin/bash
set -e

export COMPOSE_PROJECT_NAME=malcon
export PROJECT_DIRECTORY=$PWD
export CORE_PEER_TLS_ENABLED=true
export ORDERER_CA=$PROJECT_DIRECTORY/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export ORDERER_ADDRESS=0.0.0.0:7050
export ORDERER_HOSTNAME=orderer.example.com
export ORG1_TLS_ROOTCERT_FILE=$PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export ORG2_TLS_ROOTCERT_FILE=$PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt
export ORG3_TLS_ROOTCERT_FILE=$PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org3.example.com/peers/peer0.org3.example.com/tls/ca.crt
export FABRIC_CFG_PATH=$PROJECT_DIRECTORY/network/config/
export CCVERSION=1.0
export CHANNEL_NAME=mychannel

# TODO: CHANGE THIS
ORGS=10
PEERS=10

script_path=`dirname "$0"`

if [ ! -d "$script_path/chaincodes" ]; then
  echo "chaincodes/ folder was not found."
  exit 1
fi

function printHelp() {
  echo "Usage: "
  echo "  network.sh <Mode>"
  echo "    Modes:"
  echo "      "$'\e[0;32m'up$'\e[0m' - brings up fabric orderer and peer nodes. with channel creation.
  echo "      "$'\e[0;32m'down$'\e[0m' - clears the network with docker-compose down
  echo "      "$'\e[0;32m'restart$'\e[0m' - restarts the network
  echo "      "$'\e[0;32m'clear$'\e[0m' - clears the state of the blockchain
  echo "      "$'\e[0;32m'netstat$'\e[0m' - checks network status
  echo "      "$'\e[0;32m'deployCC$'\e[0m' - installs and instantiate the chaincode
  echo "      "$'\e[0;32m'invokeCC$'\e[0m' - invokes the chaincode
  echo "      "$'\e[0;32m'createC$'\e[0m' - creates channel
}

function setVariables() {
  orgId=$1
  port=$((6051+orgId*1000))
  export CORE_PEER_ADDRESS=0.0.0.0:${port}
  export CORE_PEER_LOCALMSPID="Org${orgId}MSP"
  export PEER_ORG_CA=$PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org${orgId}.example.com/peers/peer0.org${orgId}.example.com/tls/ca.crt
  export CORE_PEER_TLS_ROOTCERT_FILE=$PEER_ORG_CA
  export CORE_PEER_MSPCONFIGPATH=$PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org${orgId}.example.com/users/Admin@org${orgId}.example.com/msp    
}

function restartNetwork() {
  docker rm -f $(docker ps -aq) || true
  #docker rmi -f $(docker images -a -q) || true
  docker volume rm $(docker volume ls)  || true
}

function clearNetwork {
  docker rm -f $(docker ps -aq) || true
  docker rmi -f $(docker images -a -q) || true
  docker volume rm $(docker volume ls)  || true  
}

function generateBlocks() {
  cd $PROJECT_DIRECTORY/network/
  echo "Generating crypto-config files..."
  if [ -d "crypto-config" ]; then
    rm -rf ./crypto-config/
  fi
  cryptogen generate --config=crypto-config.yaml

  echo "Generating genesis block..."
  cd $PROJECT_DIRECTORY/network/config/
  if test -f "genesis.block"; then
      rm *.block
  fi
  if test -f "$CHANNEL_NAME.tx"; then
      rm $CHANNEL_NAME.tx
  fi
  configtxgen -outputBlock genesis.block -profile FiveOrgsOrdererGenesis -channelID system-channel -configPath=.

  echo "Generating channel block..."
  configtxgen -profile FiveOrgsChannel -outputCreateChannelTx $CHANNEL_NAME.tx -channelID $CHANNEL_NAME -configPath=.
}

function networkUp() {
  cd $PROJECT_DIRECTORY/network/
  
  #docker-compose -f docker-compose.yml up -d ca.example.com ca.org1.example.com ca.org2.example.com ca.org3.example.com orderer.example.com

  #sleep 3

  docker-compose -f docker-compose.yml up 

  #sleep 3

  #docker-compose -f docker-compose.yml up -d peer1.org1.example.com peer1.org2.example.com peer1.org3.example.com

  
  echo "**********************************"
  echo "********* Network Status *********"
  echo "**********************************"

  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

}

function checkNetworkStatus() {
  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

function installDependencies() {
  for orgId in $(seq $ORGS);
  do
    for peerId in $(seq $PEERS);
    do
      echo "Installing dependencies on peer$peerId.org$orgId.example.com"
      docker exec -d peer$peerId.org$orgId.example.com /bin/sh -c "apk add --no-cache --virtual .build-deps g++ python3-dev libffi-dev openssl-dev openssl screen && apk add --no-cache --update python3 && apk add --no-cache --update redis && redis-server /client/peer$peerId.org$orgId.example.com.rd.conf && pip3 install --upgrade pip setuptools && pip3 install -r /client/requirements.txt"
    done
  done  
}

function configureRedis() {
  for orgId in $(seq $ORGS);
  do
    for peerId in $(seq $PEERS);
    do
      echo "Configuring redis on peer$peerId.org$orgId.example.com"
      docker exec -d peer$peerId.org$orgId.example.com /bin/sh -c "cp /client/redis.conf /client/peer$peerId.org$orgId.example.com.rd.conf && sed -i 's/XXXXX/110$orgId$peerId/' /client/peer$peerId.org$orgId.example.com.rd.conf && redis-server /client/peer$peerId.org$orgId.example.com.rd.conf"
    done
  done  
}

function generateKeys() {
  for orgId in $(seq $ORGS);
  do
    for peerId in $(seq $PEERS);
    do
      echo "Generating keys on peer$peerId.org$orgId.example.com..."
      docker exec -d peer$peerId.org$orgId.example.com /bin/sh -c "/bin/sh /core/generate_keypair.sh &"
    done
  done  
}

function runEndpoints() {
  for orgId in $(seq $ORGS);
  do
    for peerId in $(seq $PEERS);
    do
      echo "Running endpoint on peer$peerId.org$orgId.example.com..."
      docker exec -d peer$peerId.org$orgId.example.com /bin/sh -c "python3 /client/app.py"
    done
  done
}

function runGateways() {
  for orgId in $(seq $ORGS);
  do
    echo "Running gateway on peer0.org$orgId.example.com..."
    docker exec -d peer0.org$orgId.example.com /bin/sh -c "python3 /core/gateway.py"  
  done
}

function createChannel() {
  setVariables 1
  
  echo "Creating channel..."
  peer channel create -o $ORDERER_ADDRESS  --ordererTLSHostnameOverride $ORDERER_HOSTNAME -c $CHANNEL_NAME -f $PROJECT_DIRECTORY/network/config/$CHANNEL_NAME.tx --outputBlock $PROJECT_DIRECTORY/network/config/$CHANNEL_NAME.block --tls true --cafile $ORDERER_CA

  echo "Joining peers to channel..."
  for orgId in $(seq $ORGS);
  do
      setVariables $orgId
      peer channel join -b $PROJECT_DIRECTORY/network/config/$CHANNEL_NAME.block 
  done
}

function monitorNetwork() {
  if [ -z "$1" ]; then
    DOCKER_NETWORK=malcon_basic
  else
    DOCKER_NETWORK="$1"
  fi

  if [ -z "$2" ]; then
    PORT=8000
  else
    PORT="$2"
  fi

  echo "Starting monitoring on all containers on the network ${DOCKER_NETWORK}"

  docker kill logspout 2> /dev/null 1>&2 || true
  docker rm logspout 2> /dev/null 1>&2 || true

  docker run -d --name="logspout" \
    --volume=/var/run/docker.sock:/var/run/docker.sock \
    --publish=127.0.0.1:${PORT}:80 \
    --network  ${DOCKER_NETWORK} \
    gliderlabs/logspout
  sleep 3
  curl http://127.0.0.1:${PORT}/logs
}

function clearState() {
    docker exec peer0.org1.example.com \
    peer chaincode invoke -o $ORDERER_ADDRESS -C $CHANNEL_NAME -n malcon \
    --peerAddresses peer0.org1.example.com:7051 \
    --tls --cafile $ORDERER_CA --tlsRootCertFiles $ORG1_TLS_ROOTCERT_FILE \
    --peerAddresses peer0.org2.example.com:8051 \
    --tls --cafile $ORDERER_CA --tlsRootCertFiles $ORG2_TLS_ROOTCERT_FILE \
    --peerAddresses peer0.org3.example.com:9051 \
    --tls --cafile $ORDERER_CA --tlsRootCertFiles $ORG3_TLS_ROOTCERT_FILE \
    -c '{"Args":["clearState"]}'
}

function deployChaincode() {
  cd $PROJECT_DIRECTORY
  echo "Packaging $1 chaincode..."
  peer lifecycle chaincode package $1.tar.gz --path ./chaincodes/$1cc --lang golang --label ${1}_${CCVERSION}
  
  echo "Installing $1 chaincode on peers..."
  for orgId in $(seq $ORGS);
  do
      setVariables $orgId
      peer lifecycle chaincode install $1.tar.gz
  done
  
  echo "Exporting $1 Package ID..."
  CC_PACKAGE_ID=$(peer lifecycle chaincode queryinstalled)
  CC_PACKAGE_ID=${CC_PACKAGE_ID%,*}
  CC_PACKAGE_ID=${CC_PACKAGE_ID#*:}
  CC_PACKAGE_ID=${CC_PACKAGE_ID##* }
  export CC_PACKAGE_ID=$CC_PACKAGE_ID

  echo "Approving $1 chaincode for Organizations..."
  for orgId in $(seq $ORGS);
  do
    setVariables $orgId
    peer lifecycle chaincode approveformyorg -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --channelID $CHANNEL_NAME --name $1 --version $CCVERSION --package-id $CC_PACKAGE_ID --sequence 1 --tls --cafile $ORDERER_CA --signature-policy "OR ('Org1MSP.member','Org2MSP.member', 'Org3MSP.member')"
  done

  echo "Check for $1 commit readiness..."
  peer lifecycle chaincode checkcommitreadiness --channelID $CHANNEL_NAME --name $1 --version $CCVERSION --sequence 1 --tls --cafile $ORDERER_CA --signature-policy "OR ('Org1MSP.member','Org2MSP.member', 'Org3MSP.member')" --output json

  # TODO: make this more modular and modify endorsement policy in PROD
  echo "Committing $1 chaincode definition to channel..."
  peer lifecycle chaincode commit -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --channelID $CHANNEL_NAME --name $1 --version $CCVERSION --sequence 1 --tls --cafile $ORDERER_CA --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt --peerAddresses 0.0.0.0:8051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt --peerAddresses 0.0.0.0:9051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org3.example.com/peers/peer0.org3.example.com/tls/ca.crt --signature-policy "OR ('Org1MSP.member','Org2MSP.member', 'Org3MSP.member')"

  peer lifecycle chaincode querycommitted --channelID $CHANNEL_NAME --name $1 --cafile $ORDERER_CA
}

function invokeChaincode() {
  cd $PROJECT_DIRECTORY
  setVariables 1
  # FIXME: make this more modular
  echo "Invoke $1 chaincode..."
  peer chaincode invoke -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --tls --cafile $ORDERER_CA -C $CHANNEL_NAME -n $1  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt --peerAddresses 0.0.0.0:8051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt --peerAddresses 0.0.0.0:9051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org3.example.com/peers/peer0.org3.example.com/tls/ca.crt -c '{"function":"InitLedger","Args":[]}'

}

function queryChainecode() {
  echo "Querying $1 chaincodes..."
  cd $PROJECT_DIRECTORY
  setVariables 1
  if [ "$1" == "malware" ]; then
    peer chaincode query -C mychannel -n $1 -c '{"Args":["getAllMalware"]}'
  elif [ "$1" == "pubkey" ]; then
    peer chaincode query -C mychannel -n $1 -c '{"Args":["getAllPubkeys"]}'
  elif [ "$1" == "strategy" ]; then
    peer chaincode query -C mychannel -n $1 -c '{"Args":["getAllStrategies"]}'
  elif [ "$1" == "action" ]; then
  peer chaincode query -C mychannel -n $1 -c '{"Args":["getAllActions"]}'
  else
    peer chaincode query -C mychannel -n malware -c '{"Args":["getAllMalware"]}'
    sleep 1
    peer chaincode query -C mychannel -n pubkey -c '{"Args":["getAllPubkeys"]}'
    sleep 1
    peer chaincode query -C mychannel -n strategy -c '{"Args":["getAllStrategies"]}'
    sleep 1
    peer chaincode query -C mychannel -n action -c '{"Args":["getAllActions"]}'
  fi
}

function populate() {
  echo "${PWD}"
  echo "Create peer peer1.org1.example.com"
  peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreatePeer","Args":["peer1.org1.example.com", "[\"peer2.org1.example.com\"]", "1606834745", "PID_000001", "true", "true", "true"]}'

  sleep 3

  echo "Create peer peer1.org2.example.com"
  peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n peer  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreatePeer","Args":["peer1.org2.example.com", "[\"peer1.org1.example.com\"]", "1606834745", "PID_000001", "false", "true", "true"]}'

  sleep 3

  echo "Create malware MAL_000004"
  peer chaincode invoke -o 0.0.0.0:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile ${PWD}/network/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem -C mychannel -n malware  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt -c '{"function":"CreateMalware","Args":["MAL_000004", "kitkat.dark.mal", "/client/kitkat.dark.mal", "bot", "4e4d6c332b6fe62a63afe56171fd3725", "1606834745", "peer1.org1.example.com", "false", "[\"M\"]", "[1337]"]}'

}

if [[ $# -lt 1 ]] ; then
  printHelp
  exit 0
else
  MODE=$1
  shift
fi

if [ "${MODE}" == "up" ]; then
  generateBlocks
  sleep 2
  networkUp
  sleep 3
  createChannel
  sleep 3
  deployChaincode "malware"
  sleep 2
  deployChaincode "action"
  sleep 2
  deployChaincode "peer"
  sleep 2
  invokeChaincode "malware"
  sleep 2
  invokeChaincode "action"
  sleep 2
  invokeChaincode "peer"
elif [ "${MODE}" == "down" ]; then
  networkDown
elif [ "${MODE}" == "clear" ]; then
  clearState
elif [ "${MODE}" == "monitor" ]; then
  monitorNetwork
elif [ "${MODE}" == "deployCC" ]; then
  deployChaincode "malware"
  sleep 2
  deployChaincode "peer"
elif [ "${MODE}" == "invokeCC" ]; then
  invokeChaincode "malware"
  sleep 2
  invokeChaincode "peer"  
elif [ "${MODE}" == "netstat" ]; then
  checkNetworkStatus
elif [ "${MODE}" == "createC" ]; then
  createChannel
elif [ "${MODE}" == "clear" ]; then
  clearNetwork
elif [ "${MODE}" == "restart" ]; then
  restartNetwork
  sleep 2
  python3 ./test/generator.py -o $ORGS -p $PEERS
  sleep 2
  cp ./tests/docker_compose_test.yml ./network/docker_compose.yml 
  cp ./tests/peers_ports.json ./core/peers_ports.json
  sleep 3
  generateBlocks
  sleep 2
  networkUp
  sleep 3
  createChannel
  sleep 3
  deployChaincode "malware"
  sleep 2
  deployChaincode "peer"
  sleep 2
  invokeChaincode "malware"
  sleep 2
  invokeChaincode "peer"
  sleep 5
  #installDependencies
  #sleep 1
  generateKeys
  sleep 3
  configureRedis
  sleep 3
  runEndpoints
  #sleep 3
  #runGateways
elif [ "${MODE}" == "query" ]; then
  queryChainecode "action"
elif [ "${MODE}" == "deployW" ]; then
  deployWebServer
elif [ "${MODE}" == "populate" ]; then
  populate
elif [ "${MODE}" == "runEndpoints" ]; then
  runEndpoints
else
  printHelp
  exit 1
fi
