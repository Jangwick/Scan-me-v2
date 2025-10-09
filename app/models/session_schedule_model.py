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
        """Check if session is currently active with proper timezone handling"""
        if self.status not in [SessionStatus.SCHEDULED, SessionStatus.ACTIVE]:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        session_end = self.get_session_end_datetime()
        
        # Include grace period for attendance (15 minutes before and after)
        grace_period = timedelta(minutes=15)
        attendance_window_start = session_start - grace_period
        attendance_window_end = session_end + grace_period
        
        return attendance_window_start <= now <= attendance_window_end
    
    def can_time_in(self):
        """Check if students can time in to this session"""
        if not self.qr_code_active or self.status not in [SessionStatus.SCHEDULED, SessionStatus.ACTIVE]:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        session_end = self.get_session_end_datetime()
        
        # Can time in from 15 minutes before session until 15 minutes after session ends (grace period)
        grace_period = timedelta(minutes=15)
        time_in_start = session_start - grace_period
        time_in_end = session_end + grace_period  # Extended to include grace period
        
        return time_in_start <= now <= time_in_end
    
    def can_time_out(self):
        """Check if students can time out from this session"""
        if not self.qr_code_active or self.status not in [SessionStatus.SCHEDULED, SessionStatus.ACTIVE]:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        session_end = self.get_session_end_datetime()
        
        # Can time out from session start until 15 minutes after session ends
        grace_period = timedelta(minutes=15)
        time_out_start = session_start
        time_out_end = session_end + grace_period
        
        return time_out_start <= now <= time_out_end
    
    def process_student_attendance(self, student_id, scanned_by_user_id):
        """
        Process student attendance for this session using new logic
        Returns: dict with success, message, and action
        """
        try:
            from app.services.new_attendance_service import NewAttendanceService
            from app.models import Student, Room
            
            # Get required entities
            student = Student.query.get(student_id)
            room = Room.query.get(self.room_id)
            
            if not student or not room:
                return {
                    'success': False,
                    'message': 'Student or room not found',
                    'action': 'error'
                }
            
            # Use the new attendance service
            service = NewAttendanceService()
            result = service.process_session_schedule_attendance(
                student_id=student_id,
                session_schedule=self,
                scanned_by=scanned_by_user_id
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing attendance: {str(e)}',
                'action': 'error'
            }
    
    def get_student_attendance_status(self, student_id):
        """
        Get student's attendance status for this session
        Returns: dict with status, time_in, time_out info
        """
        try:
            from app.models import AttendanceRecord
            
            # Look for attendance record for this student in this session
            record = AttendanceRecord.query.filter_by(
                student_id=student_id,
                schedule_session_id=self.id
            ).first()
            
            if not record:
                return {
                    'status': 'not_attended',
                    'time_in': None,
                    'time_out': None,
                    'duration': 0
                }
            
            if record.time_out:
                return {
                    'status': 'completed',
                    'time_in': record.time_in,
                    'time_out': record.time_out,
                    'duration': record.get_duration()
                }
            else:
                return {
                    'status': 'timed_in',
                    'time_in': record.time_in,
                    'time_out': None,
                    'duration': record.get_duration()  # Current duration
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_session_attendance_summary(self):
        """
        Get attendance summary for this session
        Returns: dict with counts and statistics
        """
        try:
            from app.models import AttendanceRecord, Student
            
            # Get all attendance records for this session
            records = AttendanceRecord.query.filter_by(schedule_session_id=self.id).all()
            
            total_students = len(records)
            completed_attendance = len([r for r in records if r.time_out is not None])
            currently_in_session = len([r for r in records if r.time_out is None])
            late_arrivals = len([r for r in records if r.is_late])
            
            # Calculate average duration for completed attendances
            completed_records = [r for r in records if r.time_out is not None]
            avg_duration = 0
            if completed_records:
                total_duration = sum(r.get_duration() for r in completed_records)
                avg_duration = total_duration / len(completed_records)
            
            return {
                'total_students': total_students,
                'completed_attendance': completed_attendance,
                'currently_in_session': currently_in_session,
                'late_arrivals': late_arrivals,
                'average_duration_minutes': round(avg_duration, 1),
                'attendance_rate': round((completed_attendance / max(total_students, 1)) * 100, 1)
            }
            
        except Exception as e:
            return {
                'total_students': 0,
                'completed_attendance': 0,
                'currently_in_session': 0,
                'late_arrivals': 0,
                'average_duration_minutes': 0,
                'attendance_rate': 0,
                'error': str(e)
            }
    
    def can_take_attendance(self):
        """Check if attendance can be taken (within attendance window)"""
        if not self.qr_code_active or self.status not in [SessionStatus.SCHEDULED, SessionStatus.ACTIVE]:
            return False
        
        now = datetime.now()
        session_start = self.get_session_datetime()
        session_end = self.get_session_end_datetime()
        
        # Allow attendance from 15 minutes before until 15 minutes after session
        grace_before = timedelta(minutes=15)
        grace_after = timedelta(minutes=15)
        attendance_start = session_start - grace_before
        attendance_end = session_end + grace_after
        
        return attendance_start <= now <= attendance_end
    
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