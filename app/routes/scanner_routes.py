"""
Simplified Scanner Routes for ScanMe Attendance System
Handles QR code scanning and attendance recording (without camera scanning initially)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models.student_model import Student
from app.models.room_model import Room
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.user_model import User
from app.utils.auth_utils import requires_scanner_access
from app.utils.qr_utils import validate_qr_data, process_uploaded_qr_image
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
    """Process QR code scan"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data', '').strip()
        room_id = data.get('room_id')
        session_id = data.get('session_id')
        
        # Validation
        if not qr_data:
            return jsonify({'success': False, 'error': 'QR code data is required'}), 400
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room selection is required'}), 400
        
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
            return jsonify({
                'success': False, 
                'error': 'Student not found in database'
            }), 404
        
        # Get room
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Invalid room selected'}), 400
        
        # Get or create attendance session
        attendance_session = None
        if session_id:
            attendance_session = AttendanceSession.query.get(session_id)
        else:
            # Use current active session or create default
            current_time = datetime.now().time()
            attendance_session = AttendanceSession.query.filter(
                AttendanceSession.is_active == True,
                AttendanceSession.start_time <= current_time,
                AttendanceSession.end_time >= current_time
            ).first()
        
        # Check for duplicate scan
        today = datetime.now().date()
        existing_record = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.room_id == room.id,
            AttendanceRecord.scan_date == today
        ).first()
        
        scan_info = {
            'scan_time': datetime.now().isoformat(),
            'is_duplicate': existing_record is not None,
            'is_late': False,
            'room_name': room.name
        }
        
        if existing_record:
            # Update existing record with new scan time
            existing_record.scan_time = datetime.now()
            existing_record.updated_at = datetime.now()
            db.session.commit()
            
            scan_info['previous_scan_time'] = existing_record.created_at.isoformat()
            message = f'Duplicate scan: {student.name} already scanned in {room.name} today'
        else:
            # Create new attendance record
            attendance_record = AttendanceRecord(
                student_id=student.id,
                room_id=room.id,
                session_id=attendance_session.id if attendance_session else None,
                scan_time=datetime.now(),
                scan_date=today,
                scanner_user_id=current_user.id
            )
            
            # Check if late (if session has start time)
            if attendance_session and attendance_session.start_time:
                session_start = datetime.combine(today, attendance_session.start_time)
                late_threshold = timedelta(minutes=15)  # Configure this
                scan_info['is_late'] = datetime.now() > (session_start + late_threshold)
                attendance_record.is_late = scan_info['is_late']
            
            db.session.add(attendance_record)
            db.session.commit()
            
            message = f'Attendance recorded: {student.name} in {room.name}'
            if scan_info['is_late']:
                message += ' (Late arrival)'
        
        # Return success response
        return jsonify({
            'success': True,
            'message': message,
            'student': {
                'id': student.id,
                'name': student.name,
                'student_no': student.student_no,
                'department': student.department,
                'section': student.section,
                'year_level': student.year_level,
                'email': student.email
            },
            'scan_info': scan_info
        })
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error processing scan: {str(e)}'
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
    """Get recent scan records"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        recent_scans = db.session.query(AttendanceRecord)\
            .join(Student)\
            .join(Room)\
            .order_by(AttendanceRecord.scan_time.desc())\
            .limit(limit)\
            .all()
        
        scans_data = []
        for record in recent_scans:
            scans_data.append({
                'id': record.id,
                'scan_time': record.scan_time.isoformat(),
                'is_late': record.is_late,
                'student': {
                    'id': record.student.id,
                    'name': record.student.name,
                    'student_no': record.student.student_no
                },
                'room': {
                    'id': record.room.id,
                    'name': record.room.name
                }
            })
        
        return jsonify({
            'success': True,
            'scans': scans_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting recent scans: {str(e)}'
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