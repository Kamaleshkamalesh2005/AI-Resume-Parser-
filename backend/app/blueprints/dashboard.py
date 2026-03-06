"""
Dashboard Blueprint Module
Provides application statistics and health checks
MVC Pattern - View/Controller layer
"""

from flask import Blueprint, jsonify, current_app
import logging
from app.models.matcher import MatcherModel
from app.use_cases.dashboard_use_case import DashboardUseCase

logger = logging.getLogger(__name__)

# Blueprint definition
dashboard_bp = Blueprint('dashboard', __name__)

matcher_model = MatcherModel()
dashboard_use_case = DashboardUseCase(matcher_model=matcher_model)


@dashboard_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get application statistics
    
    Response:
        - models_loaded: Whether ML models are loaded
        - upload_stats: File upload statistics
        - system_info: System information
    """
    try:
        payload, status = dashboard_use_case.stats(current_app.config)
        logger.info("Stats retrieved successfully")
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Stats retrieval error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    
    Response:
        - status: 'healthy' or 'degraded'
        - components: Status of individual components
    """
    try:
        payload, status = dashboard_use_case.health(current_app.config)
        return jsonify(payload), status
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e)
        }), 500


@dashboard_bp.route('/info', methods=['GET'])
def app_info():
    """
    Get application information
    
    Response:
        - version: Application version
        - name: Application name
        - features: Supported features
    """
    payload, status = dashboard_use_case.info(current_app.debug)
    return jsonify(payload), status
