"""
Schedule Routes for ScanMe Attendance System
Handles session scheduling and management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
from sqlalchemy import func
from app import db
from app.models.session_schedule_model import SessionSchedule, SessionStatus, RecurrenceType
from app.models.room_model import Room
from app.models.user_model import User
from app.utils.auth_utils import requires_admin

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')

@schedule_bp.route('/')
@login_required
def schedule_overview():
    """Schedule overview dashboard"""
    try:
        # Get upcoming sessions
        today = date.today()
        upcoming_sessions = SessionSchedule.query.filter(
            SessionSchedule.session_date >= today,
            SessionSchedule.status == SessionStatus.SCHEDULED
        ).order_by(SessionSchedule.session_date, SessionSchedule.start_time).limit(10).all()
        
        # Get today's sessions
        today_sessions = SessionSchedule.query.filter(
            SessionSchedule.session_date == today
        ).order_by(SessionSchedule.start_time).all()
        
        # Get statistics
        total_sessions = SessionSchedule.query.count()
        active_sessions = SessionSchedule.query.filter(
            SessionSchedule.status == SessionStatus.ACTIVE
        ).count()
        
        return render_template('schedule/overview.html',
                             upcoming_sessions=upcoming_sessions,
                             today_sessions=today_sessions,
                             total_sessions=total_sessions,
                             active_sessions=active_sessions)
    except Exception as e:
        flash(f'Error loading schedule: {str(e)}', 'error')
        return render_template('schedule/overview.html',
                             upcoming_sessions=[],
                             today_sessions=[],
                             total_sessions=0,
                             active_sessions=0)

@schedule_bp.route('/sessions')
@login_required
def manage_sessions():
    """Manage all sessions"""
    try:
        # Get filter parameters
        room_id = request.args.get('room_id', type=int)
        status_filter = request.args.get('status', 'all')
        date_filter = request.args.get('date', 'all')
        
        # Base query
        query = SessionSchedule.query
        
        # Apply filters
        if room_id:
            query = query.filter(SessionSchedule.room_id == room_id)
        
        if status_filter != 'all':
            try:
                status = SessionStatus(status_filter)
                query = query.filter(SessionSchedule.status == status)
            except ValueError:
                pass
        
        if date_filter == 'today':
            query = query.filter(SessionSchedule.session_date == date.today())
        elif date_filter == 'week':
            week_start = date.today() - timedelta(days=date.today().weekday())
            week_end = week_start + timedelta(days=6)
            query = query.filter(SessionSchedule.session_date.between(week_start, week_end))
        elif date_filter == 'upcoming':
            query = query.filter(SessionSchedule.session_date >= date.today())
        
        # Order and get results
        sessions = query.order_by(
            SessionSchedule.session_date.desc(),
            SessionSchedule.start_time
        ).all()
        
        # Get rooms for filter dropdown
        rooms = Room.query.filter(Room.is_active == True).order_by(Room.building, Room.room_number).all()
        
        return render_template('schedule/manage_sessions.html',
                             sessions=sessions,
                             rooms=rooms,
                             current_room_id=room_id,
                             current_status=status_filter,
                             current_date=date_filter)
    except Exception as e:
        flash(f'Error loading sessions: {str(e)}', 'error')
        return render_template('schedule/manage_sessions.html',
                             sessions=[], rooms=[],
                             current_room_id=None,
                             current_status='all',
                             current_date='all')

@schedule_bp.route('/sessions/add', methods=['GET', 'POST'])
@login_required
@requires_admin
def add_session():
    """Add new session"""
    if request.method == 'POST':
        try:
            # Get form data
            session_data = {
                'title': request.form.get('title', '').strip(),
                'description': request.form.get('description', '').strip(),
                'room_id': request.form.get('room_id', type=int),
                'instructor_id': request.form.get('instructor_id', type=int, default=current_user.id),
                'session_date': datetime.strptime(request.form.get('session_date'), '%Y-%m-%d').date(),
                'start_time': datetime.strptime(request.form.get('start_time'), '%H:%M').time(),
                'end_time': datetime.strptime(request.form.get('end_time'), '%H:%M').time(),
                'max_attendees': request.form.get('max_attendees', type=int),
                'is_mandatory': request.form.get('is_mandatory') == 'on',
                'requires_registration': request.form.get('requires_registration') == 'on',
                'attendance_window_minutes': request.form.get('attendance_window_minutes', type=int, default=15),
                'recurrence_type': RecurrenceType(request.form.get('recurrence_type', 'none')),
                'recurrence_interval': request.form.get('recurrence_interval', type=int, default=1),
                'recurrence_end_date': None
            }
            
            # Parse recurrence end date if provided
            if request.form.get('recurrence_end_date'):
                session_data['recurrence_end_date'] = datetime.strptime(
                    request.form.get('recurrence_end_date'), '%Y-%m-%d'
                ).date()
            
            # Validate session data
            validation_result = validate_session_data(session_data)
            if not validation_result['valid']:
                for error in validation_result['errors']:
                    flash(error, 'error')
                return render_template('schedule/add_session.html',
                                     rooms=get_active_rooms(),
                                     instructors=get_instructors(),
                                     session_data=session_data,
                                     today=date.today())
            
            # Create main session
            session = SessionSchedule(**session_data)
            db.session.add(session)
            
            # Generate recurring sessions if needed
            if session_data['recurrence_type'] != RecurrenceType.NONE and session_data['recurrence_end_date']:
                recurring_sessions = session.generate_recurring_sessions()
                for recurring_data in recurring_sessions:
                    recurring_session = SessionSchedule(**recurring_data)
                    db.session.add(recurring_session)
            
            db.session.commit()
            
            flash(f'Session "{session.title}" created successfully!', 'success')
            return redirect(url_for('schedule.manage_sessions'))
            
        except ValueError as e:
            flash(f'Invalid date/time format: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating session: {str(e)}', 'error')
    
    # GET request - show form
    return render_template('schedule/add_session.html',
                         rooms=get_active_rooms(),
                         instructors=get_instructors(),
                         session_data={},
                         today=date.today())

@schedule_bp.route('/sessions/<int:id>/view')
@login_required
def view_session(id):
    """View session details"""
    try:
        session = SessionSchedule.query.get_or_404(id)
        return render_template('schedule/view_session.html', session=session)
    except Exception as e:
        flash(f'Error loading session details: {str(e)}', 'error')
        return redirect(url_for('schedule.manage_sessions'))

@schedule_bp.route('/sessions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(id):
    """Edit session details"""
    session = SessionSchedule.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_admin and session.instructor_id != current_user.id:
        flash('You can only edit your own sessions.', 'error')
        return redirect(url_for('schedule.view_session', id=id))
    
    if request.method == 'POST':
        try:
            # Update session data
            session.title = request.form.get('title', '').strip()
            session.description = request.form.get('description', '').strip()
            session.room_id = request.form.get('room_id', type=int)
            session.session_date = datetime.strptime(request.form.get('session_date'), '%Y-%m-%d').date()
            session.start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
            session.end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
            session.max_attendees = request.form.get('max_attendees', type=int)
            session.is_mandatory = request.form.get('is_mandatory') == 'on'
            session.requires_registration = request.form.get('requires_registration') == 'on'
            session.attendance_window_minutes = request.form.get('attendance_window_minutes', type=int, default=15)
            
            # Recalculate duration
            session.duration_minutes = session._calculate_duration(session.start_time, session.end_time)
            
            db.session.commit()
            
            flash(f'Session "{session.title}" updated successfully!', 'success')
            return redirect(url_for('schedule.view_session', id=id))
            
        except ValueError as e:
            flash(f'Invalid date/time format: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating session: {str(e)}', 'error')
    
    return render_template('schedule/edit_session.html',
                         session=session,
                         rooms=get_active_rooms(),
                         instructors=get_instructors(),
                         today=date.today())

@schedule_bp.route('/sessions/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_session(id):
    """Cancel a session"""
    try:
        session = SessionSchedule.query.get_or_404(id)
        
        # Check permissions
        if not current_user.is_admin and session.instructor_id != current_user.id:
            flash('You can only cancel your own sessions.', 'error')
            return redirect(url_for('schedule.view_session', id=id))
        
        session.status = SessionStatus.CANCELLED
        db.session.commit()
        
        flash(f'Session "{session.title}" has been cancelled.', 'success')
        return redirect(url_for('schedule.manage_sessions'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling session: {str(e)}', 'error')
        return redirect(url_for('schedule.view_session', id=id))

@schedule_bp.route('/sessions/<int:id>/start', methods=['POST'])
@login_required
def start_session(id):
    """Start a session"""
    try:
        session = SessionSchedule.query.get_or_404(id)
        
        # Check permissions
        if not current_user.is_admin and session.instructor_id != current_user.id:
            flash('You can only start your own sessions.', 'error')
            return redirect(url_for('schedule.view_session', id=id))
        
        # Check if session can be started
        if session.status != SessionStatus.SCHEDULED:
            flash('Only scheduled sessions can be started.', 'error')
            return redirect(url_for('schedule.view_session', id=id))
        
        session.status = SessionStatus.ACTIVE
        db.session.commit()
        
        flash(f'Session "{session.title}" started successfully!', 'success')
        return redirect(url_for('schedule.manage_sessions'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting session: {str(e)}', 'error')
        return redirect(url_for('schedule.view_session', id=id))

@schedule_bp.route('/sessions/<int:id>/delete', methods=['POST'])
@login_required
@requires_admin
def delete_session(id):
    """Delete a session completely"""
    try:
        session = SessionSchedule.query.get_or_404(id)
        session_title = session.title
        
        # Get force delete parameter
        force_delete = request.form.get('force_delete') == 'true'
        
        # Import attendance models to check for related records
        from app.models.attendance_model import AttendanceRecord
        from app.models.attendance_event_model import AttendanceEvent
        
        # Check for related attendance records and events
        attendance_count = AttendanceRecord.query.filter_by(session_id=session.id).count()
        event_count = AttendanceEvent.query.filter_by(session_id=session.id).count()
        
        has_related_data = attendance_count > 0 or event_count > 0
        
        if has_related_data and not force_delete:
            # Provide detailed information about what's preventing deletion
            details = []
            if attendance_count > 0:
                details.append(f"{attendance_count} attendance record(s)")
            if event_count > 0:
                details.append(f"{event_count} attendance event(s)")
            
            flash(f'Cannot delete session "{session_title}" because it has {", ".join(details)}. Cancel the session instead, or use force delete to remove all related data.', 'error')
            return redirect(url_for('schedule.view_session', id=id))
        
        if force_delete and has_related_data:
            # Force delete: Remove all related records first
            try:
                # Delete attendance events first (they may reference attendance records)
                AttendanceEvent.query.filter_by(session_id=session.id).delete(synchronize_session=False)
                
                # Delete attendance records
                AttendanceRecord.query.filter_by(session_id=session.id).delete(synchronize_session=False)
                
                flash(f'Force deleted session "{session_title}" and removed {attendance_count} attendance records and {event_count} events.', 'warning')
            except Exception as e:
                db.session.rollback()
                flash(f'Error during force delete: {str(e)}', 'error')
                return redirect(url_for('schedule.view_session', id=id))
        
        # Delete the session
        db.session.delete(session)
        db.session.commit()
        
        if not force_delete:
            flash(f'Session "{session_title}" deleted successfully.', 'success')
        
        return redirect(url_for('schedule.manage_sessions'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting session: {str(e)}', 'error')
        return redirect(url_for('schedule.view_session', id=id))

@schedule_bp.route('/sessions/<int:id>/delete-info')
@login_required
@requires_admin
def delete_session_info(id):
    """Get information about session deletion impact (AJAX endpoint)"""
    try:
        session = SessionSchedule.query.get_or_404(id)
        
        # Import attendance models
        from app.models.attendance_model import AttendanceRecord
        from app.models.attendance_event_model import AttendanceEvent
        
        # Check for related data
        attendance_count = AttendanceRecord.query.filter_by(session_id=session.id).count()
        event_count = AttendanceEvent.query.filter_by(session_id=session.id).count()
        
        # Get some sample student names affected
        affected_students = db.session.query(
            AttendanceRecord.student_id,
            func.count(AttendanceRecord.id).label('record_count')
        ).filter_by(session_id=session.id).group_by(AttendanceRecord.student_id).limit(5).all()
        
        student_info = []
        if affected_students:
            from app.models.student_model import Student
            for student_id, record_count in affected_students:
                student = Student.query.get(student_id)
                if student:
                    student_info.append({
                        'name': student.get_full_name(),
                        'record_count': record_count
                    })
        
        return jsonify({
            'success': True,
            'session_title': session.title,
            'can_delete_safely': attendance_count == 0 and event_count == 0,
            'attendance_count': attendance_count,
            'event_count': event_count,
            'affected_students': student_info,
            'total_affected_students': len(affected_students)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@schedule_bp.route('/sessions/bulk-delete', methods=['POST'])
@login_required
@requires_admin
def bulk_delete_sessions():
    """Delete multiple sessions at once"""
    try:
        session_ids = request.form.getlist('session_ids')
        force_delete = request.form.get('force_delete') == 'true'
        
        if not session_ids:
            flash('No sessions selected for deletion.', 'error')
            return redirect(url_for('schedule.manage_sessions'))
        
        # Convert to integers
        session_ids = [int(sid) for sid in session_ids]
        
        # Import attendance models
        from app.models.attendance_model import AttendanceRecord
        from app.models.attendance_event_model import AttendanceEvent
        
        deleted_count = 0
        skipped_count = 0
        force_deleted_count = 0
        
        for session_id in session_ids:
            try:
                session = SessionSchedule.query.get(session_id)
                if not session:
                    continue
                
                # Check for related data
                attendance_count = AttendanceRecord.query.filter_by(session_id=session.id).count()
                event_count = AttendanceEvent.query.filter_by(session_id=session.id).count()
                has_related_data = attendance_count > 0 or event_count > 0
                
                if has_related_data and not force_delete:
                    skipped_count += 1
                    continue
                
                if force_delete and has_related_data:
                    # Delete related records first
                    AttendanceEvent.query.filter_by(session_id=session.id).delete(synchronize_session=False)
                    AttendanceRecord.query.filter_by(session_id=session.id).delete(synchronize_session=False)
                    force_deleted_count += 1
                
                # Delete the session
                db.session.delete(session)
                deleted_count += 1
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting session {session_id}: {str(e)}', 'error')
                continue
        
        db.session.commit()
        
        # Provide summary feedback
        messages = []
        if deleted_count > 0:
            messages.append(f"{deleted_count} sessions deleted successfully")
        if force_deleted_count > 0:
            messages.append(f"{force_deleted_count} sessions force-deleted with attendance data")
        if skipped_count > 0:
            messages.append(f"{skipped_count} sessions skipped due to attendance data")
        
        if messages:
            flash('. '.join(messages) + '.', 'success' if skipped_count == 0 else 'warning')
        else:
            flash('No sessions were deleted.', 'info')
        
        return redirect(url_for('schedule.manage_sessions'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during bulk deletion: {str(e)}', 'error')
        return redirect(url_for('schedule.manage_sessions'))

@schedule_bp.route('/api/check_room_availability')
@login_required
def check_room_availability():
    """AJAX endpoint to check room availability"""
    room_id = request.args.get('room_id', type=int)
    session_date = request.args.get('date')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    exclude_session_id = request.args.get('exclude_id', type=int)  # For editing
    
    if not all([room_id, session_date, start_time, end_time]):
        return jsonify({'available': True, 'conflicts': []})
    
    try:
        # Parse inputs
        check_date = datetime.strptime(session_date, '%Y-%m-%d').date()
        check_start = datetime.strptime(start_time, '%H:%M').time()
        check_end = datetime.strptime(end_time, '%H:%M').time()
        
        # Query for conflicting sessions
        query = SessionSchedule.query.filter(
            SessionSchedule.room_id == room_id,
            SessionSchedule.session_date == check_date,
            SessionSchedule.status.in_([SessionStatus.SCHEDULED, SessionStatus.ACTIVE])
        )
        
        # Exclude current session if editing
        if exclude_session_id:
            query = query.filter(SessionSchedule.id != exclude_session_id)
        
        existing_sessions = query.all()
        
        # Check for time conflicts
        conflicts = []
        for session in existing_sessions:
            if (check_start < session.end_time and check_end > session.start_time):
                conflicts.append({
                    'title': session.title,
                    'time': session.get_formatted_time(),
                    'instructor': session.instructor.get_display_name() if session.instructor else 'Unknown'
                })
        
        return jsonify({
            'available': len(conflicts) == 0,
            'conflicts': conflicts
        })
        
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})

def validate_session_data(data):
    """Validate session data"""
    errors = []
    
    # Required fields
    required_fields = ['title', 'room_id', 'session_date', 'start_time', 'end_time']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Validate times
    if data.get('start_time') and data.get('end_time'):
        if data['start_time'] >= data['end_time']:
            errors.append("End time must be after start time")
    
    # Validate date
    if data.get('session_date'):
        if data['session_date'] < date.today():
            errors.append("Session date cannot be in the past")
    
    # Validate room exists
    if data.get('room_id'):
        room = Room.query.get(data['room_id'])
        if not room:
            errors.append("Selected room does not exist")
        elif not room.is_active:
            errors.append("Selected room is not active")
    
    # Validate instructor exists
    if data.get('instructor_id'):
        instructor = User.query.get(data['instructor_id'])
        if not instructor:
            errors.append("Selected instructor does not exist")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def get_active_rooms():
    """Get list of active rooms"""
    return Room.query.filter(Room.is_active == True).order_by(Room.building, Room.room_number).all()

def get_instructors():
    """Get list of potential instructors"""
    return User.query.filter(User.is_active == True).order_by(User.username).all()