#!/usr/bin/env python3

import argparse
import json
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path("/laboratorio3/modulo-b-ricart-agrawala")
CONFIG_FILE = BASE_DIR / "config" / "nodos.json"
RESOURCE_FILE = BASE_DIR / "recurso" / "estado_global.txt"
LOG_DIR = BASE_DIR / "logs"

BUFFER_SIZE = 4096
CONNECTION_TIMEOUT = 5
REPLY_TIMEOUT = 20


class RicartAgrawalaNode:
    def __init__(self, node_name: str) -> None:
        self.node_name = node_name

        self.nodes = self.load_nodes()
        self.host = self.nodes[node_name]["host"]
        self.port = self.nodes[node_name]["port"]

        self.clock = 0

        self.requesting = False
        self.in_critical_section = False
        self.request_timestamp: int | None = None

        self.received_replies: set[str] = set()
        self.deferred_replies: set[str] = set()

        self.lock = threading.RLock()
        self.reply_condition = threading.Condition(self.lock)

        self.running = True

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        RESOURCE_FILE.parent.mkdir(parents=True, exist_ok=True)

        self.log_file = LOG_DIR / f"{self.node_name}.log"

    @staticmethod
    def load_nodes() -> dict[str, dict[str, Any]]:
        if not CONFIG_FILE.is_file():
            raise FileNotFoundError(
                f"No se encontró la configuración: {CONFIG_FILE}"
            )

        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    def log(self, message: str) -> None:
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        with self.lock:
            formatted = (
                f"[{current_time}] "
                f"[{self.node_name}] "
                f"[L={self.clock}] "
                f"{message}"
            )

        print(formatted, flush=True)

        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(formatted + "\n")

    def increment_clock(self) -> int:
        with self.lock:
            self.clock += 1
            return self.clock

    def update_clock(self, received_timestamp: int) -> int:
        with self.lock:
            self.clock = max(self.clock, received_timestamp) + 1
            return self.clock

    def create_message(self, message_type: str) -> dict[str, Any]:
        timestamp = self.increment_clock()

        return {
            "type": message_type,
            "sender": self.node_name,
            "timestamp": timestamp,
        }

    def send_message(
        self,
        destination_node: str,
        message: dict[str, Any],
        retries: int = 3,
    ) -> bool:
        destination = self.nodes[destination_node]
        serialized = json.dumps(message).encode("utf-8") + b"\n"

        for attempt in range(1, retries + 1):
            try:
                with socket.create_connection(
                    (destination["host"], destination["port"]),
                    timeout=CONNECTION_TIMEOUT,
                ) as client_socket:
                    client_socket.sendall(serialized)

                self.log(
                    f"ENVIADO {message['type']} a {destination_node} "
                    f"con timestamp {message['timestamp']}"
                )

                return True

            except (ConnectionRefusedError, socket.timeout, OSError) as error:
                self.log(
                    f"Intento {attempt}/{retries} fallido al enviar "
                    f"{message['type']} a {destination_node}: {error}"
                )

                time.sleep(1)

        return False

    def send_reply(self, destination_node: str) -> None:
        reply = self.create_message("REPLY")
        self.send_message(destination_node, reply)

    def broadcast_request(self) -> None:
        with self.lock:
            self.clock += 1
            self.request_timestamp = self.clock
            request_timestamp = self.request_timestamp

        request = {
            "type": "REQUEST",
            "sender": self.node_name,
            "timestamp": request_timestamp,
        }

        for node_name in self.nodes:
            if node_name != self.node_name:
                self.send_message(node_name, request)

    def handle_request(
        self,
        sender: str,
        timestamp: int,
    ) -> None:
        self.update_clock(timestamp)

        with self.lock:
            should_defer = False

            if self.in_critical_section:
                should_defer = True

            elif self.requesting and self.request_timestamp is not None:
                own_priority = (
                    self.request_timestamp,
                    self.node_name,
                )

                sender_priority = (
                    timestamp,
                    sender,
                )

                if own_priority < sender_priority:
                    should_defer = True

            if should_defer:
                self.deferred_replies.add(sender)

                self.log(
                    f"REQUEST de {sender} diferido. "
                    f"Prioridad local="
                    f"({self.request_timestamp}, {self.node_name}), "
                    f"prioridad remota=({timestamp}, {sender})"
                )

                return

        self.log(
            f"REQUEST de {sender} aceptado; se enviará REPLY."
        )

        self.send_reply(sender)

    def handle_reply(
        self,
        sender: str,
        timestamp: int,
    ) -> None:
        self.update_clock(timestamp)

        with self.reply_condition:
            self.received_replies.add(sender)

            expected_replies = len(self.nodes) - 1

            self.log(
                f"REPLY recibido de {sender}. "
                f"Respuestas={len(self.received_replies)}/"
                f"{expected_replies}"
            )

            self.reply_condition.notify_all()

    def handle_release(
        self,
        sender: str,
        timestamp: int,
    ) -> None:
        self.update_clock(timestamp)

        self.log(
            f"RELEASE recibido de {sender}."
        )

    def process_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        sender = message.get("sender")
        timestamp = message.get("timestamp")

        if not isinstance(sender, str):
            self.log("Mensaje rechazado: sender inválido.")
            return

        if not isinstance(timestamp, int):
            self.log("Mensaje rechazado: timestamp inválido.")
            return

        self.log(
            f"RECIBIDO {message_type} desde {sender} "
            f"con timestamp {timestamp}"
        )

        if message_type == "REQUEST":
            self.handle_request(sender, timestamp)

        elif message_type == "REPLY":
            self.handle_reply(sender, timestamp)

        elif message_type == "RELEASE":
            self.handle_release(sender, timestamp)

        else:
            self.log(
                f"Tipo de mensaje desconocido: {message_type}"
            )

    def handle_connection(
        self,
        connection: socket.socket,
        address: tuple[str, int],
    ) -> None:
        try:
            with connection:
                received = b""

                while b"\n" not in received:
                    chunk = connection.recv(BUFFER_SIZE)

                    if not chunk:
                        break

                    received += chunk

                if not received:
                    return

                raw_message = received.split(b"\n", 1)[0]
                message = json.loads(raw_message.decode("utf-8"))

                self.process_message(message)

        except json.JSONDecodeError as error:
            self.log(
                f"JSON inválido desde {address}: {error}"
            )

        except Exception as error:
            self.log(
                f"Error procesando conexión desde {address}: {error}"
            )

    def start_server(self) -> None:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as server_socket:
            server_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )

            server_socket.bind(("0.0.0.0", self.port))
            server_socket.listen(20)
            server_socket.settimeout(1)

            self.log(
                f"Servidor iniciado en 0.0.0.0:{self.port}"
            )

            while self.running:
                try:
                    connection, address = server_socket.accept()

                    thread = threading.Thread(
                        target=self.handle_connection,
                        args=(connection, address),
                        daemon=True,
                    )

                    thread.start()

                except socket.timeout:
                    continue

                except OSError as error:
                    if self.running:
                        self.log(
                            f"Error en servidor TCP: {error}"
                        )

    def wait_for_replies(self) -> bool:
        expected_nodes = {
            node_name
            for node_name in self.nodes
            if node_name != self.node_name
        }

        deadline = time.monotonic() + REPLY_TIMEOUT

        with self.reply_condition:
            while self.received_replies != expected_nodes:
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    missing = (
                        expected_nodes - self.received_replies
                    )

                    self.log(
                        f"TIMEOUT esperando REPLY de: "
                        f"{sorted(missing)}"
                    )

                    return False

                self.reply_condition.wait(timeout=remaining)

        return True

    def enter_critical_section(
        self,
        duration: int,
    ) -> None:
        with self.lock:
            self.in_critical_section = True

        self.increment_clock()

        self.log(
            ">>> ENTRANDO A LA SECCIÓN CRÍTICA <<<"
        )

        timestamp = datetime.now().isoformat(timespec="seconds")

        with RESOURCE_FILE.open("a", encoding="utf-8") as file:
            file.write(
                f"{timestamp} | "
                f"{self.node_name} | "
                f"Lamport={self.clock} | "
                f"ENTRADA\n"
            )

            file.flush()

            for second in range(1, duration + 1):
                self.log(
                    f"Ejecutando operación crítica "
                    f"{second}/{duration}"
                )

                time.sleep(1)

            file.write(
                f"{datetime.now().isoformat(timespec='seconds')} | "
                f"{self.node_name} | "
                f"Lamport={self.clock} | "
                f"SALIDA\n"
            )

        self.increment_clock()

        self.log(
            "<<< SALIENDO DE LA SECCIÓN CRÍTICA >>>"
        )

        with self.lock:
            self.in_critical_section = False

    def release_critical_section(self) -> None:
        with self.lock:
            deferred_nodes = list(self.deferred_replies)

            self.deferred_replies.clear()
            self.requesting = False
            self.request_timestamp = None
            self.received_replies.clear()

        release = self.create_message("RELEASE")

        for node_name in self.nodes:
            if node_name != self.node_name:
                self.send_message(node_name, release)

        for node_name in deferred_nodes:
            self.log(
                f"Enviando REPLY diferido a {node_name}."
            )

            self.send_reply(node_name)

    def request_critical_section(
        self,
        duration: int,
    ) -> bool:
        with self.lock:
            if self.requesting or self.in_critical_section:
                self.log(
                    "Ya existe una solicitud o ejecución activa."
                )
                return False

            self.requesting = True
            self.received_replies.clear()

        self.log(
            "Solicitando acceso a la sección crítica."
        )

        self.broadcast_request()

        if not self.wait_for_replies():
            with self.lock:
                self.requesting = False
                self.request_timestamp = None
                self.received_replies.clear()

            self.log(
                "Solicitud cancelada por timeout."
            )

            return False

        self.log(
            "Todos los REPLY fueron recibidos."
        )

        self.enter_critical_section(duration)
        self.release_critical_section()

        return True

    def interactive_console(self) -> None:
        print()
        print("Comandos disponibles:")
        print("  request <segundos>  Solicitar sección crítica")
        print("  status              Mostrar estado interno")
        print("  exit                Terminar el nodo")
        print()

        while self.running:
            try:
                command = input(
                    f"{self.node_name}> "
                ).strip()

                if not command:
                    continue

                parts = command.split()

                if parts[0] == "request":
                    duration = 5

                    if len(parts) > 1:
                        duration = int(parts[1])

                    thread = threading.Thread(
                        target=self.request_critical_section,
                        args=(duration,),
                        daemon=True,
                    )

                    thread.start()

                elif parts[0] == "status":
                    with self.lock:
                        print(
                            json.dumps(
                                {
                                    "node": self.node_name,
                                    "clock": self.clock,
                                    "requesting": self.requesting,
                                    "in_critical_section":
                                        self.in_critical_section,
                                    "request_timestamp":
                                        self.request_timestamp,
                                    "received_replies":
                                        sorted(
                                            self.received_replies
                                        ),
                                    "deferred_replies":
                                        sorted(
                                            self.deferred_replies
                                        ),
                                },
                                indent=2,
                            )
                        )

                elif parts[0] == "exit":
                    self.running = False
                    break

                else:
                    print("Comando no reconocido.")

            except ValueError:
                print(
                    "La duración debe ser un número entero."
                )

            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

    def run(self) -> None:
        server_thread = threading.Thread(
            target=self.start_server,
            daemon=True,
        )

        server_thread.start()

        time.sleep(1)

        self.interactive_console()

        self.log("Nodo detenido.")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Nodo distribuido con exclusión mutua "
            "Ricart-Agrawala."
        )
    )

    parser.add_argument(
        "--node",
        required=True,
        choices=[
            "nodo-master",
            "nodo-slave1",
            "nodo-slave2",
        ],
        help="Nombre del nodo que ejecutará el proceso.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()

    node = RicartAgrawalaNode(arguments.node)
    node.run()
