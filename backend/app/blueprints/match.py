"""
Match Blueprint Module
Handles resume-job matching and similarity computation
MVC Pattern - View/Controller layer
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from app.use_cases.matching_use_case import MatchingUseCase

logger = logging.getLogger(__name__)

# Blueprint definition
match_bp = Blueprint('match', __name__)


def _build_use_case() -> MatchingUseCase:
    return MatchingUseCase(
        similarity_threshold=current_app.config.get('COSINE_SIMILARITY_THRESHOLD', 0.5),
    )


@match_bp.route('/similarity', methods=['POST'])
def calculate_similarity():
    """
    Calculate similarity between resume and job description
    
    Request JSON:
        - resume_text: Resume text content
        - job_description: Job description text
    
    Response:
        - similarity_score: Float (0-1)
        - ml_probability: Float (0-1)
        - final_score: Float (0-1)
        - percentage: Int (0-100)
        - is_match: Boolean based on threshold
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        use_case = _build_use_case()
        payload, status = use_case.calculate_similarity(
            resume_text=data.get('resume_text', ''),
            job_description=data.get('job_description', ''),
        )
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Similarity calculation error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Similarity calculation failed',
            'message': str(e)
        }), 500


@match_bp.route('/batch', methods=['POST'])
def batch_matching():
    """
    Match one resume against multiple job descriptions
    
    Request JSON:
        - resume_text: Resume text
        - job_descriptions: List of job description texts
    
    Response:
        - matches: List of scored matches sorted by final_score
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        use_case = _build_use_case()
        payload, status = use_case.batch_similarity(
            resume_text=data.get('resume_text', ''),
            job_descriptions=data.get('job_descriptions', []),
        )
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Batch matching error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Batch matching failed',
            'message': str(e)
        }), 500


@match_bp.route('/predict', methods=['POST'])
def predict_match():
    """
    Use ML model to predict if resume matches job
    
    Request JSON:
        - features: Feature dictionary or list
    
    Response:
        - prediction: Match prediction (bool)
        - probability: Match probability (float)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        use_case = _build_use_case()
        payload, status = use_case.predict(features=data.get('features'))
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Prediction failed',
            'message': str(e)
        }), 500


@match_bp.route('/model-info', methods=['GET'])
def get_model_info():
    """
    Get information about the matching model
    
    Response:
        - model: Model information including status
        - similarity_threshold: Threshold for matching
    """
    try:
        use_case = _build_use_case()
        payload, status = use_case.model_info(current_app.config)
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Model info error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

