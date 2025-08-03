# PDF Editor

A Flask-based web application for editing PDFs, allowing page reordering and deletion.

## Features
- Upload PDFs and preview pages at 100 DPI.
- Reorder pages via drag-and-drop.
- Delete pages with a 0.3s fade-out animation.
- Download modified PDFs at 150 DPI with [original]_modified.pdf naming.
- Dark mode, glassmorphism UI, and responsive 1–3 column grid.

## Setup
1. Install dependencies: `pip install flask PyPDF2 PyMuPDF pillow numpy`
2. Run: `python app.py`
3. Access: `http://localhost:5000`

## Requirements
- Python 3.x
- Flask, PyPDF2, PyMuPDF, Pillow, NumPy

## License
MIT License