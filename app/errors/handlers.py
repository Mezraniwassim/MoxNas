"""Error handlers"""
from flask import render_template, request, jsonify
from app.errors import bp
from app.models import SystemLog, LogLevel

@bp.app_errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    if request.is_json:
        return jsonify({'error': 'Bad request'}), 400
    return render_template('errors/400.html'), 400

@bp.app_errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    SystemLog.log_event(
        level=LogLevel.WARNING,
        category='security',
        message=f'Access denied to {request.url}',
        ip_address=request.remote_addr
    )
    
    if request.is_json:
        return jsonify({'error': 'Access denied'}), 403
    return render_template('errors/403.html'), 403

@bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.is_json:
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    SystemLog.log_event(
        level=LogLevel.ERROR,
        category='system',
        message=f'Internal server error: {str(error)}',
        ip_address=request.remote_addr
    )
    
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500

@bp.app_errorhandler(503)
def service_unavailable(error):
    """Handle 503 errors"""
    if request.is_json:
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    return render_template('errors/503.html'), 503