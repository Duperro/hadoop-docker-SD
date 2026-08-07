#!/usr/bin/env python3

import socket
import ssl
import sys
from pathlib import Path


SERVER_HOST = "nodo-master"
SERVER_PORT = 8443

BASE_DIR = Path("/laboratorio3/modulo-a-tls")
CA_CERT = BASE_DIR / "certificados" / "ca" / "ca.crt"


def create_ssl_context() -> ssl.SSLContext:
    """
    Crea un contexto que confía en la CA del servidor,
    pero no carga ningún certificado de cliente.
    """

    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(CA_CERT),
    )

    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True

    return context


def run_client() -> None:
    if not CA_CERT.is_file():
        raise FileNotFoundError(
            f"No se encontró el certificado de la CA: {CA_CERT}"
        )

    ssl_context = create_ssl_context()

    print("=" * 65)
    print("Cliente no autorizado")
    print(f"Servidor: {SERVER_HOST}:{SERVER_PORT}")
    print("Certificado de cliente: NO PRESENTADO")
    print("=" * 65)

    with socket.create_connection(
        (SERVER_HOST, SERVER_PORT),
        timeout=10,
    ) as tcp_socket:

        print("[CLIENTE NO AUTORIZADO] Conexión TCP establecida.")

        with ssl_context.wrap_socket(
            tcp_socket,
            server_hostname=SERVER_HOST,
        ) as tls_socket:

            print(
                "[CLIENTE NO AUTORIZADO] Handshake aparentemente completado."
            )

            # Forzamos intercambio de datos para recibir la alerta TLS
            # del servidor cuando exige certificado de cliente.
            tls_socket.sendall(
                b"Intento de acceso sin certificado de cliente\n"
            )

            response = tls_socket.recv(4096)

            print(
                "[CLIENTE NO AUTORIZADO] Respuesta recibida: "
                f"{response!r}"
            )


if __name__ == "__main__":
    try:
        run_client()

        print(
            "[RESULTADO] La conexión no fue rechazada como se esperaba.",
            file=sys.stderr,
        )
        sys.exit(1)

    except ssl.SSLError as error:
        print()
        print("[RESULTADO] Conexión rechazada correctamente.")
        print(f"[DETALLE TLS] {error}")
        sys.exit(0)

    except ConnectionRefusedError:
        print(
            "[ERROR] El servidor TLS no está ejecutándose.",
            file=sys.stderr,
        )
        sys.exit(1)

    except socket.timeout:
        print(
            "[ERROR] La conexión excedió el tiempo de espera.",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as error:
        print(
            f"[ERROR] Error inesperado: {error}",
            file=sys.stderr,
        )
        sys.exit(1)
