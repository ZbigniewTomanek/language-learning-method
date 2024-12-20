import sys
from typing import Optional

import loguru

from src.service.config_manager import ConfigManager
from src.service_factory import ServiceFactory, ServiceFactoryConfig

config_manager = ConfigManager()

settings_ = config_manager.read_settings()
loguru.logger.remove()
loguru.logger.add(
    sys.stdout,
    level=settings_.logger_level,
)


def get_service_factory(llm_name: Optional[str]) -> ServiceFactory:
    settings = config_manager.read_settings()

    if llm_name:
        llm_config = settings.llms_config.get(llm_name)
    else:
        llm_config = settings.llms_config.get(settings.default_llm_name)

    if not llm_config:
        raise ValueError(f"LLM with name {llm_name} not found")

    service_factory = ServiceFactory(
        ServiceFactoryConfig(llm_config=llm_config, data_dir=settings.data_dir)
    )
    return service_factory
