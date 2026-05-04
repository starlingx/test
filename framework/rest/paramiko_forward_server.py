import socket
import threading

import paramiko


class _ParamikoForwardServer(threading.Thread):
    """Local TCP server that forwards connections through a paramiko channel.

    Listens on a local port and for each accepted connection opens a
    direct-tcpip channel through the jump host to the target host:port,
    then shuttles data between the two sockets.
    """

    def __init__(self, local_port: int, remote_host: str, remote_port: int, jump_transport: paramiko.Transport):
        """Initialize the forward server.

        Args:
            local_port (int): Local port to listen on.
            remote_host (str): Remote host to forward to.
            remote_port (int): Remote port to forward to.
            jump_transport (paramiko.Transport): Paramiko transport of the jump host connection.
        """
        super().__init__(daemon=True)
        self._local_port = local_port
        self._remote_host = remote_host
        self._remote_port = remote_port
        self._jump_transport = jump_transport
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", local_port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Accept connections and forward them through the jump host."""
        while not self._stop_event.is_set():
            try:
                client_sock, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            threading.Thread(target=self._handle, args=(client_sock,), daemon=True).start()

    def _handle(self, client_sock: socket.socket) -> None:
        """Forward a single connection through the paramiko channel.

        Args:
            client_sock (socket.socket): The accepted local client socket.
        """
        try:
            channel = self._jump_transport.open_channel(
                "direct-tcpip",
                (self._remote_host, self._remote_port),
                ("127.0.0.1", 0),
            )
        except Exception:
            client_sock.close()
            return

        def _pump(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dst.close()
                except Exception:
                    pass

        t1 = threading.Thread(target=_pump, args=(client_sock, channel), daemon=True)
        t2 = threading.Thread(target=_pump, args=(channel, client_sock), daemon=True)
        t1.start()
        t2.start()

    def stop(self) -> None:
        """Stop the forward server."""
        self._stop_event.set()
        try:
            self._server_socket.close()
        except Exception:
            pass


def _find_free_port() -> int:
    """Find an available local port.

    Returns:
        int: An available local port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port
