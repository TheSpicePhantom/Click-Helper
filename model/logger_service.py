"""
Schlanker Logger – Standard WARNING, Datei nur bei Bedarf.
"""

import logging
from pathlib import Path
from typing import Optional

_logger: Optional[logging.Logger] = None
_file_attached = False


class LoggerService:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def debug(self, message: str, **kwargs):
        self.logger.debug(_fmt(message, kwargs))

    def info(self, message: str, **kwargs):
        self.logger.info(_fmt(message, kwargs))

    def warning(self, message: str, **kwargs):
        self.logger.warning(_fmt(message, kwargs))

    def error(self, message: str, **kwargs):
        self.logger.error(_fmt(message, kwargs))

    def critical(self, message: str, **kwargs):
        self.logger.critical(_fmt(message, kwargs))


def _fmt(message: str, kwargs: dict) -> str:
    return f"{message} - {kwargs}" if kwargs else message


def get_logger() -> LoggerService:
    global _logger
    if _logger is None:
        _logger = logging.getLogger("ClickHelper")
        if not _logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            _logger.addHandler(handler)
        _logger.setLevel(logging.WARNING)
    return LoggerService(_logger)


def set_log_level(level: int):
    logger = get_logger()
    logger.logger.setLevel(level)
    if level <= logging.INFO:
        enable_file_logging()


def enable_file_logging():
    """Hängt optional einen Datei-Handler an (nicht beim Start)."""
    global _file_attached
    if _file_attached:
        return
    log_dir = Path.home() / "Documents" / "Click-Helper" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "click_helper.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    )
    get_logger().logger.addHandler(handler)
    _file_attached = True
