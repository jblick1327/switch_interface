"""Logging helpers for the package."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


_DEFAULT_LOG = Path.home() / ".switch_interface.log"


def setup(level: int = logging.INFO, log_file: str | Path | None = None) -> None:
    """Configure logging for the package.

    Parameters
    ----------
    level:
        Minimum severity level for log messages.
    log_file:
        Optional path to the log file.  If not provided,
        ``~/.switch_interface.log`` is used.
    """

    if log_file is None:
        log_file = _DEFAULT_LOG
    else:
        log_file = Path(log_file)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        handlers.append(file_handler)
    except Exception:
        # Fall back to console-only logging if the file can't be opened.
        pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )

    def _excepthook(exc_type, exc, tb) -> None:
        logging.getLogger(__name__).critical(
            "Unhandled exception", exc_info=(exc_type, exc, tb)
        )

    sys.excepthook = _excepthook

