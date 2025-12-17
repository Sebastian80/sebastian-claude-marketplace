"""
CLI Main - Entry point for the `bridge` command.

Usage:
    bridge start [--foreground]   Start the daemon
    bridge stop                   Stop the daemon
    bridge restart                Restart the daemon
    bridge status                 Show daemon and component status
    bridge health                 Quick health check
    bridge plugins                List loaded plugins
    bridge connectors             List connectors and their state
    bridge <plugin> <path...>     Route to plugin endpoint
"""

import sys

from ..config import BridgeConfig
from .client import print_error
from .commands import BUILTIN_COMMANDS, run_command
from .parser import create_parser
from .plugin_router import run_plugin_command

__all__ = ["main"]


def main(args: list[str] | None = None) -> int:
    """Main entry point for the bridge CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    if args is None:
        args = sys.argv[1:]

    # Check if first arg is a plugin name (not a built-in command)
    if args and args[0] not in BUILTIN_COMMANDS and not args[0].startswith("-"):
        return run_plugin_command(args)

    parser = create_parser()
    parsed = parser.parse_args(args)

    config = BridgeConfig()

    if not hasattr(parsed, "command") or parsed.command is None:
        parser.print_help()
        return 0

    try:
        return run_command(parsed.command, parsed, config)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print_error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
