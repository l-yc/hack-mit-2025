from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import mimetypes
from PIL import Image

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
    'image/bmp', 'image/webp'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file_path):
    """Validate that the uploaded file is actually an image"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension"""
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{unique_id}.{file_ext}"

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Photo Upload API is running',
        'version': '1.0.0'
    }), 200

@app.route('/upload', methods=['POST'])
def upload_photo():
    """Upload a single photo"""
    try:
        # Check if file is present in request
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo file provided'}), 400
        
        file = request.files['photo']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid file type',
                'allowed_types': list(ALLOWED_EXTENSIONS)
            }), 400
        
        # Validate MIME type
        if file.mimetype not in ALLOWED_MIME_TYPES:
            return jsonify({
                'error': 'Invalid MIME type',
                'received': file.mimetype,
                'allowed_types': list(ALLOWED_MIME_TYPES)
            }), 400
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Validate that it's actually an image
        if not validate_image(file_path):
            os.remove(file_path)  # Clean up invalid file
            return jsonify({'error': 'Invalid image file'}), 400
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return jsonify({
            'message': 'Photo uploaded successfully',
            'filename': unique_filename,
            'original_filename': original_filename,
            'size_bytes': file_size,
            'upload_time': datetime.now().isoformat(),
            'file_url': f'/photos/{unique_filename}'
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/upload/multiple', methods=['POST'])
def upload_multiple_photos():
    """Upload multiple photos at once"""
    try:
        if 'photos' not in request.files:
            return jsonify({'error': 'No photos provided'}), 400
        
        files = request.files.getlist('photos')
        
        if not files:
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        errors = []
        
        for i, file in enumerate(files):
            try:
                if file.filename == '':
                    errors.append(f'File {i+1}: No filename')
                    continue
                
                if not allowed_file(file.filename):
                    errors.append(f'File {i+1}: Invalid file type')
                    continue
                
                if file.mimetype not in ALLOWED_MIME_TYPES:
                    errors.append(f'File {i+1}: Invalid MIME type')
                    continue
                
                original_filename = secure_filename(file.filename)
                unique_filename = generate_unique_filename(original_filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                file.save(file_path)
                
                if not validate_image(file_path):
                    os.remove(file_path)
                    errors.append(f'File {i+1}: Invalid image file')
                    continue
                
                file_size = os.path.getsize(file_path)
                
                uploaded_files.append({
                    'filename': unique_filename,
                    'original_filename': original_filename,
                    'size_bytes': file_size,
                    'file_url': f'/photos/{unique_filename}'
                })
                
            except Exception as e:
                errors.append(f'File {i+1}: {str(e)}')
        
        return jsonify({
            'message': f'Processed {len(files)} files',
            'uploaded_count': len(uploaded_files),
            'uploaded_files': uploaded_files,
            'errors': errors,
            'upload_time': datetime.now().isoformat()
        }), 201 if uploaded_files else 400
    
    except Exception as e:
        return jsonify({'error': f'Multiple upload failed: {str(e)}'}), 500

@app.route('/photos/<filename>', methods=['GET'])
def get_photo(filename):
    """Serve uploaded photos"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return jsonify({'error': 'Photo not found'}), 404

@app.route('/photos', methods=['GET'])
def list_photos():
    """List all uploaded photos"""
    try:
        photos = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                photos.append({
                    'filename': filename,
                    'size_bytes': stat.st_size,
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_url': f'/photos/{filename}'
                })
        
        return jsonify({
            'photos': sorted(photos, key=lambda x: x['modified_time'], reverse=True),
            'total_count': len(photos)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to list photos: {str(e)}'}), 500

@app.route('/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    """Delete a specific photo"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Photo not found'}), 404
        
        os.remove(file_path)
        
        return jsonify({
            'message': 'Photo deleted successfully',
            'filename': filename
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete photo: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'error': 'File too large',
        'max_size_mb': MAX_FILE_SIZE / (1024 * 1024)
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)