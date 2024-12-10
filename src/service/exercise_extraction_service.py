import os
from pathlib import Path
from typing import List

from loguru import logger

from src.constants import DATA_DIR
from src.model import ExtractedExercises, ExtractedExercise
from src.service.llm_service import LLMService
from src.service.persitence_service import PersistenceService


class ExerciseExtractionService:
    _EXTRACTION_PROMPT = """You are a parsing and extraction assistant.
Given the following page content from a Spanish language workbook, identify and extract all distinct exercises.
For each exercise:
- Provide a short descriptive title if available (or assign a suitable one).
- Summarize the instructions for the exercise.
- Extract the list of questions or tasks for the student.

An 'exercise' is any part of the text that asks the student to do something: answer questions, fill in blanks, complete dialogues, translate sentences, etc.

Return the exercises in a structured JSON format with fields: title, instructions, and questions. 
If no exercises are present, return an empty list.
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

    def __init__(
            self,
            persistence_service: PersistenceService,
            llm_service: LLMService,
            data_dir: Path = DATA_DIR,
    ):
        self.data_dir = data_dir
        self.exercises_dir = self.data_dir / "exercises"
        if not self.exercises_dir.exists():
            self.exercises_dir.mkdir(parents=True)
        self.persistence_service = persistence_service
        self.llm_service = llm_service
        logger.info(
            f"ExcerciseService initialized with data directory: {self.data_dir}"
        )

    def extract_exercises(self, book_name: str, start_page: int, end_page: int) -> None:
        """
        Extracts exercises from the specified pages and saves each exercise
        as a separate .md file containing a prompt for a Spanish teacher persona.
        """
        logger.info(
            f"Starting exercise extraction from {book_name}, pages {start_page}-{end_page}"
        )

        for page_num in range(start_page, end_page + 1):
            logger.info(f"Processing page {page_num}")
            page = self.persistence_service.get_parsed_page(book_name, page_num)
            if not page or not page.content.strip():
                logger.info(f"No content for page {page_num}, skipping...")
                continue

            exercises = self._extract_exercises_from_page(page.content, page_num)
            if not exercises:
                logger.info(f"No exercises found on page {page_num}")
                continue

            # Save each exercise as a separate MD file
            self._save_exercises(page_num, exercises, book_name)

    def _extract_exercises_from_page(
            self, content: str, page_num: int
    ) -> List[ExtractedExercise]:
        """
        Use the LLM to identify and extract exercises from page content.
        """
        logger.info(f"Extracting exercises for page {page_num}")
        user_prompt = f"Page content:\n\n{content}"

        response = self.llm_service.prompt_with_structure(
            prompt=self._EXTRACTION_PROMPT,
            response_model=ExtractedExercises,
            system_prompt=user_prompt,
        )

        try:
            logger.debug(f"LLM response received for page {page_num}")
            exercises = response.choices[0].message.parsed.exercises
            logger.info(f"Extracted {len(exercises)} exercises from page {page_num}")
            logger.debug(exercises)
            return exercises
        except Exception as e:
            logger.exception(f"Error extracting exercises from page {page_num}: {e}")
            return []

    def _save_exercises(
            self, page_num: int, exercises: List[ExtractedExercise], book_path: str
    ) -> None:
        """
        Save each extracted exercise as a separate markdown file with a Spanish-teacher prompt.
        """
        book_name = os.path.splitext(os.path.basename(book_path))[0]
        output_dir = self.exercises_dir / book_name / f"page_{page_num}"
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        for i, exercise in enumerate(exercises, start=1):
            questions_text = "\n".join([f"- {q}" for q in exercise.questions])
            teacher_prompt = self._TEACHER_PROMPT_TEMPLATE.format(
                title=exercise.title,
                instructions=exercise.instructions,
                questions=questions_text,
            )

            filename = f"exercise_page_{page_num}_exercise_{i}.md"
            file_path = output_dir / filename
            logger.info(f"Saving exercise {i} from page {page_num} to {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(teacher_prompt)
            logger.info(f"Exercise saved: {file_path}")
