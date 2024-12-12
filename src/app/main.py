from pathlib import Path
from typing import Optional
from venv import logger

import typer
from click import prompt
from typer import Typer, Argument, Option

from src.app.config import app as config_app
from src.service.persitence_service import PersistenceService
from src.service_factory import ServiceFactory, ServiceFactoryConfig
from src.app import config_manager

app = Typer()
app.add_typer(config_app, name="config", help="Configuration commands")


def _get_service_factory(llm_name: Optional[str]) -> ServiceFactory:
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


@app.command()
def book(
    book_path: Path = Argument(
        ...,
        help="The path or name of the book",
    ),
    book_name: Optional[str] = Option(
        ..., help="The name of the book under which it should be saved", prompt=True
    ),
) -> None:
    """
    Add book to the system
    """
    if not book_path.exists():
        raise FileNotFoundError(f"File {book_path} not found")

    if not book_name:
        raise ValueError("Book name is required")

    from src.service.persitence_service import PersistenceService

    service_factory = _get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()

    persistence_service.add_book(book_path, book_name)
    typer.echo(f"Book {book_name} added successfully")


@app.command()
def create_deck_from_book(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
    out_dir: Path = Argument(Path("."), help="The directory to save the deck"),
    llm_name: Optional[str] = Argument(
        None, help="The name of the LLM to use, if not given the default LLM is used"
    ),
) -> None:
    """
    Creates a deck of Anki flashcards out of a parsed textbook.
    """
    from src.service.deck_service import DeckService

    service_factory = _get_service_factory(llm_name)
    deck_service: DeckService = service_factory.deck_service()

    deck_service.create_deck(book_name, start_page, end_page, out_dir)


@app.command()
def create_deck_from_prompt(
    prompt: str = Argument(..., help="The prompt to generate the deck from"),
    num_of_flashcards: int = Argument(25, help="The number of flashcards to generate"),
    out_dir: Path = Argument(Path("."), help="The directory to save the deck"),
    llm_name: Optional[str] = Argument(
        None, help="The name of the LLM to use, if not given the default LLM is used"
    ),
) -> None:
    """
    Creates a deck of Anki flashcards out of a prompt.
    """
    from src.service.deck_from_prompt_service import DeckFromPromptService

    service_factory = _get_service_factory(llm_name)
    deck_from_prompt_service: DeckFromPromptService = (
        service_factory.deck_from_prompt_service()
    )
    deck_from_prompt_service.create_deck(prompt, num_of_flashcards, out_dir)


@app.command()
def extract_exercises(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
    llm_name: Optional[str] = Argument(
        None, help="The name of the LLM to use, if not given the default LLM is used"
    ),
) -> None:
    """
    Extracts exercises from a parsed textbook using the LLM.
    """
    from src.service.exercise_extraction_service import ExerciseExtractionService

    service_factory = _get_service_factory(llm_name)
    exercise_extraction_service: ExerciseExtractionService = (
        service_factory.exercise_extractor_service()
    )
    exercise_extraction_service.extract_exercises(
        book_name=book_name, start_page=start_page, end_page=end_page
    )


@app.command()
def parse_pdf(book_name: str) -> None:
    """
    Parse a PDF file into text using pdf-extract-api
    """
    from src.service.pdf_parser import PDFParser

    service_factory = _get_service_factory(None)

    pdf_parser: PDFParser = service_factory.pdf_parser()
    persistence_service: PersistenceService = service_factory.persistence_service()
    saved_book = persistence_service.get_book(book_name)
    if saved_book is None:
        raise ValueError(
            f"Book with name {book_name} not found",
            "available books are",
            persistence_service.list_book_names(),
        )

    logger.info(f"Starting to parse book {book_name}")
    pdf_parser.parse_pdf_from_bytes(saved_book.book_content)


@app.command()
def get_exercises_prompts(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
    out_dir: Path = Argument(Path("."), help="The directory to save the exercises"),
    llm_name: Optional[str] = Argument(
        None, help="The name of the LLM to use, if not given the default LLM is used"
    ),
) -> None:
    """
    Get all the prompts of the exercises
    """
    from src.service.exercise_builder_service import ExerciseBuilderService

    service_factory = _get_service_factory(llm_name)
    exercise_builder_service: ExerciseBuilderService = (
        service_factory.exercise_builder_service()
    )
    exercise_builder_service.build_exercise_prompts(
        book_name, out_dir, start_page, end_page
    )


if __name__ == "__main__":
    app()
