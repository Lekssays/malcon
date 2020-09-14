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

script_path=`dirname "$0"`

if [ ! -d "$script_path/chaincode" ]; then
  echo "chaincode/ folder was not found."
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

function networkDown() {
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
  configtxgen -outputBlock genesis.block -profile ThreeOrgsOrdererGenesis -channelID system-channel -configPath=.

  echo "Generating channel block..."
  configtxgen -profile ThreeOrgsChannel -outputCreateChannelTx $CHANNEL_NAME.tx -channelID $CHANNEL_NAME -configPath=.
}

function networkUp() {
  cd $PROJECT_DIRECTORY/network/
  
  docker-compose -f docker-compose.yml up -d ca.example.com orderer.example.com

  sleep 3

  docker-compose -f docker-compose.yml up -d peer0.org1.example.com peer0.org2.example.com peer0.org3.example.com cli

  sleep 2
  
  echo "**********************************"
  echo "********* Network Status *********"
  echo "**********************************"

  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

}

function checkNetworkStatus() {
  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

function createChannel() {
  setVariables 1
  
  echo "Creating channel..."
  peer channel create -o $ORDERER_ADDRESS  --ordererTLSHostnameOverride $ORDERER_HOSTNAME -c $CHANNEL_NAME -f $PROJECT_DIRECTORY/network/config/$CHANNEL_NAME.tx --outputBlock $PROJECT_DIRECTORY/network/config/$CHANNEL_NAME.block --tls true --cafile $ORDERER_CA

  echo "Joining peers to channel..."
  for orgId in 1 2 3
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
  echo "Packaging chaincode..."
  peer lifecycle chaincode package $COMPOSE_PROJECT_NAME.tar.gz --path ./chaincode --lang golang --label ${COMPOSE_PROJECT_NAME}_${CCVERSION}
  
  echo "Installing chaincode on peers..."
  for orgId in 1 2 3
  do
      setVariables $orgId
      peer lifecycle chaincode install $COMPOSE_PROJECT_NAME.tar.gz
  done
  
  echo "Exporting Package ID..."
  CC_PACKAGE_ID=$(peer lifecycle chaincode queryinstalled)
  CC_PACKAGE_ID=${CC_PACKAGE_ID%,*}
  CC_PACKAGE_ID=${CC_PACKAGE_ID#*:}
  CC_PACKAGE_ID=${CC_PACKAGE_ID##* }
  export CC_PACKAGE_ID=$CC_PACKAGE_ID

  echo "Approving chaincode for Organizations..."
  for orgId in 1 2 3
  do
    setVariables $orgId
    peer lifecycle chaincode approveformyorg -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --channelID $CHANNEL_NAME --name $COMPOSE_PROJECT_NAME --version $CCVERSION --package-id $CC_PACKAGE_ID --sequence 1 --tls --cafile $ORDERER_CA
  done

  echo "Check for commit readiness..."
  peer lifecycle chaincode checkcommitreadiness --channelID $CHANNEL_NAME --name $COMPOSE_PROJECT_NAME --version $CCVERSION --sequence 1 --tls --cafile $ORDERER_CA --output json

  # FIXME: make this more modular
  echo "Committing chaincode definition to channel..."
  peer lifecycle chaincode commit -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --channelID $CHANNEL_NAME --name $COMPOSE_PROJECT_NAME --version $CCVERSION --sequence 1 --tls --cafile $ORDERER_CA --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt --peerAddresses 0.0.0.0:8051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt --peerAddresses 0.0.0.0:9051 --tlsRootCertFiles ${PWD}/network/crypto-config/peerOrganizations/org3.example.com/peers/peer0.org3.example.com/tls/ca.crt

  peer lifecycle chaincode querycommitted --channelID $CHANNEL_NAME --name $COMPOSE_PROJECT_NAME --cafile $ORDERER_CA
}

function invokeChaincode() {
  cd $PROJECT_DIRECTORY
  setVariables 1
  # FIXME: make this more modular
  echo "Invoke chaincode..."
  peer chaincode invoke -o $ORDERER_ADDRESS --ordererTLSHostnameOverride $ORDERER_HOSTNAME --tls --cafile $ORDERER_CA -C $CHANNEL_NAME -n $COMPOSE_PROJECT_NAME  --peerAddresses 0.0.0.0:7051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt --peerAddresses 0.0.0.0:8051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt --peerAddresses 0.0.0.0:9051 --tlsRootCertFiles $PROJECT_DIRECTORY/network/crypto-config/peerOrganizations/org3.example.com/peers/peer0.org3.example.com/tls/ca.crt -c '{"function":"initLedger","Args":[]}'

  # JUST TO TEST
  peer chaincode query -C mychannel -n malcon -c '{"Args":["getAllAssets"]}'
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
elif [ "${MODE}" == "down" ]; then
  networkDown
elif [ "${MODE}" == "clear" ]; then
  clearState
elif [ "${MODE}" == "monitor" ]; then
  monitorNetwork
elif [ "${MODE}" == "deployCC" ]; then
  deployChaincode
elif [ "${MODE}" == "invokeCC" ]; then
  invokeChaincode
elif [ "${MODE}" == "netstat" ]; then
  checkNetworkStatus
elif [ "${MODE}" == "createC" ]; then
  createChannel
elif [ "${MODE}" == "restart" ]; then
  networkDown
  sleep 2
  generateBlocks
  sleep 2
  networkUp
  sleep 3
  createChannel
else
  printHelp
  exit 1
fi
