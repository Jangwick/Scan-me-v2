"""
User Model for ScanMe Attendance System
Handles user authentication and role management
Supports: Admin, Student, Professor roles
"""

from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash

class User(UserMixin, db.Model):
    """
    User model for authentication and authorization
    Supports multiple user roles: admin, student, professor
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # admin, student, professor
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='scanned_by_user', lazy=True,
                                       foreign_keys='AttendanceRecord.scanned_by')
    time_in_records = db.relationship('AttendanceRecord', backref='time_in_scanned_by_user', lazy=True,
                                    foreign_keys='AttendanceRecord.time_in_scanned_by')
    time_out_records = db.relationship('AttendanceRecord', backref='time_out_scanned_by_user', lazy=True,
                                     foreign_keys='AttendanceRecord.time_out_scanned_by')
    
    def __init__(self, username, email, password, role='student', is_active=True):
        """Initialize user with required fields"""
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.is_active = is_active
    
    def check_password(self, password):
        """Check if provided password matches stored hash"""
        return check_password_hash(self.password, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'
    
    def is_professor(self):
        """Check if user has professor role"""
        return self.role == 'professor'
    
    def is_student(self):
        """Check if user has student role"""
        return self.role == 'student'
    
    def can_access_admin(self):
        """Check if user can access admin features"""
        return self.role in ['admin']
    
    def can_manage_students(self):
        """Check if user can manage students"""
        return self.role in ['admin', 'professor']
    
    def can_view_reports(self):
        """Check if user can view attendance reports"""
        return self.role in ['admin', 'professor']
    
    def can_scan_attendance(self):
        """Check if user can scan QR codes for attendance"""
        return self.role in ['admin', 'professor']
    
    def get_display_name(self):
        """Get display name for user"""
        return self.username.title()
    
    def get_role_display(self):
        """Get formatted role name for display"""
        role_names = {
            'admin': 'Administrator',
            'professor': 'Professor',
            'student': 'Student'
        }
        return role_names.get(self.role, self.role.title())
    
    def to_dict(self):
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'role_display': self.get_role_display(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        """String representation of user"""
        return f'<User {self.username} ({self.role})>'
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_active_users():
        """Get all active users"""
        return User.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_users_by_role(role):
        """Get users by role"""
        return User.query.filter_by(role=role, is_active=True).all()
    
    @staticmethod
    def create_user(username, email, password, role='student'):
        """Create new user with validation"""
        from app.utils.auth_utils import hash_password, validate_email, validate_username
        
        # Validate input
        if not validate_username(username):
            raise ValueError("Invalid username format")
        
        if not validate_email(email):
            raise ValueError("Invalid email format")
        
        # Check for existing user
        if User.get_by_username(username):
            raise ValueError("Username already exists")
        
        if User.get_by_email(email):
            raise ValueError("Email already exists")
        
        # Create user
        user = User(
            username=username,
            email=email,
            password=hash_password(password),
            role=role
        )
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def update_profile(self, username=None, email=None):
        """Update user profile information"""
        if username and username != self.username:
            if User.get_by_username(username):
                raise ValueError("Username already exists")
            self.username = username
        
        if email and email != self.email:
            if User.get_by_email(email):
                raise ValueError("Email already exists")
            self.email = email
        
        db.session.commit()
    
    def change_password(self, old_password, new_password):
        """Change user password with validation"""
        from app.utils.auth_utils import hash_password
        
        if not self.check_password(old_password):
            raise ValueError("Current password is incorrect")
        
        self.password = hash_password(new_password)
        db.session.commit()
    
    def deactivate(self):
        """Deactivate user account"""
        self.is_active = False
        db.session.commit()
    
    def activate(self):
        """Activate user account"""
        self.is_active = True
        db.session.commit()