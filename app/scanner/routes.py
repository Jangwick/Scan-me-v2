"""
Scanner routes for QR code scanning functionality
"""
from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from datetime import datetime, date, time, timedelta
from sqlalchemy import func, and_, or_
import json
import uuid

from app import db
from app.models import Student, Room, AttendanceRecord, AttendanceSession
from . import scanner

@scanner.route('/')
@login_required
def index():
    """Main scanner page with modern interface"""
    # Get today's sessions
    today = date.today()
    sessions = AttendanceSession.query.join(Room).filter(
        func.date(AttendanceSession.start_time) == today
    ).all()
    
    return render_template('scanner/index.html', 
                         title="QR Code Scanner",
                         sessions=sessions)

# API Routes
@scanner.route('/api/sessions')
@login_required
def api_get_sessions():
    """Get all active sessions for today"""
    try:
        today = datetime.now().date()
        
        sessions = AttendanceSession.query.join(Room).filter(
            func.date(AttendanceSession.start_time) == today,
            AttendanceSession.is_active == True
        ).all()
        
        session_data = []
        for session in sessions:
            # Check if session is currently active
            now = datetime.now()
            is_active = (
                session.start_time - timedelta(minutes=30) <= now <= 
                session.end_time + timedelta(minutes=30)
            )
            
            session_data.append({
                'id': session.id,
                'name': session.session_name,
                'room_name': session.room.room_name if session.room else 'Unknown Room',
                'start_time': session.start_time.strftime('%H:%M'),
                'end_time': session.end_time.strftime('%H:%M'),
                'is_active': is_active,
                'capacity': session.expected_students or 0
            })
        
        # Sort by start time, active sessions first
        session_data.sort(key=lambda x: (not x['is_active'], x['start_time']))
        
        return jsonify(session_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify([]), 500

@scanner.route('/api/scan-qr', methods=['POST'])
@login_required
def api_scan_qr_code():
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
        session = AttendanceSession.query.get(session_id)
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
                Student.student_no == student_id,
                Student.email == student_id,
                func.cast(Student.id, db.String) == str(student_id)
            )
        ).first()
        
        # If no student found, try creating one (if QR has enough data)
        if not student:
            # For demo purposes, create a mock student
            if student_id and len(str(student_id)) >= 3:
                # Generate a name from the ID for demo
                first_name = f"Student"
                last_name = f"{str(student_id)[-3:]}"
                email = f"student{str(student_id)[-3:]}@university.edu"
                
                student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    student_no=str(student_id),
                    phone="000-000-0000",
                    department="General"
                )
                db.session.add(student)
                db.session.flush()  # Get ID without committing
            else:
                return jsonify({'success': False, 'message': 'Invalid QR code format'})
        
        # Check if already scanned today for this session
        today = datetime.now().date()
        existing_attendance = AttendanceRecord.query.filter(
            and_(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id == session.id,
                func.date(AttendanceRecord.scan_time) == today
            )
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False, 
                'message': f'{student.get_full_name()} already marked present for this session',
                'student_name': student.get_full_name()
            })
        
        # Determine if late
        now = datetime.now()
        is_late = now > (session.start_time + timedelta(minutes=10))  # 10-minute grace period
        
        # Create attendance record
        from flask_login import current_user
        attendance = AttendanceRecord(
            student_id=student.id,
            room_id=session.room_id,
            session_id=session.id,
            scanned_by=current_user.id,
            is_late=is_late
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully marked {student.get_full_name()} as present' + (' (Late)' if is_late else ''),
            'student_name': student.get_full_name(),
            'is_late': is_late,
            'timestamp': now.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing QR scan: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to process scan: {str(e)}'})

@scanner.route('/api/scan-image', methods=['POST'])
@login_required
def api_scan_image():
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
        
        # Mock QR data extraction (in real implementation, decode QR from image)
        mock_qr_data = f"STU{str(uuid.uuid4())[:3].upper()}"
        
        # Process the extracted QR data using the same logic as scan_qr_code
        return process_qr_data(mock_qr_data, session_id)
        
    except Exception as e:
        current_app.logger.error(f"Error processing image scan: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to process image'})

@scanner.route('/api/recent-scans')
@login_required
def api_get_recent_scans():
    """Get recent attendance scans"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        recent_scans = db.session.query(
            AttendanceRecord.scan_time,
            AttendanceRecord.is_late,
            Student.first_name,
            Student.last_name,
            Room.room_name,
            AttendanceSession.session_name
        ).join(
            Student, AttendanceRecord.student_id == Student.id
        ).join(
            AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
        ).join(
            Room, AttendanceSession.room_id == Room.id
        ).order_by(
            AttendanceRecord.scan_time.desc()
        ).limit(limit).all()
        
        scans_data = []
        for scan in recent_scans:
            student_name = f"{scan.first_name} {scan.last_name}".strip()
            time_ago = get_time_ago(scan.scan_time)
            scans_data.append({
                'student_name': student_name,
                'room_name': scan.room_name,
                'session_name': scan.session_name,
                'timestamp': scan.scan_time.isoformat(),
                'time_ago': time_ago,
                'is_late': scan.is_late
            })
        
        return jsonify(scans_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent scans: {str(e)}")
        return jsonify([])

@scanner.route('/api/session-stats/<int:session_id>')
@login_required
def api_get_session_stats(session_id):
    """Get statistics for a specific session"""
    try:
        today = datetime.now().date()
        
        # Count today's scans for this session
        scans_today = AttendanceRecord.query.filter(
            and_(
                AttendanceRecord.session_id == session_id,
                func.date(AttendanceRecord.scan_time) == today
            )
        ).count()
        
        # Count unique students
        unique_students = db.session.query(
            AttendanceRecord.student_id
        ).filter(
            and_(
                AttendanceRecord.session_id == session_id,
                func.date(AttendanceRecord.scan_time) == today
            )
        ).distinct().count()
        
        return jsonify({
            'scans_today': scans_today,
            'unique_students': unique_students
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching session stats: {str(e)}")
        return jsonify({'scans_today': 0, 'unique_students': 0})

@scanner.route('/api/today-stats')
@login_required
def api_get_today_stats():
    """Get overall statistics for today"""
    try:
        today = datetime.now().date()
        
        # Total scans today
        total_scans = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.scan_time) == today
        ).count()
        
        # Unique students today
        unique_students = db.session.query(
            AttendanceRecord.student_id
        ).filter(
            func.date(AttendanceRecord.scan_time) == today
        ).distinct().count()
        
        return jsonify({
            'total_scans': total_scans,
            'unique_students': unique_students
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching today stats: {str(e)}")
        return jsonify({'total_scans': 0, 'unique_students': 0})

def process_qr_data(qr_data, session_id):
    """Helper function to process QR data consistently"""
    try:
        # Get the session
        session = AttendanceSession.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'message': 'Invalid session'})
        
        # Parse QR code data
        try:
            qr_json = json.loads(qr_data)
            student_id = qr_json.get('student_id') or qr_json.get('id')
        except (json.JSONDecodeError, ValueError):
            student_id = qr_data
        
        # Find student
        student = Student.query.filter(
            or_(
                Student.student_no == student_id,
                Student.email == student_id,
                func.cast(Student.id, db.String) == str(student_id)
            )
        ).first()
        
        # Create student if not found
        if not student:
            if student_id and len(str(student_id)) >= 3:
                first_name = "Student"
                last_name = f"{str(student_id)[-3:]}"
                email = f"student{str(student_id)[-3:]}@university.edu"
                
                student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    student_no=str(student_id),
                    phone="000-000-0000",
                    department="General"
                )
                db.session.add(student)
                db.session.flush()
            else:
                return jsonify({'success': False, 'message': 'Invalid QR code format'})
        
        # Check existing attendance
        today = datetime.now().date()
        existing_attendance = AttendanceRecord.query.filter(
            and_(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id == session.id,
                func.date(AttendanceRecord.scan_time) == today
            )
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False, 
                'message': f'{student.get_full_name()} already marked present',
                'student_name': student.get_full_name()
            })
        
        # Create attendance record
        now = datetime.now()
        is_late = now > (session.start_time + timedelta(minutes=10))
        
        from flask_login import current_user
        attendance = AttendanceRecord(
            student_id=student.id,
            room_id=session.room_id,
            session_id=session.id,
            scanned_by=current_user.id,
            is_late=is_late
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully marked {student.get_full_name()} as present' + (' (Late)' if is_late else ''),
            'student_name': student.get_full_name(),
            'is_late': is_late,
            'timestamp': now.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing QR data: {str(e)}")
        return jsonify({'success': False, 'message': 'Processing failed'})

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