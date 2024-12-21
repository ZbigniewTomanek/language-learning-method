from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

from src.constants import DATA_DIR
from src.service.llm_service import LLMConfig


class LanguageLearningMethodSettings(BaseSettings):
    llms_config: dict[str, LLMConfig] = {
        "gpt-4o": LLMConfig(
            llm_class_path="langchain_openai.ChatOpenAI",
            llm_kwargs={"model_name": "gpt-4o", "temperature": 0.0},
        )
    }
    default_llm_name: str = "gpt-4o"
    logger_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = DATA_DIR
