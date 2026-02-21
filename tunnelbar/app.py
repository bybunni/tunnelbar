"""Tunnelbar: macOS menubar SSH tunnel manager."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import rumps

from .config import (
    CONFIG_PATH,
    Config,
    PortEntry,
    ServerEntry,
    TunnelKey,
    diff_configs,
    ensure_config,
    load_config,
)
from .tunnel import TunnelManager

log = logging.getLogger(__name__)

_RESOURCES = Path(__file__).resolve().parent / "resources"
ICON_IDLE = str(_RESOURCES / "icon_idle.png")
ICON_ACTIVE = str(_RESOURCES / "icon_active.png")
HEALTH_CHECK_INTERVAL = 10  # seconds


class TunnelbarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(name="Tunnelbar", icon=ICON_IDLE, template=True, quit_button=None)
        self.manager = TunnelManager()
        self.config: Config = Config()
        self._menu_items: dict[TunnelKey, rumps.MenuItem] = {}

        self._load_initial_config()
        self._build_menu()

    # ------------------------------------------------------------------ config

    def _load_initial_config(self) -> None:
        existed = ensure_config()
        if not existed:
            rumps.notification(
                "Tunnelbar",
                "Welcome!",
                "Config created at ~/.config/tunnelbar/config.yaml — edit it to add your servers.",
            )
            self._open_config_file()

        try:
            self.config = load_config()
        except Exception as exc:
            log.exception("Failed to load config on startup")
            rumps.notification("Tunnelbar", "Config Error", str(exc)[:200])
            self.config = Config()

    # ------------------------------------------------------------------ menu

    def _build_menu(self) -> None:
        self.menu.clear()
        self._menu_items.clear()

        for i, server in enumerate(self.config.servers):
            if i > 0:
                self.menu.add(rumps.separator)

            # Non-clickable server header
            header = rumps.MenuItem(server.name)
            header.set_callback(None)
            self.menu.add(header)

            for port_entry in server.ports:
                key: TunnelKey = (server.host, port_entry.local_port)
                title = f"  {port_entry.display}"
                item = rumps.MenuItem(
                    title,
                    callback=self._make_toggle(key, server, port_entry),
                )
                item.state = self.manager.is_active(key)
                self.menu.add(item)
                self._menu_items[key] = item

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("\u21bb Reload Config", callback=self._on_reload))
        self.menu.add(rumps.MenuItem("\u270e Edit Config", callback=self._on_edit))
        self.menu.add(rumps.MenuItem("Quit", callback=self._on_quit))

        self._update_icon()

    def _make_toggle(
        self, key: TunnelKey, server: ServerEntry, port_entry: PortEntry
    ) -> callable:
        """Return a closure that toggles the tunnel for *key*."""

        def toggle(sender: rumps.MenuItem) -> None:
            if self.manager.is_active(key):
                self.manager.kill(key)
                sender.state = False
            else:
                error, displaced = self.manager.spawn(
                    host=server.host,
                    remote_port=port_entry.remote_port,
                    local_port=port_entry.local_port,
                )
                # Uncheck the menu item of any tunnel we displaced
                if displaced is not None:
                    displaced_item = self._menu_items.get(displaced)
                    if displaced_item is not None:
                        displaced_item.state = False
                if error:
                    rumps.notification("Tunnelbar", "Tunnel Error", error)
                    sender.state = False
                else:
                    sender.state = True
            self._update_icon()

        return toggle

    def _update_icon(self) -> None:
        self.icon = ICON_ACTIVE if self.manager.has_active else ICON_IDLE

    # ------------------------------------------------------------------ timer

    @rumps.timer(HEALTH_CHECK_INTERVAL)
    def _health_check(self, _sender: rumps.Timer) -> None:
        dead_keys = self.manager.health_check()
        for key in dead_keys:
            item = self._menu_items.get(key)
            if item is not None:
                item.state = False
            host, local_port = key
            rumps.notification(
                "Tunnel dropped",
                host,
                f"Port {local_port} disconnected",
            )
        if dead_keys:
            self._update_icon()

    # ------------------------------------------------------------------ actions

    def _on_reload(self, _sender: rumps.MenuItem) -> None:
        try:
            new_config = load_config()
        except Exception as exc:
            log.exception("Failed to reload config")
            rumps.notification("Tunnelbar", "Config Error", str(exc)[:200])
            return

        _added, removed, _unchanged = diff_configs(self.config, new_config)
        self.manager.kill_keys(removed)
        self.config = new_config
        self._build_menu()

    def _on_edit(self, _sender: rumps.MenuItem) -> None:
        ensure_config()
        self._open_config_file()

    def _on_quit(self, _sender: rumps.MenuItem) -> None:
        self.manager.kill_all()
        rumps.quit_application()

    @staticmethod
    def _open_config_file() -> None:
        subprocess.Popen(["open", str(CONFIG_PATH)])


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    app = TunnelbarApp()
    app.run()
