"""
Room Model for ScanMe Attendance System
Handles room information and capacity management
"""

from app import db
from datetime import datetime
from sqlalchemy import func

class Room(db.Model):
    """
    Room model for managing classroom/venue information
    Tracks room capacity and attendance sessions
    """
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    room_name = db.Column(db.String(100), nullable=True)
    building = db.Column(db.String(50), nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=30)
    room_type = db.Column(db.String(30), nullable=False, default='classroom')  # classroom, laboratory, auditorium
    equipment = db.Column(db.Text)  # JSON string of available equipment
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='room', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('AttendanceSession', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, room_number, building, floor, capacity=30, room_type='classroom', room_name=None):
        """Initialize room with required fields"""
        self.room_number = room_number
        self.room_name = room_name  # Now optional
        self.building = building
        self.floor = floor
        self.capacity = capacity
        self.room_type = room_type
    
    def get_full_name(self):
        """Get room's full display name"""
        if self.room_name:
            return f"{self.room_number} - {self.room_name}"
        return self.room_number
    
    def get_location(self):
        """Get room's full location"""
        floor_suffix = self._get_floor_suffix(self.floor)
        return f"{self.building}, {self.floor}{floor_suffix} Floor"
    
    def _get_floor_suffix(self, floor):
        """Get appropriate suffix for floor number"""
        if 10 <= floor % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(floor % 10, 'th')
        return suffix
    
    def get_current_occupancy(self, session_id=None):
        """Get current number of students in room (session-specific or room-wide)"""
        from app.models.attendance_model import AttendanceRecord
        from datetime import date
        today = date.today()
        
        # Count unique active students in room
        query = db.session.query(AttendanceRecord.student_id)\
            .filter(AttendanceRecord.room_id == self.id)\
            .filter(AttendanceRecord.is_active == True)
        
        # If session_id provided, filter by specific session only
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        
        unique_students = query.distinct().count()
        return unique_students
    
    def get_occupancy_percentage(self, session_id=None):
        """Get current occupancy as percentage of capacity (session-specific or room-wide)"""
        current = self.get_current_occupancy(session_id)
        if self.capacity == 0:
            return 0
        return min((current / self.capacity) * 100, 100)
    
    def is_over_capacity(self, session_id=None):
        """Check if room is over capacity (session-specific or room-wide)"""
        return self.get_current_occupancy(session_id) > self.capacity
    
    def get_attendance_stats(self, start_date=None, end_date=None, session_id=None):
        """Get attendance statistics for room (session-specific or room-wide)"""
        from app.models.attendance_model import AttendanceRecord
        from app import db
        
        query = db.session.query(AttendanceRecord).filter(AttendanceRecord.room_id == self.id)
        
        # SESSION ISOLATION: Filter by specific session if provided
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        
        if start_date:
            query = query.filter(AttendanceRecord.scan_time >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.scan_time <= end_date)
        
        records = query.all()
        
        # Group by date
        daily_counts = {}
        for record in records:
            date_key = record.scan_time.date()
            if date_key not in daily_counts:
                daily_counts[date_key] = set()
            daily_counts[date_key].add(record.student_id)
        
        return {
            'total_scans': len(records),
            'unique_students': len(set(record.student_id for record in records)),
            'unique_days': len(daily_counts),
            'average_daily_attendance': sum(len(students) for students in daily_counts.values()) / len(daily_counts) if daily_counts else 0,
            'peak_attendance': max(len(students) for students in daily_counts.values()) if daily_counts else 0,
            'daily_breakdown': {str(date): len(students) for date, students in daily_counts.items()},
            'session_specific': session_id is not None
        }
    
    def get_recent_visitors(self, limit=10, session_id=None):
        """Get recent visitors to the room (session-specific or room-wide)"""
        from app.models.attendance_model import AttendanceRecord
        from app import db
        
        query = db.session.query(AttendanceRecord).filter(AttendanceRecord.room_id == self.id)
        
        # SESSION ISOLATION: Filter by specific session if provided
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        
        recent_records = query\
            .order_by(AttendanceRecord.scan_time.desc())\
            .limit(limit)\
            .all()
        
        return [{
            'student': record.student,
            'scan_time': record.scan_time,
            'is_late': record.is_late,
            'session_id': record.session_id
        } for record in recent_records]
    
    def to_dict(self):
        """Convert room to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'room_number': self.room_number,
            'room_name': self.room_name,
            'full_name': self.get_full_name(),
            'building': self.building,
            'floor': self.floor,
            'location': self.get_location(),
            'capacity': self.capacity,
            'room_type': self.room_type,
            'equipment': self.equipment,
            'description': self.description,
            'is_active': self.is_active,
            'current_occupancy': self.get_current_occupancy(),
            'occupancy_percentage': self.get_occupancy_percentage(),
            'is_over_capacity': self.is_over_capacity(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of room"""
        return f'<Room {self.room_number}: {self.room_name}>'
    
    @staticmethod
    def get_by_room_number(room_number):
        """Get room by room number"""
        return Room.query.filter_by(room_number=room_number).first()
    
    @staticmethod
    def get_active_rooms():
        """Get all active rooms"""
        return Room.query.filter_by(is_active=True).order_by(Room.building, Room.floor, Room.room_number).all()
    
    @staticmethod
    def get_by_building(building):
        """Get rooms by building"""
        return Room.query.filter_by(building=building, is_active=True)\
            .order_by(Room.floor, Room.room_number).all()
    
    @staticmethod
    def get_by_type(room_type):
        """Get rooms by type"""
        return Room.query.filter_by(room_type=room_type, is_active=True)\
            .order_by(Room.building, Room.floor, Room.room_number).all()
    
    @staticmethod
    def search_rooms(query):
        """Search rooms by number, name, or building"""
        search_term = f"%{query}%"
        return Room.query.filter(
            db.or_(
                Room.room_number.like(search_term),
                Room.room_name.like(search_term),
                Room.building.like(search_term)
            ),
            Room.is_active == True
        ).order_by(Room.building, Room.floor, Room.room_number).all()
    
    @staticmethod
    def get_buildings():
        """Get list of unique buildings"""
        buildings = db.session.query(Room.building).filter(Room.is_active == True).distinct().all()
        return [building[0] for building in buildings]
    
    @staticmethod
    def get_room_types():
        """Get list of unique room types"""
        types = db.session.query(Room.room_type).filter(Room.is_active == True).distinct().all()
        return [room_type[0] for room_type in types]
    
    def update_info(self, **kwargs):
        """Update room information"""
        allowed_fields = ['room_name', 'building', 'floor', 'capacity', 'room_type', 'equipment', 'description']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivate room"""
        self.is_active = False
        db.session.commit()
    
    def activate(self):
        """Activate room"""
        self.is_active = True
        db.session.commit()
    
    def get_capacity_status(self):
        """Get capacity status with color coding"""
        percentage = self.get_occupancy_percentage()
        
        if percentage >= 100:
            return {'status': 'full', 'color': 'danger', 'text': 'Full'}
        elif percentage >= 80:
            return {'status': 'high', 'color': 'warning', 'text': 'High'}
        elif percentage >= 50:
            return {'status': 'moderate', 'color': 'info', 'text': 'Moderate'}
        else:
            return {'status': 'low', 'color': 'success', 'text': 'Low'}