"""
Logging Configuration for SankoSlides Backend

Provides structured logging to replace emoji print statements.
"""

import logging
import logging.config
from typing import Optional


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "app": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.pipeline": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.routers": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.services": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "app.tools": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def setup_logging(level: Optional[str] = None) -> None:
    """
    Initialize logging configuration for the application.
    
    Args:
        level: Optional override for log level (DEBUG, INFO, WARNING, ERROR)
    """
    config = LOGGING_CONFIG.copy()
    
    if level:
        level = level.upper()
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["level"] = level
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module name.
    
    Usage:
        from app.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Pipeline started")
        logger.warning("Skipping step")
        logger.error("Failed with error")
    
    Args:
        name: Typically __name__ of the calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
