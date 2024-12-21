import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any

from langchain.smith.evaluation.runner_utils import logger
from pydantic import BaseModel

from src.constants import DATA_DIR
from src.error import LanguageLearningMethodException


class TableNames(Enum):
    PARSED_PAGES = "parsed_pages"
    EXERCISES = "exercises"
    EXERCISE_QUESTIONS = "exercise_questions"
    BOOKS = "books"


@dataclass
class ParsedPage:
    book_path: str
    page_number: int
    content: str
    parsed_at: datetime
    extraction_task_id: Optional[str] = None

    def to_stdout_dict(self) -> dict[str, Any]:
        return {
            "book_path": self.book_path,
            "page_number": self.page_number,
            "parsed_at": self.parsed_at,
        }


class ExtractedExercise(BaseModel):
    title: str
    instructions: str
    questions: List[str]


class ExtractedExercises(BaseModel):
    exercises: List[ExtractedExercise]


@dataclass
class StoredExercise:
    id: Optional[int]
    book_path: str
    page_number: int
    title: str
    instructions: str
    questions: List[str]
    extracted_at: datetime


@dataclass
class Book:
    name: str
    added_at: datetime
    book_content: bytes

    @contextmanager
    def as_temp_pdf(self):
        tmp_dir = tempfile.gettempdir()
        pdf_path = Path(tmp_dir) / f"{self.name}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(self.book_content)

        try:
            yield pdf_path
        finally:
            pdf_path.unlink(missing_ok=True)


class PersistenceService:
    def __init__(self, data_dir: Path = DATA_DIR, db_path: str = "parsed_pages.db"):
        self.db_path = (data_dir / db_path).as_posix()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database and create required tables if they don't exist"""
        create_parsed_pages = f"""
            CREATE TABLE IF NOT EXISTS {TableNames.PARSED_PAGES.value} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_path TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                parsed_at TIMESTAMP NOT NULL,
                extraction_task_id TEXT,
                UNIQUE(book_path, page_number)
            )
        """

        create_exercises = f"""
            CREATE TABLE IF NOT EXISTS {TableNames.EXERCISES.value} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_path TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                instructions TEXT NOT NULL,
                extracted_at TIMESTAMP NOT NULL,
                FOREIGN KEY(book_path, page_number) 
                REFERENCES {TableNames.PARSED_PAGES.value}(book_path, page_number)
            )
        """

        create_exercise_questions = f"""
            CREATE TABLE IF NOT EXISTS {TableNames.EXERCISE_QUESTIONS.value} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                question_order INTEGER NOT NULL,
                FOREIGN KEY(exercise_id) REFERENCES {TableNames.EXERCISES.value}(id)
            )
        """

        create_books = f"""
            CREATE TABLE IF NOT EXISTS {TableNames.BOOKS.value} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                book_content_base64 TEXT NOT NULL,
                date_added TIMESTAMP NOT NULL
            )
        """

        for query in [
            create_parsed_pages,
            create_exercises,
            create_exercise_questions,
            create_books,
        ]:
            self.execute_query(query, ())

    def execute_query(self, query: str, params: tuple) -> list[tuple]:
        logger.debug(f"Executing query: {query} with params: {params}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()

    def add_book(self, book_path: Path, book_name: str) -> Book:
        with open(book_path, "rb") as f:
            book_content = f.read()
        book_content_base64 = book_content.hex()
        book = Book(name=book_name, added_at=datetime.now(), book_content=book_content)

        query = f"""
            INSERT INTO {TableNames.BOOKS.value} (name, book_content_base64, date_added)
            VALUES (?, ?, ?)
        """
        self.execute_query(
            query, (book_name, book_content_base64, book.added_at.isoformat())
        )
        return book

    def get_book(self, book_name: str) -> Optional[Book]:
        query = f"""
            SELECT name, book_content_base64, date_added
            FROM {TableNames.BOOKS.value}
            WHERE name = ?
        """
        rows = self.execute_query(query, (book_name,))
        if rows:
            row = rows[0]
            return Book(
                name=row[0],
                added_at=datetime.fromisoformat(row[2]),
                book_content=bytes.fromhex(row[1]),
            )
        return None

    def list_book_names(self) -> list[str]:
        query = f"""
            SELECT name
            FROM {TableNames.BOOKS.value}
        """
        rows = self.execute_query(query, ())
        return [row[0] for row in rows]

    def store_exercise(self, exercise: StoredExercise) -> int:
        """Store an exercise and its questions in the database"""
        insert_exercise = f"""
            INSERT INTO {TableNames.EXERCISES.value}
            (book_path, page_number, title, instructions, extracted_at)
            VALUES (?, ?, ?, ?, ?)
        """
        rows = self.execute_query(
            insert_exercise,
            (
                exercise.book_path,
                exercise.page_number,
                exercise.title,
                exercise.instructions,
                exercise.extracted_at.isoformat(),
            ),
        )
        exercise_id = rows[0][0] if rows else None

        if exercise_id is not None:
            insert_question = f"""
                INSERT INTO {TableNames.EXERCISE_QUESTIONS.value}
                (exercise_id, question, question_order)
                VALUES (?, ?, ?)
            """
            for i, question in enumerate(exercise.questions):
                self.execute_query(insert_question, (exercise_id, question, i))

        if exercise_id is None:
            raise LanguageLearningMethodException(
                "Error storing exercise - no exercise ID"
            )
        return exercise_id

    def get_exercises(
        self, book_path: str, page_number: Optional[int] = None
    ) -> List[StoredExercise]:
        base_query = f"""
            SELECT e.id, e.book_path, e.page_number, e.title, e.instructions, e.extracted_at
            FROM {TableNames.EXERCISES.value} e
            WHERE e.book_path = ?
        """
        params = [book_path]

        if page_number is not None:
            base_query += " AND e.page_number = ?"
            params.append(page_number)

        exercise_rows = self.execute_query(base_query, tuple(params))
        exercises = []

        for row in exercise_rows:
            question_query = f"""
                SELECT question FROM {TableNames.EXERCISE_QUESTIONS.value}
                WHERE exercise_id = ?
                ORDER BY question_order
            """
            question_rows = self.execute_query(question_query, (row[0],))
            questions = [q[0] for q in question_rows]

            exercises.append(
                StoredExercise(
                    id=row[0],
                    book_path=row[1],
                    page_number=row[2],
                    title=row[3],
                    instructions=row[4],
                    questions=questions,
                    extracted_at=datetime.fromisoformat(row[5]),
                )
            )

        return exercises

    def store_parsed_page(self, parsed_page: ParsedPage) -> bool:
        try:
            query = f"""
                INSERT OR REPLACE INTO {TableNames.PARSED_PAGES.value}
                (book_path, page_number, content, parsed_at, extraction_task_id)
                VALUES (?, ?, ?, ?, ?)
            """
            self.execute_query(
                query,
                (
                    str(parsed_page.book_path),
                    parsed_page.page_number,
                    parsed_page.content,
                    parsed_page.parsed_at.isoformat(),
                    parsed_page.extraction_task_id,
                ),
            )
            return True
        except sqlite3.Error:
            return False

    def is_page_parsed(self, book_name: str, page_number: int) -> bool:
        query = f"""
            SELECT COUNT(*) FROM {TableNames.PARSED_PAGES.value}
            WHERE book_path = ? AND page_number = ?
        """
        rows = self.execute_query(query, (str(book_name), page_number))
        return rows[0][0] > 0

    def get_parsed_page(self, book_name: str, page_number: int) -> Optional[ParsedPage]:
        query = f"""
            SELECT book_path, page_number, content, parsed_at, extraction_task_id
            FROM {TableNames.PARSED_PAGES.value}
            WHERE book_path = ? AND page_number = ?
        """
        rows = self.execute_query(query, (str(book_name), page_number))

        if rows:
            row = rows[0]
            return ParsedPage(
                book_path=row[0],
                page_number=row[1],
                content=row[2],
                parsed_at=datetime.fromisoformat(row[3]),
                extraction_task_id=row[4],
            )
        return None

    def get_all_parsed_pages(self, book_name: str) -> List[ParsedPage]:
        query = f"""
            SELECT book_path, page_number, content, parsed_at, extraction_task_id
            FROM {TableNames.PARSED_PAGES.value}
            WHERE book_path = ?
            ORDER BY page_number
        """
        rows = self.execute_query(query, (str(book_name),))

        return [
            ParsedPage(
                book_path=row[0],
                page_number=row[1],
                content=row[2],
                parsed_at=datetime.fromisoformat(row[3]),
                extraction_task_id=row[4],
            )
            for row in rows
        ]

    def clear_book_pages(self, book_name: str) -> bool:
        try:
            query = f"""
                DELETE FROM {TableNames.PARSED_PAGES.value}
                WHERE book_path = ?
            """
            self.execute_query(query, (str(book_name),))
            return True
        except sqlite3.Error:
            return False

    def delete_book_and_connected_data(self, book_name: str) -> None:
        delete_book = f"""
            DELETE FROM {TableNames.BOOKS.value}
            WHERE name = ?
        """
        delete_pages = f"""
            DELETE FROM {TableNames.PARSED_PAGES.value}
            WHERE book_path = ?
        """
        self.execute_query(delete_book, (book_name,))
        self.execute_query(delete_pages, (book_name,))
