# Tunnelbar

macOS menubar SSH tunnel manager.

## Stack
- Python 3.11+, rumps, pyyaml, subprocess
- uv for environment and dependency management
- Config at ~/.config/tunnelbar/config.yaml

## Architecture
- app.py: rumps.App subclass, menu construction, toggle callbacks, health timer
- config.py: YAML loading, dataclasses (PortEntry, ServerEntry, Config), diffing
- tunnel.py: TunnelManager class, subprocess.Popen lifecycle
- ports.py: socket.connect_ex port-in-use check

## Key patterns
- TunnelKey = tuple[str, int] = (host, local_port) used everywhere
- Menu is fully rebuilt on config reload via menu.clear() + menu.add()
- Timer-based health check every 10s via @rumps.timer decorator
- Closures for toggle callbacks (see _make_toggle in app.py)

## Dev commands
- `make install` — uv sync
- `make plist` — install launchd agent
- `make unplist` — remove launchd agent
- `uv run tunnelbar` — run directly

## Not implemented (by design)
No key management, no password prompts, no SSH config editor,
no other forwarding modes, no Windows/Linux, no auto-reconnect.
