"""
Error Log Model for ScanMe Attendance System
Tracks system errors for monitoring and debugging
"""

from app import db
from datetime import datetime, timedelta

class ErrorLog(db.Model):
    """
    Error log model for tracking system errors and debugging
    """
    __tablename__ = 'error_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(50), nullable=False, index=True)
    error_data = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __init__(self, error_type, error_data):
        """Initialize error log"""
        self.error_type = error_type
        self.error_data = error_data
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'error_type': self.error_type,
            'error_data': self.error_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by
        }
    
    def mark_resolved(self, user_id=None):
        """Mark error as resolved"""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
        db.session.commit()
    
    @staticmethod
    def get_recent_errors(hours=24, limit=100):
        """Get recent errors"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return ErrorLog.query.filter(
            ErrorLog.created_at >= cutoff
        ).order_by(
            ErrorLog.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_error_counts_by_type(hours=24):
        """Get error counts by type"""
        from sqlalchemy import func
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return db.session.query(
            ErrorLog.error_type,
            func.count(ErrorLog.id).label('count')
        ).filter(
            ErrorLog.created_at >= cutoff
        ).group_by(ErrorLog.error_type).all()
    
    def __repr__(self):
        """String representation"""
        return f'<ErrorLog {self.error_type} at {self.created_at}>'