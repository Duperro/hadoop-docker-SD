#!/usr/bin/env bash

set -uo pipefail

errores=0

correcto() {
    echo "[OK] $1"
}

fallo() {
    echo "[ERROR] $1"
    errores=$((errores + 1))
}

echo "========================================"
echo " Verificación del clúster Hadoop"
echo "========================================"

echo
echo "1. Procesos del nodo maestro"
jps

if jps | grep -q "NameNode"; then
    correcto "NameNode activo"
else
    fallo "NameNode no encontrado"
fi

if jps | grep -q "ResourceManager"; then
    correcto "ResourceManager activo"
else
    fallo "ResourceManager no encontrado"
fi

echo
echo "2. DataNodes activos"

if hdfs dfsadmin -report 2>/dev/null |
    grep -q "Live datanodes (2)"; then
    correcto "Dos DataNodes activos"
else
    fallo "No se encontraron dos DataNodes activos"
fi

echo
echo "3. NodeManagers activos"

if yarn node -list 2>&1 |
    grep -Eq "Total Nodes:[[:space:]]*2"; then
    correcto "Dos NodeManagers activos"
else
    fallo "No se encontraron dos NodeManagers activos"
fi

echo
echo "4. Archivo de prueba"

if hdfs dfs -test -e \
    /user/hadoop/laboratorio1/datos-prueba.txt; then
    correcto "Archivo datos-prueba.txt disponible"
else
    fallo "Archivo datos-prueba.txt no encontrado"
fi

echo
echo "5. Integridad del archivo"

if hdfs fsck \
    /user/hadoop/laboratorio1/datos-prueba.txt \
    2>/dev/null |
    grep -q "Status: HEALTHY"; then
    correcto "Archivo HDFS saludable"
else
    fallo "El archivo no tiene estado HEALTHY"
fi

echo
echo "6. Resultado de MapReduce"

if hdfs dfs -test -e \
    /user/hadoop/laboratorio1/salida-wordcount/_SUCCESS; then
    correcto "Trabajo WordCount completado"
else
    fallo "No se encontró el resultado exitoso de WordCount"
fi

echo
echo "========================================"

if [[ "${errores}" -eq 0 ]]; then
    echo "RESULTADO: CLÚSTER COMPLETAMENTE OPERATIVO"
    exit 0
else
    echo "RESULTADO: ${errores} COMPROBACIÓN(ES) FALLIDA(S)"
    exit 1
fi