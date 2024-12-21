import json
from pathlib import Path
from typing import Optional

import typer
from typer import Typer, Argument, Option

from src.app import get_service_factory
from src.enums import OutputFormat
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
    typer.echo(f"✅ {book_name} added successfully")



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


@app.command()
def show_pages(
    book_name: str = Argument(..., help="The name of the book"),
    start_page_num: int = Option(1, help="The starting page number"),
    number_of_pages: int = Option(10, help="The number of pages to show"),
    format: OutputFormat = Option("md", help="The format of the output"),
) -> None:
    """
    Show parsed pages of a book.

    E.g. Show pages from 10 to 20 of a `life-vision` book:
    > show-pages "life-vision" --offset 10 --limit 20 --format md
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    book = persistence_service.get_book(book_name)
    if not book:
        raise ValueError(f"Book with name {book_name} not found")

    book_pages = persistence_service.get_all_parsed_pages(book_name)
    if len(book_pages) <= 0:
        typer.echo("No parsed pages found", err=True)
        return

    if number_of_pages < 1:
        raise ValueError("Number of pages must be greater than 0")

    if start_page_num <= 0 or start_page_num > len(book_pages):
        raise ValueError(f"Invalid start page number {start_page_num}")

    if len(book_pages) < start_page_num + number_of_pages:
        number_of_pages = len(book_pages) - start_page_num

    book_pages.sort(key=lambda page: page.page_number)
    pages = book_pages[start_page_num - 1 : start_page_num + number_of_pages - 1]
    if format == OutputFormat.json:
        typer.echo(
            json.dumps(
                [page.to_stdout_dict() for page in pages],
            )
        )
    elif format == OutputFormat.md:
        for page in pages:
            typer.echo(f"== Page {page.page_number}")
            typer.echo(page.content)
            typer.echo("\n" + "-" * 80 + "\n")
    else:
        raise NotImplementedError(f"Output format {format} not implemented")


@app.command()
def clear_pages(
    book_name: str = Argument(..., help="The name of the book"),
) -> None:
    """
    Delete all parsed pages of a book
    """
    service_factory = get_service_factory(None)
    persistence_service: PersistenceService = service_factory.persistence_service()
    book = persistence_service.get_book(book_name)
    if not book:
        raise ValueError(f"Book with name {book_name} not found")

    book_pages = persistence_service.get_all_parsed_pages(book_name)
    if len(book_pages) == 0:
        typer.echo(f"No parsed pages found for {book_name}")
        return

    persistence_service.clear_book_pages(book_name)
    typer.echo(f"✅ parsed pages of {book_name} deleted successfully")


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
    typer.echo(f"✅ {book_name} deleted successfully")
