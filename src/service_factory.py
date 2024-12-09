from dataclasses import dataclass
from functools import cache
from pathlib import Path

from src.service.deck_service import DeckService
from src.service.exercise_builder_service import ExerciseBuilderService
from src.service.exercise_extraction_service import ExerciseExtractionService
from src.service.llm_service import LLMService, LLMConfig
from src.service.pdf_parser import PDFParser
from src.service.pdf_splitter import PDFSplitter
from src.service.persitence_service import PersistenceService


@dataclass
class ServiceFactoryConfig:
    llm_config: LLMConfig
    data_dir: Path


class ServiceFactory:
    def __init__(self, settings: ServiceFactoryConfig) -> None:
        self.settings = settings

    @cache
    def exercise_builder_service(self) -> ExerciseBuilderService:
        return ExerciseBuilderService(data_dir=self.settings.data_dir)

    @cache
    def llm_service(self) -> LLMService:
        return LLMService(self.settings.llm_config)

    @cache
    def persistence_service(self) -> PersistenceService:
        return PersistenceService(data_dir=self.settings.data_dir)

    @cache
    def exercise_extractor_service(self) -> ExerciseExtractionService:
        return ExerciseExtractionService(
            data_dir=self.settings.data_dir,
            persistence_service=self.persistence_service(),
            llm_service=self.llm_service(),
        )

    @cache
    def pdf_parser(self) -> PDFParser:
        return PDFParser(data_dir=self.settings.data_dir)

    @cache
    def pdf_splitter(self) -> PDFSplitter:
        return PDFSplitter()

    @cache
    def deck_service(self) -> DeckService:
        return DeckService(
            llm_service=self.llm_service(),
            persistence_service=self.persistence_service(),
            data_dir=self.settings.data_dir,
        )
