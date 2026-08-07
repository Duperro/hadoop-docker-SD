#!/usr/bin/env bash

set -euo pipefail

NODO="${1:-}"

if [[ -z "$NODO" ]]; then
    echo "Uso: $0 <nombre-del-nodo>"
    echo "Ejemplo: $0 nodo-slave1"
    exit 1
fi

BASE_DIR="/laboratorio3/modulo-a-tls/certificados"
CA_DIR="$BASE_DIR/ca"
NODE_DIR="$BASE_DIR/$NODO"

CA_CERT="$CA_DIR/ca.crt"
CA_KEY="$CA_DIR/ca.key"

NODE_KEY="$NODE_DIR/$NODO.key"
NODE_CSR="$NODE_DIR/$NODO.csr"
NODE_CERT="$NODE_DIR/$NODO.crt"
NODE_CONFIG="$NODE_DIR/$NODO.cnf"
NODE_EXT="$NODE_DIR/$NODO.ext"

if [[ ! -f "$CA_CERT" || ! -f "$CA_KEY" ]]; then
    echo "Error: no se encontraron los archivos de la CA."
    exit 1
fi

mkdir -p "$NODE_DIR"

cat > "$NODE_CONFIG" <<CONFIG
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = EC
ST = Guayas
L = Guayaquil
O = Universidad
OU = Sistemas Distribuidos
CN = $NODO

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $NODO
CONFIG

cat > "$NODE_EXT" <<CONFIG
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $NODO
CONFIG

echo "Generando clave privada para $NODO..."
openssl genrsa -out "$NODE_KEY" 2048
chmod 600 "$NODE_KEY"

echo "Generando CSR para $NODO..."
openssl req \
    -new \
    -key "$NODE_KEY" \
    -out "$NODE_CSR" \
    -config "$NODE_CONFIG"

echo "Firmando certificado de $NODO con la CA..."
openssl x509 \
    -req \
    -in "$NODE_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAserial "$CA_DIR/ca.srl" \
    -CAcreateserial \
    -out "$NODE_CERT" \
    -days 825 \
    -sha256 \
    -extfile "$NODE_EXT"

echo
echo "Verificando certificado..."
openssl verify \
    -CAfile "$CA_CERT" \
    "$NODE_CERT"

echo
echo "Certificado generado correctamente:"
echo "$NODE_CERT"
