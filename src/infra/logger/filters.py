import os
from typing import Optional
from pathlib import Path
import logging

class PathFilter(logging.Filter):
    """Фильтр, который удаляет абсолютный root-путь из начала пути файла в логах"""
    def __init__(self, root_path: Optional[str | Path] = None) -> None:
        super().__init__()

        root_path = root_path or Path(__file__).parent.parent.parent

        self.root_path = os.path.normpath(str(root_path))

    def filter(self, record: logging.LogRecord) -> bool:
        record.pathname = record.pathname.replace(self.root_path, "..")
        return True