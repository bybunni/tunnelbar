"""Check whether a local TCP port is already bound."""

import socket


def is_port_in_use(port: int) -> bool:
    """Return True if *port* on localhost is already accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0
