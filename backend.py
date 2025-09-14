from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import io
import base64
from datetime import datetime

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'  # You can change this to PostgreSQL, MySQL, etc.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Database model
class ImageStorage(db.Model):
    __tablename__ = 'images'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)  # Store binary data
    content_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'content_type': self.content_type,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat()
        }

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_tables():
    """Create database tables if they don't exist"""
    with app.app_context():
        db.create_all()

# Routes

@app.route('/api/images', methods=['POST'])
def upload_image():
    """Upload an image to the database"""
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Supported types: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Check for empty filename after securing
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        # Check if file is empty
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        content_type = file.content_type or 'application/octet-stream'
        
        # Check if image with same filename already exists
        existing_image = ImageStorage.query.filter_by(filename=filename).first()
        if existing_image:
            return jsonify({'error': f'Image with filename "{filename}" already exists'}), 409
        
        # Create new image record
        new_image = ImageStorage(
            filename=filename,
            content=file_content,
            content_type=content_type,
            file_size=file_size
        )
        
        # Save to database
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image': new_image.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
def list_images():
    """Get list of all uploaded images"""
    try:
        images = ImageStorage.query.all()
        return jsonify({
            'count': len(images),
            'images': [image.to_dict() for image in images]
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve images: {str(e)}'}), 500

@app.route('/api/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    """Retrieve a specific image by ID"""
    try:
        image = ImageStorage.query.get_or_404(image_id)
        
        # Return image file
        return send_file(
            io.BytesIO(image.content),
            mimetype=image.content_type,
            as_attachment=False,
            download_name=image.filename
        )
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve image: {str(e)}'}), 500

@app.route('/api/images/<filename>', methods=['GET'])
def get_image_by_filename(filename):
    """Retrieve a specific image by filename"""
    try:
        image = ImageStorage.query.filter_by(filename=filename).first()
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Return image file
        return send_file(
            io.BytesIO(image.content),
            mimetype=image.content_type,
            as_attachment=False,
            download_name=image.filename
        )
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve image: {str(e)}'}), 500

@app.route('/api/images/<int:image_id>/info', methods=['GET'])
def get_image_info(image_id):
    """Get image metadata without downloading the file"""
    try:
        image = ImageStorage.query.get_or_404(image_id)
        return jsonify({'image': image.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve image info: {str(e)}'}), 500

@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete a specific image"""
    try:
        image = ImageStorage.query.get_or_404(image_id)
        
        filename = image.filename  # Store filename before deletion
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'message': f'Image "{filename}" deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete image: {str(e)}'}), 500

@app.route('/api/images/<int:image_id>/base64', methods=['GET'])
def get_image_base64(image_id):
    """Get image as base64 encoded string"""
    try:
        image = ImageStorage.query.get_or_404(image_id)
        
        # Encode image content to base64
        encoded_content = base64.b64encode(image.content).decode('utf-8')
        
        return jsonify({
            'filename': image.filename,
            'content_type': image.content_type,
            'content': encoded_content,
            'file_size': image.file_size
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve image: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create database tables
    create_tables()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=6741)