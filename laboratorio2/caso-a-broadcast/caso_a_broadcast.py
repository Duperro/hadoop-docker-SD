from pyspark.sql import SparkSession
import os
import socket
import time


spark = (
    SparkSession.builder
    .appName("Laboratorio2-CasoA-Broadcast")
    .getOrCreate()
)

sc = spark.sparkContext
sc.setLogLevel("WARN")

# Estructura global original ubicada en el Driver.
configuracion_global = {
    "umbral_alerta": 80,
    "factor_penalizacion": 1.25,
    "modo": "laboratorio",
    "version": 1
}

print("=" * 65)
print("CASO A: MEMORIA DISTRIBUIDA DE SOLO LECTURA")
print("=" * 65)
print(f"Configuración original: {configuracion_global}")

# Spark serializa y distribuye una copia del objeto.
configuracion_broadcast = sc.broadcast(configuracion_global)

# Cambiar el objeto original no modifica las copias ya distribuidas.
configuracion_global["umbral_alerta"] = 999
configuracion_global["version"] = 2

print(f"Configuración modificada en el Driver: {configuracion_global}")


def leer_broadcast(indice_particion, elementos):
    hostname = socket.gethostname()
    pid = os.getpid()

    # La copia se obtiene una vez y se reutiliza en el proceso ejecutor.
    copia_local = configuracion_broadcast.value

    inicio = time.time()
    acumulado = 0

    # Simular muchas lecturas sobre la copia local.
    for _ in range(100000):
        acumulado += copia_local["umbral_alerta"]

    # Mantener la tarea activa para observar los ejecutores.
    time.sleep(8)

    yield {
        "particion": indice_particion,
        "nodo": hostname,
        "pid": pid,
        "id_local": id(copia_local),
        "umbral_leido": copia_local["umbral_alerta"],
        "version_leida": copia_local["version"],
        "lecturas": 100000,
        "resultado": acumulado,
        "tiempo": round(time.time() - inicio, 4)
    }


# Cuatro particiones para repartir trabajo entre los dos ejecutores.
resultados = (
    sc.parallelize(range(4), 4)
    .mapPartitionsWithIndex(leer_broadcast)
    .collect()
)

print()
print("RESULTADOS RECIBIDOS DESDE LOS EJECUTORES")
print("-" * 65)

for resultado in sorted(resultados, key=lambda elemento: elemento["particion"]):
    print(
        f"Partición={resultado['particion']} | "
        f"Nodo={resultado['nodo']} | "
        f"PID={resultado['pid']} | "
        f"ID local={resultado['id_local']} | "
        f"Umbral={resultado['umbral_leido']} | "
        f"Versión={resultado['version_leida']} | "
        f"Lecturas={resultado['lecturas']} | "
        f"Resultado={resultado['resultado']} | "
        f"Tiempo={resultado['tiempo']}s"
    )

nodos = sorted({resultado["nodo"] for resultado in resultados})

print()
print(f"Nodos ejecutores observados: {nodos}")
print(f"Valor actual en el Driver: {configuracion_global['umbral_alerta']}")
print(f"Valor conservado en Broadcast: {configuracion_broadcast.value['umbral_alerta']}")

if len(nodos) >= 2:
    print("DISTRIBUCIÓN CONFIRMADA: participaron al menos dos nodos.")
else:
    print("ADVERTENCIA: YARN asignó las tareas a un solo nodo.")

if configuracion_broadcast.value["umbral_alerta"] == 80:
    print("INMUTABILIDAD CONFIRMADA: Broadcast conservó la copia original.")
else:
    print("ERROR: el valor Broadcast cambió inesperadamente.")

configuracion_broadcast.unpersist()
spark.stop()