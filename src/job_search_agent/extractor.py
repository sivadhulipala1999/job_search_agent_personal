"""
PDF Extraction module.
"""
from pathlib import Path
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from a PDF file."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    reader = PdfReader(path)
    text_content = []
    
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_content.append(page_text)
            
    return "\n".join(text_content)
