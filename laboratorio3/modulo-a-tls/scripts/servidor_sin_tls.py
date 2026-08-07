#!/usr/bin/env python3

import socket
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8080
BUFFER_SIZE = 4096

BASE_DIR = Path("/laboratorio3/modulo-a-tls")
RECEIVED_DIR = BASE_DIR / "archivos-recibidos-sin-tls"

RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f"[SIN TLS] Servidor escuchando en {HOST}:{PORT}")

    while True:
        connection, address = server.accept()

        with connection:
            print(f"[SIN TLS] Conexión desde {address}")

            data = connection.recv(BUFFER_SIZE)

            if data:
                destination = RECEIVED_DIR / "mensaje-recibido.txt"
                destination.write_bytes(data)

                print("[SIN TLS] Contenido recibido:")
                print(data.decode("utf-8", errors="replace"))

                connection.sendall(
                    b"Archivo recibido sin cifrado\n"
                )
