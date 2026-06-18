"""CLI entry point: collect apps and normalize icons."""

from .apps import collect_apps
from .normalize import main as normalize_main


def main():
    collect_apps()
    normalize_main()


if __name__ == '__main__':
    main()
