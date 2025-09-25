"""
Admin Routes for ScanMe Attendance System
Handles admin-only functions like user management and system settings
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user_model import User
from app.models.room_model import Room
from app.utils.auth_utils import requires_admin, validate_room_data, get_user_permissions
from datetime import datetime

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
    """Add new room"""
    if request.method == 'POST':
        room_data = {
            'room_number': request.form.get('room_number', '').strip(),
            'room_name': request.form.get('room_name', '').strip(),
            'building': request.form.get('building', '').strip(),
            'floor': request.form.get('floor', type=int),
            'capacity': request.form.get('capacity', type=int),
            'room_type': request.form.get('room_type', 'classroom')
        }
        
        validation = validate_room_data(room_data)
        if not validation['valid']:
            for error in validation['errors']:
                flash(error, 'error')
            return render_template('admin/add_room.html', room_data=room_data)
        
        try:
            room = Room(**room_data)
            db.session.add(room)
            db.session.commit()
            
            flash(f'Room {room.get_full_name()} added successfully!', 'success')
            return redirect(url_for('admin.manage_rooms'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding room: {str(e)}', 'error')
    
    return render_template('admin/add_room.html', room_data={})

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
    """Deactivate room"""
    try:
        room = Room.query.get_or_404(id)
        room.deactivate()
        flash(f'Room {room.get_full_name()} deactivated.', 'success')
    except Exception as e:
        flash(f'Error deactivating room: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_rooms'))