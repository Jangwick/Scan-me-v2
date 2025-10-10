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
        session_id = request.args.get('session_id', type=int)  # SESSION ISOLATION
        department = request.args.get('department')
        status_filter = request.args.get('status_filter')
        limit = request.args.get('limit', 100, type=int)
        
        # Build query with joins for student data (needed for department filter)
        query = AttendanceRecord.query
        
        # Join with Student table if department filter is provided
        if department:
            from app.models.student_model import Student
            query = query.join(Student, AttendanceRecord.student_id == Student.id)
            query = query.filter(Student.department == department)
        
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
        
        # SESSION ISOLATION: Filter by session if provided
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        
        # Status filter
        if status_filter:
            if status_filter == 'on_time':
                query = query.filter(AttendanceRecord.is_late == False)
            elif status_filter == 'late':
                query = query.filter(AttendanceRecord.is_late == True)
            elif status_filter == 'duplicate':
                query = query.filter(AttendanceRecord.is_duplicate == True)
        
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
        session_id = request.args.get('session_id', type=int)  # SESSION ISOLATION
        department = request.args.get('department')
        status_filter = request.args.get('status_filter')
        
        # Build query with joins for student data (needed for department filter)
        query = AttendanceRecord.query
        
        # Join with Student table if department filter is provided
        if department:
            from app.models.student_model import Student
            query = query.join(Student, AttendanceRecord.student_id == Student.id)
            query = query.filter(Student.department == department)
        
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
        
        # SESSION ISOLATION: Filter by session if provided
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        
        # Status filter
        if status_filter:
            if status_filter == 'on_time':
                query = query.filter(AttendanceRecord.is_late == False)
            elif status_filter == 'late':
                query = query.filter(AttendanceRecord.is_late == True)
            elif status_filter == 'duplicate':
                query = query.filter(AttendanceRecord.is_duplicate == True)
        
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

@attendance_bp.route('/student/<int:student_id>')
@login_required
@requires_professor_or_admin
def view_student_attendance(student_id):
    """View attendance records for a specific student"""
    try:
        from app.models.student_model import Student
        
        student = Student.query.get_or_404(student_id)
        
        # Get date range from request args
        end_date = request.args.get('end_date', date.today().isoformat())
        start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
        
        # Parse dates
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            start_date_obj = date.today() - timedelta(days=30)
            end_date_obj = date.today()
            start_date = start_date_obj.isoformat()
            end_date = end_date_obj.isoformat()
        
        # Get attendance records for this student
        records = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            db.func.date(AttendanceRecord.scan_time) >= start_date_obj,
            db.func.date(AttendanceRecord.scan_time) <= end_date_obj
        ).order_by(AttendanceRecord.scan_time.desc()).all()
        
        # Get attendance statistics
        attendance_stats = student.get_attendance_stats(
            datetime.combine(start_date_obj, datetime.min.time()),
            datetime.combine(end_date_obj, datetime.max.time())
        )
        
        return render_template('attendance/student_attendance.html',
                             student=student,
                             records=records,
                             attendance_stats=attendance_stats,
                             start_date=start_date,
                             end_date=end_date)
        
    except Exception as e:
        flash(f'Error loading student attendance: {str(e)}', 'error')
        return redirect(url_for('students.view_student', id=student_id))

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

@attendance_bp.route('/sessions/<int:session_id>')
@login_required
@requires_professor_or_admin
def view_session(session_id):
    """View individual session details"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Get attendance records for this session
        attendance_records = AttendanceRecord.query.filter_by(session_id=session_id)\
            .order_by(AttendanceRecord.time_in.desc()).all()
        
        # Get session statistics
        session_stats = session.get_attendance_summary()
        
        # Get currently active students in this session
        active_students = AttendanceRecord.query.filter_by(
            session_id=session_id,
            is_active=True
        ).all()
        
        return render_template('attendance/session_detail.html', 
                             session=session,
                             attendance_records=attendance_records,
                             session_stats=session_stats,
                             active_students=active_students)
    
    except Exception as e:
        flash(f'Error loading session: {str(e)}', 'error')
        return redirect(url_for('attendance.manage_sessions'))

@attendance_bp.route('/sessions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_professor_or_admin
def edit_session(id):
    """Edit an existing attendance session"""
    try:
        session = AttendanceSession.query.get_or_404(id)
        
        if request.method == 'POST':
            # Update session details
            session.session_name = request.form.get('session_name')
            session.subject = request.form.get('subject')
            session.instructor = request.form.get('instructor')
            session.expected_students = int(request.form.get('expected_students', 0))
            
            # Parse start and end times
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            
            if start_time_str:
                # Parse time and combine with today's date
                time_obj = datetime.strptime(start_time_str, '%H:%M').time()
                session.start_time = datetime.combine(datetime.now().date(), time_obj)
            if end_time_str:
                # Parse time and combine with today's date
                time_obj = datetime.strptime(end_time_str, '%H:%M').time()
                session.end_time = datetime.combine(datetime.now().date(), time_obj)
            
            # Update room if provided
            room_id = request.form.get('room_id')
            if room_id:
                session.room_id = int(room_id)
            
            db.session.commit()
            flash('Session updated successfully!', 'success')
            return redirect(url_for('attendance.view_session', session_id=session.id))
        
        # GET request - show edit form
        rooms = Room.query.filter_by(is_active=True).all()
        
        return render_template('attendance/edit_session.html', 
                             session=session,
                             rooms=rooms)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating session: {str(e)}', 'error')
        return redirect(url_for('attendance.manage_sessions'))

@attendance_bp.route('/sessions/<int:session_id>/qr')
@login_required
@requires_professor_or_admin
def session_qr(session_id):
    """Generate QR code for session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # For now, redirect to the main session view
        # In a full implementation, this would generate/display a QR code
        flash('QR code generation feature coming soon!', 'info')
        return redirect(url_for('attendance.view_session', session_id=session_id))
        
    except Exception as e:
        flash(f'Error generating QR code: {str(e)}', 'error')
        return redirect(url_for('attendance.manage_sessions'))

@attendance_bp.route('/sessions/<int:session_id>/attendance')
@login_required
@requires_professor_or_admin
def session_attendance(session_id):
    """View attendance for specific session"""
    try:
        session = AttendanceSession.query.get_or_404(session_id)
        
        # Get attendance records for this session
        attendance_records = AttendanceRecord.query.filter_by(
            session_id=session_id
        ).join(Student).order_by(Student.last_name, Student.first_name).all()
        
        return render_template('attendance/session_attendance.html',
                             session=session,
                             attendance_records=attendance_records)
        
    except Exception as e:
        flash(f'Error loading session attendance: {str(e)}', 'error')
        return redirect(url_for('attendance.manage_sessions'))

@attendance_bp.route('/api/attendance-trends')
@login_required
@requires_professor_or_admin
def get_attendance_trends():
    """Get attendance trends for the last 30 days"""
    try:
        # Get date range (last 30 days)
        from datetime import datetime as dt
        end_date = date.today()
        start_date = end_date - timedelta(days=29)
        
        # Convert to datetime for comparison
        start_datetime = dt.combine(start_date, dt.min.time())
        end_datetime = dt.combine(end_date, dt.max.time())
        
        # Query attendance records grouped by date
        from sqlalchemy import func
        
        # Use func.date() to extract date from datetime
        daily_stats = db.session.query(
            func.date(AttendanceRecord.time_in).label('date'),
            func.count(AttendanceRecord.id).label('total_scans'),
            func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students')
        ).filter(
            AttendanceRecord.time_in >= start_datetime,
            AttendanceRecord.time_in <= end_datetime
        ).group_by(
            func.date(AttendanceRecord.time_in)
        ).order_by(
            func.date(AttendanceRecord.time_in)
        ).all()
        
        # Format data for chart
        dates = []
        total_scans = []
        unique_students = []
        
        # Create a complete date range
        current_date = start_date
        date_map = {}
        
        # Convert string dates from query to date objects
        for stat in daily_stats:
            if stat.date:
                # Parse the date string
                if isinstance(stat.date, str):
                    date_obj = dt.strptime(stat.date, '%Y-%m-%d').date()
                else:
                    date_obj = stat.date
                date_map[date_obj] = stat
        
        # Build complete date range with all days
        while current_date <= end_date:
            dates.append(current_date.strftime('%b %d'))
            
            if current_date in date_map:
                stat = date_map[current_date]
                total_scans.append(stat.total_scans)
                unique_students.append(stat.unique_students)
            else:
                total_scans.append(0)
                unique_students.append(0)
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'dates': dates,
            'total_scans': total_scans,
            'unique_students': unique_students
        })
        
    except Exception as e:
        import traceback
        print(f"Error in get_attendance_trends: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@attendance_bp.route('/api/department-breakdown')
@login_required
@requires_professor_or_admin
def get_department_breakdown():
    """Get attendance breakdown by department"""
    try:
        from sqlalchemy import func
        
        # Query attendance records with student department info
        department_stats = db.session.query(
            Student.department,
            func.count(AttendanceRecord.id).label('total_records'),
            func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students')
        ).join(
            AttendanceRecord, Student.id == AttendanceRecord.student_id
        ).group_by(
            Student.department
        ).order_by(
            func.count(AttendanceRecord.id).desc()
        ).all()
        
        # Format data for chart
        departments = []
        attendance_counts = []
        student_counts = []
        
        for stat in department_stats:
            if stat.department:  # Skip null departments
                departments.append(stat.department)
                attendance_counts.append(stat.total_records)
                student_counts.append(stat.unique_students)
        
        return jsonify({
            'success': True,
            'departments': departments,
            'attendance_counts': attendance_counts,
            'student_counts': student_counts
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@attendance_bp.route('/api/analytics-insights')
@login_required
@requires_professor_or_admin
def get_analytics_insights():
    """Get analytics insights for top classes, peak hours, and areas for improvement"""
    try:
        from sqlalchemy import func, extract
        
        # Top performing classes (by session)
        top_sessions = db.session.query(
            AttendanceSession.session_name,
            AttendanceSession.subject,
            func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students'),
            func.count(AttendanceRecord.id).label('total_scans'),
            AttendanceSession.expected_students
        ).join(
            AttendanceRecord, AttendanceSession.id == AttendanceRecord.session_id
        ).group_by(
            AttendanceSession.id
        ).order_by(
            func.count(func.distinct(AttendanceRecord.student_id)).desc()
        ).limit(4).all()
        
        top_classes = []
        for session in top_sessions:
            attendance_rate = 0
            if session.expected_students and session.expected_students > 0:
                attendance_rate = round((session.unique_students / session.expected_students) * 100, 1)
            
            top_classes.append({
                'name': f"{session.subject or session.session_name}",
                'attendance_rate': attendance_rate,
                'students': session.unique_students
            })
        
        # Peak hours (attendance by hour)
        peak_hours_data = db.session.query(
            extract('hour', AttendanceRecord.time_in).label('hour'),
            func.count(AttendanceRecord.id).label('count')
        ).group_by(
            extract('hour', AttendanceRecord.time_in)
        ).order_by(
            func.count(AttendanceRecord.id).desc()
        ).limit(4).all()
        
        peak_hours = []
        for hour_stat in peak_hours_data:
            hour = int(hour_stat.hour)
            count = hour_stat.count
            
            # Format hour
            start_hour = hour % 12 if hour % 12 != 0 else 12
            end_hour = (hour + 1) % 12 if (hour + 1) % 12 != 0 else 12
            start_period = 'AM' if hour < 12 else 'PM'
            end_period = 'AM' if hour + 1 < 12 else 'PM'
            
            # Determine activity level
            if count > 50:
                activity = 'High activity'
            elif count > 20:
                activity = 'Medium activity'
            else:
                activity = 'Low activity'
            
            peak_hours.append({
                'time_range': f"{start_hour}:00 {start_period} - {end_hour}:00 {end_period}",
                'activity': activity,
                'count': count
            })
        
        # Areas for improvement
        # 1. Late arrivals percentage
        total_records = AttendanceRecord.query.count()
        late_arrivals = AttendanceRecord.query.filter_by(is_late=True).count()
        late_percentage = round((late_arrivals / total_records * 100), 1) if total_records > 0 else 0
        
        # 2. Friday attendance (typically lower)
        friday_records = db.session.query(
            func.count(AttendanceRecord.id)
        ).filter(
            extract('dow', AttendanceRecord.time_in) == 5  # Friday
        ).scalar() or 0
        
        # 3. Room with issues (duplicate scans)
        problem_rooms = db.session.query(
            Room.room_name,
            func.count(AttendanceRecord.id).label('issues')
        ).join(
            AttendanceRecord, Room.id == AttendanceRecord.room_id
        ).filter(
            AttendanceRecord.is_duplicate == True
        ).group_by(
            Room.id
        ).order_by(
            func.count(AttendanceRecord.id).desc()
        ).first()
        
        # 4. Duplicate scans
        duplicate_scans = AttendanceRecord.query.filter_by(is_duplicate=True).count()
        duplicate_percentage = round((duplicate_scans / total_records * 100), 1) if total_records > 0 else 0
        
        improvements = [
            {
                'metric': 'Late arrivals',
                'value': f"{late_percentage}% of records",
                'count': late_arrivals
            },
            {
                'metric': 'Friday classes',
                'value': 'Lower attendance',
                'count': friday_records
            }
        ]
        
        if problem_rooms:
            improvements.append({
                'metric': f"Room {problem_rooms.room_name}",
                'value': 'Technical issues',
                'count': problem_rooms.issues
            })
        
        improvements.append({
            'metric': 'Duplicate scans',
            'value': f"{duplicate_percentage}% of records",
            'count': duplicate_scans
        })
        
        return jsonify({
            'success': True,
            'top_classes': top_classes,
            'peak_hours': peak_hours,
            'improvements': improvements
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500