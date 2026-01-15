import logging
from typing import Final, Optional
from pathlib import Path

class ColorStreamHandler(logging.StreamHandler):
    """Цветные логи по уровням"""

    COLOR_CODES: Final[dict[int, str]] = {
        logging.DEBUG: "\033[90m",   # Gray
        logging.INFO: "\033[97m",    # White
        logging.WARNING: "\033[93m", # Yellow
        logging.ERROR: "\033[91m",   # Red
        logging.CRITICAL: "\033[95m" # Magenta
    }

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = self.COLOR_CODES.get(record.levelno, "")
        return f"{color}{message}\033[0m" if color else message

class ErrorFileHandler(logging.FileHandler):
    """Запись в журнал логов"""
    def __init__(self, file_path: Optional[str | Path] = None) -> None:
        file_path = file_path or Path(__file__).parent.parent.parent
        super().__init__(filename=Path(file_path) / 'error.log')