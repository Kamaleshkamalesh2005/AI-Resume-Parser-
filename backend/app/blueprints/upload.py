"""
Upload Blueprint Module
Handles resume file uploads with validation and processing
MVC Pattern - View/Controller layer
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from app.use_cases.upload_use_case import UploadUseCase

logger = logging.getLogger(__name__)

# Blueprint definition
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/resume', methods=['POST'])
def upload_resume():
    """
    Upload and process a single resume
    
    Request:
        - file: Resume file (PDF or DOCX)
    
    Response:
        - success: bool
        - data: Parsed resume information
        - error: Error message if failed
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'message': 'Request must include a file'
            }), 400

        use_case = UploadUseCase(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
        )
        payload, status = use_case.process_single(request.files['file'])
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Resume upload error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


@upload_bp.route('/batch', methods=['POST'])
def upload_batch():
    """
    Upload and process multiple resumes
    
    Request:
        - files: Multiple resume files
    
    Response:
        - success: bool
        - data: List of parsed resumes
        - failed: List of failed uploads with errors
    """
    try:
        files = request.files.getlist('files')
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        use_case = UploadUseCase(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
        )
        payload, status = use_case.process_batch(files)
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Batch processing failed',
            'message': str(e)
        }), 500


@upload_bp.route('/validate', methods=['POST'])
def validate_upload():
    """
    Validate file without processing
    
    Request:
        - file: Resume file to validate
    
    Response:
        - valid: bool
        - error: Error message if invalid
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'valid': False,
                'error': 'No file provided'
            }), 400
        
        use_case = UploadUseCase(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
        )
        file = request.files['file']
        is_valid, error = use_case.validate(file)
        
        return jsonify({
            'valid': is_valid,
            'error': error,
            'filename': file.filename if file else None
        }), 200
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500


@upload_bp.route('/job-description', methods=['POST'])
def upload_job_description():
    """Save job description from text input or uploaded file."""
    try:
        use_case = UploadUseCase(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
        )
        text = request.form.get('text', '')
        file_obj = request.files.get('file')
        payload, status = use_case.process_job_description(text, file_obj)
        return jsonify(payload), status
    except Exception as e:
        logger.error(f"Job description upload error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500
