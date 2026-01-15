import logging
from src.infra.logger import formatters, handlers, filters

class Simple(logging.Logger):
    """
    Простой логгер для повседневной работы.

    Что делает:
    - Логирует в консоль (цветной вывод через ColorStreamHandler)
    - Использует простой формат сообщений (module + строка)
    - Отключает проброс логов наверх (propagate = False),
      чтобы не было дублей, если корневой логгер тоже настроен.
    - Добавляет фильтр для обрезки корневого пути
    """
    formatter=logging.Formatter(
        fmt=formatters.TextFormat.simple,
        datefmt=formatters.DateFormat.simple
        )
    def __init__(self, name: str = "SimpleLogger", level: int = logging.DEBUG) -> None:
        """
        :param name: имя логгера
        :param level: уровень логгера
        """
        super().__init__(name=name, level=level)
        
        self.propagate = False

        self.addFilter(filters.PathFilter())

        self.addHandler(handler=handlers.ColorStreamHandler())

    def addHandler(self, handler: logging.Handler, level: int = logging.DEBUG) -> None:
        handler.setFormatter(fmt=self.formatter)
        handler.setLevel(level=level)
        super().addHandler(hdlr=handler)

class Detailed(logging.Logger):
    """
    Детальный логгер: расширенный вывод + запись ошибок в файл.

    Что делает:
    - Логирует в консоль (цветной вывод)
    - Использует подробный формат (pathname + строка)
    - Ошибки (ERROR и выше) дополнительно пишет в файл через ErrorFileHandler
    """
    formatter=logging.Formatter(
        fmt=formatters.TextFormat.detailed,
        datefmt=formatters.DateFormat.detailed
        )
    def __init__(self, name: str = "DetailedLogger", level: int = logging.DEBUG) -> None:
        """
        :param name: имя логгера
        :param level: уровень логгера
        """
        super().__init__(name=name, level=level)
        
        self.propagate = False

        self.addFilter(filters.PathFilter())

        self.addHandler(handler=handlers.ColorStreamHandler())

        self.addHandler(handler=handlers.ErrorFileHandler(), level=logging.ERROR)
        
    def addHandler(self, handler: logging.Handler, level: int = logging.DEBUG) -> None:
        handler.setFormatter(fmt=self.formatter)
        handler.setLevel(level=level)
        super().addHandler(hdlr=handler)



