import logging


def setup(level: int = logging.INFO) -> None:
    """Configure basic logging for the package."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

