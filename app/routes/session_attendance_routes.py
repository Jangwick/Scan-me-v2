"""
Session Attendance Routes - Handle attendance for SessionSchedule classes
"""
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import SessionSchedule, Student, AttendanceRecord
from app import db
from app.services.new_attendance_service import NewAttendanceService
from datetime import datetime

session_attendance_bp = Blueprint('session_attendance', __name__, url_prefix='/session-attendance')

@session_attendance_bp.route('/process-scan', methods=['POST'])
@login_required
def process_scan():
    """
    Process QR code scan for scheduled session attendance
    """
    try:
        data = request.get_json()
        
        # Get required data
        student_qr_data = data.get('qr_data')
        session_id = data.get('session_id')
        
        if not student_qr_data or not session_id:
            return jsonify({
                'success': False,
                'error': 'Missing QR data or session ID'
            }), 400
        
        # Find student by QR code
        student = Student.get_by_qr_code(student_qr_data)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
        
        # Find session
        session = SessionSchedule.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Process attendance using the session's method
        result = session.process_student_attendance(
            student_id=student.id,
            scanned_by_user_id=current_user.id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'action': result['action'],
                'student': {
                    'id': student.id,
                    'name': student.get_full_name(),
                    'student_no': student.student_no,
                    'department': student.department,
                    'section': student.section
                },
                'session': {
                    'id': session.id,
                    'title': session.title,
                    'time': session.get_formatted_time()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        }), 500

@session_attendance_bp.route('/session/<int:session_id>/attendance', methods=['GET'])
@login_required
def get_session_attendance(session_id):
    """
    Get attendance data for a specific session
    """
    try:
        session = SessionSchedule.query.get_or_404(session_id)
        
        # Check if user has access to this session
        if session.instructor_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get attendance summary
        summary = session.get_session_attendance_summary()
        
        # Get individual attendance records
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        attendance_list = []
        
        for record in records:
            student_data = {
                'student_id': record.student.id,
                'student_no': record.student.student_no,
                'name': record.student.get_full_name(),
                'department': record.student.department,
                'section': record.student.section,
                'time_in': record.time_in.strftime('%I:%M %p') if record.time_in else None,
                'time_out': record.time_out.strftime('%I:%M %p') if record.time_out else None,
                'duration': record.get_duration(),
                'is_late': record.is_late,
                'status': 'completed' if record.time_out else 'in_session'
            }
            attendance_list.append(student_data)
        
        return jsonify({
            'success': True,
            'session': {
                'id': session.id,
                'title': session.title,
                'date': session.get_formatted_date(),
                'time': session.get_formatted_time(),
                'status': session.get_status_display()
            },
            'summary': summary,
            'attendance': attendance_list
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving attendance: {str(e)}'
        }), 500

@session_attendance_bp.route('/session/<int:session_id>/status', methods=['GET'])
@login_required
def get_session_status(session_id):
    """
    Get current status of a session (active, can_time_in, etc.)
    """
    try:
        session = SessionSchedule.query.get_or_404(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session.id,
            'title': session.title,
            'is_active': session.is_active_now(),
            'can_time_in': session.can_time_in(),
            'can_time_out': session.can_time_out(),
            'status': session.get_status_display(),
            'time_range': session.get_formatted_time(),
            'date': session.get_formatted_date()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting session status: {str(e)}'
        }), 500

@session_attendance_bp.route('/session/<int:session_id>/manual-attendance', methods=['POST'])
@login_required
def manual_attendance():
    """
    Manually add/remove student attendance (for professors)
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        student_id = data.get('student_id')
        action = data.get('action')  # 'add_time_in', 'add_time_out', 'remove'
        
        session = SessionSchedule.query.get_or_404(session_id)
        
        # Check if user has permission
        if session.instructor_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        student = Student.query.get_or_404(student_id)
        
        if action == 'add_time_in':
            # Process as time in
            result = session.process_student_attendance(student_id, current_user.id)
            return jsonify(result)
        
        elif action == 'add_time_out':
            # Find existing record and time out
            record = AttendanceRecord.query.filter_by(
                student_id=student_id,
                session_id=session_id,
                time_out=None
            ).first()
            
            if record:
                record.time_out = datetime.utcnow()
                record.time_out_scanned_by = current_user.id
                record.is_active = False
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Manually timed out {student.get_full_name()}',
                    'action': 'time_out'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No active time-in record found for this student'
                }), 400
        
        elif action == 'remove':
            # Remove attendance record
            record = AttendanceRecord.query.filter_by(
                student_id=student_id,
                session_id=session_id
            ).first()
            
            if record:
                db.session.delete(record)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Removed attendance record for {student.get_full_name()}',
                    'action': 'remove'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No attendance record found for this student'
                }), 400
        
        else:
            return jsonify({'error': 'Invalid action'}), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error processing manual attendance: {str(e)}'
        }), 500