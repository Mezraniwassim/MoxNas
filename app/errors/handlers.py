"""Enhanced error handlers with structured logging and standardized responses"""
from flask import render_template, request, jsonify, current_app
from werkzeug.exceptions import HTTPException
from app.errors import bp
from app.models import SystemLog, LogLevel
from app.utils.enhanced_logging import get_logger, correlation_context
from app.utils.error_handling import MoxNASError, ErrorSeverity
import traceback
import uuid
from datetime import datetime


@bp.app_errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors with enhanced logging"""
    logger = get_logger('error_handler')
    
    error_id = str(uuid.uuid4())
    error_details = {
        'error_id': error_id,
        'url': request.url,
        'method': request.method,
        'user_agent': request.headers.get('User-Agent'),
        'content_type': request.content_type
    }
    
    logger.warning(
        "Bad request received",
        category='http_error',
        error_code=400,
        error_id=error_id,
        details=error_details
    )
    
    SystemLog.log_event(
        level=LogLevel.WARNING,
        category="http_error",
        message=f"Bad request: {request.url}",
        ip_address=request.remote_addr,
        details=error_details,
    )
    
    if request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": 400,
                "message": "Bad request - invalid or malformed request data",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 400
    
    return render_template("errors/400.html", error_id=error_id), 400


@bp.app_errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors with security logging"""
    logger = get_logger('error_handler')
    
    error_id = str(uuid.uuid4())
    error_details = {
        'error_id': error_id,
        'url': request.url,
        'method': request.method,
        'endpoint': request.endpoint,
        'user_agent': request.headers.get('User-Agent'),
        'referer': request.headers.get('Referer')
    }
    
    logger.security_event(
        'access_denied',
        'medium',
        f"Access denied to {request.url}",
        **error_details
    )
    
    SystemLog.log_event(
        level=LogLevel.WARNING,
        category="security",
        message=f"Access denied to {request.url}",
        ip_address=request.remote_addr,
        details=error_details,
    )
    
    if request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": 403,
                "message": "Access denied - insufficient privileges",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 403
    
    return render_template("errors/403.html", error_id=error_id), 403


@bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    logger = get_logger('error_handler')
    
    error_id = str(uuid.uuid4())
    
    # Don't log static assets as errors to avoid log spam
    if not request.path.startswith('/static/'):
        error_details = {
            'error_id': error_id,
            'url': request.url,
            'method': request.method,
            'user_agent': request.headers.get('User-Agent'),
            'referer': request.headers.get('Referer')
        }
        
        logger.info(
            f"Resource not found: {request.url}",
            category='http_error',
            error_code=404,
            details=error_details
        )
    
    if request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": 404,
                "message": "Resource not found",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 404
    
    return render_template("errors/404.html", error_id=error_id), 404


@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error with comprehensive logging"""
    from app import db
    
    logger = get_logger('error_handler')
    
    # Rollback any pending database transactions
    try:
        db.session.rollback()
    except Exception as rollback_error:
        logger.error(f"Failed to rollback database session: {rollback_error}")
    
    error_id = str(uuid.uuid4())
    error_details = {
        'error_id': error_id,
        'url': request.url,
        'method': request.method,
        'endpoint': request.endpoint,
        'user_agent': request.headers.get('User-Agent'),
        'error_type': type(error).__name__,
        'traceback': traceback.format_exc() if current_app.debug else None
    }
    
    logger.critical(
        f"Internal server error: {str(error)}",
        category='system_error',
        error_id=error_id,
        details=error_details
    )
    
    SystemLog.log_event(
        level=LogLevel.ERROR,
        category="system",
        message=f"Internal server error [ID: {error_id}]: {str(error)}",
        ip_address=request.remote_addr,
        details=error_details,
    )
    
    if request.is_json:
        response_data = {
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error - the server encountered an unexpected condition",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        # Include traceback in debug mode
        if current_app.debug and error_details['traceback']:
            response_data['error']['traceback'] = error_details['traceback']
        
        return jsonify(response_data), 500
    
    return render_template(
        "errors/500.html", 
        error_id=error_id,
        show_details=current_app.debug,
        error_details=error_details if current_app.debug else None
    ), 500


@bp.app_errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limiting errors"""
    SystemLog.log_event(
        level=LogLevel.WARNING,
        category="security",
        message=f"Rate limit exceeded for {request.endpoint}",
        ip_address=request.remote_addr,
        details={"endpoint": request.endpoint, "method": request.method},
    )

    if request.is_json:
        return (
            jsonify(
                {"error": "Rate limit exceeded", "retry_after": getattr(error, "retry_after", None)}
            ),
            429,
        )
    return render_template("errors/429.html"), 429


@bp.app_errorhandler(503)
def service_unavailable(error):
    """Handle 503 Service Unavailable errors"""
    logger = get_logger('error_handler')
    
    error_id = str(uuid.uuid4())
    error_details = {
        'error_id': error_id,
        'url': request.url,
        'method': request.method,
        'user_agent': request.headers.get('User-Agent')
    }
    
    logger.error(
        "Service temporarily unavailable",
        category='service_error',
        error_code=503,
        details=error_details
    )
    
    SystemLog.log_event(
        level=LogLevel.ERROR,
        category="system",
        message="Service temporarily unavailable",
        ip_address=request.remote_addr,
        details=error_details,
    )
    
    if request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": 503,
                "message": "Service temporarily unavailable - please try again later",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id,
                "retry_after": 60  # Suggest retry after 60 seconds
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 503
    
    return render_template("errors/503.html", error_id=error_id), 503


@bp.app_errorhandler(MoxNASError)
def handle_moxnas_error(error: MoxNASError):
    """Handle custom MoxNAS errors with detailed context"""
    logger = get_logger('error_handler')
    
    error_id = str(uuid.uuid4())
    
    # Determine HTTP status code based on error category
    status_codes = {
        'validation': 400,
        'authentication': 401,
        'authorization': 403,
        'network': 503,
        'database': 503,
        'storage': 503,
        'system': 500
    }
    status_code = status_codes.get(error.category.value, 500)
    
    # Log with appropriate level based on severity
    log_levels = {
        ErrorSeverity.LOW: logger.info,
        ErrorSeverity.MEDIUM: logger.warning,
        ErrorSeverity.HIGH: logger.error,
        ErrorSeverity.CRITICAL: logger.critical
    }
    
    log_func = log_levels.get(error.severity, logger.error)
    log_func(
        f"MoxNAS Error: {error.message}",
        category=error.category.value,
        severity=error.severity.value,
        error_id=error_id,
        recoverable=error.recoverable,
        details=error.context.additional_data if error.context else {}
    )
    
    SystemLog.log_event(
        level=LogLevel.ERROR if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else LogLevel.WARNING,
        category=error.category.value,
        message=f"[{error_id}] {error.message}",
        ip_address=request.remote_addr,
        details={
            'error_id': error_id,
            'severity': error.severity.value,
            'recoverable': error.recoverable,
            'context': error.context.additional_data if error.context else {}
        }
    )
    
    if request.is_json:
        response_data = error.to_dict()
        response_data['error']['error_id'] = error_id
        response_data['error']['correlation_id'] = correlation_context.correlation_id
        
        return jsonify(response_data), status_code
    
    # For HTML responses, use appropriate error template
    template_map = {
        400: "errors/400.html",
        401: "errors/401.html",
        403: "errors/403.html",
        500: "errors/500.html",
        503: "errors/503.html"
    }
    
    template = template_map.get(status_code, "errors/500.html")
    return render_template(
        template,
        error_id=error_id,
        error_message=error.message if not error.severity == ErrorSeverity.CRITICAL else "A system error occurred"
    ), status_code


@bp.app_errorhandler(Exception)
def handle_generic_exception(error: Exception):
    """Catch-all handler for unhandled exceptions"""
    logger = get_logger('error_handler')
    
    # Don't handle HTTPExceptions here, let specific handlers deal with them
    if isinstance(error, HTTPException):
        return error
    
    error_id = str(uuid.uuid4())
    error_details = {
        'error_id': error_id,
        'url': request.url,
        'method': request.method,
        'error_type': type(error).__name__,
        'traceback': traceback.format_exc()
    }
    
    logger.critical(
        f"Unhandled exception: {str(error)}",
        category='system_error',
        error_id=error_id,
        details=error_details
    )
    
    SystemLog.log_event(
        level=LogLevel.CRITICAL,
        category="system",
        message=f"Unhandled exception [ID: {error_id}]: {type(error).__name__}",
        ip_address=request.remote_addr,
        details=error_details,
    )
    
    # Attempt database rollback
    try:
        from app import db
        db.session.rollback()
    except Exception:
        pass  # Don't let rollback failure mask the original error
    
    if request.is_json:
        return jsonify({
            "success": False,
            "error": {
                "code": 500,
                "message": "An unexpected error occurred",
                "error_id": error_id,
                "correlation_id": correlation_context.correlation_id
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 500
    
    return render_template(
        "errors/500.html",
        error_id=error_id,
        show_details=current_app.debug,
        error_details=error_details if current_app.debug else None
    ), 500
