from pathlib import Path
from typing import List, Optional

from loguru import logger

from src.constants import DATA_DIR
from src.service.persitence_service import PersistenceService, StoredExercise


class ExerciseBuilderService:
    """
    Builds exercise prompts from database content and saves them as markdown files.
    Each exercise is transformed into a Spanish teacher prompt format.
    """

    _TEACHER_PROMPT_TEMPLATE = """You are now acting as a Spanish teacher speaking to a student in a conversational, voice-friendly manner.
Present the following exercise to the student. First, greet the student, then explain the instructions clearly in Spanish, and then ask the questions one by one. Encourage the student to answer out loud.

Exercise Title: {title}

Instructions: {instructions}

Questions:
{questions}

In your speaking, use a friendly, encouraging tone. For example:
"¡Hola! Hoy vamos a practicar un ejercicio. {instructions}. Vamos a empezar con la primera pregunta: ..."

Don't write out of character. Only produce what you would say to the student as their Spanish teacher.
"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.exercises_dir = self.data_dir / "exercises"
        self.persistence_service = PersistenceService()
        logger.info(
            f"ExerciseBuilderService initialized with data directory: {self.data_dir}"
        )

    def build_exercise_prompts(
        self,
        book_name: str,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
    ) -> None:
        """
        Retrieves exercises from the database and builds markdown prompts for specified pages.
        If start_page and end_page are not provided, processes all exercises for the book.

        Args:
            book_name: Name of the book to process
            start_page: Optional starting page number
            end_page: Optional ending page number
        """
        logger.info(f"Building exercise prompts for {book_name}")

        if start_page is not None and end_page is not None:
            logger.info(f"Processing pages {start_page} to {end_page}")
            # Process exercises page by page
            for page_num in range(start_page, end_page + 1):
                exercises = self.persistence_service.get_exercises(book_name, page_num)
                if exercises:
                    self._process_page_exercises(book_name, page_num, exercises)
        else:
            logger.info("Processing all exercises for the book")
            # Get all exercises and group them by page
            all_exercises = self.persistence_service.get_exercises(book_name)
            exercises_by_page = {}
            for exercise in all_exercises:
                exercises_by_page.setdefault(exercise.page_number, []).append(exercise)

            # Process each page's exercises
            for page_num, page_exercises in exercises_by_page.items():
                self._process_page_exercises(book_name, page_num, page_exercises)

    def _process_page_exercises(
        self, book_name: str, page_num: int, exercises: List[StoredExercise]
    ) -> None:
        """
        Process and save exercises for a specific page.

        Args:
            book_name: Name of the book
            page_num: Page number
            exercises: List of exercises to process
        """
        output_dir = self._ensure_output_directory(book_name, page_num)

        for i, exercise in enumerate(exercises, start=1):
            prompt = self._build_teacher_prompt(exercise)
            self._save_prompt(output_dir, page_num, i, prompt)

    def _build_teacher_prompt(self, exercise: StoredExercise) -> str:
        """
        Build a teacher prompt from an exercise.

        Args:
            exercise: StoredExercise object containing exercise data

        Returns:
            str: Formatted teacher prompt
        """
        questions_text = "\n".join([f"- {q}" for q in exercise.questions])
        return self._TEACHER_PROMPT_TEMPLATE.format(
            title=exercise.title,
            instructions=exercise.instructions,
            questions=questions_text,
        )

    def _ensure_output_directory(self, book_name: str, page_num: int) -> Path:
        """
        Ensure the output directory exists for the given book and page.

        Args:
            book_name: Name of the book
            page_num: Page number

        Returns:
            Path: Path to the output directory
        """
        output_dir = self.exercises_dir / book_name / f"page_{page_num}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _save_prompt(
        self, output_dir: Path, page_num: int, exercise_num: int, prompt: str
    ) -> None:
        """
        Save a prompt to a markdown file.

        Args:
            output_dir: Directory to save the file in
            page_num: Page number
            exercise_num: Exercise number
            prompt: Prompt content to save
        """
        filename = f"exercise_page_{page_num}_exercise_{exercise_num}.md"
        file_path = output_dir / filename

        logger.info(
            f"Saving exercise {exercise_num} from page {page_num} to {file_path}"
        )
        file_path.write_text(prompt, encoding="utf-8")
        logger.info(f"Exercise saved: {file_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build exercise prompts from database and save as markdown files"
    )
    parser.add_argument("book_name", type=str, help="Name of the book")
    parser.add_argument(
        "--start-page", type=int, help="Starting page number (optional)"
    )
    parser.add_argument("--end-page", type=int, help="Ending page number (optional)")
    args = parser.parse_args()

    builder_service = ExerciseBuilderService()
    builder_service.build_exercise_prompts(
        args.book_name, start_page=args.start_page, end_page=args.end_page
    )


if __name__ == "__main__":
    main()
