import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from src.constants import DATA_DIR


@dataclass
class ParsedPage:
    """Data class to store parsed page information"""

    book_path: str
    page_number: int
    content: str
    parsed_at: datetime
    extraction_task_id: Optional[str] = None


class ExtractedExercise(BaseModel):
    title: str
    instructions: str
    questions: List[str]


class ExtractedExercises(BaseModel):
    exercises: List[ExtractedExercise]


@dataclass
class ParsedPage:
    book_path: str
    page_number: int
    content: str
    parsed_at: datetime
    extraction_task_id: Optional[str] = None


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
    def temp_pdf(self):
        tmp_dir = tempfile.gettempdir()
        pdf_path = Path(tmp_dir) / "temp.pdf"
        with open(pdf_path, "wb") as f:
            f.write(self.book_content)

        try:
            yield self
        finally:
            pdf_path.unlink(missing_ok=True)


class PersistenceService:
    def __init__(self, data_dir: Path = DATA_DIR, db_path: str = "parsed_pages.db"):
        self.db_path = (data_dir / db_path).as_posix()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database and create required tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Existing parsed_pages table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS parsed_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    parsed_at TIMESTAMP NOT NULL,
                    extraction_task_id TEXT,
                    UNIQUE(book_path, page_number)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    extracted_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(book_path, page_number) REFERENCES parsed_pages(book_path, page_number)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    question_order INTEGER NOT NULL,
                    FOREIGN KEY(exercise_id) REFERENCES exercises(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    book_content_base64 TEXT NOT NULL,
                    date_added TIMESTAMP NOT NULL
                )
                """
            )
            conn.commit()

    def add_book(self, book_path: Path, book_name: str) -> Book:
        with open(book_path, "rb") as f:
            book_content = f.read()
        book_content_base64 = book_content.hex()
        book = Book(name=book_name, added_at=datetime.now(), book_content=book_content)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO books (name, book_content_base64, date_added)
                VALUES (?, ?, ?)
                """,
                (book_name, book_content_base64, book.added_at.isoformat()),
            )
            conn.commit()
        return book

    def get_book(self, book_name: str) -> Optional[Book]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, book_content_base64, date_added
                FROM books
                WHERE name = ?
                """,
                (book_name,),
            )
            row = cursor.fetchone()
            if row:
                return Book(
                    name=row[0],
                    added_at=datetime.fromisoformat(row[2]),
                    book_content=bytes.fromhex(row[1]),
                )
        return None

    def list_book_names(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name
                FROM books
                """
            )
            return [row[0] for row in cursor.fetchall()]

    def store_exercise(self, exercise: StoredExercise) -> int:
        """Store an exercise and its questions in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert exercise
            cursor.execute(
                """
                INSERT INTO exercises 
                (book_path, page_number, title, instructions, extracted_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    exercise.book_path,
                    exercise.page_number,
                    exercise.title,
                    exercise.instructions,
                    exercise.extracted_at.isoformat(),
                ),
            )

            exercise_id = cursor.lastrowid

            # Insert questions
            for i, question in enumerate(exercise.questions):
                cursor.execute(
                    """
                    INSERT INTO exercise_questions 
                    (exercise_id, question, question_order)
                    VALUES (?, ?, ?)
                """,
                    (exercise_id, question, i),
                )

            conn.commit()
            return exercise_id

    def get_exercises(
        self, book_path: str, page_number: Optional[int] = None
    ) -> List[StoredExercise]:
        """Retrieve exercises for a book, optionally filtered by page number"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT e.id, e.book_path, e.page_number, e.title, e.instructions, e.extracted_at
                FROM exercises e
                WHERE e.book_path = ?
            """
            params = [book_path]

            if page_number is not None:
                query += " AND e.page_number = ?"
                params.append(page_number)

            cursor.execute(query, params)
            exercises = []

            for row in cursor.fetchall():
                # Get questions for this exercise
                cursor.execute(
                    """
                    SELECT question FROM exercise_questions
                    WHERE exercise_id = ?
                    ORDER BY question_order
                """,
                    (row[0],),
                )

                questions = [q[0] for q in cursor.fetchall()]

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
        """
        Store a parsed page in the database

        Args:
            parsed_page: ParsedPage object containing the page information

        Returns:
            bool: True if storage was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO parsed_pages 
                    (book_path, page_number, content, parsed_at, extraction_task_id)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        str(parsed_page.book_path),
                        parsed_page.page_number,
                        parsed_page.content,
                        parsed_page.parsed_at.isoformat(),
                        parsed_page.extraction_task_id,
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def is_page_parsed(self, book_name: str, page_number: int) -> bool:
        """
        Check if a specific page of a book has already been parsed

        Args:
            book_namePath to the book file
            page_number: Page number to check

        Returns:
            bool: True if the page has been parsed, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM parsed_pages 
                WHERE book_path = ? AND page_number = ?
            """,
                (str(book_name), page_number),
            )
            return cursor.fetchone()[0] > 0

    def get_parsed_page(self, book_name: str, page_number: int) -> Optional[ParsedPage]:
        """
        Retrieve a parsed page from the database

        Args:
            book_namePath to the book file
            page_number: Page number to retrieve

        Returns:
            Optional[ParsedPage]: ParsedPage object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT book_path, page_number, content, parsed_at, extraction_task_id 
                FROM parsed_pages 
                WHERE book_path = ? AND page_number = ?
            """,
                (str(book_name), page_number),
            )

            row = cursor.fetchone()
            if row:
                return ParsedPage(
                    book_path=row[0],
                    page_number=row[1],
                    content=row[2],
                    parsed_at=datetime.fromisoformat(row[3]),
                    extraction_task_id=row[4],
                )
        return None

    def get_all_parsed_pages(self, book_name: str) -> List[ParsedPage]:
        """
        Retrieve all parsed pages for a specific book

        Args:
            book_namePath to the book file

        Returns:
            List[ParsedPage]: List of ParsedPage objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT book_path, page_number, content, parsed_at, extraction_task_id 
                FROM parsed_pages 
                WHERE book_path = ?
                ORDER BY page_number
            """,
                (str(book_name),),
            )

            return [
                ParsedPage(
                    book_path=row[0],
                    page_number=row[1],
                    content=row[2],
                    parsed_at=datetime.fromisoformat(row[3]),
                    extraction_task_id=row[4],
                )
                for row in cursor.fetchall()
            ]

    def clear_book_pages(self, book_name: str) -> bool:
        """
        Delete all parsed pages for a specific book

        Args:
            book_namePath to the book file

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM parsed_pages 
                    WHERE book_path = ?
                """,
                    (str(book_name),),
                )
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def delete_book_and_connected_data(self, book_name: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM books
                WHERE name = ?
                """,
                (book_name,),
            )
            cursor.execute(
                """
                DELETE FROM parsed_pages
                WHERE book_path = ?
                """,
                (book_name,),
            )
            conn.commit()
