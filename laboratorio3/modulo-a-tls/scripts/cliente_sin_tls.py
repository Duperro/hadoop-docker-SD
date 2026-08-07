#!/usr/bin/env python3

import socket
from pathlib import Path

HOST = "nodo-master"
PORT = 8080

FILE_PATH = Path(
    "/laboratorio3/modulo-a-tls/archivos-prueba/mensaje.txt"
)

data = FILE_PATH.read_bytes()

with socket.create_connection((HOST, PORT), timeout=10) as client:
    client.sendall(data)

    response = client.recv(4096)

    print(f"[SIN TLS] Se enviaron {len(data)} bytes")
    print(
        f"[SIN TLS] Respuesta: "
        f"{response.decode('utf-8').strip()}"
    )
