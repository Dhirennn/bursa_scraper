"""Deprecated. Use `bursa-picker rank` instead.

This shim is kept to avoid breaking existing user muscle memory; it will
be removed in a future release.
"""

from __future__ import annotations

import sys
import warnings


def main() -> None:
    warnings.warn(
        "scripts/main.py is deprecated; use `bursa-picker rank` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from bursa_picker.cli.main import app

    sys.argv = ["bursa-picker", "rank", "--top", "20", "--narrative"]
    app()


if __name__ == "__main__":
    main()
