"""
Session Schedule Model for ScanMe Attendance System
Handles room scheduling and session management
"""

from app import db
from datetime import datetime, date, time, timedelta
import enum

class SessionStatus(enum.Enum):
    """Session status enumeration"""
    SCHEDULED = 'scheduled'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    POSTPONED = 'postponed'

class RecurrenceType(enum.Enum):
    """Recurrence pattern enumeration"""
    NONE = 'none'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    BIWEEKLY = 'biweekly'
    MONTHLY = 'monthly'
    CUSTOM = 'custom'

class SessionSchedule(db.Model):
    """
    Session Schedule model for managing scheduled room sessions
    Handles timing, recurrence, and session details
    """
    __tablename__ = 'session_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Session Details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Room and User Associations
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Date and Time
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Duration (calculated field, stored for quick access)
    duration_minutes = db.Column(db.Integer, nullable=False)
    
    # Recurrence Settings
    recurrence_type = db.Column(db.Enum(RecurrenceType), default=RecurrenceType.NONE, nullable=False)
    recurrence_end_date = db.Column(db.Date)  # When recurrence ends
    recurrence_interval = db.Column(db.Integer, default=1)  # Every N days/weeks/months
    recurrence_days_of_week = db.Column(db.String(20))  # For weekly: "1,3,5" (Mon,Wed,Fri)
    
    # Status and Metadata
    status = db.Column(db.Enum(SessionStatus), default=SessionStatus.SCHEDULED, nullable=False)
    max_attendees = db.Column(db.Integer)  # Override room capacity if needed
    is_mandatory = db.Column(db.Boolean, default=False, nullable=False)
    requires_registration = db.Column(db.Boolean, default=False, nullable=False)
    
    # QR Code and Attendance
    qr_code_active = db.Column(db.Boolean, default=True, nullable=False)
    attendance_window_minutes = db.Column(db.Integer, default=15)  # How long QR is active
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='scheduled_sessions')
    instructor = db.relationship('User', backref='scheduled_sessions')
    # Note: attendance_records relationship will be added when we have session_schedule_id in AttendanceRecord
    
    def __init__(self, title, room_id, instructor_id, session_date, start_time, end_time, **kwargs):
        """Initialize session schedule"""
        self.title = title
        self.room_id = room_id
        self.instructor_id = instructor_id
        self.session_date = session_date
        self.start_time = start_time
        self.end_time = end_time
        
        # Calculate duration
        self.duration_minutes = self._calculate_duration(start_time, end_time)
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _calculate_duration(self, start_time, end_time):
        """Calculate session duration in minutes"""
        start_datetime = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        
        # Handle sessions that cross midnight
        if end_datetime < start_datetime:
            end_datetime = datetime.combine(date.today() + timedelta(days=1), end_time)
        
        duration = end_datetime - start_datetime
        return int(duration.total_seconds() / 60)
    
    def get_session_datetime(self):
        """Get session start as datetime object"""
        return datetime.combine(self.session_date, self.start_time)
    
    def get_session_end_datetime(self):
        """Get session end as datetime object"""
        session_end = datetime.combine(self.session_date, self.end_time)
        # Handle sessions that cross midnight
        if self.end_time < self.start_time:
            session_end += timedelta(days=1)
        return session_end
    
    def is_active_now(self):
        """Check if session is currently active"""
        if self.status != SessionStatus.SCHEDULED:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        session_end = self.get_session_end_datetime()
        
        return session_start <= now <= session_end
    
    def can_take_attendance(self):
        """Check if attendance can be taken (within attendance window)"""
        if not self.qr_code_active:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        attendance_end = session_start + timedelta(minutes=self.attendance_window_minutes)
        
        return session_start <= now <= attendance_end
    
    def get_formatted_time(self):
        """Get formatted time range"""
        start_str = self.start_time.strftime('%I:%M %p')
        end_str = self.end_time.strftime('%I:%M %p')
        return f"{start_str} - {end_str}"
    
    def get_formatted_date(self):
        """Get formatted date"""
        return self.session_date.strftime('%B %d, %Y')
    
    def get_status_display(self):
        """Get human-readable status"""
        if not hasattr(self, 'status') or self.status is None:
            return 'Scheduled'  # Default status
            
        status_map = {
            SessionStatus.SCHEDULED: 'Scheduled',
            SessionStatus.ACTIVE: 'Active',
            SessionStatus.COMPLETED: 'Completed',
            SessionStatus.CANCELLED: 'Cancelled',
            SessionStatus.POSTPONED: 'Postponed'
        }
        return status_map.get(self.status, 'Unknown')
    
    def get_recurrence_display(self):
        """Get human-readable recurrence pattern"""
        if not hasattr(self, 'recurrence_type') or self.recurrence_type is None:
            return 'One-time session'
            
        if self.recurrence_type == RecurrenceType.NONE:
            return 'One-time session'
        elif self.recurrence_type == RecurrenceType.DAILY:
            return f'Daily (every {self.recurrence_interval} day{"s" if self.recurrence_interval > 1 else ""})'
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return f'Weekly (every {self.recurrence_interval} week{"s" if self.recurrence_interval > 1 else ""})'
        elif self.recurrence_type == RecurrenceType.BIWEEKLY:
            return 'Every 2 weeks'
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            return f'Monthly (every {self.recurrence_interval} month{"s" if self.recurrence_interval > 1 else ""})'
        else:
            return 'Custom pattern'
    
    def generate_recurring_sessions(self):
        """Generate recurring session instances (returns list of session data)"""
        if self.recurrence_type == RecurrenceType.NONE or not self.recurrence_end_date:
            return []
        
        sessions = []
        current_date = self.session_date
        end_date = self.recurrence_end_date
        
        while current_date <= end_date:
            if self.recurrence_type == RecurrenceType.DAILY:
                current_date += timedelta(days=self.recurrence_interval)
            elif self.recurrence_type == RecurrenceType.WEEKLY:
                current_date += timedelta(weeks=self.recurrence_interval)
            elif self.recurrence_type == RecurrenceType.BIWEEKLY:
                current_date += timedelta(weeks=2)
            elif self.recurrence_type == RecurrenceType.MONTHLY:
                # Add months (approximate)
                current_date += timedelta(days=30 * self.recurrence_interval)
            
            if current_date <= end_date:
                session_data = {
                    'title': self.title,
                    'description': self.description,
                    'room_id': self.room_id,
                    'instructor_id': self.instructor_id,
                    'session_date': current_date,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'status': SessionStatus.SCHEDULED,
                    'max_attendees': self.max_attendees,
                    'is_mandatory': self.is_mandatory,
                    'requires_registration': self.requires_registration,
                    'qr_code_active': self.qr_code_active,
                    'attendance_window_minutes': self.attendance_window_minutes
                }
                sessions.append(session_data)
        
        return sessions
    
    def get_capacity(self):
        """Get effective capacity (room capacity or override)"""
        if not self.room:
            return self.max_attendees or 0
            
        room_capacity = getattr(self.room, 'capacity', 0)
        if self.max_attendees:
            return min(self.max_attendees, room_capacity)
        return room_capacity
    
    def get_attendance_count(self):
        """Get current attendance count - will implement when relationships are set up"""
        # TODO: Implement when session_schedule_id is added to AttendanceRecord
        return 0
    
    def is_full(self):
        """Check if session is at capacity"""
        return self.get_attendance_count() >= self.get_capacity()
    
    def __repr__(self):
        return f'<SessionSchedule {self.title} - {self.session_date} {self.start_time}>'