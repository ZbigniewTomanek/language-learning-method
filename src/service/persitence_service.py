import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class ParsedPage:
    """Data class to store parsed page information"""
    book_path: str
    page_number: int
    content: str
    parsed_at: datetime
    extraction_task_id: Optional[str] = None


class PersistenceService:
    def __init__(self, db_path: str = "parsed_pages.db"):
        """
        Initialize the Persistence Service

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database and create required tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parsed_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    parsed_at TIMESTAMP NOT NULL,
                    extraction_task_id TEXT,
                    UNIQUE(book_path, page_number)
                )
            """)
            conn.commit()

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
                cursor.execute("""
                    INSERT OR REPLACE INTO parsed_pages 
                    (book_path, page_number, content, parsed_at, extraction_task_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    str(parsed_page.book_path),
                    parsed_page.page_number,
                    parsed_page.content,
                    parsed_page.parsed_at.isoformat(),
                    parsed_page.extraction_task_id
                ))
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def is_page_parsed(self, book_path: str, page_number: int) -> bool:
        """
        Check if a specific page of a book has already been parsed

        Args:
            book_path: Path to the book file
            page_number: Page number to check

        Returns:
            bool: True if the page has been parsed, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM parsed_pages 
                WHERE book_path = ? AND page_number = ?
            """, (str(book_path), page_number))
            return cursor.fetchone()[0] > 0

    def get_parsed_page(self, book_path: str, page_number: int) -> Optional[ParsedPage]:
        """
        Retrieve a parsed page from the database

        Args:
            book_path: Path to the book file
            page_number: Page number to retrieve

        Returns:
            Optional[ParsedPage]: ParsedPage object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT book_path, page_number, content, parsed_at, extraction_task_id 
                FROM parsed_pages 
                WHERE book_path = ? AND page_number = ?
            """, (str(book_path), page_number))

            row = cursor.fetchone()
            if row:
                return ParsedPage(
                    book_path=row[0],
                    page_number=row[1],
                    content=row[2],
                    parsed_at=datetime.fromisoformat(row[3]),
                    extraction_task_id=row[4]
                )
        return None

    def get_all_parsed_pages(self, book_path: str) -> List[ParsedPage]:
        """
        Retrieve all parsed pages for a specific book

        Args:
            book_path: Path to the book file

        Returns:
            List[ParsedPage]: List of ParsedPage objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT book_path, page_number, content, parsed_at, extraction_task_id 
                FROM parsed_pages 
                WHERE book_path = ?
                ORDER BY page_number
            """, (str(book_path),))

            return [
                ParsedPage(
                    book_path=row[0],
                    page_number=row[1],
                    content=row[2],
                    parsed_at=datetime.fromisoformat(row[3]),
                    extraction_task_id=row[4]
                )
                for row in cursor.fetchall()
            ]

    def clear_book_pages(self, book_path: str) -> bool:
        """
        Delete all parsed pages for a specific book

        Args:
            book_path: Path to the book file

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM parsed_pages 
                    WHERE book_path = ?
                """, (str(book_path),))
                conn.commit()
                return True
        except sqlite3.Error:
            return False
