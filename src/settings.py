from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

from src.constants import DATA_DIR
from src.service.llm_service import LLMConfig


class LanguageLearningMethodSettings(BaseSettings):
    llm_config: LLMConfig = LLMConfig(
        llm_class_path="langchain_ollama.llms.OllamaLLM", llm_kwargs={}
    )
    logger_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = DATA_DIR
