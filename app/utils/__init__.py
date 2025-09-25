"""
Utils package initialization
Exports utility functions for easy importing
"""

from app.utils.auth_utils import *
from app.utils.qr_utils import *
from app.utils.export_utils import *

__all__ = [
    # Auth utilities
    'hash_password',
    'verify_password',
    'validate_email',
    'validate_username',
    'validate_password',
    'requires_role',
    'requires_admin',
    'requires_professor_or_admin',
    'requires_scanner_access',
    'get_user_permissions',
    'validate_student_data',
    'validate_room_data',
    
    # QR utilities
    'generate_student_qr_code',
    'scan_qr_from_image',
    'scan_qr_from_webcam',
    'validate_qr_code',
    'decode_qr_data',
    'create_qr_code_batch',
    'qr_code_to_base64',
    
    # Export utilities
    'export_attendance_to_excel',
    'export_attendance_to_csv',
    'export_attendance_to_pdf',
    'generate_student_report',
    'generate_room_report',
    'export_students_to_excel',
    'get_export_summary'
]