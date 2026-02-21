"""SSH tunnel process lifecycle: spawn, kill, health-check."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from .config import TunnelKey
from .ports import is_port_in_use

log = logging.getLogger(__name__)

_SSH_PATH = shutil.which("ssh") or "/usr/bin/ssh"


@dataclass
class TunnelInfo:
    """Metadata and process handle for a managed tunnel."""

    host: str
    remote_port: int
    local_port: int
    proc: Optional[subprocess.Popen] = None

    @property
    def key(self) -> TunnelKey:
        return (self.host, self.local_port)

    @property
    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None


class TunnelManager:
    """Manages the set of active SSH tunnel subprocesses."""

    def __init__(self) -> None:
        self._tunnels: dict[TunnelKey, TunnelInfo] = {}

    @property
    def has_active(self) -> bool:
        return any(t.is_alive for t in self._tunnels.values())

    def is_active(self, key: TunnelKey) -> bool:
        info = self._tunnels.get(key)
        return info is not None and info.is_alive

    def find_by_local_port(self, local_port: int) -> TunnelKey | None:
        """Return the key of an active tunnel bound to *local_port*, if any."""
        for key, info in self._tunnels.items():
            if info.local_port == local_port and info.is_alive:
                return key
        return None

    def spawn(self, host: str, remote_port: int, local_port: int) -> tuple[str | None, TunnelKey | None]:
        """Start an SSH tunnel.

        Returns ``(error, displaced_key)`` — *error* is ``None`` on success,
        *displaced_key* is the key of a tunnel that was killed to free the port.
        """
        key: TunnelKey = (host, local_port)
        displaced: TunnelKey | None = None

        if self.is_active(key):
            return None, None  # already running

        # If another of our tunnels holds this port, kill it first.
        existing = self.find_by_local_port(local_port)
        if existing is not None:
            self.kill(existing)
            displaced = existing
        elif is_port_in_use(local_port):
            return f"Port {local_port} is already in use by another process", None

        cmd = [
            _SSH_PATH,
            "-N",
            "-o", "BatchMode=yes",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-L", f"{local_port}:localhost:{remote_port}",
            host,
        ]
        log.info("Spawning tunnel: %s", " ".join(cmd))

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            return "ssh command not found — is OpenSSH installed?", displaced
        except OSError as exc:
            return f"Failed to start ssh: {exc}", displaced

        self._tunnels[key] = TunnelInfo(
            host=host,
            remote_port=remote_port,
            local_port=local_port,
            proc=proc,
        )
        return None, displaced

    def kill(self, key: TunnelKey) -> None:
        """Terminate a tunnel and wait briefly for cleanup."""
        info = self._tunnels.pop(key, None)
        if info is None or info.proc is None:
            return
        log.info("Killing tunnel %s", key)
        info.proc.terminate()
        try:
            info.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            info.proc.kill()
            info.proc.wait(timeout=2)

    def kill_all(self) -> None:
        for key in list(self._tunnels):
            self.kill(key)

    def kill_keys(self, keys: set[TunnelKey]) -> None:
        """Tear down tunnels matching the given keys (used during config reload)."""
        for key in keys:
            if key in self._tunnels:
                self.kill(key)

    def health_check(self) -> list[TunnelKey]:
        """Poll all tunnels.  Returns keys of tunnels that died since last check."""
        dead: list[TunnelKey] = []
        for key, info in list(self._tunnels.items()):
            if info.proc is not None and info.proc.poll() is not None:
                log.warning("Tunnel %s exited with code %s", key, info.proc.returncode)
                dead.append(key)
                del self._tunnels[key]
        return dead
