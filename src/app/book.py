from pathlib import Path
from typing import Optional
from venv import logger

import typer
from typer import Typer, Argument, Option

from src.app import get_service_factory
from src.service.persitence_service import PersistenceService

app = Typer()


@app.command()
def add(
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

    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()

    persistence_service.add_book(book_path, book_name)
    typer.echo(f"Book {book_name} added successfully")


@app.command()
def create_deck(
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

    service_factory = get_service_factory(llm_name)
    deck_service: DeckService = service_factory.deck_service()

    deck_service.create_deck(book_name, start_page, end_page, out_dir)


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

    service_factory = get_service_factory(llm_name)
    exercise_builder_service: ExerciseBuilderService = (
        service_factory.exercise_builder_service()
    )
    exercise_builder_service.build_exercise_prompts(
        book_name, out_dir, start_page, end_page
    )


@app.command()
def list_all() -> None:
    """
    List all available books
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    books = sorted(persistence_service.list_book_names())
    for book_name in books:
        typer.echo(book_name)


@app.command()
def describe(
    book_name: str = Argument(..., help="The name of the book"),
) -> None:
    """
    Describe a book
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    book_ = persistence_service.get_book(book_name)
    if not book_:
        raise ValueError(f"Book with name {book_} not found")

    parsed_pages = persistence_service.get_all_parsed_pages(book_name)
    typer.echo(f"Name: {book_.name}")
    typer.echo(f"Pages: {len(parsed_pages)}")
    for i, page in enumerate(parsed_pages, 1):
        typer.echo(f"Page {i}")
        typer.echo(page.content)
        typer.echo("\n\n")


@app.command()
def clear_pages(
    book_name: str = Argument(..., help="The name of the book"),
) -> None:
    """
    Delete all parsed pages of a book
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    persistence_service.clear_book_pages(book_name)
    typer.echo(f"All parsed pages of {book_name} deleted successfully")


@app.command()
def delete(
    book_name: str = Argument(..., help="The name of the book"),
) -> None:
    """
    Delete a book and all connected data
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    persistence_service.delete_book_and_connected_data(book_name)
    typer.echo(f"Book {book_name} deleted successfully")
