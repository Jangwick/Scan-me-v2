"""
Authentication Utilities for ScanMe System
Handles password hashing, validation, and user authentication helpers
"""

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user
from functools import wraps
from flask import redirect, url_for, flash, request
import re
import secrets
import string

def hash_password(password):
    """
    Hash password using Werkzeug's secure method
    Args:
        password (str): Plain text password
    Returns:
        str: Hashed password
    """
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

def verify_password(password_hash, password):
    """
    Verify password against hash
    Args:
        password_hash (str): Stored password hash
        password (str): Plain text password to verify
    Returns:
        bool: True if password matches
    """
    return check_password_hash(password_hash, password)

def validate_email(email):
    """
    Validate email address format
    Args:
        email (str): Email address to validate
    Returns:
        bool: True if email is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """
    Validate username format
    Args:
        username (str): Username to validate
    Returns:
        bool: True if username is valid
    """
    # Username should be 3-20 characters, alphanumeric and underscores only
    if not username or len(username) < 3 or len(username) > 20:
        return False
    
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None

def validate_password(password):
    """
    Validate password strength
    Args:
        password (str): Password to validate
    Returns:
        dict: Validation result with success status and messages
    """
    errors = []
    
    if not password:
        errors.append("Password is required")
        return {'valid': False, 'errors': errors}
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\?]', password):
        errors.append("Password must contain at least one special character")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def generate_random_password(length=12):
    """
    Generate a secure random password
    Args:
        length (int): Length of password to generate
    Returns:
        str: Random password
    """
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

def requires_role(allowed_roles):
    """
    Decorator to require specific user roles for route access
    Args:
        allowed_roles (list): List of allowed roles
    Returns:
        function: Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            if current_user.role not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_admin(f):
    """
    Decorator to require admin role
    """
    return requires_role(['admin'])(f)

def requires_professor_or_admin(f):
    """
    Decorator to require professor or admin role
    """
    return requires_role(['admin', 'professor'])(f)

def requires_scanner_access(f):
    """
    Decorator to require student access (any authenticated user)
    """
    return requires_role(['admin', 'professor', 'student'])(f)

def get_user_permissions(user):
    """
    Get user permissions based on role
    Args:
        user: User object
    Returns:
        dict: Dictionary of permissions
    """
    permissions = {
        'can_scan_attendance': False,
        'can_view_reports': False,
        'can_manage_students': False,
        'can_manage_rooms': False,
        'can_manage_users': False,
        'can_manage_sessions': False,
        'can_export_data': False,
        'can_view_dashboard': False
    }
    
    if not user or not user.is_authenticated:
        return permissions
    
    # Base permissions for all authenticated users
    permissions['can_view_dashboard'] = True
    
    if user.role in ['student', 'professor', 'admin']:
        permissions['can_scan_attendance'] = True
    
    if user.role in ['professor', 'admin']:
        permissions['can_view_reports'] = True
        permissions['can_manage_students'] = True
        permissions['can_manage_sessions'] = True
        permissions['can_export_data'] = True
    
    if user.role == 'admin':
        permissions['can_manage_rooms'] = True
        permissions['can_manage_users'] = True
    
    return permissions

def validate_student_data(data):
    """
    Validate student registration data
    Args:
        data (dict): Student data to validate
    Returns:
        dict: Validation result
    """
    errors = []
    
    required_fields = ['student_no', 'first_name', 'last_name', 'email', 'department', 'section', 'year_level']
    
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Validate email
    if data.get('email') and not validate_email(data['email']):
        errors.append("Invalid email address format")
    
    # Validate year level
    if data.get('year_level'):
        try:
            year = int(data['year_level'])
            if year < 1 or year > 6:
                errors.append("Year level must be between 1 and 6")
        except (ValueError, TypeError):
            errors.append("Year level must be a number")
    
    # Validate student number format
    if data.get('student_no'):
        student_no = data['student_no'].strip()
        if len(student_no) < 6 or len(student_no) > 20:
            errors.append("Student number must be between 6 and 20 characters")
        
        # Check for alphanumeric format
        if not re.match(r'^[A-Za-z0-9\-_]+$', student_no):
            errors.append("Student number can only contain letters, numbers, hyphens, and underscores")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_room_data(data):
    """
    Validate room data
    Args:
        data (dict): Room data to validate
    Returns:
        dict: Validation result
    """
    errors = []
    
    # Required fields (matching the frontend form requirements)
    required_fields = ['room_number', 'building', 'floor', 'capacity']
    
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Room name is optional, but if provided should not be empty
    if data.get('room_name') is not None and data.get('room_name').strip() == '':
        data['room_name'] = None  # Convert empty string to None for optional field
    
    # Validate capacity
    if data.get('capacity'):
        try:
            capacity = int(data['capacity'])
            if capacity < 1 or capacity > 1000:
                errors.append("Capacity must be between 1 and 1000")
        except (ValueError, TypeError):
            errors.append("Capacity must be a number")
    
    # Validate floor
    if data.get('floor'):
        try:
            floor = int(data['floor'])
            if floor < 0 or floor > 50:
                errors.append("Floor must be between 0 and 50")
        except (ValueError, TypeError):
            errors.append("Floor must be a number")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }