import tempfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.constants import DATA_DIR
from src.error import LanguageLearningMethodException
from src.service.pdf_splitter import PDFSplitter
from src.service.persitence_service import PersistenceService, ParsedPage
from src.service.text_extraction_service import TextExtractionService


class PDFParser:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        if not self.data_dir.exists():
            self.data_dir.mkdir()

        self.persistence_service = PersistenceService()
        self.pdf_splitter = PDFSplitter()
        self.text_extraction_service = TextExtractionService()

    def parse_pdf(self, book_name: str, pdf_path: Path) -> None:
        pages = self.pdf_splitter.split_pdf(pdf_path)
        logger.info(f"Split PDF into {len(pages)} pages")

        for page_num in sorted(pages.keys()):
            page = pages[page_num]
            if not self.persistence_service.is_page_parsed(book_name, page_num):
                start_time = datetime.now()
                result = self.text_extraction_service.extract_text(page)
                if result.error:
                    raise LanguageLearningMethodException(
                        f"Error extracting text from page {page_num}: {result.error}"
                    )
                end_time = datetime.now()
                logger.info(
                    f"Extracted text from page {page_num + 1} in {end_time - start_time}"
                )
                if result.extracted_text:
                    parsed_page = ParsedPage(
                        book_path=book_name,
                        page_number=page_num,
                        content=result.extracted_text,
                        parsed_at=datetime.now(),
                        extraction_task_id=result.task_id,
                    )
                    self.persistence_service.store_parsed_page(parsed_page)
            else:
                logger.info(f"Page {page_num} already parsed")
