"""Load, validate, and diff tunnelbar configuration."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".config" / "tunnelbar"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


def _find_example_config() -> Path:
    """Locate config.example.yaml in both development and .app bundle contexts."""
    # Development: two levels up from this file → project root
    dev_path = Path(__file__).resolve().parent.parent / "config.example.yaml"
    if dev_path.exists():
        return dev_path

    # py2app bundle: RESOURCEPATH points to Contents/Resources/
    resource_path = os.environ.get("RESOURCEPATH")
    if resource_path:
        bundle_path = Path(resource_path) / "config.example.yaml"
        if bundle_path.exists():
            return bundle_path

    return dev_path  # fallback; ensure_config handles missing file gracefully


EXAMPLE_CONFIG = _find_example_config()

# A TunnelKey uniquely identifies a tunnel on this machine: (host, local_port).
TunnelKey = tuple[str, int]


@dataclass(frozen=True)
class PortEntry:
    """A single port-forward specification within a server."""

    remote_port: int
    local_port: int  # equals remote_port when not remapped

    @property
    def display(self) -> str:
        if self.remote_port != self.local_port:
            return f"{self.remote_port} \u2192 {self.local_port}"
        return str(self.remote_port)


@dataclass(frozen=True)
class ServerEntry:
    """A single SSH server with its port-forward list."""

    name: str
    host: str
    ports: tuple[PortEntry, ...]


@dataclass
class Config:
    """Parsed configuration file."""

    servers: list[ServerEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def ensure_config() -> bool:
    """Ensure the config directory and file exist.

    Returns ``True`` if the config file already existed, ``False`` if it was
    created from the example template (caller should open it for the user).
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        return True
    if EXAMPLE_CONFIG.exists():
        shutil.copy2(EXAMPLE_CONFIG, CONFIG_PATH)
    else:
        CONFIG_PATH.write_text(
            "servers:\n"
            "  - name: example\n"
            "    host: example.com\n"
            "    ports:\n"
            "      - port: 8080\n",
            encoding="utf-8",
        )
    return False


def load_config() -> Config:
    """Parse the YAML config file into a :class:`Config`.

    Raises :class:`yaml.YAMLError` on parse failure and
    :class:`KeyError`/:class:`ValueError` on schema violations.
    """
    raw: dict[str, Any] = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    servers: list[ServerEntry] = []
    for srv in raw.get("servers", []):
        name = str(srv["name"])
        host = str(srv["host"])
        ports: list[PortEntry] = []
        for p in srv.get("ports", []):
            remote = int(p["port"])
            local = int(p.get("local_port", remote))
            ports.append(PortEntry(remote_port=remote, local_port=local))
        servers.append(ServerEntry(name=name, host=host, ports=tuple(ports)))
    return Config(servers=servers)


# ---------------------------------------------------------------------------
# Diffing (for config reload)
# ---------------------------------------------------------------------------


def _tunnel_keys(config: Config) -> set[TunnelKey]:
    keys: set[TunnelKey] = set()
    for srv in config.servers:
        for p in srv.ports:
            keys.add((srv.host, p.local_port))
    return keys


def diff_configs(
    old: Config, new: Config
) -> tuple[set[TunnelKey], set[TunnelKey], set[TunnelKey]]:
    """Compare two configs and return ``(added, removed, unchanged)`` tunnel keys."""
    old_keys = _tunnel_keys(old)
    new_keys = _tunnel_keys(new)
    return new_keys - old_keys, old_keys - new_keys, old_keys & new_keys
