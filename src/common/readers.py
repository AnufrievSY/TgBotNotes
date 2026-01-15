from pathlib import Path
from pydantic._internal._model_construction import ModelMetaclass
import yaml

def _check_file(file_path: Path | str, expected_type: str) -> Path:
    """
    Проверяет, существует ли файл и имеет ли он расширение и правильное ли у него расширение.
    :param file_path: Путь к файлу.
    :return: Путь к файлу.

    :raises FileNotFoundError: Если файл не найден.
    :raises ValueError: Если файл не имеет расширение .yaml.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Файл {file_path} не найден")

    if file_path.suffix != f".{expected_type}":
        raise ValueError(f"Файл {file_path} должен иметь расширение .{expected_type}")

    return Path(file_path)

def yaml_read(file_path: Path | str, schema: ModelMetaclass):
    """
    Загружает и валидирует данные из YAML-файла согласно указанной схеме.

    :param file_path: Путь к YAML-файлу.
    :param schema: Схема для валидации данных.
    """
    file_path = _check_file(file_path, "yaml")

    with open(file_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Файл {file_path} пуст или повреждён")

    return schema(**data)

def txt_read(file_path: Path | str) -> list[str]:
    """
    Читает данные из текстового файла.

    :param file_path: Путь к файлу.
    """

    file_path = _check_file(file_path, "txt")

    with open(file_path, encoding="utf-8") as f:
        data = f.read()
    return data.splitlines()

def txt_add(file_path: Path | str, data: str):
    """
    Добавляет данные в текстовый файл.

    :param file_path: Путь к файлу.
    :param data: Данные для записи.
    """
    file_path = _check_file(file_path, "txt")

    old_data = txt_read(file_path)
    if len(old_data) > 0:
        data = "\n" + data

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(data)

