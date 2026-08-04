import json
from datetime import datetime
import redis


HOST_REDIS = "redis-memoria"
PUERTO_REDIS = 6379

PREFIJO_MEMORIA = "memoria:0x"
TOTAL_DIRECCIONES = 256

CLAVE_RESULTADOS = "laboratorio:resultados"
CLAVE_METADATA = "laboratorio:metadata"


def obtener_direccion(indice):
    return f"{PREFIJO_MEMORIA}{indice:04X}"


cliente = redis.Redis(
    host=HOST_REDIS,
    port=PUERTO_REDIS,
    decode_responses=True,
    socket_connect_timeout=5
)

print("=" * 70)
print("INICIALIZACIÓN DEL ESPACIO DE DIRECCIONES DISTRIBUIDO")
print("=" * 70)

if not cliente.ping():
    raise ConnectionError("Redis no respondió correctamente.")

# Eliminar únicamente el espacio utilizado por el laboratorio.
direcciones_anteriores = list(
    cliente.scan_iter(match=f"{PREFIJO_MEMORIA}*")
)

if direcciones_anteriores:
    cliente.delete(*direcciones_anteriores)

cliente.delete(CLAVE_RESULTADOS)
cliente.delete(CLAVE_METADATA)
cliente.config_resetstat()

# Crear las 256 posiciones.
pipeline = cliente.pipeline(transaction=False)

for indice in range(TOTAL_DIRECCIONES):
    direccion = obtener_direccion(indice)

    valor_inicial = {
        "direccion": direccion,
        "estado": "inicializada",
        "escritor": "nodo-master",
        "operacion": 0,
        "fecha": datetime.now().isoformat()
    }

    pipeline.set(direccion, json.dumps(valor_inicial))

pipeline.execute()

cliente.hset(
    CLAVE_METADATA,
    mapping={
        "direccion_inicial": obtener_direccion(0),
        "direccion_final": obtener_direccion(TOTAL_DIRECCIONES - 1),
        "total_direcciones": TOTAL_DIRECCIONES
    }
)

print(f"Servidor Redis: {HOST_REDIS}:{PUERTO_REDIS}")
print(f"Dirección inicial: {obtener_direccion(0)}")
print(f"Dirección final: {obtener_direccion(TOTAL_DIRECCIONES - 1)}")
print(f"Direcciones creadas: {TOTAL_DIRECCIONES}")
print()
print("ESPACIO DE DIRECCIONES INICIALIZADO CORRECTAMENTE")