"""
Entry point for running serena_cli as a module.

Usage:
    python -m serena_cli find Customer --kind class
    python -m serena_cli status
"""

from .cli import main

if __name__ == "__main__":
    main()
