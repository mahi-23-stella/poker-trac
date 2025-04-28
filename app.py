from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
import logging
import cv2
import numpy as np
import camelot  # For table detection and extraction

# Install required packages if not already:
# pip install flask pymupdf pytesseract pdf2image opencv-python camelot-py[cv]

app = Flask(__name__)

# === Configure Your Poppler Path Here ===
poppler_path = r'C:\Users\mahi\OneDrive\Desktop\bank statement analysis\Release-23.11.0-0\poppler-23.11.0\Library\bin'  # <-- UPDATE this to your real path!!

# === HTML Page Template ===
HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <title>PDF Text Extractor with OCR</title>
</head>
<body>
  <h1>Upload PDFs to Extract Text (with OCR fallback)</h1>
  <form method="POST" enctype="multipart/form-data">
    <input type="file" name="pdfs" multiple accept="application/pdf">
    <button type="submit">Upload and Extract</button>
  </form>
  {% if texts %}
    <h2>Extracted Text:</h2>
    {% for text in texts %}
      <div style="border:1px solid #ccc; padding:10px; margin:10px;">
        <pre>{{ text }}</pre>
      </div>
    {% endfor %}
  {% endif %}
</body>
</html>
"""

# === Configure Logging ===
logging.basicConfig(level=logging.DEBUG)

# === Text Extraction Logic ===
def is_image_based_pdf(pdf_bytes):
    """Check if the PDF is image-based (no text layer)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        if not page.get_text().strip():  # No text layer found
            return True
    return False

def preprocess_image_for_ocr(image):
    """Preprocess images for better OCR performance."""
    gray_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    # Apply Gaussian blur to reduce noise
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    # Use adaptive thresholding for better text recognition in varying lighting conditions
    binarized_image = cv2.adaptiveThreshold(blurred_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return binarized_image

def extract_text_with_ocr(pdf_bytes):
    """Extract text using PyMuPDF and fallback to OCR if needed."""
    text = ""
    
    try:
        # Try direct text extraction (fast)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            page_text = page.get_text("text")  # Cleaner extraction
            if page_text.strip():
                text += page_text
        doc.close()

        # If text found, return it
        if text.strip():
            return text

        # Check if it's image-based PDF
        if is_image_based_pdf(pdf_bytes):
            logging.info("Image-based PDF detected, using OCR...")
        else:
            logging.info("No text detected, using OCR fallback...")

        # Fallback: OCR on images
        images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path)
        ocr_text = ""
        for img in images:
            processed_img = preprocess_image_for_ocr(img)  # Apply image preprocessing
            ocr_text += pytesseract.image_to_string(processed_img, config=r'--oem 3 --psm 6')  # OCR with custom config

        return ocr_text.strip()

    except fitz.fitz.FileDataError as e:
        logging.error(f"PDF file error: {e}")
        return "The PDF file seems corrupted or is not a valid PDF."
    except Exception as e:
        logging.error(f"General error during text extraction: {e}")
        return f"An error occurred during text extraction: {e}"

def extract_tables_from_pdf(pdf_bytes):
    """Extract tables from the PDF using Camelot."""
    try:
        # Convert the PDF to images (required for Camelot)
        tables_text = ""

        # Use Camelot to extract tables from each page
        tables = camelot.read_pdf(pdf_bytes, pages='all', flavor='stream')  # Switch to 'stream' if 'lattice' doesn't work

        # If no tables are found using Camelot, return a message
        if not tables:
            return "No tables detected."

        # Extract the tables as text in a row-wise manner
        for table in tables:
            # Access the table data (list of rows)
            for row in table.df.values:
                # Each row contains columns, join them for output row-wise
                # Adding extra spaces for better separation between columns
                tables_text += "  ".join(row) + "\n"

            # Adding a break between each table for clear separation
            tables_text += "\n" * 2  # Add more space between tables

        # Returning the formatted tables text
        return tables_text.strip()

    except Exception as e:
        logging.error(f"Error during table extraction: {e}")
        return "An error occurred during table extraction."

# === Web Routes ===
@app.route('/', methods=['GET', 'POST'])
def upload_pdfs():
    texts = []
    if request.method == 'POST':
        files = request.files.getlist('pdfs')
        for file in files:
            logging.info(f"Processing file: {file.filename}")  # Log file name
            if file.filename.endswith('.pdf'):
                try:
                    text = extract_text_with_ocr(file.read())
                    if text:
                        texts.append(text)
                    
                    # Attempt to extract tables from the PDF
                    tables_text = extract_tables_from_pdf(file.read())
                    if tables_text:
                        texts.append(f"Tables detected:\n{tables_text}")
                except Exception as e:
                    texts.append(f"Error processing {file.filename}: {e}")
            else:
                texts.append(f"{file.filename} is not a valid PDF file.")
    return render_template_string(HTML_PAGE, texts=texts)

# === Run Server ===
if __name__ == '__main__':
    app.run(debug=True)
