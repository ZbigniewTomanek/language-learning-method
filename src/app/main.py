from pathlib import Path
from typing import Optional
from venv import logger

from typer import Typer, Argument, Option

from src.app import get_service_factory
from src.app.config import app as config_app
from src.app.book import app as book_app
from src.service.persitence_service import PersistenceService

app = Typer()
app.add_typer(config_app, name="config", help="Configuration commands")
app.add_typer(book_app, name="book", help="Book management commands")


@app.command()
def create_deck_from_book(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
    out_dir: Path = Argument(Path("."), help="The directory to save the deck"),
    llm_name: Optional[str] = Argument(
        None, help="The name of the LLM to use, if not given the default LLM is used"
    ),
    custom_llm_prompt: Optional[str] = Option(
        None,
        help="This prompt will tell LLM how to generate the flashcards, otherwise the default prompt is used",
    ),
) -> None:
    """
    Creates a deck of Anki flashcards out of a parsed textbook.
    """
    from src.service.deck_service import DeckService

    service_factory = get_service_factory(llm_name)
    deck_service: DeckService = service_factory.deck_service()

    if custom_llm_prompt:
        deck_service.create_deck(
            book_name, start_page, end_page, out_dir, custom_llm_prompt
        )
    else:
        deck_service.default_create_deck(book_name, start_page, end_page, out_dir)


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

    service_factory = get_service_factory(llm_name)
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

    service_factory = get_service_factory(llm_name)
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

    service_factory = get_service_factory(None)

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
    with saved_book.as_temp_pdf() as pdf_path:
        pdf_parser.parse_pdf(book_name=book_name, pdf_path=pdf_path)


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

    service_factory = get_service_factory(llm_name)
    exercise_builder_service: ExerciseBuilderService = (
        service_factory.exercise_builder_service()
    )
    exercise_builder_service.build_exercise_prompts(
        book_name, out_dir, start_page, end_page
    )


if __name__ == "__main__":
    app()
