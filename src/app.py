from typer import Typer, Argument

from src.constants import DATA_DIR
from src.service_factory import ServiceFactory
from src.settings import LanguageLearningMethodSettings

app = Typer()


def _read_settings() -> LanguageLearningMethodSettings:
    with open(DATA_DIR / "settings.json", "r") as file:
        return LanguageLearningMethodSettings.model_validate_json(file.read())


@app.command()
def create_deck(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
) -> None:
    service_factory = ServiceFactory(_read_settings())
    from src.service.deck_service import DeckService

    deck_service: DeckService = service_factory.deck_service()

    deck_service.create_deck(book_name, start_page, end_page)


@app.command()
def extract_exercises(
    book_name: str = Argument(..., help="The name of the textbook"),
    start_page: int = Argument(..., help="The starting page number"),
    end_page: int = Argument(..., help="The ending page number"),
) -> None:
    from src.service.exercise_extraction_service import ExerciseExtractionService

    service_factory = ServiceFactory(_read_settings())
    exercise_extraction_service: ExerciseExtractionService = (
        service_factory.exercise_extractor_service()
    )
    exercise_extraction_service.extract_exercises(
        book_name=book_name, start_page=start_page, end_page=end_page
    )


if __name__ == "__main__":
    app()
