"""
Student Model for ScanMe Attendance System
Handles student information and QR code management
"""

from app import db
from datetime import datetime
import qrcode
import os
from io import BytesIO
from PIL import Image

class Student(db.Model):
    """
    Student model for managing student information and QR codes
    Each student has a unique QR code for attendance tracking
    """
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    department = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(20), nullable=False)
    year_level = db.Column(db.Integer, nullable=False)
    qr_code_data = db.Column(db.Text, nullable=False)  # Unique QR data
    qr_code_path = db.Column(db.String(255))  # Path to QR code image
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, student_no, first_name, last_name, email, department, section, year_level):
        """Initialize student with required fields and generate QR code"""
        self.student_no = student_no
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.department = department
        self.section = section
        self.year_level = year_level
        self.qr_code_data = self._generate_qr_data()
    
    def _generate_qr_data(self):
        """Generate unique QR code data for student"""
        import hashlib
        import time
        
        # Create unique data combining student info and timestamp
        data_string = f"{self.student_no}_{self.first_name}_{self.last_name}_{time.time()}"
        hash_object = hashlib.md5(data_string.encode())
        return f"SCANME_{hash_object.hexdigest()}"
    
    def generate_qr_code(self, save_to_file=True):
        """Generate QR code image for student"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            qr.add_data(self.qr_code_data)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            if save_to_file:
                # Save QR code to file
                filename = f"qr_{self.student_no}.png"
                
                # Use Flask's static folder path
                from flask import current_app
                static_folder = current_app.static_folder if current_app else 'app/static'
                qr_codes_dir = os.path.join(static_folder, 'qr_codes')
                
                # Create directory if it doesn't exist
                os.makedirs(qr_codes_dir, exist_ok=True)
                
                filepath = os.path.join(qr_codes_dir, filename)
                img.save(filepath)
                self.qr_code_path = f"qr_codes/{filename}"
                db.session.commit()
                
                return filepath
            else:
                # Return image as bytes
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                return img_byte_arr
                
        except Exception as e:
            print(f"Error generating QR code for student {self.student_no}: {e}")
            return None
    
    def get_full_name(self):
        """Get student's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_display_info(self):
        """Get formatted student information for display"""
        return {
            'name': self.get_full_name(),
            'student_no': self.student_no,
            'department': self.department,
            'section': self.section,
            'year_level': self.year_level,
            'email': self.email
        }
    
    def get_attendance_stats(self, start_date=None, end_date=None):
        """Get attendance statistics for student"""
        from app.models.attendance_model import AttendanceRecord
        
        # Create a proper query instead of using the relationship directly
        query = AttendanceRecord.query.filter(AttendanceRecord.student_id == self.id)
        
        if start_date:
            query = query.filter(AttendanceRecord.scan_time >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.scan_time <= end_date)
        
        records = query.all()
        
        return {
            'total_scans': len(records),
            'unique_days': len(set(record.scan_time.date() for record in records)),
            'rooms_visited': len(set(record.room_id for record in records)),
            'late_arrivals': len([r for r in records if r.is_late]),
            'recent_activity': sorted(records, key=lambda x: x.scan_time, reverse=True)[:10]
        }
    
    def to_dict(self):
        """Convert student to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'student_no': self.student_no,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'email': self.email,
            'department': self.department,
            'section': self.section,
            'year_level': self.year_level,
            'qr_code_data': self.qr_code_data,
            'qr_code_path': self.qr_code_path,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of student"""
        return f'<Student {self.student_no}: {self.get_full_name()}>'
    
    @staticmethod
    def get_by_student_no(student_no):
        """Get student by student number"""
        return Student.query.filter_by(student_no=student_no).first()
    
    @staticmethod
    def get_by_qr_code(qr_code_data):
        """Get student by QR code data"""
        return Student.query.filter_by(qr_code_data=qr_code_data).first()
    
    @staticmethod
    def get_active_students():
        """Get all active students"""
        return Student.query.filter_by(is_active=True).order_by(Student.last_name, Student.first_name).all()
    
    @staticmethod
    def get_by_department(department):
        """Get students by department"""
        return Student.query.filter_by(department=department, is_active=True).order_by(Student.last_name, Student.first_name).all()
    
    @staticmethod
    def get_by_section(section):
        """Get students by section"""
        return Student.query.filter_by(section=section, is_active=True).order_by(Student.last_name, Student.first_name).all()
    
    @staticmethod
    def search_students(query):
        """Search students by name, student number, or email"""
        search_term = f"%{query}%"
        return Student.query.filter(
            db.or_(
                Student.first_name.like(search_term),
                Student.last_name.like(search_term),
                Student.student_no.like(search_term),
                Student.email.like(search_term)
            ),
            Student.is_active == True
        ).order_by(Student.last_name, Student.first_name).all()
    
    def update_info(self, **kwargs):
        """Update student information"""
        allowed_fields = ['first_name', 'last_name', 'email', 'department', 'section', 'year_level']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivate student"""
        self.is_active = False
        db.session.commit()
    
    def activate(self):
        """Activate student"""
        self.is_active = True
        db.session.commit()
    
    def regenerate_qr_code(self):
        """Regenerate QR code for student"""
        self.qr_code_data = self._generate_qr_data()
        self.generate_qr_code()
        db.session.commit()