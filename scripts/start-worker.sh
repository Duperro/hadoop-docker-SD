#!/usr/bin/env bash

set -Eeuo pipefail

echo "========================================"
echo " Iniciando nodo trabajador: ${HOSTNAME}"
echo "========================================"

cleanup() {
    echo "Deteniendo servicios de ${HOSTNAME}..."

    yarn --daemon stop nodemanager || true
    hdfs --daemon stop datanode || true
}

trap cleanup SIGTERM SIGINT EXIT

mkdir -p /data/hdfs/datanode
mkdir -p /tmp/hadoop-yarn/local
mkdir -p /tmp/hadoop-yarn/logs

echo "Iniciando DataNode..."
hdfs --daemon start datanode

echo "Iniciando NodeManager..."
yarn --daemon start nodemanager

echo "Servicios de ${HOSTNAME} iniciados."

jps

# Mantener el contenedor funcionando
sleep infinity &
wait $!