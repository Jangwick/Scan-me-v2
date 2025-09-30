"""
Attendance Models for ScanMe Attendance System
Handles attendance records and session management
"""

from app import db
from datetime import datetime, time

class AttendanceRecord(db.Model):
    """
    Attendance record model for individual scan events
    Supports time-in and time-out functionality for complete attendance tracking
    """
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=True, index=True)
    
    # Time tracking fields
    time_in = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_out = db.Column(db.DateTime, nullable=True, index=True)
    
    # Legacy field for backward compatibility
    scan_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Status tracking
    is_late = db.Column(db.Boolean, default=False, nullable=False)
    is_duplicate = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # True = student is currently in room
    
    # Scan tracking
    time_in_scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    time_out_scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Legacy field
    
    # Additional info
    notes = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # Support IPv6
    user_agent = db.Column(db.String(255))
    
    def __init__(self, student_id, room_id, scanned_by, session_id=None, is_late=False, notes=None):
        """Initialize attendance record with time-in"""
        self.student_id = student_id
        self.room_id = room_id
        self.time_in_scanned_by = scanned_by
        self.scanned_by = scanned_by  # Legacy compatibility
        self.session_id = session_id
        self.is_late = is_late
        self.notes = notes
        
        # Set time_in to current time
        current_time = datetime.utcnow()
        self.time_in = current_time
        self.scan_time = current_time  # Legacy compatibility
        
        # Mark as active (student is in room)
        self.is_active = True
        
        # Check for duplicates after setting all required fields
        # self.is_duplicate = self._check_duplicate()  # Commented out to avoid issues during init
    
    def check_and_set_duplicate_status(self):
        """Check and set duplicate status after record is properly initialized"""
        self.is_duplicate = self._check_duplicate()
        return self.is_duplicate
    
    def time_out_student(self, scanned_by_user_id):
        """Record time-out for the student"""
        if not self.is_active:
            return False, "Student is already timed out"
        
        self.time_out = datetime.utcnow()
        self.time_out_scanned_by = scanned_by_user_id
        self.is_active = False
        db.session.commit()
        return True, "Successfully timed out"
    
    def get_duration(self):
        """Get duration spent in room (in minutes)"""
        if not self.time_out:
            # Still in room - calculate current duration
            current_time = datetime.utcnow()
            duration = current_time - self.time_in
        else:
            duration = self.time_out - self.time_in
        
        return int(duration.total_seconds() / 60)
    
    def get_status(self):
        """Get current status of the attendance record"""
        if self.is_active and not self.time_out:
            return "in_room"
        elif not self.is_active and self.time_out:
            return "timed_out"
        else:
            return "unknown"
    
    def _check_duplicate(self):
        """Check if this is a duplicate time-in within a short time period"""
        from datetime import timedelta
        
        # Check for active records for same student in same room
        existing_active = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == self.student_id,
            AttendanceRecord.room_id == self.room_id,
            AttendanceRecord.is_active == True,
            AttendanceRecord.id != getattr(self, 'id', None)
        ).first()
        
        return existing_active is not None
    
    def get_scan_info(self):
        """Get formatted scan information"""
        return {
            'student': self.student.get_full_name() if self.student else 'Unknown',
            'room': self.room.get_full_name() if self.room else 'Unknown',
            'time_in': self.time_in,
            'time_out': self.time_out,
            'duration': self.get_duration(),
            'status': self.get_status(),
            'is_late': self.is_late,
            'is_duplicate': self.is_duplicate,
            'is_active': self.is_active,
            'time_in_scanner': self.time_in_scanned_by_user.username if hasattr(self, 'time_in_scanned_by_user') and self.time_in_scanned_by_user else 'System',
            'time_out_scanner': self.time_out_scanned_by_user.username if hasattr(self, 'time_out_scanned_by_user') and self.time_out_scanned_by_user else None
        }
    
    def mark_as_late(self, session_start_time=None):
        """Mark attendance as late based on session or default time"""
        if session_start_time:
            self.is_late = self.time_in > session_start_time
        else:
            # Default: mark as late if after 9:00 AM
            default_start = time(9, 0)
            time_in_only = self.time_in.time()
            self.is_late = time_in_only > default_start
        
        db.session.commit()
    
    def to_dict(self):
        """Convert attendance record to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.get_full_name() if self.student else None,
            'student_no': self.student.student_no if self.student else None,
            'room_id': self.room_id,
            'room_name': self.room.get_full_name() if self.room else None,
            'session_id': self.session_id,
            'time_in': self.time_in.isoformat(),
            'time_out': self.time_out.isoformat() if self.time_out else None,
            'scan_time': self.scan_time.isoformat(),  # Legacy compatibility
            'duration_minutes': self.get_duration(),
            'status': self.get_status(),
            'time_in_scanned_by': self.time_in_scanned_by,
            'time_out_scanned_by': self.time_out_scanned_by,
            'time_in_scanner_name': self.time_in_scanned_by_user.username if hasattr(self, 'time_in_scanned_by_user') and self.time_in_scanned_by_user else None,
            'time_out_scanner_name': self.time_out_scanned_by_user.username if hasattr(self, 'time_out_scanned_by_user') and self.time_out_scanned_by_user else None,
            'is_late': self.is_late,
            'is_duplicate': self.is_duplicate,
            'is_active': self.is_active,
            'notes': self.notes,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    def __repr__(self):
        """String representation of attendance record"""
        student_name = self.student.get_full_name() if self.student else 'Unknown'
        room_name = self.room.room_number if self.room else 'Unknown'
        status = self.get_status()
        return f'<AttendanceRecord {student_name} in {room_name} - {status}>'
    
    @staticmethod
    def get_by_student_today(student_id):
        """Get today's attendance records for a student"""
        from datetime import date
        today = date.today()
        return AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            db.func.date(AttendanceRecord.time_in) == today
        ).order_by(AttendanceRecord.time_in.desc()).all()
    
    @staticmethod
    def get_by_room_today(room_id):
        """Get today's attendance records for a room"""
        from datetime import date
        today = date.today()
        return AttendanceRecord.query.filter(
            AttendanceRecord.room_id == room_id,
            db.func.date(AttendanceRecord.time_in) == today
        ).order_by(AttendanceRecord.time_in.desc()).all()
    
    @staticmethod
    def get_active_in_room(room_id):
        """Get students currently active (timed-in) in a room"""
        return AttendanceRecord.query.filter(
            AttendanceRecord.room_id == room_id,
            AttendanceRecord.is_active == True
        ).order_by(AttendanceRecord.time_in.desc()).all()
    
    @staticmethod
    def get_student_active_record(student_id, room_id):
        """Get active attendance record for student in specific room"""
        return AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.room_id == room_id,
            AttendanceRecord.is_active == True
        ).first()
    
    @staticmethod
    def get_recent_scans(limit=50):
        """Get recent attendance scans across all rooms"""
        return AttendanceRecord.query.order_by(AttendanceRecord.time_in.desc()).limit(limit).all()
    
    @staticmethod
    def create_attendance_record(student_id, room_id, scanned_by, session_id=None, **kwargs):
        """Create new attendance record with validation"""
        record = AttendanceRecord(
            student_id=student_id,
            room_id=room_id,
            scanned_by=scanned_by,
            session_id=session_id,
            **kwargs
        )
        
        db.session.add(record)
        db.session.commit()
        
        return record

class AttendanceSession(db.Model):
    """
    Attendance session model for managing class/meeting sessions
    Groups attendance records by session for better organization
    """
    __tablename__ = 'attendance_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    session_name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100))
    instructor = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    expected_students = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy=True)
    
    def __init__(self, room_id, session_name, start_time, end_time, created_by, 
                 subject=None, instructor=None, expected_students=0):
        """Initialize attendance session"""
        self.room_id = room_id
        self.session_name = session_name
        self.subject = subject
        self.instructor = instructor
        self.start_time = start_time
        self.end_time = end_time
        self.expected_students = expected_students
        self.created_by = created_by
    
    def is_current_session(self):
        """Check if session is currently active"""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time and self.is_active
    
    def get_attendance_count(self):
        """Get the count of unique students who attended this session"""
        unique_students = len(set(record.student_id for record in self.attendance_records))
        return unique_students
    
    def get_attendance_summary(self):
        """Get attendance summary for this session"""
        total_scans = len(self.attendance_records)
        unique_students = len(set(record.student_id for record in self.attendance_records))
        late_arrivals = len([record for record in self.attendance_records if record.is_late])
        duplicates = len([record for record in self.attendance_records if record.is_duplicate])
        
        attendance_rate = 0
        if self.expected_students > 0:
            attendance_rate = (unique_students / self.expected_students) * 100
        
        return {
            'total_scans': total_scans,
            'unique_students': unique_students,
            'late_arrivals': late_arrivals,
            'duplicates': duplicates,
            'expected_students': self.expected_students,
            'attendance_rate': round(attendance_rate, 2)
        }
    
    def get_session_status(self):
        """Get current session status"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return 'inactive'
        elif now < self.start_time:
            return 'scheduled'
        elif now > self.end_time:
            return 'completed'
        else:
            return 'active'
    
    def get_status(self):
        """Alias for get_session_status for template compatibility"""
        return self.get_session_status()
    
    def get_status_class(self):
        """Get CSS class for session status"""
        status = self.get_session_status()
        status_classes = {
            'active': 'status-active',
            'scheduled': 'status-scheduled', 
            'completed': 'status-completed',
            'inactive': 'status-inactive'
        }
        return status_classes.get(status, 'status-unknown')
    
    def is_session_active(self):
        """Check if session is currently active (method for templates)"""
        # Access the database column value directly  
        active_status = getattr(self, 'is_active', True)
        return active_status and self.get_session_status() == 'active'
    
    def to_dict(self):
        """Convert session to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_name': self.room.get_full_name() if self.room else None,
            'session_name': self.session_name,
            'subject': self.subject,
            'instructor': self.instructor,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'expected_students': self.expected_students,
            'is_active': self.is_active,
            'status': self.get_session_status(),
            'attendance_summary': self.get_attendance_summary(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        """String representation of attendance session"""
        return f'<AttendanceSession {self.session_name} in {self.room.room_number if self.room else "Unknown"}>'
    
    @staticmethod
    def get_active_sessions():
        """Get all active sessions"""
        return AttendanceSession.query.filter_by(is_active=True)\
            .order_by(AttendanceSession.start_time).all()
    
    @staticmethod
    def get_current_sessions():
        """Get currently running sessions"""
        now = datetime.utcnow()
        return AttendanceSession.query.filter(
            AttendanceSession.start_time <= now,
            AttendanceSession.end_time >= now,
            AttendanceSession.is_active == True
        ).all()
    
    @staticmethod
    def get_sessions_by_room(room_id, start_date=None, end_date=None):
        """Get sessions for a specific room"""
        query = AttendanceSession.query.filter_by(room_id=room_id)
        
        if start_date:
            query = query.filter(AttendanceSession.start_time >= start_date)
        if end_date:
            query = query.filter(AttendanceSession.end_time <= end_date)
        
        return query.order_by(AttendanceSession.start_time.desc()).all()
    
    def close_session(self):
        """Close/deactivate session"""
        self.is_active = False
        db.session.commit()
    
    def reopen_session(self):
        """Reopen/reactivate session"""
        self.is_active = True
        db.session.commit()