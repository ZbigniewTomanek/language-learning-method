import sys

import loguru

from src.service.config_manager import ConfigManager

config_manager = ConfigManager()

settings = config_manager.read_settings()
loguru.logger.remove()
loguru.logger.add(
    sys.stdout,
    level=settings.logger_level,
)
