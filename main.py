from flask import Flask, render_template, request
import camelot
import os

# Create Flask application
app = Flask(__name__)

# Folder to save uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extract Tables from PDFs using Camelot
def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF and format them."""
    try:
        # Read all tables from the PDF using Camelot
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')  # 'stream' is for tables without borders
        
        # If no tables are found, return a message
        if not tables:
            return "No tables detected in this PDF."

        all_tables_text = ""
        
        # Loop through each table and format them into readable text
        for table in tables:
            df = table.df  # Get the DataFrame of the table
            all_tables_text += df.to_string(index=False) + "\n\n"  # Convert table to string format without the index
        return all_tables_text
    except Exception as e:
        return f"Error extracting tables: {e}"

# Function to process PDF (tables extraction only)
def process_pdf(pdf_path):
    """Process the PDF to extract only tables and return the result."""
    extracted_tables = extract_tables_from_pdf(pdf_path)
    
    # Return the formatted tables as the final output
    return extracted_tables

@app.route('/')
def upload_form():
    """Render the file upload form"""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and table extraction"""
    if 'pdf' not in request.files:
        return "No file part"
    file = request.files['pdf']
    if file.filename == '':
        return "No selected file"
    if file and file.filename.endswith('.pdf'):
        # Save the uploaded file to the server
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Process the uploaded PDF to extract tables
        output = process_pdf(file_path)

        # Return the extracted tables to the user
        return render_template('output.html', output=output)
    
    return "Invalid file type. Please upload a PDF."


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
