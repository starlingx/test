"""Standalone bounded TCP/UDP echo payload executed inside test-owned pods.

IPsecPolicyTrafficKeywords reads this file into a ConfigMap and mounts it
read-only as /probe/traffic.py. The pod runs its server/client CLI to verify
fresh nonce-correlated traffic independently of the ACE controller process.
It is a test resource, rather than an imported keyword: the remote Python
container needs only the standard library, not the automation framework.
"""

import argparse
import json
import socket
import time


def receive_message(connection: socket.socket) -> bytes:
    """Read one newline-delimited TCP message with a strict size limit.

    Args:
        connection (socket.socket): Connected TCP socket with a timeout.

    Returns:
        bytes: Complete bounded message.
    """
    message = b""
    deadline = time.monotonic() + connection.gettimeout()
    while not message.endswith(b"\n"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Timed out receiving a complete traffic response")
        connection.settimeout(remaining)
        chunk = connection.recv(1024)
        if not chunk:
            raise RuntimeError("Peer closed before completing the response")
        message += chunk
        if len(message) > 4096:
            raise RuntimeError("Oversized traffic message")
    return message


def run_server(arguments: argparse.Namespace) -> None:
    """Serve nonce echoes for a bounded pod lifetime.

    Args:
        arguments (argparse.Namespace): Explicit family, protocol, port and identity.
    """
    family = socket.AF_INET6 if arguments.family == 6 else socket.AF_INET
    kind = socket.SOCK_DGRAM if arguments.protocol == "udp" else socket.SOCK_STREAM
    with socket.socket(family, kind) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("::" if arguments.family == 6 else "0.0.0.0", arguments.port))
        server.settimeout(1)
        if kind == socket.SOCK_STREAM:
            server.listen(8)
        print("TRAFFIC SERVER READY", flush=True)
        deadline = time.monotonic() + arguments.lifetime
        while time.monotonic() < deadline:
            try:
                if kind == socket.SOCK_DGRAM:
                    message, peer = server.recvfrom(4096)
                    request = json.loads(message)
                    response = json.dumps({"nonce": request["nonce"], "server": arguments.identity, "protocol": arguments.protocol, "port": arguments.port}).encode() + b"\n"
                    server.sendto(response, peer)
                else:
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(3)
                        request = json.loads(receive_message(connection))
                        response = json.dumps({"nonce": request["nonce"], "server": arguments.identity, "protocol": arguments.protocol, "port": arguments.port}).encode() + b"\n"
                        connection.sendall(response)
            except (TimeoutError, json.JSONDecodeError, KeyError):
                continue


def run_client(arguments: argparse.Namespace) -> None:
    """Require a response from the selected server for every bounded request.

    Args:
        arguments (argparse.Namespace): Flow identity, nonce and request count.
    """
    family = socket.AF_INET6 if arguments.family == 6 else socket.AF_INET
    kind = socket.SOCK_DGRAM if arguments.protocol == "udp" else socket.SOCK_STREAM
    deadline = time.monotonic() + 40
    for index in range(arguments.count):
        nonce = f"{arguments.nonce}-{index}"
        request = json.dumps({"nonce": nonce}).encode() + b"\n"
        with socket.socket(family, kind) as client:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Overall traffic deadline exceeded")
            client.settimeout(min(arguments.timeout, remaining))
            client.connect((arguments.address, arguments.port))
            # UDP can lose the triggering datagram while a trap policy negotiates
            # its CHILD_SA. Retransmit only timeouts, retaining the same nonce and
            # the overall deadline; malformed or wrong-peer replies still fail.
            for attempt in range(3 if kind == socket.SOCK_DGRAM else 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Overall traffic deadline exceeded")
                client.settimeout(min(arguments.timeout, remaining))
                client.sendall(request)
                try:
                    response = client.recv(4096) if kind == socket.SOCK_DGRAM else receive_message(client)
                    break
                except TimeoutError:
                    if kind != socket.SOCK_DGRAM or attempt == 2:
                        raise
            observed = json.loads(response)
            if observed != {"nonce": nonce, "server": arguments.identity, "protocol": arguments.protocol, "port": arguments.port}:
                raise RuntimeError(f"Wrong peer, port or stale response: {observed}")
    print(json.dumps({"nonce": arguments.nonce, "server": arguments.identity, "protocol": arguments.protocol, "port": arguments.port, "count": arguments.count, "address": arguments.address}))


def main() -> None:
    """Parse explicitly bounded workload options and execute one role."""
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("server", "client"))
    parser.add_argument("--family", type=int, choices=(4, 6), required=True)
    parser.add_argument("--protocol", choices=("tcp", "udp"), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--address")
    parser.add_argument("--nonce")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--lifetime", type=int, default=3600)
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535 or not 1 <= arguments.count <= 20 or not 1 <= arguments.timeout <= 10 or not 1 <= arguments.lifetime <= 14400:
        parser.error("Traffic bounds exceeded")
    if arguments.role == "client" and (not arguments.address or not arguments.nonce):
        parser.error("Client address and fresh nonce are required")
    (run_server if arguments.role == "server" else run_client)(arguments)


if __name__ == "__main__":
    main()
