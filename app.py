from flask import Flask, request, jsonify, send_file, render_template, session
import PyPDF2
import io
import base64
from PIL import Image
import fitz  # PyMuPDF
import os
import tempfile
import uuid
import numpy as np

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for session management
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Prevent caching
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Function to convert PDF pages to images
def pdf_to_images(pdf_path):
    try:
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        images = []
        for page_num in range(total_pages):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))  # 150 DPI
            # Ensure RGB color space and correct channel order
            if pix.n == 4:  # CMYK or RGBA, convert to RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            # Use pix.samples for raw RGB data
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG', optimize=True)  # Optimize PNG
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()
            images.append(img_base64)
            print(f"Processed page {page_num + 1}/{total_pages}, base64 length: {len(img_base64)}")
        pdf_document.close()
        return images, total_pages
    except Exception as e:
        print(f"Error in pdf_to_images: {str(e)}")
        raise

# Function to modify PDF
def modify_pdf(pdf_path, page_order, pages_to_delete):
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
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
    if 'pdf' not in request.files or request.files['pdf'].filename == '':
        return jsonify({'error': 'No PDF file selected'}), 400
    pdf_file = request.files['pdf']
    try:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_file.save(tmp)
            session['pdf_path'] = tmp.name
        session['page_order'] = []
        session['pages_to_delete'] = []
        session.modified = True
        images, total_pages = pdf_to_images(session['pdf_path'])
        print(f"Upload completed - Session ID: {session_id}, File: {session['pdf_path']}, Pages: {total_pages}")
        return jsonify({
            'session_id': session_id,
            'images': images,
            'total_pages': total_pages
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
            print(f"PDF file not found for modify: {session.get('pdf_path')}")
            return jsonify({'error': 'No PDF uploaded or session expired'}), 400
        modified_pdf, original_count, modified_count = modify_pdf(
            session['pdf_path'],
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
    session_id = session.get('session_id')
    if 'pdf_path' in session and os.path.exists(session['pdf_path']):
        try:
            os.unlink(session['pdf_path'])
            print(f"Deleted temp file: {session['pdf_path']}")
        except Exception as e:
            print(f"Error deleting temp file: {str(e)}")
    session.clear()
    print("Cleared state")
    return jsonify({'status': 'cleared'})

if __name__ == '__main__':
    # app.run(debug=True, port=5000, threaded=True)
    app.run(host='0.0.0.0', debug=False, port=5000, threaded=True)