"""
Centralized loguru configuration for the weon-garmentcode repository.

This module automatically configures loguru when imported, providing consistent
logging formatting across the entire codebase.
"""

import sys
from loguru import logger


def setup_logger(level: str = "DEBUG") -> None:
    """
    Configure loguru logger with the standard format.
    
    Args:
        level: Log level (default: "INFO"). Can be "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    """
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level
    )


def set_log_level(level: str) -> None:
    """
    Change the log level dynamically.
    
    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    """
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level=level
    )


# Auto-configure logger when module is imported
setup_logger()

