import logging
import os

class LoggerConfig:
    """
    Configuration for the project logger.
    Reads environment variables for dynamic configuration.
    """
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )


def setup_logger(name: str) -> logging.Logger:
    """
    Creates and configures a logger with the given name.

    Args:
        name: The logger's name, typically __name__ of the calling module.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LoggerConfig.LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LoggerConfig.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
