#!/bin/bash

openssl genrsa -out ${CORE_PEER_ID}_private_key.pem 2048

openssl rsa -in ${CORE_PEER_ID}_private_key.pem -outform PEM -pubout -out ${CORE_PEER_ID}_public_key.pem