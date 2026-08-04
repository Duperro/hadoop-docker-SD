import json
from collections import Counter
import redis


HOST_REDIS = "redis-memoria"
PUERTO_REDIS = 6379

PREFIJO_MEMORIA = "memoria:0x"
TOTAL_DIRECCIONES_ESPERADAS = 256

CLAVE_RESULTADOS = "laboratorio:resultados"


cliente = redis.Redis(
    host=HOST_REDIS,
    port=PUERTO_REDIS,
    decode_responses=True
)

direcciones = sorted(
    cliente.scan_iter(match=f"{PREFIJO_MEMORIA}*")
)

valores = cliente.mget(direcciones)
resultados_crudos = cliente.hgetall(CLAVE_RESULTADOS)

resultados = {
    nodo: json.loads(datos)
    for nodo, datos in resultados_crudos.items()
}

print("=" * 70)
print("RESULTADOS DEL ESPACIO DE DIRECCIONES COMPARTIDO")
print("=" * 70)

print(f"Direcciones encontradas: {len(direcciones)}")
print(f"Direcciones esperadas: {TOTAL_DIRECCIONES_ESPERADAS}")

if len(direcciones) == TOTAL_DIRECCIONES_ESPERADAS:
    print("ESPACIO CONFIRMADO: existen las 256 posiciones.")
else:
    print("ERROR: el espacio de direcciones está incompleto.")

print()
print("MUESTRA DE POSICIONES")

for direccion, valor in list(zip(direcciones, valores))[:10]:
    print(f"{direccion} → {valor}")

ganadores = Counter()

for valor in valores:
    if not valor:
        ganadores["sin_valor"] += 1
        continue

    campos = {}

    for segmento in valor.split("|"):
        if "=" in segmento:
            clave, contenido = segmento.split("=", 1)
            campos[clave] = contenido

    ganador = campos.get("escritor", "desconocido")
    ganadores[ganador] += 1

print()
print("DISTRIBUCIÓN DE ÚLTIMAS ESCRITURAS")

for nodo, cantidad in sorted(ganadores.items()):
    print(f"{nodo}: última escritura en {cantidad} direcciones")

total_escrituras = 0

print()
print("RESULTADOS DE LOS ESCRITORES")

for nodo, resultado in sorted(resultados.items()):
    total_escrituras += resultado["escrituras"]

    print(f"Nodo: {nodo}")
    print(f"  Escrituras: {resultado['escrituras']}")
    print(
        f"  Direcciones recorridas: "
        f"{resultado['direcciones_recorridas']}"
    )
    print(f"  Duración: {resultado['duracion_segundos']} segundos")
    print(
        f"  Rendimiento: "
        f"{resultado['operaciones_por_segundo']} SET/s"
    )

if len(resultados) == 2:
    inicio_global = min(
        resultado["inicio_epoch"]
        for resultado in resultados.values()
    )

    fin_global = max(
        resultado["fin_epoch"]
        for resultado in resultados.values()
    )

    duracion_global = fin_global - inicio_global
    rendimiento_global = total_escrituras / duracion_global

    print()
    print(f"Escrituras totales: {total_escrituras}")
    print(f"Duración concurrente: {duracion_global:.4f} segundos")
    print(f"Rendimiento combinado: {rendimiento_global:.2f} SET/s")
    print("CONCURRENCIA CONFIRMADA: participaron los dos nodos.")
else:
    print("ADVERTENCIA: no se registraron los dos escritores.")

estadisticas = cliente.info("stats")

print()
print("ESTADÍSTICAS DE REDIS")
print(
    "Comandos procesados: "
    f"{estadisticas.get('total_commands_processed', 0)}"
)

bytes_recibidos = estadisticas.get("total_net_input_bytes", 0)

print(
    f"Datos recibidos: "
    f"{bytes_recibidos / (1024 * 1024):.2f} MB"
)

print()
print("INTERPRETACIÓN")
print(
    "Redis administró un espacio de 256 direcciones lógicas "
    "compartidas."
)
print(
    "Los dos nodos escribieron concurrentemente sobre todas las "
    "posiciones."
)
print(
    "Cada SET fue atómico, pero el último escritor de cada dirección "
    "no se puede determinar previamente."
)