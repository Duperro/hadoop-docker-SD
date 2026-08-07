#!/usr/bin/env python3

import argparse
import socket
import ssl
import sys
from pathlib import Path


SERVER_HOST = "nodo-master"
SERVER_PORT = 8443
BUFFER_SIZE = 4096

BASE_DIR = Path("/laboratorio3/modulo-a-tls")
CERTIFICATES_DIR = BASE_DIR / "certificados"
CA_CERT = CERTIFICATES_DIR / "ca" / "ca.crt"


def parse_arguments() -> argparse.Namespace:
    """Lee los argumentos enviados desde la terminal."""

    parser = argparse.ArgumentParser(
        description="Cliente para transferencia de archivos mediante mTLS."
    )

    parser.add_argument(
        "--node",
        required=True,
        choices=["nodo-slave1", "nodo-slave2"],
        help="Nombre del nodo que ejecuta el cliente.",
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Ruta del archivo que será enviado.",
    )

    parser.add_argument(
        "--host",
        default=SERVER_HOST,
        help=f"Servidor TLS. Valor predeterminado: {SERVER_HOST}",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=SERVER_PORT,
        help=f"Puerto TLS. Valor predeterminado: {SERVER_PORT}",
    )

    return parser.parse_args()


def validate_files(
    client_certificate: Path,
    client_key: Path,
    source_file: Path,
) -> None:
    """Comprueba que existan certificados, clave y archivo."""

    required_files = [
        CA_CERT,
        client_certificate,
        client_key,
        source_file,
    ]

    for file_path in required_files:
        if not file_path.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo requerido: {file_path}"
            )


def create_ssl_context(
    client_certificate: Path,
    client_key: Path,
) -> ssl.SSLContext:
    """Configura TLS y el certificado del cliente."""

    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(CA_CERT),
    )

    context.load_cert_chain(
        certfile=str(client_certificate),
        keyfile=str(client_key),
    )

    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # El nombre debe coincidir con nodo-master en el SAN.
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    return context


def send_file(
    tls_socket: ssl.SSLSocket,
    source_file: Path,
) -> None:
    """Envía metadatos y contenido del archivo."""

    file_size = source_file.stat().st_size

    metadata = (
        f"{source_file.name}\n"
        f"{file_size}\n"
    )

    tls_socket.sendall(metadata.encode("utf-8"))

    bytes_sent = 0

    with source_file.open("rb") as input_file:
        while True:
            chunk = input_file.read(BUFFER_SIZE)

            if not chunk:
                break

            tls_socket.sendall(chunk)
            bytes_sent += len(chunk)

    print(
        f"[CLIENTE] Archivo enviado: {source_file.name} "
        f"({bytes_sent} bytes)"
    )


def run_client() -> None:
    """Conecta con nodo-master y envía el archivo."""

    arguments = parse_arguments()

    client_directory = CERTIFICATES_DIR / arguments.node
    client_certificate = (
        client_directory / f"{arguments.node}.crt"
    )
    client_key = (
        client_directory / f"{arguments.node}.key"
    )
    source_file = Path(arguments.file)

    validate_files(
        client_certificate,
        client_key,
        source_file,
    )

    ssl_context = create_ssl_context(
        client_certificate,
        client_key,
    )

    print("=" * 65)
    print("Cliente mTLS")
    print(f"Nodo: {arguments.node}")
    print(f"Servidor: {arguments.host}:{arguments.port}")
    print(f"Archivo: {source_file}")
    print("=" * 65)

    with socket.create_connection(
        (arguments.host, arguments.port),
        timeout=10,
    ) as tcp_socket:

        with ssl_context.wrap_socket(
            tcp_socket,
            server_hostname=arguments.host,
        ) as tls_socket:

            print("[CLIENTE] Handshake TLS completado.")
            print(f"[CLIENTE] Versión TLS: {tls_socket.version()}")
            print(f"[CLIENTE] Cifrado: {tls_socket.cipher()}")

            server_certificate = tls_socket.getpeercert()

            print(
                "[CLIENTE] Certificado del servidor verificado: "
                f"{server_certificate.get('subject')}"
            )

            send_file(tls_socket, source_file)

            response = tls_socket.recv(BUFFER_SIZE)

            if response:
                print(
                    "[CLIENTE] Respuesta del servidor: "
                    f"{response.decode('utf-8').strip()}"
                )


if __name__ == "__main__":
    try:
        run_client()

    except FileNotFoundError as error:
        print(f"[CLIENTE] Error: {error}", file=sys.stderr)
        sys.exit(1)

    except PermissionError as error:
        print(
            f"[CLIENTE] Error de permisos: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ssl.SSLCertVerificationError as error:
        print(
            f"[CLIENTE] El certificado del servidor no es válido: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ssl.SSLError as error:
        print(
            f"[CLIENTE] Error durante el handshake TLS: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ConnectionRefusedError:
        print(
            "[CLIENTE] El servidor rechazó la conexión. "
            "Verifica que servidor_tls.py esté ejecutándose.",
            file=sys.stderr,
        )
        sys.exit(1)

    except socket.timeout:
        print(
            "[CLIENTE] La conexión excedió el tiempo de espera.",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as error:
        print(
            f"[CLIENTE] Error inesperado: {error}",
            file=sys.stderr,
        )
        sys.exit(1)
