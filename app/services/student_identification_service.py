"""
Student Identification Service for QR Attendance System
Handles comprehensive student lookup with edge case management
"""

from app import db
from app.models.student_model import Student
from sqlalchemy import or_, func
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class StudentIdentificationService:
    """Service for handling student identification edge cases"""
    
    @staticmethod
    def find_student_by_qr_data(validated_qr_data):
        """
        Find student by validated QR data with comprehensive edge case handling
        
        Args:
            validated_qr_data (dict): Pre-validated QR data from validate_qr_data()
            
        Returns:
            tuple: (student_object, error_info)
                student_object: Student instance or None
                error_info: dict with error details or None
        """
        try:
            if validated_qr_data.get('legacy') or validated_qr_data.get('type') == 'scanme_qr_code':
                return StudentIdentificationService._handle_legacy_lookup(validated_qr_data)
            else:
                return StudentIdentificationService._handle_structured_lookup(validated_qr_data)
                
        except Exception as e:
            logger.error(f"Error in student identification: {str(e)}")
            return None, {
                'error': f'Student identification failed: {str(e)}',
                'error_code': 'IDENTIFICATION_ERROR'
            }
    
    @staticmethod
    def _handle_legacy_lookup(validated_qr_data):
        """Handle legacy QR code format and SCANME_ format"""
        if validated_qr_data.get('type') == 'scanme_qr_code':
            # This is our SCANME_ QR code format
            qr_data = validated_qr_data.get('qr_data')
            
            if not qr_data:
                return None, {
                    'error': 'SCANME QR code missing data',
                    'error_code': 'MISSING_QR_DATA'
                }
            
            # Look up student by QR code data
            student = Student.query.filter_by(qr_code_data=qr_data).first()
            
            if not student:
                logger.warning(f"No student found for QR data: {qr_data}")
                return None, {
                    'error': f'No student found with QR code: {qr_data[:20]}...',
                    'error_code': 'STUDENT_NOT_FOUND'
                }
            
            return student, None
        
        else:
            # Legacy student number lookup
            student_no = validated_qr_data.get('student_no')
            
            if not student_no:
                return None, {
                    'error': 'Legacy QR code missing student number',
                    'error_code': 'MISSING_STUDENT_NO'
                }
            
            # Edge Case: Case sensitivity handling
            student = Student.query.filter(
                func.lower(Student.student_no) == func.lower(student_no)
            ).first()
            
            # Edge Case: Multiple students with similar numbers
            if not student:
                similar_students = Student.query.filter(
                    Student.student_no.like(f'%{student_no}%')
                ).all()
                
                if len(similar_students) == 1:
                    logger.info(f"Found similar student number match: {similar_students[0].student_no} for {student_no}")
                    student = similar_students[0]
                elif len(similar_students) > 1:
                    logger.warning(f"Multiple similar student numbers found for {student_no}")
                    return None, {
                        'error': f'Multiple students found with similar numbers to {student_no}',
                        'error_code': 'MULTIPLE_SIMILAR_STUDENTS',
                        'similar_count': len(similar_students)
                    }
            
            return student, None
    
    @staticmethod
    def _handle_structured_lookup(validated_qr_data):
        """Handle structured QR code format (JSON)"""
        student_id = validated_qr_data.get('student_id')
        student_no = validated_qr_data.get('student_no')
        email = validated_qr_data.get('email')
        name = validated_qr_data.get('name')
        
        # Build lookup query with multiple strategies
        lookup_conditions = []
        
        # Strategy 1: Student ID lookup
        if student_id:
            if isinstance(student_id, int):
                lookup_conditions.append(Student.id == student_id)
            elif isinstance(student_id, str) and student_id.isdigit():
                lookup_conditions.append(Student.id == int(student_id))
            
        # Strategy 2: Student number lookup (with case insensitivity)
        if student_no:
            lookup_conditions.append(func.lower(Student.student_no) == func.lower(str(student_no)))
        
        # Strategy 3: Email lookup (with case insensitivity)
        if email:
            lookup_conditions.append(func.lower(Student.email) == func.lower(email))
        
        if not lookup_conditions:
            return None, {
                'error': 'QR code does not contain sufficient identification data',
                'error_code': 'INSUFFICIENT_LOOKUP_DATA'
            }
        
        # Execute lookup
        student = Student.query.filter(or_(*lookup_conditions)).first()
        
        # Edge Case: Multiple matches
        if not student and len(lookup_conditions) > 1:
            # Try individual conditions to identify conflicts
            for condition in lookup_conditions:
                matches = Student.query.filter(condition).all()
                if len(matches) > 1:
                    logger.warning(f"Multiple students match condition: {condition}")
                    return None, {
                        'error': 'Multiple students match the provided information',
                        'error_code': 'MULTIPLE_MATCHES'
                    }
        
        # Edge Case: Name verification if student found
        if student and name:
            qr_name_lower = name.lower().strip()
            student_name_lower = student.get_full_name().lower()
            
            # Check if names are reasonably similar
            if qr_name_lower not in student_name_lower and student_name_lower not in qr_name_lower:
                logger.warning(f"Name mismatch: QR={name}, DB={student.get_full_name()}")
                # Don't fail here, but log for investigation
        
        return student, None
    
    @staticmethod
    def create_student_from_qr_data(validated_qr_data):
        """
        Create a new student from QR data with edge case handling
        
        Args:
            validated_qr_data (dict): Validated QR data
            
        Returns:
            tuple: (student_object, error_info)
        """
        try:
            if validated_qr_data.get('legacy'):
                return StudentIdentificationService._create_legacy_student(validated_qr_data)
            else:
                return StudentIdentificationService._create_structured_student(validated_qr_data)
                
        except Exception as e:
            logger.error(f"Error creating student: {str(e)}")
            return None, {
                'error': f'Failed to create student: {str(e)}',
                'error_code': 'CREATION_ERROR'
            }
    
    @staticmethod
    def _create_legacy_student(validated_qr_data):
        """Create student from legacy QR data"""
        student_no = validated_qr_data.get('student_no')
        
        # Edge Case: Check for existing student_no
        existing = Student.query.filter_by(student_no=student_no).first()
        if existing:
            return None, {
                'error': f'Student number {student_no} already exists',
                'error_code': 'DUPLICATE_STUDENT_NO'
            }
        
        # Generate basic information
        suffix = str(student_no)[-3:] if len(str(student_no)) >= 3 else str(student_no)
        first_name = "Student"
        last_name = suffix
        base_email = f"student{suffix}@university.edu"
        
        # Edge Case: Handle email conflicts
        email = StudentIdentificationService._generate_unique_email(base_email)
        
        student = Student(
            student_no=student_no,
            first_name=first_name,
            last_name=last_name,
            email=email,
            department="General",
            section="Auto-Generated",
            year_level=1
        )
        
        db.session.add(student)
        db.session.flush()  # Get ID without full commit
        
        logger.info(f"Created legacy student: {student.get_full_name()} ({student_no})")
        return student, None
    
    @staticmethod
    def _create_structured_student(validated_qr_data):
        """Create student from structured QR data"""
        # Extract required fields
        student_no = validated_qr_data.get('student_no')
        name = validated_qr_data.get('name', 'Unknown Student')
        department = validated_qr_data.get('department', 'General')
        section = validated_qr_data.get('section', 'Unknown')
        year_level = validated_qr_data.get('year_level', 1)
        
        # Edge Case: Parse name into first/last
        name_parts = name.strip().split()
        if len(name_parts) >= 2:
            first_name = ' '.join(name_parts[:-1])
            last_name = name_parts[-1]
        else:
            first_name = name
            last_name = "Unknown"
        
        # Edge Case: Check for existing student_no
        existing = Student.query.filter_by(student_no=student_no).first()
        if existing:
            return None, {
                'error': f'Student number {student_no} already exists',
                'error_code': 'DUPLICATE_STUDENT_NO'
            }
        
        # Generate email if not provided
        email = validated_qr_data.get('email')
        if not email:
            base_email = f"{first_name.lower().replace(' ', '.')}.{last_name.lower()}@university.edu"
            email = StudentIdentificationService._generate_unique_email(base_email)
        else:
            # Edge Case: Check email conflicts
            existing_email = Student.query.filter_by(email=email).first()
            if existing_email:
                return None, {
                    'error': f'Email {email} already exists',
                    'error_code': 'DUPLICATE_EMAIL'
                }
        
        student = Student(
            student_no=student_no,
            first_name=first_name,
            last_name=last_name,
            email=email,
            department=department,
            section=section,
            year_level=year_level
        )
        
        db.session.add(student)
        db.session.flush()  # Get ID without full commit
        
        logger.info(f"Created structured student: {student.get_full_name()} ({student_no})")
        return student, None
    
    @staticmethod
    def _generate_unique_email(base_email):
        """Generate unique email address"""
        email = base_email
        counter = 1
        
        while Student.query.filter_by(email=email).first():
            name_part, domain = base_email.rsplit('@', 1)
            email = f"{name_part}{counter}@{domain}"
            counter += 1
            
            # Edge Case: Prevent infinite loop
            if counter > 1000:
                timestamp = datetime.now().strftime('%H%M%S')
                email = f"{name_part}_{timestamp}@{domain}"
                break
        
        return email
    
    @staticmethod
    def validate_student_for_attendance(student):
        """
        Validate student for attendance recording
        
        Args:
            student: Student object
            
        Returns:
            tuple: (is_valid, error_info)
        """
        if not student:
            return False, {
                'error': 'No student provided',
                'error_code': 'NO_STUDENT'
            }
        
        # Edge Case: Inactive student
        if not student.is_active:
            return False, {
                'error': f'Student {student.get_full_name()} is not active',
                'error_code': 'INACTIVE_STUDENT'
            }
        
        # Edge Case: Missing required fields
        if not student.student_no or not student.email:
            return False, {
                'error': 'Student missing required information',
                'error_code': 'INCOMPLETE_STUDENT_DATA'
            }
        
        return True, None
    
    @staticmethod
    def log_identification_attempt(qr_data, student, success, error_info=None):
        """Log student identification attempts for debugging"""
        if success:
            logger.info(f"Student identification successful: {student.get_full_name()} ({student.student_no})")
        else:
            logger.warning(f"Student identification failed: {error_info.get('error', 'Unknown error')} for QR: {qr_data[:50]}...")