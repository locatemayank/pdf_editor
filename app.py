from flask import Flask, request, jsonify, send_file, render_template, session
from flask_cors import CORS  # Added for CORS support
import PyPDF2
import io
import base64
from PIL import Image
import fitz  # PyMuPDF
import os
import tempfile

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for session management
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevent caching
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Ensure cookies work on mobile
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True for HTTPS in production
CORS(app, supports_credentials=True, origins=["http://10.184.65.74:5000", "https://pdfglide.onrender.com"], methods=['POST']) # Adjust origins for your domain


# Function to convert PDF pages to images
def pdf_to_images(pdf_file):
    pdf_file.seek(0)
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72))  # 200 DPI
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.tobytes("ppm"))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        images.append(base64.b64encode(img_byte_arr.getvalue()).decode())
    pdf_document.close()
    return images

# Function to modify PDF
def modify_pdf(pdf_file, page_order, pages_to_delete):
    try:
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_writer = PyPDF2.PdfWriter()

        for idx in page_order:
            if idx not in pages_to_delete and idx < len(pdf_reader.pages):
                pdf_writer.add_page(pdf_reader.pages[idx])

        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        if output.getbuffer().nbytes == 0:
            raise ValueError("Generated PDF is empty")
        output.seek(0)
        return output, len(pdf_reader.pages), len(pdf_writer.pages)
    except Exception as e:
        print(f"Error in modify_pdf: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    pdf_file = request.files['pdf']
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_file.save(tmp)
            session['pdf_path'] = tmp.name
        pdf_file.seek(0)
        images = pdf_to_images(pdf_file)
        session['page_order'] = list(range(len(images)))
        session['pages_to_delete'] = []
        session.modified = True  # Ensure session is marked as modified
        print(f"Initial state - Pages: {len(images)}, Page Order: {session['page_order']}, Pages to Delete: {session['pages_to_delete']}")
        return jsonify({
            'previews': images,
            'pageOrder': session['page_order'],
            'pagesToDelete': session['pages_to_delete']
        })
    except Exception as e:
        print(f"Error in /upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/modify', methods=['POST'])
def modify():
    try:
        data = request.json
        page_order = data.get('pageOrder', [])
        pages_to_delete = data.get('pagesToDelete', [])
        print(f"Before download - Page Order: {page_order}, Pages to Delete: {pages_to_delete}")
        if 'pdf_path' not in session or not os.path.exists(session['pdf_path']):
            return jsonify({'error': 'No PDF uploaded or session expired'}), 400
        with open(session['pdf_path'], 'rb') as f:
            modified_pdf, original_count, modified_count = modify_pdf(
                io.BytesIO(f.read()),
                page_order,
                pages_to_delete
            )
        print(f"Modified PDF size: {modified_pdf.getbuffer().nbytes} bytes")
        print(f"Original PDF: {original_count} pages, Modified PDF: {modified_count} pages")
        print("Download initiated")
        modified_pdf.seek(0)
        return send_file(
            modified_pdf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='modified.pdf'
        )
    except Exception as e:
        print(f"Error in /modify: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear():
    if 'pdf_path' in session and os.path.exists(session['pdf_path']):
        try:
            os.unlink(session['pdf_path'])
        except Exception as e:
            print(f"Error deleting temp file: {str(e)}")
    session.clear()
    print("Cleared state")
    return jsonify({'status': 'cleared'})

if __name__ == '__main__':
    # app.run(debug=True, port=5000, threaded=True)
    app.run(host='0.0.0.0', debug=False, port=5000, threaded=True)