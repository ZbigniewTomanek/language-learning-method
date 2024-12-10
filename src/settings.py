from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

from src.constants import DATA_DIR
from src.service.llm_service import LLMConfig


class LanguageLearningMethodSettings(BaseSettings):
    llms_config: dict[str, LLMConfig] = {
        "ollama-llama3.1": LLMConfig(
            llm_class_path="langchain_ollama.llms.OllamaLLM",
            llm_kwargs={"model": "llama3.1"},
        )
    }
    default_llm_name: str = "ollama-llama3.1"
    logger_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = DATA_DIR
