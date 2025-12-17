"""
CLI Commands - Built-in command handlers.

Handles daemon management, status, plugins, deps, reload, etc.
"""

import argparse
from typing import TYPE_CHECKING

from ..deps import show_deps_status, sync_dependencies
from .client import BridgeClient, print_error, print_status
from .daemon import daemon_status, restart_daemon, start_daemon, stop_daemon

if TYPE_CHECKING:
    from ..config import BridgeConfig

__all__ = ["BUILTIN_COMMANDS", "handle_deps_command", "handle_reload_command", "run_command"]

# Built-in commands (not plugin names)
BUILTIN_COMMANDS = {
    "start", "stop", "restart", "status", "health",
    "plugins", "reconnect", "notify", "deps", "reload",
}


def run_command(command: str, args: argparse.Namespace, config: "BridgeConfig") -> int:
    """Run the specified command.

    Args:
        command: Command name
        args: Parsed arguments
        config: Bridge configuration

    Returns:
        Exit code
    """
    # Daemon management commands (don't need running daemon)
    if command == "start":
        return start_daemon(config, foreground=args.foreground)
    elif command == "stop":
        return stop_daemon(config)
    elif command == "restart":
        return restart_daemon(config)
    elif command == "deps":
        return handle_deps_command(args.action, config)

    # Status check (works regardless of daemon state)
    if command == "status":
        # First check if daemon is running
        exit_code = daemon_status(config)
        if exit_code != 0:
            return exit_code

        # Then get detailed status from API
        with BridgeClient(config) as client:
            if client.is_running():
                status = client.status()
                print()
                print_status(status)
        return 0

    # Commands that require running daemon
    with BridgeClient(config) as client:
        if not client.is_running():
            print_error("Bridge is not running. Start it with: bridge start")
            return 1

        if command == "health":
            health = client.health()
            print(f"Status: {health.get('status', 'unknown')}")
            return 0 if health.get("status") == "ok" else 1

        elif command == "plugins":
            plugins = client.plugins()
            if not plugins:
                print("No plugins loaded")
            else:
                for p in plugins:
                    state = "[*]" if p.get("started") else "[ ]"
                    cli_info = f" (cli: {p['cli']})" if p.get("cli") else ""
                    print(f"{state} {p['name']} v{p['version']}{cli_info}")
                    if p.get("description"):
                        print(f"    {p['description']}")
            return 0

        elif command == "reconnect":
            result = client.reconnect(args.name)
            print(f"Reconnected: {result.get('connector')}")
            return 0

        elif command == "notify":
            if args.action == "status":
                result = client.notifications_status()
                enabled = result.get("enabled", False)
                available = result.get("available", False)
                print(f"Notifications: {'enabled' if enabled else 'disabled'}")
                print(f"System support: {'available' if available else 'not available'}")
                return 0
            else:
                result = client.notifications_action(args.action)
                print(f"Notifications: {result.get('status', 'unknown')}")
                return 0

        elif command == "reload":
            return handle_reload_command(args.plugin, client)

    return 0


def handle_reload_command(plugin: str | None, client: BridgeClient) -> int:
    """Handle the reload subcommand.

    Args:
        plugin: Plugin name to reload, or None for all
        client: Bridge client

    Returns:
        Exit code
    """
    if plugin:
        print(f"Reloading plugin: {plugin}...")
        try:
            client.reload_plugin(plugin)
            print(f"Plugin '{plugin}' reloaded successfully.")
            return 0
        except Exception as e:
            print_error(f"Failed to reload plugin: {e}")
            return 1
    else:
        print("Reloading all plugins...")
        try:
            result = client.reload_all()
            plugins = result.get("plugins", {})
            for name, success in plugins.items():
                status = "OK" if success else "FAILED"
                print(f"  {name}: {status}")
            failed = sum(1 for s in plugins.values() if not s)
            if failed:
                print_error(f"{failed} plugin(s) failed to reload.")
                return 1
            print("All plugins reloaded successfully.")
            return 0
        except Exception as e:
            print_error(f"Failed to reload plugins: {e}")
            return 1


def handle_deps_command(action: str, config: "BridgeConfig") -> int:
    """Handle the deps subcommand.

    Args:
        action: One of 'status', 'sync', 'force'
        config: Bridge configuration

    Returns:
        Exit code
    """
    if action == "status":
        status = show_deps_status(config)
        print("Plugin Dependencies")
        print("=" * 40)
        uv_msg = "yes" if status["uv_available"] else "NO - run: pip install uv"
        print(f"UV available: {uv_msg}")
        venv = status.get("venv_path", "unknown")
        venv_state = "(exists)" if status["venv_exists"] else "(missing)"
        print(f"Venv:         {venv} {venv_state}")
        sync_msg = "yes" if status["in_sync"] else "NO - run: bridge deps sync"
        print(f"In sync:      {sync_msg}")
        stored = status["stored_hash"]
        hash_info = f"(stored: {stored})" if stored else "(not stored)"
        print(f"Hash:         {status['current_hash']} {hash_info}")
        print()
        print("Dependencies:")
        for dep in status["dependencies"]:
            print(f"  - {dep}")
        return 0

    elif action == "sync":
        print("Syncing dependencies...")
        if sync_dependencies(config):
            print("Dependencies in sync.")
            return 0
        else:
            print_error("Failed to sync dependencies.")
            return 1

    elif action == "force":
        print("Force reinstalling all dependencies...")
        if sync_dependencies(config, force=True):
            print("Dependencies reinstalled.")
            return 0
        else:
            print_error("Failed to reinstall dependencies.")
            return 1

    return 0
