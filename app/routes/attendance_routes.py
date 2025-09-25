"""
Attendance Routes for ScanMe Attendance System
Handles attendance reports and analytics
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.student_model import Student
from app.models.room_model import Room
from app.utils.auth_utils import requires_professor_or_admin
from app.utils.export_utils import export_attendance_to_excel, export_attendance_to_csv, export_attendance_to_pdf
from datetime import datetime, date, timedelta

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/')
@login_required
@requires_professor_or_admin
def reports():
    """Attendance reports main page"""
    try:
        # Get filter options
        rooms = Room.get_active_rooms()
        students = Student.get_active_students()[:100]  # Limit for dropdown
        
        # Get date range
        end_date = request.args.get('end_date', date.today().isoformat())
        start_date = request.args.get('start_date', (date.today() - timedelta(days=7)).isoformat())
        
        return render_template('attendance/reports.html',
                             rooms=rooms,
                             students=students,
                             start_date=start_date,
                             end_date=end_date)
    
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return render_template('attendance/reports.html', rooms=[], students=[])

@attendance_bp.route('/api/records')
@login_required
@requires_professor_or_admin
def api_records():
    """API endpoint for attendance records"""
    try:
        # Get filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        room_id = request.args.get('room_id', type=int)
        student_id = request.args.get('student_id', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Build query
        query = AttendanceRecord.query
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AttendanceRecord.scan_time) >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AttendanceRecord.scan_time) <= end_date)
        
        if room_id:
            query = query.filter(AttendanceRecord.room_id == room_id)
        
        if student_id:
            query = query.filter(AttendanceRecord.student_id == student_id)
        
        records = query.order_by(AttendanceRecord.scan_time.desc()).limit(limit).all()
        
        return jsonify([record.to_dict() for record in records])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/export/<format>')
@login_required
@requires_professor_or_admin
def export_records(format):
    """Export attendance records"""
    try:
        # Get filters (same as api_records)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        room_id = request.args.get('room_id', type=int)
        student_id = request.args.get('student_id', type=int)
        
        # Build query
        query = AttendanceRecord.query
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AttendanceRecord.scan_time) >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AttendanceRecord.scan_time) <= end_date_obj)
        
        if room_id:
            query = query.filter(AttendanceRecord.room_id == room_id)
        
        if student_id:
            query = query.filter(AttendanceRecord.student_id == student_id)
        
        records = query.order_by(AttendanceRecord.scan_time.desc()).all()
        
        # Convert to export format
        export_data = [
            {
                'Date': record.scan_time.strftime('%Y-%m-%d'),
                'Time': record.scan_time.strftime('%H:%M:%S'),
                'Student Name': record.student.get_full_name() if record.student else 'Unknown',
                'Student No': record.student.student_no if record.student else 'N/A',
                'Department': record.student.department if record.student else 'N/A',
                'Room': record.room.get_full_name() if record.room else 'Unknown',
                'Building': record.room.building if record.room else 'N/A',
                'Is Late': 'Yes' if record.is_late else 'No',
                'Is Duplicate': 'Yes' if record.is_duplicate else 'No',
                'Scanner': record.scanned_by_user.username if record.scanned_by_user else 'System'
            }
            for record in records
        ]
        
        # Export based on format
        if format == 'excel':
            filename = export_attendance_to_excel(export_data)
        elif format == 'csv':
            filename = export_attendance_to_csv(export_data)
        elif format == 'pdf':
            filename = export_attendance_to_pdf(export_data, title="Attendance Report")
        else:
            flash('Invalid export format.', 'error')
            return redirect(url_for('attendance.reports'))
        
        if filename:
            return send_file(filename, as_attachment=True)
        else:
            flash('Error creating export file.', 'error')
            return redirect(url_for('attendance.reports'))
    
    except Exception as e:
        flash(f'Export error: {str(e)}', 'error')
        return redirect(url_for('attendance.reports'))

@attendance_bp.route('/sessions')
@login_required
@requires_professor_or_admin
def manage_sessions():
    """Manage attendance sessions"""
    try:
        sessions = AttendanceSession.get_active_sessions()
        rooms = Room.get_active_rooms()
        
        return render_template('attendance/sessions.html', sessions=sessions, rooms=rooms)
    
    except Exception as e:
        flash(f'Error loading sessions: {str(e)}', 'error')
        return render_template('attendance/sessions.html', sessions=[], rooms=[])

@attendance_bp.route('/sessions/add', methods=['GET', 'POST'])
@login_required
@requires_professor_or_admin
def add_session():
    """Add new attendance session"""
    if request.method == 'POST':
        try:
            session_data = {
                'room_id': request.form.get('room_id', type=int),
                'session_name': request.form.get('session_name', '').strip(),
                'subject': request.form.get('subject', '').strip(),
                'instructor': request.form.get('instructor', '').strip(),
                'start_time': datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M'),
                'end_time': datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M'),
                'expected_students': request.form.get('expected_students', 0, type=int),
                'created_by': current_user.id
            }
            
            session = AttendanceSession(**session_data)
            db.session.add(session)
            db.session.commit()
            
            flash('Attendance session created successfully!', 'success')
            return redirect(url_for('attendance.manage_sessions'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating session: {str(e)}', 'error')
    
    rooms = Room.get_active_rooms()
    return render_template('attendance/add_session.html', rooms=rooms)

@attendance_bp.route('/analytics')
@login_required
@requires_professor_or_admin
def analytics():
    """Attendance analytics dashboard"""
    try:
        # Get basic stats
        total_records = AttendanceRecord.query.count()
        unique_students = db.session.query(AttendanceRecord.student_id).distinct().count()
        
        # Weekly stats
        week_start = date.today() - timedelta(days=date.today().weekday())
        weekly_records = AttendanceRecord.query.filter(
            AttendanceRecord.scan_time >= week_start
        ).count()
        
        stats = {
            'total_records': total_records,
            'unique_students': unique_students,
            'weekly_records': weekly_records
        }
        
        return render_template('attendance/analytics.html', stats=stats)
    
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'error')
        return render_template('attendance/analytics.html', stats={})