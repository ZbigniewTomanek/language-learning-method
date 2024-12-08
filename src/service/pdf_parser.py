from datetime import datetime
from pathlib import Path

from loguru import logger

from src.service.pdf_splitter import PDFSplitter
from src.service.persitence_service import PersistenceService, ParsedPage
from src.service.text_extraction_service import TextExtractionService


class PDFParser:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        if not self.data_dir.exists():
            self.data_dir.mkdir()

        self.persistence_service = PersistenceService(db_path=(self.data_dir / "parsed_pages.db").as_posix())
        self.pdf_splitter = PDFSplitter()
        self.text_extraction_service = TextExtractionService()

    def parse_pdf(self, pdf_path: Path) -> None:
        book_name = pdf_path.stem
        pages = self.pdf_splitter.split_pdf(pdf_path)
        logger.info(f"Split PDF into {len(pages)} pages")

        for page_num in sorted(pages.keys()):
            page = pages[page_num]
            if not self.persistence_service.is_page_parsed(book_name, page_num):
                start_time = datetime.now()
                result = self.text_extraction_service.extract_text(page)
                end_time = datetime.now()
                logger.info(f"Extracted text from page {page_num} in {end_time - start_time}")
                if result.extracted_text:
                    parsed_page = ParsedPage(
                        book_path=book_name,
                        page_number=page_num,
                        content=result.extracted_text,
                        parsed_at=datetime.now(),
                        extraction_task_id=result.task_id
                    )
                    self.persistence_service.store_parsed_page(parsed_page)
            else:
                logger.info(f"Page {page_num} already parsed")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Parse a PDF file")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to parse")
    args = parser.parse_args()

    pdf_parser = PDFParser()
    pdf_parser.parse_pdf(Path(args.pdf_path))


if __name__ == "__main__":
    main()
