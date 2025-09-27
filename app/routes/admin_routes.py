"""
Admin Routes for ScanMe Attendance System
Handles admin-only functions like user management and system settings
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user_model import User
from app.models.room_model import Room
from app.models.session_schedule_model import SessionSchedule, RecurrenceType
from app.utils.auth_utils import requires_admin, validate_room_data, get_user_permissions
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@requires_admin
def dashboard():
    """Admin dashboard"""
    try:
        stats = {
            'total_users': User.query.filter_by(is_active=True).count(),
            'total_rooms': Room.query.filter_by(is_active=True).count(),
            'admin_count': User.query.filter_by(role='admin', is_active=True).count(),
            'professor_count': User.query.filter_by(role='professor', is_active=True).count(),
            'student_count': User.query.filter_by(role='student', is_active=True).count()
        }
        
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html', stats=stats, recent_users=recent_users)
    
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', stats={}, recent_users=[])

@admin_bp.route('/users')
@login_required
@requires_admin
def manage_users():
    """Manage users page"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return render_template('admin/users.html', users=[])

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@requires_admin
def add_user():
    """Add new user"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            role = request.form.get('role', 'student')
            
            user = User.create_user(username, email, password, role)
            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('admin/add_user.html')

@admin_bp.route('/rooms')
@login_required
@requires_admin
def manage_rooms():
    """Manage rooms page"""
    try:
        rooms = Room.query.order_by(Room.building, Room.floor, Room.room_number).all()
        return render_template('admin/rooms.html', rooms=rooms)
    except Exception as e:
        flash(f'Error loading rooms: {str(e)}', 'error')
        return render_template('admin/rooms.html', rooms=[])

@admin_bp.route('/rooms/add', methods=['GET', 'POST'])
@login_required
@requires_admin
def add_room():
    """Add new room with optional session scheduling"""
    if request.method == 'POST':
        room_data = {
            'room_number': request.form.get('number', '').strip(),  # Fixed: 'number' not 'room_number'
            'room_name': request.form.get('name', '').strip(),      # Fixed: 'name' not 'room_name'
            'building': request.form.get('building', '').strip(),
            'floor': request.form.get('floor', type=int),
            'capacity': request.form.get('capacity', type=int),
            'room_type': request.form.get('type', 'classroom')      # Fixed: 'type' not 'room_type'
        }
        
        # Check if user wants to schedule a session
        schedule_session = request.form.get('schedule_session') == 'on'
        
        validation = validate_room_data(room_data)
        if not validation['valid']:
            for error in validation['errors']:
                flash(error, 'error')
            return render_template('admin/add_room.html', 
                                 room_data=room_data, 
                                 instructors=get_instructors(),
                                 schedule_session=schedule_session)
        
        try:
            # Check if room number already exists
            existing_room = Room.query.filter_by(room_number=room_data['room_number']).first()
            if existing_room:
                flash(f'Room number {room_data["room_number"]} already exists. Please use a different room number.', 'error')
                return render_template('admin/add_room.html', 
                                     room_data=room_data, 
                                     instructors=get_instructors(),
                                     schedule_session=schedule_session)
            
            # Create the room
            room = Room(
                room_number=room_data['room_number'],
                building=room_data['building'],
                floor=room_data['floor'],
                capacity=room_data['capacity'],
                room_type=room_data['room_type'],
                room_name=room_data.get('room_name') if room_data.get('room_name') else None
            )
            db.session.add(room)
            db.session.flush()  # Flush to get the room ID
            
            # If user wants to schedule a session, create it
            session_created = False
            if schedule_session:
                session_data = validate_and_create_session(request.form, room.id)
                if session_data['success']:
                    session_created = True
                    flash(f'Room {room.get_full_name()} created successfully and session "{session_data["session"].title}" scheduled!', 'success')
                else:
                    for error in session_data['errors']:
                        flash(error, 'error')
            
            db.session.commit()
            
            if not session_created:
                flash(f'Room {room.get_full_name()} added successfully!', 'success')
            
            return redirect(url_for('admin.manage_rooms'))
        
        except Exception as e:
            db.session.rollback()
            # Provide more specific error messages
            error_msg = str(e)
            if 'UNIQUE constraint failed: rooms.room_number' in error_msg:
                flash(f'Room number {room_data["room_number"]} already exists. Please use a different room number.', 'error')
            elif 'UNIQUE constraint failed' in error_msg:
                flash('A room with this information already exists. Please check your input.', 'error')
            else:
                flash(f'Error adding room: {error_msg}', 'error')
    
    return render_template('admin/add_room.html', 
                         room_data={}, 
                         instructors=get_instructors(),
                         schedule_session=False)

@admin_bp.route('/check_room_number')
@login_required
@requires_admin
def check_room_number():
    """AJAX endpoint to check if room number exists"""
    room_number = request.args.get('room_number', '').strip()
    
    if not room_number:
        return jsonify({'exists': False})
    
    existing_room = Room.query.filter_by(room_number=room_number).first()
    
    return jsonify({
        'exists': existing_room is not None,
        'room_info': {
            'room_number': existing_room.room_number,
            'room_name': existing_room.room_name,
            'building': existing_room.building,
            'floor': existing_room.floor
        } if existing_room else None
    })

@admin_bp.route('/settings')
@login_required
@requires_admin
def system_settings():
    """System settings page"""
    return render_template('admin/settings.html')

@admin_bp.route('/users/<int:id>/deactivate', methods=['POST'])
@login_required
@requires_admin
def deactivate_user(id):
    """Deactivate user"""
    try:
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('You cannot deactivate yourself.', 'error')
        else:
            user.deactivate()
            flash(f'User {user.username} deactivated.', 'success')
    except Exception as e:
        flash(f'Error deactivating user: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/rooms/<int:id>/delete', methods=['POST'])
@login_required
@requires_admin
def delete_room(id):
    """Delete room completely"""
    try:
        room = Room.query.get_or_404(id)
        room_name = room.get_full_name()
        
        # Check if room has any attendance records
        if hasattr(room, 'attendance_records') and room.attendance_records:
            flash(f'Cannot delete room {room_name} because it has attendance records. Set it to maintenance instead.', 'error')
        else:
            db.session.delete(room)
            db.session.commit()
            flash(f'Room {room_name} deleted successfully.', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting room: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_rooms'))

@admin_bp.route('/rooms/<int:id>/view')
@login_required
@requires_admin
def view_room(id):
    """View room details"""
    try:
        room = Room.query.get_or_404(id)
        return render_template('admin/view_room.html', room=room)
    except Exception as e:
        flash(f'Error loading room details: {str(e)}', 'error')
        return redirect(url_for('admin.manage_rooms'))

@admin_bp.route('/rooms/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_admin
def edit_room(id):
    """Edit room details"""
    room = Room.query.get_or_404(id)
    
    if request.method == 'POST':
        room_data = {
            'room_number': request.form.get('number', '').strip(),
            'room_name': request.form.get('name', '').strip(),
            'building': request.form.get('building', '').strip(),
            'floor': request.form.get('floor', type=int),
            'capacity': request.form.get('capacity', type=int),
            'room_type': request.form.get('type', 'classroom')
        }
        
        validation = validate_room_data(room_data)
        if not validation['valid']:
            for error in validation['errors']:
                flash(error, 'error')
            return render_template('admin/edit_room.html', room=room, room_data=room_data)
        
        try:
            # Check if room number already exists (excluding current room)
            if room_data['room_number'] != room.room_number:
                existing_room = Room.query.filter_by(room_number=room_data['room_number']).first()
                if existing_room:
                    flash(f'Room number {room_data["room_number"]} already exists. Please use a different room number.', 'error')
                    return render_template('admin/edit_room.html', room=room, room_data=room_data)
            
            # Update room details
            room.room_number = room_data['room_number']
            room.room_name = room_data.get('room_name') if room_data.get('room_name') else None
            room.building = room_data['building']
            room.floor = room_data['floor']
            room.capacity = room_data['capacity']
            room.room_type = room_data['room_type']
            
            db.session.commit()
            flash(f'Room {room.get_full_name()} updated successfully!', 'success')
            return redirect(url_for('admin.manage_rooms'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            if 'UNIQUE constraint failed: rooms.room_number' in error_msg:
                flash(f'Room number {room_data["room_number"]} already exists. Please use a different room number.', 'error')
            else:
                flash(f'Error updating room: {error_msg}', 'error')
    
    # Convert room data for form display
    room_data = {
        'room_number': room.room_number,
        'room_name': room.room_name,
        'building': room.building,
        'floor': room.floor,
        'capacity': room.capacity,
        'room_type': room.room_type
    }
    
    return render_template('admin/edit_room.html', room=room, room_data=room_data)

@admin_bp.route('/rooms/<int:id>/maintenance', methods=['POST'])
@login_required
@requires_admin
def set_room_maintenance(id):
    """Set room to maintenance mode"""
    try:
        room = Room.query.get_or_404(id)
        room.is_active = False  # Set to maintenance (inactive)
        db.session.commit()
        flash(f'Room {room.get_full_name()} set to maintenance mode.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting room to maintenance: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_rooms'))

@admin_bp.route('/rooms/<int:id>/activate', methods=['POST'])
@login_required
@requires_admin
def activate_room(id):
    """Activate room from maintenance mode"""
    try:
        room = Room.query.get_or_404(id)
        room.is_active = True  # Set to active
        db.session.commit()
        flash(f'Room {room.get_full_name()} activated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error activating room: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_rooms'))

def get_instructors():
    """Get list of potential instructors (professors and admins)"""
    return User.query.filter(
        User.is_active == True,
        User.role.in_(['professor', 'admin'])
    ).order_by(User.username).all()

def validate_and_create_session(form_data, room_id):
    """Validate session data and create session"""
    try:
        # Extract session data from form
        title = form_data.get('session_title', '').strip()
        description = form_data.get('session_description', '').strip()
        instructor_id = form_data.get('instructor_id', type=int)
        session_date = form_data.get('session_date', '').strip()
        start_time = form_data.get('start_time', '').strip()
        end_time = form_data.get('end_time', '').strip()
        max_attendees = form_data.get('max_attendees', type=int)
        is_mandatory = form_data.get('is_mandatory') == 'on'
        attendance_window_minutes = form_data.get('attendance_window_minutes', type=int, default=15)
        recurrence_type = form_data.get('recurrence_type', 'none')
        
        errors = []
        
        # Validate required fields
        if not title:
            errors.append('Session title is required')
        if not instructor_id:
            errors.append('Please select an instructor')
        if not session_date:
            errors.append('Session date is required')
        if not start_time:
            errors.append('Start time is required')
        if not end_time:
            errors.append('End time is required')
        
        if errors:
            return {'success': False, 'errors': errors}
        
        # Parse date and time
        try:
            parsed_date = datetime.strptime(session_date, '%Y-%m-%d').date()
            parsed_start_time = datetime.strptime(start_time, '%H:%M').time()
            parsed_end_time = datetime.strptime(end_time, '%H:%M').time()
        except ValueError as e:
            return {'success': False, 'errors': [f'Invalid date/time format: {str(e)}']}
        
        # Validate time logic
        if parsed_start_time >= parsed_end_time:
            return {'success': False, 'errors': ['End time must be after start time']}
        
        # Check if date is not in the past
        if parsed_date < datetime.now().date():
            return {'success': False, 'errors': ['Session date cannot be in the past']}
        
        # Validate instructor exists
        instructor = User.query.get(instructor_id)
        if not instructor or instructor.role not in ['professor', 'admin']:
            return {'success': False, 'errors': ['Invalid instructor selected']}
        
        # Calculate duration
        start_datetime = datetime.combine(parsed_date, parsed_start_time)
        end_datetime = datetime.combine(parsed_date, parsed_end_time)
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # Create the session
        session = SessionSchedule(
            title=title,
            description=description or None,
            room_id=room_id,
            instructor_id=instructor_id,
            session_date=parsed_date,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            duration_minutes=duration_minutes,
            max_attendees=max_attendees or None,
            is_mandatory=is_mandatory,
            attendance_window_minutes=attendance_window_minutes or 15,
            recurrence_type=RecurrenceType[recurrence_type.upper()] if recurrence_type != 'none' else RecurrenceType.NONE,
            status='scheduled'
        )
        
        db.session.add(session)
        
        return {'success': True, 'session': session}
        
    except Exception as e:
        return {'success': False, 'errors': [f'Error creating session: {str(e)}']}
        
def get_active_rooms():
    """Get list of active rooms"""
    return Room.query.filter(Room.is_active == True).order_by(Room.building, Room.room_number).all()