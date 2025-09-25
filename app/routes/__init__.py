"""
Routes package initialization
Exports all route blueprints
"""

from app.routes.main_routes import main_bp
from app.routes.auth_routes import auth_bp
from app.routes.student_routes import student_bp
from app.routes.attendance_routes import attendance_bp
from app.routes.admin_routes import admin_bp
from app.routes.scanner_routes import scanner_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'student_bp',
    'attendance_bp',
    'admin_bp',
    'scanner_bp'
]