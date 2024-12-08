import shutil
from pathlib import Path

import PyPDF2


class PDFSplitter:
    def __init__(self):
        """Initialize PDFSplitter class"""
        pass

    def split_pdf(self, pdf_path: Path) -> dict[int, str]:
        # Check if file exists
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Create output directory
        output_dir = pdf_path.parent / f"{pdf_path.stem}-pages"
        if output_dir.exists():
            shutil.rmtree(output_dir.as_posix())

        output_dir.mkdir(exist_ok=True)
        created_files = {}

        try:
            # Open the PDF file
            with open(pdf_path, 'rb') as file:
                # Create PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)

                # Iterate through all pages
                for page_num in range(len(pdf_reader.pages)):
                    # Create PDF writer object
                    pdf_writer = PyPDF2.PdfWriter()

                    # Add page to writer
                    pdf_writer.add_page(pdf_reader.pages[page_num])

                    # Generate output filename
                    output_filename = output_dir / f"{pdf_path.stem}-page_{page_num + 1}.pdf"

                    # Write the page to a new PDF file
                    with open(output_filename, 'wb') as output_file:
                        pdf_writer.write(output_file)

                    created_files[page_num] = str(output_filename)

        except PyPDF2.PdfReadError as e:
            raise PyPDF2.PdfReadError(f"Error reading PDF: {e}")
        except Exception as e:
            raise Exception(f"An error occurred while splitting the PDF: {e}")

        return created_files
