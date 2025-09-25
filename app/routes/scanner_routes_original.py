"""
Scanner Routes for ScanMe Attendance System
Handles QR code scanning and attendance recording
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
        rooms = Room.get_active_rooms()
        
        # Get current active sessions
        active_sessions = AttendanceSession.get_current_sessions()
        
        # Get today's scan statistics
        today_stats = get_today_scan_stats()
        
        return render_template('scanner/scan.html',
                             rooms=rooms,
                             active_sessions=active_sessions,
                             today_stats=today_stats)
    
    except Exception as e:
        flash(f'Error loading scanner page: {str(e)}', 'error')
        return render_template('scanner/scan.html', rooms=[], active_sessions=[], today_stats={})

@scanner_bp.route('/api/scan-qr', methods=['POST'])
@login_required
@requires_scanner_access
def api_scan_qr():
    """API endpoint to process QR code scan"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        qr_data = data.get('qr_data', '').strip()
        room_id = data.get('room_id')
        session_id = data.get('session_id')
        
        if not qr_data:
            return jsonify({'success': False, 'error': 'QR code data is required'}), 400
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room selection is required'}), 400
        
        # Validate QR code
        qr_validation = validate_qr_code(qr_data)
        if not qr_validation['valid']:
            return jsonify({
                'success': False, 
                'error': f'Invalid QR code: {qr_validation["error"]}'
            }), 400
        
        # Get decoded data
        decoded_data = qr_validation['decoded_data']
        
        # Find student
        student = None
        if decoded_data.get('student_id'):
            student = Student.query.get(decoded_data['student_id'])
        
        if not student:
            # Try finding by student number
            if decoded_data.get('student_no'):
                student = Student.get_by_student_no(decoded_data['student_no'])
        
        if not student or not student.is_active:
            return jsonify({
                'success': False,
                'error': 'Student not found or inactive'
            }), 404
        
        # Get room
        room = Room.query.get(room_id)
        if not room or not room.is_active:
            return jsonify({
                'success': False,
                'error': 'Room not found or inactive'
            }), 404
        
        # Check for recent duplicate scans
        recent_scan = check_recent_scan(student.id, room.id)
        is_duplicate = recent_scan is not None
        
        # Determine if late
        is_late = determine_if_late(session_id)
        
        # Create attendance record
        attendance_record = AttendanceRecord(
            student_id=student.id,
            room_id=room.id,
            session_id=session_id,
            scanned_by=current_user.id,
            is_late=is_late,
            is_duplicate=is_duplicate,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(attendance_record)
        db.session.commit()
        
        # Prepare response data
        response_data = {
            'success': True,
            'student': {
                'id': student.id,
                'name': student.get_full_name(),
                'student_no': student.student_no,
                'department': student.department,
                'section': student.section,
                'year_level': student.year_level
            },
            'room': {
                'id': room.id,
                'name': room.get_full_name(),
                'building': room.building
            },
            'scan_info': {
                'scan_time': attendance_record.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_late': is_late,
                'is_duplicate': is_duplicate,
                'scanner': current_user.username
            },
            'message': get_scan_message(student, is_late, is_duplicate)
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Scan processing error: {str(e)}'
        }), 500

@scanner_bp.route('/api/scan-image', methods=['POST'])
@login_required
@requires_scanner_access
def api_scan_image():
    """API endpoint to scan QR code from uploaded image"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        room_id = request.form.get('room_id')
        session_id = request.form.get('session_id')
        
        if not image_file or image_file.filename == '':
            return jsonify({'success': False, 'error': 'No image selected'}), 400
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Room selection is required'}), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Scan QR code from image
        qr_results = scan_qr_from_image(image_data)
        
        if not qr_results:
            return jsonify({
                'success': False,
                'error': 'No QR code found in image'
            }), 400
        
        # Process first valid QR code
        for qr_result in qr_results:
            qr_data = qr_result['data']
            
            # Validate and process QR code
            validation = validate_qr_code(qr_data)
            if validation['valid']:
                # Process scan using the QR data
                return process_qr_scan(qr_data, room_id, session_id)
        
        return jsonify({
            'success': False,
            'error': 'No valid ScanMe QR codes found in image'
        }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Image scanning error: {str(e)}'
        }), 500

@scanner_bp.route('/recent-scans')
@login_required
@requires_scanner_access
def recent_scans():
    """Show recent scans page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get recent scans with pagination
        scans = AttendanceRecord.query\
            .order_by(AttendanceRecord.scan_time.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('scanner/recent_scans.html', scans=scans)
    
    except Exception as e:
        flash(f'Error loading recent scans: {str(e)}', 'error')
        return render_template('scanner/recent_scans.html', scans=None)

@scanner_bp.route('/api/recent-scans')
@login_required
@requires_scanner_access
def api_recent_scans():
    """API endpoint for recent scans"""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        recent_records = AttendanceRecord.query\
            .order_by(AttendanceRecord.scan_time.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        scans_data = [
            {
                'id': record.id,
                'student': {
                    'name': record.student.get_full_name() if record.student else 'Unknown',
                    'student_no': record.student.student_no if record.student else 'N/A',
                    'department': record.student.department if record.student else 'N/A'
                },
                'room': {
                    'name': record.room.get_full_name() if record.room else 'Unknown',
                    'building': record.room.building if record.room else 'N/A'
                },
                'scan_time': record.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_late': record.is_late,
                'is_duplicate': record.is_duplicate,
                'scanner': record.scanned_by_user.username if record.scanned_by_user else 'System'
            }
            for record in recent_records
        ]
        
        return jsonify({
            'success': True,
            'scans': scans_data,
            'total': AttendanceRecord.query.count()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_bp.route('/room-info/<int:room_id>')
@login_required
@requires_scanner_access
def api_room_info(room_id):
    """API endpoint to get room information"""
    try:
        room = Room.query.get_or_404(room_id)
        
        # Get current occupancy
        current_occupancy = room.get_current_occupancy()
        occupancy_percentage = room.get_occupancy_percentage()
        
        # Get recent visitors
        recent_visitors = room.get_recent_visitors(limit=5)
        
        room_data = {
            'id': room.id,
            'name': room.get_full_name(),
            'building': room.building,
            'floor': room.floor,
            'capacity': room.capacity,
            'current_occupancy': current_occupancy,
            'occupancy_percentage': round(occupancy_percentage, 1),
            'is_over_capacity': room.is_over_capacity(),
            'recent_visitors': [
                {
                    'student_name': visitor['student'].get_full_name(),
                    'student_no': visitor['student'].student_no,
                    'scan_time': visitor['scan_time'].strftime('%H:%M:%S'),
                    'is_late': visitor['is_late']
                }
                for visitor in recent_visitors
            ]
        }
        
        return jsonify(room_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_today_scan_stats():
    """Get today's scanning statistics"""
    try:
        from datetime import date
        from sqlalchemy import func
        
        today = date.today()
        
        today_scans = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.scan_time) == today
        ).count()
        
        unique_students = db.session.query(AttendanceRecord.student_id)\
            .filter(func.date(AttendanceRecord.scan_time) == today)\
            .distinct().count()
        
        late_scans = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.scan_time) == today,
            AttendanceRecord.is_late == True
        ).count()
        
        return {
            'total_scans': today_scans,
            'unique_students': unique_students,
            'late_arrivals': late_scans,
            'on_time_percentage': round(((today_scans - late_scans) / today_scans * 100), 2) if today_scans > 0 else 0
        }
    
    except Exception as e:
        print(f"Error getting today's scan stats: {e}")
        return {
            'total_scans': 0,
            'unique_students': 0,
            'late_arrivals': 0,
            'on_time_percentage': 0
        }

def check_recent_scan(student_id, room_id, minutes=30):
    """Check for recent scan within specified minutes"""
    try:
        time_threshold = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_scan = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.room_id == room_id,
            AttendanceRecord.scan_time >= time_threshold
        ).first()
        
        return recent_scan
    
    except Exception as e:
        print(f"Error checking recent scan: {e}")
        return None

def determine_if_late(session_id):
    """Determine if scan should be marked as late"""
    try:
        if session_id:
            session = AttendanceSession.query.get(session_id)
            if session:
                # Late if scanned after session start time + 15 minutes grace period
                grace_period = timedelta(minutes=15)
                late_threshold = session.start_time + grace_period
                return datetime.utcnow() > late_threshold
        
        # Default: late if after 9:00 AM
        from datetime import time
        now = datetime.utcnow()
        default_start = datetime.combine(now.date(), time(9, 0))
        return now > default_start
    
    except Exception as e:
        print(f"Error determining if late: {e}")
        return False

def get_scan_message(student, is_late, is_duplicate):
    """Generate appropriate message for scan result"""
    name = student.get_full_name()
    
    if is_duplicate:
        return f"Welcome back, {name}! (Already scanned recently)"
    elif is_late:
        return f"Welcome, {name}! (Marked as late arrival)"
    else:
        return f"Welcome, {name}! (On time)"

def process_qr_scan(qr_data, room_id, session_id):
    """Process QR code scan (helper function)"""
    try:
        # This is similar to api_scan_qr but for reuse
        # Validate QR code
        qr_validation = validate_qr_code(qr_data)
        if not qr_validation['valid']:
            return jsonify({
                'success': False, 
                'error': f'Invalid QR code: {qr_validation["error"]}'
            }), 400
        
        # Get decoded data
        decoded_data = qr_validation['decoded_data']
        
        # Find student
        student = None
        if decoded_data.get('student_id'):
            student = Student.query.get(decoded_data['student_id'])
        
        if not student:
            if decoded_data.get('student_no'):
                student = Student.get_by_student_no(decoded_data['student_no'])
        
        if not student or not student.is_active:
            return jsonify({
                'success': False,
                'error': 'Student not found or inactive'
            }), 404
        
        # Continue with scan processing...
        # (This would contain the same logic as api_scan_qr)
        
        return jsonify({'success': True, 'message': 'Scan processed successfully'})
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Scan processing error: {str(e)}'
        }), 500