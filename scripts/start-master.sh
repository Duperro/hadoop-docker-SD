#!/usr/bin/env bash

set -Eeuo pipefail

echo "========================================"
echo " Iniciando nodo maestro: ${HOSTNAME}"
echo "========================================"

cleanup() {
    echo "Deteniendo servicios del nodo maestro..."

    yarn --daemon stop resourcemanager || true
    hdfs --daemon stop secondarynamenode || true
    hdfs --daemon stop namenode || true
}

trap cleanup SIGTERM SIGINT EXIT

# Formatear solamente durante la primera ejecución
if [[ ! -f /data/hdfs/namenode/current/VERSION ]]; then
    echo "No se encontró un NameNode inicializado."
    echo "Formateando el NameNode..."

    hdfs namenode -format -force -nonInteractive
else
    echo "El NameNode ya está inicializado."
    echo "Se conservarán los datos existentes."
fi

echo "Iniciando NameNode..."
hdfs --daemon start namenode

sleep 2

echo "Iniciando SecondaryNameNode..."
hdfs --daemon start secondarynamenode

echo "Iniciando ResourceManager..."
yarn --daemon start resourcemanager

echo "Servicios del nodo maestro iniciados."

jps

# Mantener el contenedor funcionando
sleep infinity &
wait $!