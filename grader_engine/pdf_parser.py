
# grader_engine/pdf_parser.py
import io
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_file: io.BytesIO) -> str:
    """
    Extract raw text from uploaded PDF (file-like object).
    Uses PyMuPDF (fitz) for robust text extraction.
    """
    try:
        pdf_file.seek(0)
        # Open the PDF from a byte stream
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF with fitz: {e}")
        return ""
