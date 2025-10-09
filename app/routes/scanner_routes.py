"""
Simplified Scanner Routes for ScanMe Attendance System
Handles QR code scanning and attendance recording with time-in/time-out logic
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models.student_model import Student
from app.models.room_model import Room
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.attendance_event_model import AttendanceEvent
from app.models.user_model import User
from app.utils.auth_utils import requires_scanner_access
from app.utils.qr_utils import validate_qr_data, process_uploaded_qr_image
from app.services.attendance_state_service import AttendanceStateService
from datetime import datetime, timedelta
import json

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/')
@scanner_bp.route('/scan')
@login_required
@requires_scanner_access
def scan_page():
    """Main QR code scanning page"""
    try:
        # Get available rooms for dropdown
        rooms = Room.query.filter_by(is_active=True).all()
        
        # Get current active sessions
        active_sessions = AttendanceSession.query.filter_by(is_active=True).all()
        
        return render_template('scanner/index.html', 
                             rooms=rooms, 
                             sessions=active_sessions)
    
    except Exception as e:
        flash(f'Error loading scanner page: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))

@scanner_bp.route('/api/scan-qr', methods=['POST'])
@login_required
@requires_scanner_access
def scan_qr_code():
    """Process QR code scan using AttendanceStateService"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data', '').strip()
        room_id = data.get('room_id')
        session_id = data.get('session_id')
        scan_mode = data.get('scan_mode', 'auto')  # 'auto', 'time_in', 'time_out'
        
        # Validation
        if not qr_data:
            return jsonify({'success': False, 'error': 'QR code data is required'}), 400
        
        # Get room_id from session or direct parameter
        if session_id:
            session = AttendanceSession.query.get(session_id)
            if session:
                room_id = session.room_id
            else:
                return jsonify({'success': False, 'error': 'Invalid session selected'}), 400
        elif not room_id:
            return jsonify({'success': False, 'error': 'Room or session selection is required'}), 400
        
        # Validate QR code
        qr_validation = validate_qr_data(qr_data)
        if not qr_validation['valid']:
            return jsonify({
                'success': False, 
                'error': f'Invalid QR code: {qr_validation["error"]}'
            }), 400
        
        # Get decoded data
        decoded_data = qr_validation['data']
        
        # Find student
        student = None
        if decoded_data.get('student_id'):
            student = Student.query.get(decoded_data['student_id'])
        elif decoded_data.get('student_no'):
            student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        elif decoded_data.get('legacy') and decoded_data.get('student_no'):
            # Handle legacy QR codes (just student number)
            student = Student.query.filter_by(student_no=decoded_data['student_no']).first()
        
        if not student:
            # Try to auto-create student if we have enough data
            if decoded_data.get('name') or decoded_data.get('student_no'):
                try:
                    student = Student(
                        student_no=decoded_data.get('student_no', f'AUTO_{datetime.now().strftime("%Y%m%d%H%M%S")}'),
                        first_name=decoded_data.get('name', 'Unknown').split()[0],
                        last_name=' '.join(decoded_data.get('name', 'Student').split()[1:]) or 'Student',
                        email=decoded_data.get('email', f"{decoded_data.get('student_no', 'unknown')}@university.edu")
                    )
                    db.session.add(student)
                    db.session.commit()
                except Exception as e:
                    return jsonify({
                        'success': False, 
                        'error': 'Student not found and could not auto-create'
                    }), 404
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Student not found in database'
                }), 404
        
        # Get room
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Invalid room selected'}), 400
        
        # Process attendance using NEW AttendanceStateService logic
        result = AttendanceStateService.process_attendance_scan_new_logic(
            student_id=student.id,
            room_id=room.id,
            session_id=session_id,
            scanned_by=current_user.id,
            scan_type=scan_mode,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'action': result['action'],
                'student': {
                    'id': student.id,
                    'name': student.name,
                    'student_no': student.student_no,
                    'department': student.department,
                    'section': student.section,
                    'year_level': student.year_level,
                    'email': student.email
                },
                'room': {
                    'id': room.id,
                    'name': room.name
                },
                'scan_time': result.get('scan_time'),
                'is_late': result.get('is_late', False),
                'duration_minutes': result.get('duration_minutes')
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Scan processing failed: {str(e)}'
        }), 500

@scanner_bp.route('/api/scan-image', methods=['POST'])
@login_required
@requires_scanner_access
def scan_image():
    """Process uploaded QR code image"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'}), 400
        
        room_id = request.form.get('room_id')
        session_id = request.form.get('session_id')
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room selection is required'}), 400
        
        # Process uploaded image
        result = process_uploaded_qr_image(file)
        
        if not result['success']:
            return jsonify({
                'success': False, 
                'error': result['error']
            }), 400
        
        # If QR scanning from images becomes available, process the decoded data
        # For now, return informative message
        return jsonify({
            'success': False,
            'error': 'QR code image scanning requires additional setup. Please enter the QR code data manually.',
            'info': 'To enable image scanning, install: pip install opencv-python pyzbar'
        })
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error processing image: {str(e)}'
        }), 500

@scanner_bp.route('/api/statistics')
@login_required
@requires_scanner_access
def get_statistics():
    """Get today's scanning statistics"""
    try:
        today = datetime.now().date()
        
        # Get today's records
        today_records = AttendanceRecord.query.filter(
            AttendanceRecord.scan_date == today
        ).all()
        
        # Calculate statistics
        total_scans = len(today_records)
        unique_students = len(set(record.student_id for record in today_records))
        late_arrivals = sum(1 for record in today_records if record.is_late)
        on_time = total_scans - late_arrivals
        
        return jsonify({
            'success': True,
            'total_scans': total_scans,
            'unique_students': unique_students,
            'late_arrivals': late_arrivals,
            'on_time': on_time
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting statistics: {str(e)}'
        }), 500

@scanner_bp.route('/api/recent-scans')
@login_required
@requires_scanner_access
def get_recent_scans():
    """Get recent scan events showing time-in and time-out as separate entries"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent attendance events (each scan action is a separate event)
        recent_events = db.session.query(AttendanceEvent)\
            .join(Student)\
            .join(Room)\
            .order_by(AttendanceEvent.event_time.desc())\
            .limit(limit)\
            .all()
        
        events_data = []
        for event in recent_events:
            # Calculate time ago
            time_ago = _calculate_time_ago(event.event_time)
            
            events_data.append({
                'id': event.id,
                'student_name': event.student.get_full_name(),
                'student_no': event.student.student_no,
                'room_name': event.room.room_name or event.room.room_number,
                'action_type': event.event_type,
                'scan_time': event.event_time.isoformat(),
                'time_ago': time_ago,
                'is_late': event.is_late,
                'duration_minutes': event.duration_minutes,
                'student': {
                    'id': event.student.id,
                    'name': event.student.get_full_name(),
                    'student_no': event.student.student_no
                },
                'room': {
                    'id': event.room.id,
                    'name': event.room.room_name or event.room.room_number
                }
            })
        
        return jsonify(events_data)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting recent scans: {str(e)}'
        }), 500

def _calculate_time_ago(scan_time):
    """Helper function to calculate time ago text"""
    now = datetime.utcnow()
    time_diff = now - scan_time
    
    if time_diff.days > 0:
        return f"{time_diff.days}d ago"
    elif time_diff.seconds > 3600:
        hours = time_diff.seconds // 3600
        return f"{hours}h ago"
    elif time_diff.seconds > 60:
        minutes = time_diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"

@scanner_bp.route('/api/session-stats/<int:session_id>')
@login_required
@requires_scanner_access
def get_session_stats(session_id):
    """Get statistics for a specific session"""
    try:
        # Get the session
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Count total time-ins for this session
        total_time_ins = db.session.query(AttendanceRecord)\
            .filter_by(session_id=session_id)\
            .filter(AttendanceRecord.time_in.isnot(None))\
            .count()
        
        # Count currently in room (active records)
        currently_in_room = db.session.query(AttendanceRecord)\
            .filter_by(session_id=session_id, is_active=True)\
            .count()
        
        # Count total time-outs for this session
        total_time_outs = db.session.query(AttendanceRecord)\
            .filter_by(session_id=session_id)\
            .filter(AttendanceRecord.time_out.isnot(None))\
            .count()
        
        return jsonify({
            'session_id': session_id,
            'session_name': session.name,
            'total_time_ins': total_time_ins,
            'total_time_outs': total_time_outs,
            'currently_in_room': currently_in_room,
            'session_start': session.start_time.isoformat() if session.start_time else None,
            'session_end': session.end_time.isoformat() if session.end_time else None,
            'is_active': session.is_active
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting session stats: {str(e)}'
        }), 500

@scanner_bp.route('/api/today-stats')
@login_required
@requires_scanner_access
def get_today_stats():
    """Get today's overall statistics"""
    try:
        today = datetime.utcnow().date()
        
        # Count today's time-ins
        today_time_ins = db.session.query(AttendanceRecord)\
            .filter(db.func.date(AttendanceRecord.time_in) == today)\
            .count()
        
        # Count today's time-outs
        today_time_outs = db.session.query(AttendanceRecord)\
            .filter(db.func.date(AttendanceRecord.time_out) == today)\
            .count()
        
        # Count currently active across all sessions
        currently_active = db.session.query(AttendanceRecord)\
            .filter_by(is_active=True)\
            .count()
        
        # Count late arrivals today
        late_arrivals = db.session.query(AttendanceRecord)\
            .filter(db.func.date(AttendanceRecord.time_in) == today)\
            .filter_by(is_late=True)\
            .count()
        
        return jsonify({
            'today_time_ins': today_time_ins,
            'today_time_outs': today_time_outs,
            'currently_active': currently_active,
            'late_arrivals': late_arrivals,
            'date': today.isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting today stats: {str(e)}'
        }), 500

@scanner_bp.route('/room-info/<int:room_id>')
@login_required
@requires_scanner_access
def get_room_info(room_id):
    """Get room information and current occupancy"""
    try:
        room = Room.query.get_or_404(room_id)
        
        # Get today's attendance for this room
        today = datetime.now().date()
        today_attendance = AttendanceRecord.query.filter(
            AttendanceRecord.room_id == room_id,
            AttendanceRecord.scan_date == today
        ).all()
        
        # Calculate occupancy
        current_occupancy = len(set(record.student_id for record in today_attendance))
        occupancy_percentage = (current_occupancy / room.capacity * 100) if room.capacity > 0 else 0
        
        # Get recent visitors
        recent_visitors = []
        for record in sorted(today_attendance, key=lambda x: x.scan_time, reverse=True)[:5]:
            recent_visitors.append({
                'student_name': record.student.name,
                'scan_time': record.scan_time.strftime('%H:%M')
            })
        
        return jsonify({
            'id': room.id,
            'name': room.name,
            'building': room.building,
            'capacity': room.capacity,
            'current_occupancy': current_occupancy,
            'occupancy_percentage': round(occupancy_percentage, 1),
            'recent_visitors': recent_visitors
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Error getting room info: {str(e)}'
        }), 500

@scanner_bp.route('/manual-entry')
@login_required
@requires_scanner_access
def manual_entry_page():
    """Manual attendance entry page"""
    try:
        rooms = Room.query.filter_by(is_active=True).all()
        active_sessions = AttendanceSession.query.filter_by(is_active=True).all()
        
        return render_template('scanner/manual_entry.html', 
                             rooms=rooms, 
                             sessions=active_sessions)
    
    except Exception as e:
        flash(f'Error loading manual entry page: {str(e)}', 'danger')
        return redirect(url_for('scanner.scan_page'))

@scanner_bp.route('/api/manual-entry', methods=['POST'])
@login_required
@requires_scanner_access
def process_manual_entry():
    """Process manual attendance entry"""
    try:
        data = request.get_json()
        student_no = data.get('student_no', '').strip()
        room_id = data.get('room_id')
        session_id = data.get('session_id')
        
        # Validation
        if not student_no:
            return jsonify({'success': False, 'error': 'Student number is required'}), 400
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room selection is required'}), 400
        
        # Find student
        student = Student.query.filter_by(student_no=student_no).first()
        if not student:
            return jsonify({
                'success': False, 
                'error': f'Student with number {student_no} not found'
            }), 404
        
        # Create QR data and process like a normal scan
        manual_qr_data = json.dumps({
            'type': 'manual_entry',
            'student_id': student.id,
            'student_no': student.student_no,
            'name': student.name,
            'department': student.department,
            'section': student.section,
            'year_level': student.year_level,
            'generated_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        })
        
        # Use the existing scan processing logic
        scan_request = {
            'qr_data': manual_qr_data,
            'room_id': room_id,
            'session_id': session_id
        }
        
        # Process the manual entry as a QR scan
        with scanner_bp.test_client() as client:
            # Simulate the QR scan processing
            return scan_qr_code_helper(scan_request)
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error processing manual entry: {str(e)}'
        }), 500

def scan_qr_code_helper(data):
    """Helper function for processing QR scans (used by both API and manual entry)"""
    # This is the same logic as scan_qr_code but without request handling
    # Implementation would be similar to the scan_qr_code function above
    pass