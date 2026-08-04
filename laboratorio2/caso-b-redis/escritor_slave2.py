import json
import socket
import time
import redis


HOST_REDIS = "redis-memoria"
PUERTO_REDIS = 6379

PREFIJO_MEMORIA = "memoria:0x"
TOTAL_DIRECCIONES = 256
TOTAL_ESCRITURAS = 100_000

CLAVE_RESULTADOS = "laboratorio:resultados"


def obtener_direccion(indice):
    return f"{PREFIJO_MEMORIA}{indice:04X}"


nodo = socket.gethostname()

cliente = redis.Redis(
    host=HOST_REDIS,
    port=PUERTO_REDIS,
    decode_responses=True,
    socket_connect_timeout=5,
    health_check_interval=30
)

if not cliente.ping():
    raise ConnectionError("No fue posible conectar con Redis.")

print("=" * 70)
print(f"ESCRITOR INICIADO EN {nodo}")
print(f"Espacio disponible: {TOTAL_DIRECCIONES} direcciones")
print(f"Escrituras programadas: {TOTAL_ESCRITURAS}")
print("=" * 70)

inicio_epoch = time.time()
inicio_medicion = time.perf_counter()

for operacion in range(1, TOTAL_ESCRITURAS + 1):
    # Recorrido circular entre 0x0000 y 0x00FF.
    indice = (operacion - 1) % TOTAL_DIRECCIONES
    direccion = obtener_direccion(indice)

    valor = (
        f"escritor={nodo}|"
        f"direccion={direccion}|"
        f"operacion={operacion}|"
        f"timestamp_ns={time.time_ns()}"
    )

    cliente.set(direccion, valor)

    if operacion % 20_000 == 0:
        print(
            f"{nodo}: {operacion}/{TOTAL_ESCRITURAS} escrituras",
            flush=True
        )

fin_medicion = time.perf_counter()
fin_epoch = time.time()
duracion = fin_medicion - inicio_medicion

resultado = {
    "nodo": nodo,
    "escrituras": TOTAL_ESCRITURAS,
    "direcciones_recorridas": TOTAL_DIRECCIONES,
    "duracion_segundos": round(duracion, 4),
    "operaciones_por_segundo": round(
        TOTAL_ESCRITURAS / duracion,
        2
    ),
    "inicio_epoch": inicio_epoch,
    "fin_epoch": fin_epoch
}

cliente.hset(
    CLAVE_RESULTADOS,
    nodo,
    json.dumps(resultado)
)

print("-" * 70)
print(f"Nodo: {nodo}")
print(f"Escrituras realizadas: {TOTAL_ESCRITURAS}")
print(f"Direcciones recorridas: {TOTAL_DIRECCIONES}")
print(f"Tiempo: {duracion:.4f} segundos")
print(f"Rendimiento: {TOTAL_ESCRITURAS / duracion:.2f} SET/s")
print("ESCRITOR FINALIZADO")