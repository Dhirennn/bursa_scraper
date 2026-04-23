"""Deprecated. Use `bursa-picker rank` instead.

Forwards to the new CLI entry point. Kept only as a compatibility shim for
users following the old README.
"""

from __future__ import annotations

import sys
import warnings


def main() -> None:
    warnings.warn(
        "scripts/run_screener.py is deprecated; use `bursa-picker rank` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bursa_picker.cli.main import app

    sys.argv = ["bursa-picker", "rank", "--top", "20"]
    app()


if __name__ == "__main__":
    main()
