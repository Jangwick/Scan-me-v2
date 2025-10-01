"""
Professor Routes for ScanMe Attendance System
Handles professor-specific functionality including class management and integrated scanning
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, Room, AttendanceSession, AttendanceRecord, Student, AttendanceEvent
from app.services.attendance_state_service import AttendanceStateService
from app.utils.qr_utils import validate_qr_data
from datetime import datetime, date, timedelta
import json

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')

def requires_professor_access(f):
    """Decorator to ensure user has professor or admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not (current_user.is_professor() or current_user.is_admin()):
            flash('Access denied. Professor privileges required.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

@professor_bp.route('/')
@login_required
@requires_professor_access
def dashboard():
    """Professor dashboard showing all assigned classes"""
    try:
        # Get professor's sessions (either created by them or assigned as instructor)
        professor_name = current_user.username  # Use username since User model doesn't have first_name/last_name
        
        # Get sessions where professor is the instructor or creator
        professor_sessions = AttendanceSession.query.filter(
            db.or_(
                AttendanceSession.instructor == professor_name,
                AttendanceSession.created_by == current_user.id
            ),
            AttendanceSession.is_active == True
        ).order_by(AttendanceSession.start_time.desc()).all()
        
        # Categorize sessions
        today = datetime.now().date()
        current_sessions = []
        upcoming_sessions = []
        past_sessions = []
        
        for session in professor_sessions:
            session_date = session.start_time.date()
            session_status = session.get_session_status()
            
            if session_status == 'active':
                current_sessions.append(session)
            elif session_date >= today and session_status in ['scheduled']:
                upcoming_sessions.append(session)
            else:
                past_sessions.append(session)
        
        # Get today's statistics
        today_sessions = [s for s in professor_sessions if s.start_time.date() == today]
        total_students_today = 0
        total_scans_today = 0
        
        for session in today_sessions:
            summary = session.get_attendance_summary()
            total_students_today += summary['unique_students']
            total_scans_today += summary['total_scans']
        
        stats = {
            'total_classes_today': len(today_sessions),
            'total_students_today': total_students_today,
            'total_scans_today': total_scans_today,
            'active_sessions': len(current_sessions)
        }
        
        return render_template('professor/dashboard.html',
                             current_sessions=current_sessions,
                             upcoming_sessions=upcoming_sessions,
                             past_sessions=past_sessions[:10],  # Limit past sessions
                             stats=stats)
        
    except Exception as e:
        flash(f'Error loading professor dashboard: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@professor_bp.route('/session/<int:session_id>')
@login_required
@requires_professor_access
def session_detail(session_id):
    """Session detail view with integrated scanner"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Verify professor has access to this session
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            flash('Access denied. You do not have permission to view this session.', 'error')
            return redirect(url_for('professor.dashboard'))
        
        # Get session statistics
        attendance_summary = session.get_attendance_summary()
        
        # Get recent attendance events for this session
        recent_events = AttendanceEvent.query.filter_by(
            session_id=session_id
        ).order_by(AttendanceEvent.event_time.desc()).limit(20).all()
        
        # Get students currently in room (active attendance records)
        active_students = db.session.query(AttendanceRecord, Student).join(Student).filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.is_active == True
        ).all()
        
        return render_template('professor/session_detail.html',
                             session=session,
                             attendance_summary=attendance_summary,
                             recent_events=recent_events,
                             active_students=active_students)
        
    except Exception as e:
        flash(f'Error loading session: {str(e)}', 'error')
        return redirect(url_for('professor.dashboard'))

@professor_bp.route('/session/<int:session_id>/scanner')
@login_required
@requires_professor_access
def session_scanner(session_id):
    """Integrated scanner for a specific session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Verify professor has access to this session
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            flash('Access denied. You do not have permission to access this scanner.', 'error')
            return redirect(url_for('professor.dashboard'))
        
        return render_template('professor/session_scanner.html', session=session)
        
    except Exception as e:
        flash(f'Error loading scanner: {str(e)}', 'error')
        return redirect(url_for('professor.dashboard'))

@professor_bp.route('/api/session/<int:session_id>/scan', methods=['POST'])
@login_required
@requires_professor_access
def process_session_scan(session_id):
    """Process QR code scan for a specific session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Verify professor has access to this session
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        student_qr = data.get('student_qr')
        if not student_qr:
            return jsonify({'success': False, 'error': 'Student QR code required'}), 400
        
        # Validate QR code using the same logic as main scanner
        qr_validation = validate_qr_data(student_qr)
        if not qr_validation['valid']:
            return jsonify({
                'success': False, 
                'error': f'Invalid QR code: {qr_validation["error"]}'
            }), 400
        
        # Get decoded data
        decoded_data = qr_validation['data']
        
        # Find student based on QR data type
        student = None
        if decoded_data.get('type') == 'scanme_qr_code':
            # This is our SCANME_ format QR code
            student = Student.query.filter_by(qr_code_data=decoded_data['qr_data']).first()
        elif decoded_data.get('type') == 'student_attendance':
            # Standard JSON format
            if decoded_data.get('student_id'):
                student = Student.query.get(decoded_data['student_id'])
            elif decoded_data.get('student_no'):
                student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        elif decoded_data.get('type') == 'legacy_student_no':
            # Legacy format (just student number)
            student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Process the attendance scan
        result = AttendanceStateService.process_attendance_scan(
            student_id=student.id,
            room_id=session.room_id,
            session_id=session.id,
            scanned_by=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'student': {
                    'id': student.id,
                    'name': student.get_full_name(),
                    'student_no': student.student_no
                },
                'action': result.get('action', 'unknown'),
                'duration': result.get('duration', 0)
            })
        else:
            return jsonify({'success': False, 'error': result['message']}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Scan processing failed: {str(e)}'}), 500

@professor_bp.route('/api/scan-image', methods=['POST'])
@login_required
@requires_professor_access
def scan_image():
    """Process uploaded QR code image for professor scanner"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'}), 400
        
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID is required'}), 400
        
        # Get the session and verify access
        session = AttendanceSession.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400
        
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Process uploaded image using the QR utils
        from app.utils.qr_utils import process_uploaded_qr_image
        result = process_uploaded_qr_image(file)
        
        if not result['success']:
            return jsonify({
                'success': False, 
                'error': result['error']
            }), 400
        
        # Extract QR data and find student
        qr_data = result.get('raw_data') or result.get('data', {}).get('qr_data')
        if not qr_data:
            return jsonify({
                'success': False,
                'error': 'No valid QR code data found in image'
            }), 400
        
        # Use the same logic as the scan endpoint
        decoded_data = result['data']
        student = None
        
        if decoded_data.get('type') == 'scanme_qr_code':
            student = Student.query.filter_by(qr_code_data=decoded_data['qr_data']).first()
        elif decoded_data.get('type') == 'student_attendance':
            if decoded_data.get('student_id'):
                student = Student.query.get(decoded_data['student_id'])
            elif decoded_data.get('student_no'):
                student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        elif decoded_data.get('type') == 'legacy_student_no':
            student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
        
        # Process attendance scan
        scan_result = AttendanceStateService.process_attendance_scan(
            student_id=student.id,
            room_id=session.room_id,
            session_id=session.id,
            scanned_by=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if scan_result['success']:
            return jsonify({
                'success': True,
                'student_name': student.get_full_name(),
                'action': scan_result.get('action', 'unknown'),
                'message': scan_result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': scan_result['message']
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error processing image: {str(e)}'
        }), 500

@professor_bp.route('/api/session/<int:session_id>/recent-events')
@login_required
@requires_professor_access
def get_session_recent_events(session_id):
    """Get recent attendance events for a specific session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Verify professor has access to this session
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent events for this session
        recent_events = db.session.query(AttendanceEvent)\
            .join(Student)\
            .filter(AttendanceEvent.session_id == session_id)\
            .order_by(AttendanceEvent.event_time.desc())\
            .limit(limit)\
            .all()
        
        events_data = []
        for event in recent_events:
            # Calculate time ago
            time_diff = datetime.utcnow() - event.event_time
            if time_diff.total_seconds() < 60:
                time_ago = "Just now"
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                time_ago = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = int(time_diff.total_seconds() / 3600)
                time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
            
            events_data.append({
                'id': event.id,
                'student_name': event.student.get_full_name(),
                'student_no': event.student.student_no,
                'action_type': event.event_type,
                'event_time': event.event_time.isoformat(),
                'time_ago': time_ago,
                'is_late': event.is_late,
                'duration_minutes': event.duration_minutes
            })
        
        return jsonify(events_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to load events: {str(e)}'}), 500

@professor_bp.route('/api/session/<int:session_id>/statistics')
@login_required
@requires_professor_access
def get_session_statistics(session_id):
    """Get real-time statistics for a specific session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Verify professor has access to this session
        professor_name = current_user.username
        if not (session.instructor == professor_name or 
                session.created_by == current_user.id or 
                current_user.is_admin()):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get attendance summary
        summary = session.get_attendance_summary()
        
        # Get students currently in room
        active_count = AttendanceRecord.query.filter_by(
            session_id=session_id,
            is_active=True
        ).count()
        
        # Get recent activity count (last 10 minutes)
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        recent_activity = AttendanceEvent.query.filter(
            AttendanceEvent.session_id == session_id,
            AttendanceEvent.event_time >= ten_minutes_ago
        ).count()
        
        return jsonify({
            'success': True,
            'total_scans': summary['total_scans'],
            'unique_students': summary['unique_students'],
            'late_arrivals': summary['late_arrivals'],
            'expected_students': summary['expected_students'],
            'attendance_rate': summary['attendance_rate'],
            'students_in_room': active_count,
            'recent_activity': recent_activity,
            'session_status': session.get_session_status()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to load statistics: {str(e)}'}), 500
