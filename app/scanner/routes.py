"""
Scanner routes for QR code scanning functionality
"""
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
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

@scanner.route('/api/test-qr', methods=['POST'])
@login_required
def test_qr_endpoint():
    """Test endpoint to debug QR scanning issues"""
    try:
        current_app.logger.info("Test QR endpoint called")
        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")
        return jsonify({
            'success': True,
            'message': 'Test endpoint working',
            'received_data': data
        })
    except Exception as e:
        current_app.logger.error(f"Test endpoint error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@scanner.route('/api/scan-qr', methods=['POST'])
@login_required
def api_scan_qr_code():
    """Process a scanned QR code for time-in or time-out with comprehensive validation"""
    try:
        current_app.logger.info("=== QR SCAN REQUEST RECEIVED ===")
        
        # Edge Case: Request validation
        if not request.is_json:
            current_app.logger.error("Request is not JSON")
            return jsonify({
                'success': False, 
                'message': 'Request must be JSON',
                'error_code': 'INVALID_REQUEST_TYPE'
            }), 400
        
        data = request.get_json()
        current_app.logger.info(f"Request data received: {data}")
        
        if not data:
            current_app.logger.error("No data provided in request")
            return jsonify({
                'success': False, 
                'message': 'No data provided',
                'error_code': 'NO_DATA'
            }), 400
        
        # Extract and validate QR data
        qr_data = data.get('qr_data', '')
        session_id = data.get('session_id')
        scan_type = data.get('scan_type', 'auto')  # auto, time_in, time_out
        
        # Edge Case: Empty QR data
        if not qr_data or not qr_data.strip():
            return jsonify({
                'success': False, 
                'message': 'No QR code data provided',
                'error_code': 'EMPTY_QR_DATA'
            })
        
        # Edge Case: Missing session
        if not session_id:
            return jsonify({
                'success': False, 
                'message': 'No session selected',
                'error_code': 'NO_SESSION'
            })
        
        # Comprehensive QR validation using enhanced utility
        from app.utils.qr_utils import validate_qr_data
        qr_validation = validate_qr_data(qr_data)
        
        if not qr_validation['valid']:
            return jsonify({
                'success': False,
                'message': f'Invalid QR code: {qr_validation["error"]}',
                'error_code': qr_validation.get('error_code', 'QR_VALIDATION_FAILED'),
                'hint': 'Please scan a valid student QR code or enter student information manually'
            })
        
        # Get validated data
        validated_data = qr_validation['data']
        
        # Get the session with validation
        session = AttendanceSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False, 
                'message': 'Invalid session ID',
                'error_code': 'INVALID_SESSION'
            })
        
        # Edge Case: Inactive session
        if not session.is_active:
            return jsonify({
                'success': False,
                'message': 'Session is not active',
                'error_code': 'INACTIVE_SESSION'
            })
        
        # Student identification with comprehensive edge case handling
        from app.services.student_identification_service import StudentIdentificationService
        
        student, student_error = StudentIdentificationService.find_student_by_qr_data(validated_data)
        
        if student_error:
            return jsonify({
                'success': False,
                'message': student_error['error'],
                'error_code': student_error['error_code']
            })
        
        # Edge Case: Student not found - Auto-creation with comprehensive validation
        if not student:
            current_app.logger.info(f"Student not found, attempting auto-creation from QR data")
            student, creation_error = StudentIdentificationService.create_student_from_qr_data(validated_data)
            
            if creation_error:
                return jsonify({
                    'success': False,
                    'message': creation_error['error'],
                    'error_code': creation_error['error_code'],
                    'hint': 'Please ensure the student is registered in the system or contact an administrator'
                })
        
        # Validate student for attendance
        is_valid, validation_error = StudentIdentificationService.validate_student_for_attendance(student)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': validation_error['error'],
                'error_code': validation_error['error_code']
            })
        
        # Log successful identification
        StudentIdentificationService.log_identification_attempt(qr_data, student, True)
        
        # Process QR scan with comprehensive edge case handling
        from app.services.attendance_state_service import AttendanceStateService
        from app.services.time_management_service import TimeManagementService
        
        # Get client information for tracking
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        # Process the scan using the comprehensive state service
        result = AttendanceStateService.process_attendance_scan(
            student_id=student.id,
            room_id=session.room_id,
            session_id=session.id,
            scanned_by=current_user.id,
            scan_type=scan_type,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Add additional time analysis if successful
        if result['success'] and result['action'] in ['time_in', 'time_out']:
            # Get comprehensive time info for debugging
            time_info = TimeManagementService.get_current_time_info()
            result['debug_time_info'] = time_info
            
            # If this was a time_out, add duration analysis
            if result['action'] == 'time_out':
                duration_analysis = TimeManagementService.calculate_duration_safe(
                    datetime.fromisoformat(result['time_in'].replace('Z', '')),
                    datetime.fromisoformat(result['time_out'].replace('Z', ''))
                )
                result['duration_analysis'] = {
                    'warnings': duration_analysis.get('warnings', []),
                    'corrections_applied': duration_analysis.get('corrections_applied', []),
                    'is_reasonable_duration': duration_analysis.get('is_reasonable_duration', True)
                }
        
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing QR scan: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to process scan: {str(e)}'})
        
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
    """Get recent attendance scans with time-in/time-out information"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent records ordered by latest activity (time_in or time_out)
        recent_scans = db.session.query(
            AttendanceRecord,
            Student,
            Room,
            AttendanceSession
        ).join(
            Student, AttendanceRecord.student_id == Student.id
        ).join(
            AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
        ).join(
            Room, AttendanceSession.room_id == Room.id
        ).order_by(
            # Order by most recent activity (time_out if exists, otherwise time_in)
            func.coalesce(AttendanceRecord.time_out, AttendanceRecord.time_in).desc()
        ).limit(limit).all()
        
        scans_data = []
        for record, student, room, session in recent_scans:
            student_name = f"{student.first_name} {student.last_name}".strip()
            
            # Determine the most recent action
            if record.time_out:
                last_action_time = record.time_out
                action_type = 'time_out'
                action_text = 'Timed Out'
            else:
                last_action_time = record.time_in
                action_type = 'time_in'
                action_text = 'Timed In'
            
            time_ago = get_time_ago(last_action_time)
            
            scans_data.append({
                'student_name': student_name,
                'student_no': student.student_no,
                'room_name': room.room_name,
                'session_name': session.session_name,
                'action_type': action_type,
                'action_text': action_text,
                'timestamp': last_action_time.isoformat(),
                'time_ago': time_ago,
                'is_late': record.is_late,
                'is_active': record.is_active,
                'duration_minutes': record.get_duration() if record.time_out else None,
                'status': record.get_status()
            })
        
        return jsonify(scans_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent scans: {str(e)}")
        return jsonify([])

@scanner.route('/api/session-stats/<int:session_id>')
@login_required
def api_get_session_stats(session_id):
    """Get statistics for a specific session including time-in/time-out data"""
    try:
        today = datetime.now().date()
        
        # Get all records for this session today
        session_records = AttendanceRecord.query.filter(
            and_(
                AttendanceRecord.session_id == session_id,
                func.date(AttendanceRecord.time_in) == today
            )
        ).all()
        
        # Calculate statistics
        total_time_ins = len(session_records)
        completed_visits = len([r for r in session_records if r.time_out])
        currently_in_room = len([r for r in session_records if r.is_active])
        unique_students = len(set(r.student_id for r in session_records))
        late_arrivals = len([r for r in session_records if r.is_late])
        
        # Calculate average duration for completed visits
        completed_records = [r for r in session_records if r.time_out]
        avg_duration = 0
        if completed_records:
            total_duration = sum(r.get_duration() for r in completed_records)
            avg_duration = round(total_duration / len(completed_records), 1)
        
        return jsonify({
            'total_time_ins': total_time_ins,
            'completed_visits': completed_visits,
            'currently_in_room': currently_in_room,
            'unique_students': unique_students,
            'late_arrivals': late_arrivals,
            'avg_duration_minutes': avg_duration
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching session stats: {str(e)}")
        return jsonify({
            'total_time_ins': 0,
            'completed_visits': 0,
            'currently_in_room': 0,
            'unique_students': 0,
            'late_arrivals': 0,
            'avg_duration_minutes': 0
        })

@scanner.route('/api/today-stats')
@login_required
def api_get_today_stats():
    """Get overall statistics for today including time-in/time-out data"""
    try:
        today = datetime.now().date()
        
        # Get all records for today
        today_records = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.time_in) == today
        ).all()
        
        # Calculate statistics
        total_time_ins = len(today_records)
        completed_visits = len([r for r in today_records if r.time_out])
        currently_in_rooms = len([r for r in today_records if r.is_active])
        unique_students = len(set(r.student_id for r in today_records))
        
        return jsonify({
            'total_time_ins': total_time_ins,
            'completed_visits': completed_visits,
            'currently_in_rooms': currently_in_rooms,
            'unique_students': unique_students
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching today stats: {str(e)}")
        return jsonify({
            'total_time_ins': 0,
            'completed_visits': 0,
            'currently_in_rooms': 0,
            'unique_students': 0
        })

@scanner.route('/api/current-occupancy/<int:session_id>')
@login_required
def api_get_current_occupancy(session_id):
    """Get students currently in the room for a session"""
    try:
        # Get session details
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Get students currently in the room
        current_students = db.session.query(
            AttendanceRecord,
            Student
        ).join(
            Student, AttendanceRecord.student_id == Student.id
        ).filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.is_active == True
        ).order_by(
            AttendanceRecord.time_in.asc()
        ).all()
        
        occupancy_data = []
        for record, student in current_students:
            occupancy_data.append({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'student_no': student.student_no,
                'time_in': record.time_in.isoformat(),
                'duration_minutes': record.get_duration(),
                'is_late': record.is_late
            })
        
        return jsonify({
            'success': True,
            'session_name': session.session_name,
            'room_name': session.room.room_name if session.room else 'Unknown',
            'current_occupancy': len(occupancy_data),
            'students': occupancy_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching current occupancy: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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