"""
Attendance Event Model for ScanMe Attendance System
Tracks individual scan events (time-in and time-out actions separately)
"""

from app import db
from datetime import datetime

class AttendanceEvent(db.Model):
    """
    Individual attendance event model for tracking each scan action
    Each time-in and time-out is recorded as a separate event
    """
    __tablename__ = 'attendance_events'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=True, index=True)
    attendance_record_id = db.Column(db.Integer, db.ForeignKey('attendance_records.id'), nullable=True, index=True)
    
    # Event details
    event_type = db.Column(db.String(20), nullable=False, index=True)  # 'time_in' or 'time_out'
    event_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    scanned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Additional info
    is_late = db.Column(db.Boolean, default=False, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True)  # For time-out events
    notes = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='attendance_events')
    room = db.relationship('Room', backref='attendance_events')
    session = db.relationship('AttendanceSession', backref='attendance_events')
    scanner = db.relationship('User', backref='scanned_events')
    attendance_record = db.relationship('AttendanceRecord', backref='events')
    
    def __init__(self, student_id, room_id, event_type, scanned_by, session_id=None, 
                 attendance_record_id=None, is_late=False, duration_minutes=None, 
                 ip_address=None, user_agent=None, notes=None):
        """Initialize attendance event"""
        self.student_id = student_id
        self.room_id = room_id
        self.event_type = event_type
        self.scanned_by = scanned_by
        self.session_id = session_id
        self.attendance_record_id = attendance_record_id
        self.is_late = is_late
        self.duration_minutes = duration_minutes
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.notes = notes
    
    @staticmethod
    def get_recent_events(limit=10):
        """Get recent attendance events"""
        return AttendanceEvent.query\
            .order_by(AttendanceEvent.event_time.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_events_for_session(session_id, limit=50):
        """Get events for a specific session"""
        return AttendanceEvent.query\
            .filter_by(session_id=session_id)\
            .order_by(AttendanceEvent.event_time.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_student_events(student_id, room_id=None, limit=20):
        """Get events for a specific student"""
        query = AttendanceEvent.query.filter_by(student_id=student_id)
        if room_id:
            query = query.filter_by(room_id=room_id)
        return query.order_by(AttendanceEvent.event_time.desc()).limit(limit).all()
    
    def to_dict(self):
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_time': self.event_time.isoformat(),
            'student_id': self.student_id,
            'student_name': self.student.get_full_name() if self.student else None,
            'student_no': self.student.student_no if self.student else None,
            'room_id': self.room_id,
            'room_name': self.room.room_name or self.room.room_number if self.room else None,
            'session_id': self.session_id,
            'is_late': self.is_late,
            'duration_minutes': self.duration_minutes,
            'scanned_by': self.scanned_by,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<AttendanceEvent {self.id}: {self.event_type} - {self.student_id} in {self.room_id}>'