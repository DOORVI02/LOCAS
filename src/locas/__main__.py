"""LOCAS Application Entry Point."""

import sys
from locas.app import run_application


def main() -> int:
    """Main entry point for LOCAS application."""
    return run_application()


if __name__ == "__main__":
    sys.exit(main())
