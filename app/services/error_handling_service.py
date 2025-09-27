"""
Error Handling and Logging Service for QR Attendance System
Provides comprehensive error handling, logging, and monitoring
"""

import logging
import traceback
from datetime import datetime, timedelta
from flask import request, current_app
import json

class AttendanceErrorHandler:
    """Centralized error handling for attendance system"""
    
    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/attendance_errors.log'),
                logging.StreamHandler()
            ]
        )
        
        # Create separate loggers for different components
        qr_logger = logging.getLogger('qr_processing')
        student_logger = logging.getLogger('student_identification')
        attendance_logger = logging.getLogger('attendance_processing')
        
        return {
            'qr': qr_logger,
            'student': student_logger,
            'attendance': attendance_logger
        }
    
    @staticmethod
    def log_qr_error(qr_data, error_info, user_id=None):
        """Log QR processing errors"""
        logger = logging.getLogger('qr_processing')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'qr_data_length': len(qr_data) if qr_data else 0,
            'qr_data_preview': qr_data[:100] if qr_data else None,
            'error_code': error_info.get('error_code'),
            'error_message': error_info.get('error'),
            'request_ip': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        logger.error(f"QR Processing Error: {json.dumps(log_data, indent=2)}")
        
        # Store in database if needed for monitoring
        AttendanceErrorHandler._store_error_log('QR_PROCESSING', log_data)
    
    @staticmethod
    def log_student_identification_error(qr_data, error_info, user_id=None):
        """Log student identification errors"""
        logger = logging.getLogger('student_identification')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'qr_data_type': 'legacy' if 'student_no' in str(qr_data) else 'structured',
            'error_code': error_info.get('error_code'),
            'error_message': error_info.get('error'),
            'similar_count': error_info.get('similar_count'),
            'request_context': {
                'ip': request.remote_addr if request else None,
                'endpoint': request.endpoint if request else None
            }
        }
        
        logger.error(f"Student Identification Error: {json.dumps(log_data, indent=2)}")
        AttendanceErrorHandler._store_error_log('STUDENT_IDENTIFICATION', log_data)
    
    @staticmethod
    def log_attendance_processing_error(student_id, session_id, error_info, user_id=None):
        """Log attendance processing errors"""
        logger = logging.getLogger('attendance_processing')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'student_id': student_id,
            'session_id': session_id,
            'error_code': error_info.get('error_code'),
            'error_message': error_info.get('error'),
            'stacktrace': traceback.format_exc() if error_info.get('include_trace') else None
        }
        
        logger.error(f"Attendance Processing Error: {json.dumps(log_data, indent=2)}")
        AttendanceErrorHandler._store_error_log('ATTENDANCE_PROCESSING', log_data)
    
    @staticmethod
    def log_database_error(operation, error, context=None):
        """Log database-related errors"""
        logger = logging.getLogger('database_operations')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'context': context,
            'stacktrace': traceback.format_exc()
        }
        
        logger.error(f"Database Error: {json.dumps(log_data, indent=2)}")
        AttendanceErrorHandler._store_error_log('DATABASE_ERROR', log_data)
    
    @staticmethod
    def _store_error_log(error_type, log_data):
        """Store error logs in database for monitoring (if table exists)"""
        try:
            from app import db
            from app.models.error_log_model import ErrorLog
            
            error_log = ErrorLog(
                error_type=error_type,
                error_data=json.dumps(log_data),
                created_at=datetime.now()
            )
            
            db.session.add(error_log)
            db.session.commit()
            
        except Exception as e:
            # Don't let logging errors break the main application
            logger = logging.getLogger('error_handler')
            logger.warning(f"Failed to store error log in database: {str(e)}")
    
    @staticmethod
    def handle_exception(func):
        """Decorator for comprehensive exception handling"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger('exception_handler')
                
                error_data = {
                    'function': func.__name__,
                    'args': str(args)[:200],
                    'kwargs': str(kwargs)[:200],
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'stacktrace': traceback.format_exc()
                }
                
                logger.error(f"Unhandled Exception: {json.dumps(error_data, indent=2)}")
                
                # Return standardized error response
                return {
                    'success': False,
                    'error': 'An unexpected error occurred',
                    'error_code': 'UNHANDLED_EXCEPTION',
                    'details': str(e) if current_app.debug else None
                }
        
        return wrapper
    
    @staticmethod
    def create_error_response(error_code, error_message, **kwargs):
        """Create standardized error response"""
        response = {
            'success': False,
            'error_code': error_code,
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields
        for key, value in kwargs.items():
            if value is not None:
                response[key] = value
        
        return response
    
    @staticmethod
    def get_error_statistics():
        """Get error statistics for monitoring"""
        try:
            from app import db
            from app.models.error_log_model import ErrorLog
            from sqlalchemy import func
            
            # Get error counts by type for last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            
            error_counts = db.session.query(
                ErrorLog.error_type,
                func.count(ErrorLog.id).label('count')
            ).filter(
                ErrorLog.created_at >= yesterday
            ).group_by(ErrorLog.error_type).all()
            
            return {
                'period': '24_hours',
                'error_counts': {error_type: count for error_type, count in error_counts},
                'total_errors': sum(count for _, count in error_counts)
            }
            
        except Exception as e:
            logger = logging.getLogger('error_handler')
            logger.warning(f"Failed to get error statistics: {str(e)}")
            return {'error': 'Statistics unavailable'}

class QRProcessingErrorHandler:
    """Specialized error handler for QR processing"""
    
    ERROR_MESSAGES = {
        'EMPTY_QR': 'QR code is empty. Please scan a valid student QR code.',
        'WHITESPACE_ONLY': 'QR code contains only whitespace. Please scan a valid QR code.',
        'DATA_TOO_LONG': 'QR code data is too long. Maximum length is 5000 characters.',
        'BINARY_DATA': 'QR code contains invalid binary data. Please use text-based QR codes.',
        'MALICIOUS_CONTENT': 'QR code contains potentially unsafe content.',
        'SQL_INJECTION': 'QR code contains invalid characters.',
        'INVALID_JSON_TYPE': 'QR code must contain a valid data structure.',
        'NULL_VALUE': 'QR code contains empty required fields.',
        'MISSING_FIELDS': 'QR code is missing required student information.',
        'INVALID_STUDENT_ID_TYPE': 'Student ID format is invalid.',
        'INVALID_STUDENT_ID_FORMAT': 'Student ID contains invalid characters.',
        'INVALID_STUDENT_NO': 'Student number format is invalid.',
        'INVALID_NAME': 'Student name format is invalid.',
        'UNICODE_ERROR': 'QR code contains unsupported characters.',
        'INVALID_TYPE': 'QR code type is not supported.',
        'MALFORMED_JSON': 'QR code contains malformed data structure.',
        'LEGACY_TOO_LONG': 'Student number is too long (maximum 20 characters).',
        'LEGACY_INVALID_CHARS': 'Student number contains invalid characters.',
        'INVALID_FORMAT': 'QR code format is not recognized.'
    }
    
    @staticmethod
    def get_user_friendly_message(error_code):
        """Get user-friendly error message"""
        return QRProcessingErrorHandler.ERROR_MESSAGES.get(
            error_code, 
            'QR code format is invalid. Please scan a valid student QR code.'
        )
    
    @staticmethod
    def should_retry(error_code):
        """Determine if error condition allows retry"""
        non_retry_errors = {
            'DATA_TOO_LONG', 'BINARY_DATA', 'MALICIOUS_CONTENT', 
            'SQL_INJECTION', 'INVALID_FORMAT', 'MALFORMED_JSON'
        }
        return error_code not in non_retry_errors