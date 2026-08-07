#!/usr/bin/env python3

import socket
import ssl
from datetime import datetime
from pathlib import Path


HOST = "0.0.0.0"
PORT = 8443
BUFFER_SIZE = 4096

BASE_DIR = Path("/laboratorio3/modulo-a-tls")
CERT_DIR = BASE_DIR / "certificados"
SERVER_DIR = CERT_DIR / "nodo-master"
CA_DIR = CERT_DIR / "ca"
RECEIVED_DIR = BASE_DIR / "archivos-recibidos"

SERVER_CERT = SERVER_DIR / "nodo-master.crt"
SERVER_KEY = SERVER_DIR / "nodo-master.key"
CA_CERT = CA_DIR / "ca.crt"


def validate_files() -> None:
    """Comprueba que los certificados necesarios existan."""

    required_files = [SERVER_CERT, SERVER_KEY, CA_CERT]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo requerido: {file_path}"
            )


def create_ssl_context() -> ssl.SSLContext:
    """Crea el contexto TLS del servidor con autenticación mutua."""

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Certificado y clave privada del servidor.
    context.load_cert_chain(
        certfile=str(SERVER_CERT),
        keyfile=str(SERVER_KEY),
    )

    # CA utilizada para validar certificados de los clientes.
    context.load_verify_locations(cafile=str(CA_CERT))

    # Obliga al cliente a presentar un certificado válido.
    context.verify_mode = ssl.CERT_REQUIRED

    # Solo se permite TLS 1.2 o superior.
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    return context


def get_common_name(peer_certificate: dict) -> str:
    """Extrae el Common Name del certificado del cliente."""

    for subject_item in peer_certificate.get("subject", []):
        for key, value in subject_item:
            if key == "commonName":
                return value

    return "cliente-desconocido"


def receive_file(tls_socket: ssl.SSLSocket, client_name: str) -> None:
    """Recibe el nombre, tamaño y contenido de un archivo."""

    file_name_stream = tls_socket.makefile("rb")

    file_name = file_name_stream.readline().decode("utf-8").strip()
    file_size_line = file_name_stream.readline().decode("utf-8").strip()

    if not file_name or not file_size_line:
        raise ValueError("El cliente no envió metadatos válidos.")

    file_size = int(file_size_line)

    # Evita que el cliente escriba fuera de la carpeta permitida.
    safe_file_name = Path(file_name).name

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = RECEIVED_DIR / (
        f"{timestamp}-{client_name}-{safe_file_name}"
    )

    bytes_received = 0

    with destination.open("wb") as output_file:
        while bytes_received < file_size:
            remaining = file_size - bytes_received
            chunk = file_name_stream.read(min(BUFFER_SIZE, remaining))

            if not chunk:
                raise ConnectionError(
                    "La conexión terminó antes de recibir el archivo completo."
                )

            output_file.write(chunk)
            bytes_received += len(chunk)

    message = (
        f"Archivo recibido correctamente: {destination.name} "
        f"({bytes_received} bytes)"
    )

    print(f"[SERVIDOR] {message}")
    tls_socket.sendall(f"{message}\n".encode("utf-8"))


def run_server() -> None:
    """Inicia el servidor mTLS."""

    validate_files()
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

    ssl_context = create_ssl_context()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        server_socket.bind((HOST, PORT))
        server_socket.listen(5)

        print("=" * 65)
        print("Servidor TLS/mTLS iniciado")
        print(f"Dirección: {HOST}:{PORT}")
        print(f"Certificado: {SERVER_CERT}")
        print(f"CA confiable: {CA_CERT}")
        print("El cliente debe presentar un certificado válido.")
        print("=" * 65)

        while True:
            client_socket, client_address = server_socket.accept()

            print(
                f"\n[SERVIDOR] Conexión TCP desde "
                f"{client_address[0]}:{client_address[1]}"
            )

            try:
                with ssl_context.wrap_socket(
                    client_socket,
                    server_side=True,
                ) as tls_socket:
                    peer_certificate = tls_socket.getpeercert()
                    client_name = get_common_name(peer_certificate)

                    print(
                        f"[SERVIDOR] Handshake TLS exitoso con: "
                        f"{client_name}"
                    )
                    print(
                        f"[SERVIDOR] Versión TLS: "
                        f"{tls_socket.version()}"
                    )
                    print(
                        f"[SERVIDOR] Cifrado: "
                        f"{tls_socket.cipher()}"
                    )

                    receive_file(tls_socket, client_name)

            except ssl.SSLError as error:
                print(
                    f"[SERVIDOR] Conexión TLS rechazada: {error}"
                )
                client_socket.close()

            except Exception as error:
                print(
                    f"[SERVIDOR] Error procesando la conexión: {error}"
                )
                client_socket.close()


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Servidor detenido.")
    except Exception as error:
        print(f"[SERVIDOR] Error fatal: {error}")
        raise
