
import io
import fitz  # PyMuPDF
from PIL import Image

def extract_multimodal_content_from_pdf(pdf_file: io.BytesIO) -> list:
    """
    Extracts text, images, and tables from a PDF.
    Returns a list of content blocks, where each block is a dictionary
    representing a piece of content (text, image, or table).
    """
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        content_blocks = []
        for page_num, page in enumerate(doc):
            # Extract text
            text = page.get_text("text")
            if text.strip():
                content_blocks.append({
                    "page": page_num + 1,
                    "type": "text",
                    "content": text
                })

            # Extract images
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                # Here you would typically save the image or convert it to a different format
                content_blocks.append({
                    "page": page_num + 1,
                    "type": "image",
                    "content": image_bytes  # Or a reference to the saved image
                })

            # Find and extract tables
            tables = page.find_tables()
            for table in tables:
                # The `extract` method gives you a list of lists of strings
                table_data = table.extract()
                content_blocks.append({
                    "page": page_num + 1,
                    "type": "table",
                    "content": table_data
                })

        doc.close()
        return content_blocks
    except Exception as e:
        print(f"Error extracting multimodal content from PDF: {e}")
        return []
