"""
Main Routes for ScanMe Attendance System
Handles dashboard, home page, and general navigation
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_login import login_required, current_user
from app import db
from app.models.student_model import Student
from app.models.room_model import Room
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.user_model import User
from app.utils.auth_utils import get_user_permissions
from app.utils.qr_utils import generate_user_qr_code
from datetime import datetime, date, timedelta
from sqlalchemy import func
import io
import base64

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page with overview statistics"""
    try:
        # Get user permissions
        permissions = get_user_permissions(current_user)
        
        # Get basic statistics
        stats = get_dashboard_stats()
        
        # Get recent activity
        recent_scans = get_recent_activity(limit=10)
        
        # Get today's summary
        today_summary = get_today_summary()
        
        # Get room occupancy if user has access
        room_occupancy = []
        if permissions['can_view_reports']:
            room_occupancy = get_room_occupancy_summary()
        
        return render_template('dashboard.html',
                             stats=stats,
                             recent_scans=recent_scans,
                             today_summary=today_summary,
                             room_occupancy=room_occupancy,
                             permissions=permissions)
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             stats={}, 
                             recent_scans=[], 
                             today_summary={},
                             room_occupancy=[],
                             permissions=get_user_permissions(current_user))

@main_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/dashboard/recent-activity')
@login_required
def api_recent_activity():
    """API endpoint for recent activity"""
    try:
        limit = request.args.get('limit', 20, type=int)
        recent_scans = get_recent_activity(limit=limit)
        return jsonify(recent_scans)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/dashboard/room-occupancy')
@login_required
def api_room_occupancy():
    """API endpoint for room occupancy"""
    try:
        permissions = get_user_permissions(current_user)
        if not permissions['can_view_reports']:
            return jsonify({'error': 'Access denied'}), 403
        
        room_occupancy = get_room_occupancy_summary()
        return jsonify(room_occupancy)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/search')
@login_required
def search():
    """Global search functionality"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, students, rooms
    
    if not query:
        return render_template('search_results.html', 
                             query='', 
                             results={}, 
                             search_type='all')
    
    try:
        results = {}
        permissions = get_user_permissions(current_user)
        
        if search_type in ['all', 'students'] and permissions['can_manage_students']:
            results['students'] = Student.search_students(query)[:10]
        
        if search_type in ['all', 'rooms']:
            results['rooms'] = Room.search_rooms(query)[:10]
        
        # Search attendance records if admin
        if search_type in ['all', 'attendance'] and permissions['can_view_reports']:
            results['attendance'] = search_attendance_records(query)[:10]
        
        return render_template('search_results.html',
                             query=query,
                             results=results,
                             search_type=search_type,
                             permissions=permissions)
        
    except Exception as e:
        flash(f'Search error: {str(e)}', 'error')
        return render_template('search_results.html', 
                             query=query, 
                             results={}, 
                             search_type=search_type)

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)

@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html', user=current_user)

@main_bp.route('/generate-my-qr')
@login_required
def generate_my_qr():
    """Generate QR code for current user"""
    try:
        # Prepare user data based on role
        if current_user.is_student():
            # For students, try to find student record by email or username
            student = Student.query.filter(
                db.or_(
                    Student.email == current_user.email,
                    Student.student_no == current_user.username
                )
            ).first()
            
            if student:
                user_data = {
                    'id': student.id,
                    'student_no': student.student_no,
                    'name': student.get_full_name(),
                    'department': student.department,
                    'section': student.section,
                    'year_level': student.year_level
                }
                user_type = 'student'
            else:
                # If no student record found, use basic user info
                user_data = {
                    'id': current_user.id,
                    'username': current_user.username,
                    'email': current_user.email,
                    'role': current_user.role,
                    'display_name': current_user.get_display_name()
                }
                user_type = 'student'
        else:
            # For professors and admins
            user_data = {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role,
                'display_name': current_user.get_display_name()
            }
            user_type = current_user.role
        
        # Generate QR code as base64
        qr_base64 = generate_user_qr_code(user_data, user_type)
        
        if not qr_base64:
            flash('Failed to generate QR code. Please try again.', 'error')
            return redirect(url_for('main.profile'))
        
        return render_template('my_qr_code.html', 
                             qr_data=qr_base64,
                             user_data=user_data,
                             user_type=user_type,
                             user=current_user)
        
    except Exception as e:
        flash(f'Error generating QR code: {str(e)}', 'error')
        return redirect(url_for('main.profile'))

@main_bp.route('/download-my-qr')
@login_required
def download_my_qr():
    """Download QR code for current user"""
    try:
        # Prepare user data based on role
        if current_user.is_student():
            # For students, try to find student record by email or username
            student = Student.query.filter(
                db.or_(
                    Student.email == current_user.email,
                    Student.student_no == current_user.username
                )
            ).first()
            
            if student:
                user_data = {
                    'id': student.id,
                    'student_no': student.student_no,
                    'name': student.get_full_name(),
                    'department': student.department,
                    'section': student.section,
                    'year_level': student.year_level
                }
                user_type = 'student'
                filename = f"{student.student_no}_qr.png"
            else:
                # If no student record found, use basic user info
                user_data = {
                    'id': current_user.id,
                    'username': current_user.username,
                    'email': current_user.email,
                    'role': current_user.role,
                    'display_name': current_user.get_display_name()
                }
                user_type = 'student'
                filename = f"{current_user.username}_student_qr.png"
        else:
            # For professors and admins
            user_data = {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role,
                'display_name': current_user.get_display_name()
            }
            user_type = current_user.role
            filename = f"{current_user.username}_{user_type}_qr.png"
        
        # Generate QR code as bytes
        qr_bytes = generate_user_qr_code(user_data, user_type, return_bytes=True)
        
        if not qr_bytes:
            flash('Failed to generate QR code. Please try again.', 'error')
            return redirect(url_for('main.profile'))
        
        # Create response with file download
        response = make_response(qr_bytes)
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        flash(f'Error downloading QR code: {str(e)}', 'error')
        return redirect(url_for('main.profile'))

@main_bp.route('/api/generate-qr')
@login_required
def api_generate_qr():
    """API endpoint to generate QR code for current user"""
    try:
        # Prepare user data based on role
        if current_user.is_student():
            # For students, try to find student record by email or username
            student = Student.query.filter(
                db.or_(
                    Student.email == current_user.email,
                    Student.student_no == current_user.username
                )
            ).first()
            
            if student:
                user_data = {
                    'id': student.id,
                    'student_no': student.student_no,
                    'name': student.get_full_name(),
                    'department': student.department,
                    'section': student.section,
                    'year_level': student.year_level
                }
                user_type = 'student'
            else:
                # If no student record found, use basic user info
                user_data = {
                    'id': current_user.id,
                    'username': current_user.username,
                    'email': current_user.email,
                    'role': current_user.role,
                    'display_name': current_user.get_display_name()
                }
                user_type = 'student'
        else:
            # For professors and admins
            user_data = {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role,
                'display_name': current_user.get_display_name()
            }
            user_type = current_user.role
        
        # Generate QR code as base64
        qr_base64 = generate_user_qr_code(user_data, user_type)
        
        if not qr_base64:
            return jsonify({'error': 'Failed to generate QR code'}), 500
        
        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'user_type': user_type,
            'user_data': user_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_dashboard_stats():
    """Get statistics for dashboard"""
    try:
        today = date.today()
        
        # Basic counts
        total_students = Student.query.filter_by(is_active=True).count()
        total_rooms = Room.query.filter_by(is_active=True).count()
        total_users = User.query.filter_by(is_active=True).count()
        
        # Today's activity
        today_scans = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.scan_time) == today
        ).count()
        
        # Unique students today
        unique_students_today = db.session.query(AttendanceRecord.student_id)\
            .filter(func.date(AttendanceRecord.scan_time) == today)\
            .distinct().count()
        
        # Active sessions
        active_sessions = AttendanceSession.get_current_sessions()
        
        # This week's stats
        week_start = today - timedelta(days=today.weekday())
        week_scans = AttendanceRecord.query.filter(
            AttendanceRecord.scan_time >= week_start
        ).count()
        
        return {
            'total_students': total_students,
            'total_rooms': total_rooms,
            'total_users': total_users,
            'today_scans': today_scans,
            'unique_students_today': unique_students_today,
            'active_sessions': len(active_sessions),
            'week_scans': week_scans,
            'attendance_rate': round((unique_students_today / total_students * 100), 2) if total_students > 0 else 0
        }
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {
            'total_students': 0,
            'total_rooms': 0,
            'total_users': 0,
            'today_scans': 0,
            'unique_students_today': 0,
            'active_sessions': 0,
            'week_scans': 0,
            'attendance_rate': 0
        }

def get_recent_activity(limit=10):
    """Get recent attendance activity"""
    try:
        recent_records = AttendanceRecord.query\
            .order_by(AttendanceRecord.scan_time.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'id': record.id,
                'student_name': record.student.get_full_name() if record.student else 'Unknown',
                'student_no': record.student.student_no if record.student else 'N/A',
                'room_name': record.room.get_full_name() if record.room else 'Unknown',
                'scan_time': record.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_late': record.is_late,
                'is_duplicate': record.is_duplicate,
                'scanner': record.scanned_by_user.username if record.scanned_by_user else 'System'
            }
            for record in recent_records
        ]
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return []

def get_today_summary():
    """Get today's attendance summary"""
    try:
        today = date.today()
        
        # Get all today's records
        today_records = AttendanceRecord.query.filter(
            func.date(AttendanceRecord.scan_time) == today
        ).all()
        
        # Calculate summary
        total_scans = len(today_records)
        unique_students = len(set(record.student_id for record in today_records))
        late_arrivals = len([record for record in today_records if record.is_late])
        duplicates = len([record for record in today_records if record.is_duplicate])
        active_rooms = len(set(record.room_id for record in today_records))
        
        # Peak hour analysis
        hourly_counts = {}
        for record in today_records:
            hour = record.scan_time.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else (0, 0)
        
        return {
            'total_scans': total_scans,
            'unique_students': unique_students,
            'late_arrivals': late_arrivals,
            'duplicates': duplicates,
            'active_rooms': active_rooms,
            'on_time_percentage': round(((total_scans - late_arrivals) / total_scans * 100), 2) if total_scans > 0 else 0,
            'peak_hour': f"{peak_hour[0]:02d}:00" if peak_hour[1] > 0 else 'N/A',
            'peak_hour_count': peak_hour[1]
        }
        
    except Exception as e:
        print(f"Error getting today summary: {e}")
        return {
            'total_scans': 0,
            'unique_students': 0,
            'late_arrivals': 0,
            'duplicates': 0,
            'active_rooms': 0,
            'on_time_percentage': 0,
            'peak_hour': 'N/A',
            'peak_hour_count': 0
        }

def get_room_occupancy_summary():
    """Get room occupancy summary"""
    try:
        rooms = Room.get_active_rooms()
        
        occupancy_data = []
        for room in rooms:
            current_occupancy = room.get_current_occupancy()
            occupancy_percentage = room.get_occupancy_percentage()
            status = room.get_capacity_status()
            
            occupancy_data.append({
                'id': room.id,
                'room_number': room.room_number,
                'room_name': room.room_name,
                'full_name': room.get_full_name(),
                'building': room.building,
                'capacity': room.capacity,
                'current_occupancy': current_occupancy,
                'occupancy_percentage': round(occupancy_percentage, 1),
                'status': status['status'],
                'status_color': status['color'],
                'status_text': status['text'],
                'is_over_capacity': room.is_over_capacity()
            })
        
        # Sort by occupancy percentage (highest first)
        occupancy_data.sort(key=lambda x: x['occupancy_percentage'], reverse=True)
        
        return occupancy_data
        
    except Exception as e:
        print(f"Error getting room occupancy: {e}")
        return []

def search_attendance_records(query):
    """Search attendance records"""
    try:
        # Search by student name or student number
        records = db.session.query(AttendanceRecord)\
            .join(Student)\
            .filter(
                db.or_(
                    Student.first_name.like(f"%{query}%"),
                    Student.last_name.like(f"%{query}%"),
                    Student.student_no.like(f"%{query}%")
                )
            )\
            .order_by(AttendanceRecord.scan_time.desc())\
            .all()
        
        return [
            {
                'id': record.id,
                'student_name': record.student.get_full_name(),
                'student_no': record.student.student_no,
                'room_name': record.room.get_full_name() if record.room else 'Unknown',
                'scan_time': record.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_late': record.is_late
            }
            for record in records
        ]
        
    except Exception as e:
        print(f"Error searching attendance records: {e}")
        return []