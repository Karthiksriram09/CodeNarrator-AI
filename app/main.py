from flask import Flask, render_template, request, jsonify
import os
from services.code_parser import parse_code_structure

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_code():
    """Handle file upload and run initial AST parsing"""
    if 'code_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['code_file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Call your AST-based parser
    try:
        structure = parse_code_structure(filepath)
        return jsonify({'status': 'success', 'structure': structure})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
