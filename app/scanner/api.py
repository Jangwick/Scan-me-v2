"""
API routes for scanner functionality
"""
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, time
import base64
import io
from PIL import Image
import json
import uuid

from app.models import db, Student, Session, Room, Attendance
from app.auth.decorators import login_required

api = Blueprint('scanner_api', __name__)

@api.route('/sessions')
@login_required
def get_sessions():
    """Get all active sessions for today"""
    try:
        today = datetime.now().date()
        current_time = datetime.now().time()
        
        sessions = Session.query.join(Room).filter(
            Session.date == today
        ).all()
        
        session_data = []
        for session in sessions:
            # Check if session is currently active (within 30 minutes of start time)
            session_start = datetime.combine(today, session.start_time)
            session_end = datetime.combine(today, session.end_time)
            now = datetime.now()
            
            is_active = (
                session_start - timedelta(minutes=30) <= now <= 
                session_end + timedelta(minutes=30)
            )
            
            session_data.append({
                'id': session.id,
                'name': session.name,
                'room_name': session.room.name,
                'start_time': session.start_time.strftime('%H:%M'),
                'end_time': session.end_time.strftime('%H:%M'),
                'is_active': is_active,
                'capacity': session.capacity
            })
        
        # Sort by start time, active sessions first
        session_data.sort(key=lambda x: (not x['is_active'], x['start_time']))
        
        return jsonify(session_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify([]), 500

@api.route('/scan-qr', methods=['POST'])
@login_required
def scan_qr_code():
    """Process a scanned QR code"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data', '').strip()
        session_id = data.get('session_id')
        
        if not qr_data:
            return jsonify({'success': False, 'message': 'No QR code data provided'})
            
        if not session_id:
            return jsonify({'success': False, 'message': 'No session selected'})
        
        # Get the session
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'message': 'Invalid session'})
        
        # Parse QR code data - could be student ID, JSON, or other format
        student = None
        
        # Try to parse as JSON first (if QR code contains structured data)
        try:
            qr_json = json.loads(qr_data)
            student_id = qr_json.get('student_id') or qr_json.get('id')
        except (json.JSONDecodeError, ValueError):
            # Treat as plain student ID
            student_id = qr_data
        
        # Find student by ID, email, or student number
        student = Student.query.filter(
            or_(
                Student.student_id == student_id,
                Student.email == student_id,
                Student.id == student_id
            )
        ).first()
        
        # If no student found, try creating one (if QR has enough data)
        if not student:
            # For demo purposes, create a mock student
            if student_id and len(student_id) >= 3:
                # Generate a name from the ID for demo
                mock_name = f"Student {student_id[-3:]}"
                mock_email = f"student{student_id[-3:]}@university.edu"
                
                student = Student(
                    name=mock_name,
                    email=mock_email,
                    student_id=student_id,
                    phone="000-000-0000",
                    department="General"
                )
                db.session.add(student)
                db.session.commit()
            else:
                return jsonify({'success': False, 'message': 'Invalid QR code format'})
        
        # Check if already scanned today for this session
        today = datetime.now().date()
        existing_attendance = Attendance.query.filter(
            and_(
                Attendance.student_id == student.id,
                Attendance.session_id == session.id,
                func.date(Attendance.timestamp) == today
            )
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False, 
                'message': f'{student.name} already marked present for this session',
                'student_name': student.name
            })
        
        # Determine if late
        now = datetime.now()
        session_start = datetime.combine(today, session.start_time)
        is_late = now > (session_start + timedelta(minutes=10))  # 10-minute grace period
        
        # Create attendance record
        attendance = Attendance(
            student_id=student.id,
            session_id=session.id,
            timestamp=now,
            status='present',
            is_late=is_late
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully marked {student.name} as present' + (' (Late)' if is_late else ''),
            'student_name': student.name,
            'is_late': is_late,
            'timestamp': now.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing QR scan: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to process scan'})

@api.route('/scan-image', methods=['POST'])
@login_required
def scan_image():
    """Process an uploaded image containing a QR code"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image uploaded'})
        
        file = request.files['image']
        session_id = request.form.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'No session selected'})
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
        
        # For demo purposes, simulate QR code detection from image
        # In production, you'd use a QR code detection library like pyzbar
        
        # Simulate processing delay
        import time
        time.sleep(1)
        
        # Mock QR data extraction (in real implementation, decode QR from image)
        mock_qr_data = f"STU{str(uuid.uuid4())[:3].upper()}"
        
        # Process the extracted QR data
        return scan_qr_code_data(mock_qr_data, session_id)
        
    except Exception as e:
        current_app.logger.error(f"Error processing image scan: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to process image'})

def scan_qr_code_data(qr_data, session_id):
    """Helper function to process QR data (used by both endpoints)"""
    try:
        # Get the session
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'message': 'Invalid session'})
        
        # Find or create student
        student = Student.query.filter(
            or_(
                Student.student_id == qr_data,
                Student.email == qr_data
            )
        ).first()
        
        if not student:
            # Create mock student for demo
            mock_name = f"Student {qr_data[-3:]}"
            mock_email = f"student{qr_data[-3:]}@university.edu"
            
            student = Student(
                name=mock_name,
                email=mock_email,
                student_id=qr_data,
                phone="000-000-0000",
                department="General"
            )
            db.session.add(student)
            db.session.commit()
        
        # Check for existing attendance
        today = datetime.now().date()
        existing_attendance = Attendance.query.filter(
            and_(
                Attendance.student_id == student.id,
                Attendance.session_id == session.id,
                func.date(Attendance.timestamp) == today
            )
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False, 
                'message': f'{student.name} already marked present',
                'student_name': student.name
            })
        
        # Create attendance
        now = datetime.now()
        session_start = datetime.combine(today, session.start_time)
        is_late = now > (session_start + timedelta(minutes=10))
        
        attendance = Attendance(
            student_id=student.id,
            session_id=session.id,
            timestamp=now,
            status='present',
            is_late=is_late
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully scanned {student.name}',
            'student_name': student.name,
            'is_late': is_late
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in scan_qr_code_data: {str(e)}")
        return jsonify({'success': False, 'message': 'Processing failed'})

@api.route('/recent-scans')
@login_required
def get_recent_scans():
    """Get recent attendance scans"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        recent_scans = db.session.query(
            Attendance.timestamp,
            Attendance.is_late,
            Student.name.label('student_name'),
            Room.name.label('room_name'),
            Session.name.label('session_name')
        ).join(
            Student, Attendance.student_id == Student.id
        ).join(
            Session, Attendance.session_id == Session.id
        ).join(
            Room, Session.room_id == Room.id
        ).order_by(
            Attendance.timestamp.desc()
        ).limit(limit).all()
        
        scans_data = []
        for scan in recent_scans:
            time_ago = get_time_ago(scan.timestamp)
            scans_data.append({
                'student_name': scan.student_name,
                'room_name': scan.room_name,
                'session_name': scan.session_name,
                'timestamp': scan.timestamp.isoformat(),
                'time_ago': time_ago,
                'is_late': scan.is_late
            })
        
        return jsonify(scans_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent scans: {str(e)}")
        return jsonify([])

@api.route('/session-stats/<int:session_id>')
@login_required
def get_session_stats(session_id):
    """Get statistics for a specific session"""
    try:
        today = datetime.now().date()
        
        # Count today's scans for this session
        scans_today = Attendance.query.filter(
            and_(
                Attendance.session_id == session_id,
                func.date(Attendance.timestamp) == today
            )
        ).count()
        
        # Count unique students
        unique_students = db.session.query(
            Attendance.student_id
        ).filter(
            and_(
                Attendance.session_id == session_id,
                func.date(Attendance.timestamp) == today
            )
        ).distinct().count()
        
        return jsonify({
            'scans_today': scans_today,
            'unique_students': unique_students
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching session stats: {str(e)}")
        return jsonify({'scans_today': 0, 'unique_students': 0})

@api.route('/today-stats')
@login_required
def get_today_stats():
    """Get overall statistics for today"""
    try:
        today = datetime.now().date()
        
        # Total scans today
        total_scans = Attendance.query.filter(
            func.date(Attendance.timestamp) == today
        ).count()
        
        # Unique students today
        unique_students = db.session.query(
            Attendance.student_id
        ).filter(
            func.date(Attendance.timestamp) == today
        ).distinct().count()
        
        return jsonify({
            'total_scans': total_scans,
            'unique_students': unique_students
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching today stats: {str(e)}")
        return jsonify({'total_scans': 0, 'unique_students': 0})

def get_time_ago(timestamp):
    """Get human-readable time difference"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.seconds < 60:
        return "Just now"
    elif diff.seconds < 3600:
        minutes = diff.seconds // 60
        return f"{minutes} min{'s' if minutes != 1 else ''} ago"
    elif diff.days == 0:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days == 1:
        return "Yesterday"
    else:
        return f"{diff.days} days ago"