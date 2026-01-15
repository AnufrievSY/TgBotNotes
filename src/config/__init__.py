from pathlib import Path
from src.infra import logger
from src.config.shemas import Config
from src.common import readers

log = logger.setup.Simple(name='TgBotNotes')

ROOT: Path = Path(__file__).parent.parent.parent

config: Config = readers.yaml_read(ROOT / 'config.yaml', Config)