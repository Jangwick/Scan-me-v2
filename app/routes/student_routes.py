"""
Student Routes for ScanMe Attendance System
Handles student management (CRUD operations)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.student_model import Student
from app.utils.auth_utils import requires_professor_or_admin, validate_student_data, validate_student_edit_data
from app.utils.qr_utils import generate_student_qr_code
from datetime import datetime

student_bp = Blueprint('students', __name__)

@student_bp.route('/')
@login_required
@requires_professor_or_admin
def list_students():
    """List all students with pagination and search"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        department = request.args.get('department', '').strip()
        per_page = 20
        
        query = Student.query.filter_by(is_active=True)
        
        if search:
            students = Student.search_students(search)
            # Convert to paginated object for template compatibility
            total = len(students)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_students = students[start:end]
        elif department:
            students = Student.get_by_department(department)
            total = len(students)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_students = students[start:end]
        else:
            pagination = query.order_by(Student.last_name, Student.first_name)\
                            .paginate(page=page, per_page=per_page, error_out=False)
            paginated_students = pagination.items
            total = pagination.total
        
        # Get departments for filter
        departments = db.session.query(Student.department)\
                        .filter(Student.is_active == True)\
                        .distinct().all()
        departments = [dept[0] for dept in departments]
        
        return render_template('students/list.html',
                             students=paginated_students,
                             departments=departments,
                             search=search,
                             selected_department=department,
                             page=page,
                             total=total,
                             per_page=per_page)
    
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'error')
        return render_template('students/list.html', students=[], departments=[])

@student_bp.route('/add', methods=['GET', 'POST'])
@login_required
@requires_professor_or_admin
def add_student():
    """Add new student"""
    if request.method == 'POST':
        student_data = {
            'student_no': request.form.get('student_no', '').strip(),
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'department': request.form.get('department', '').strip(),
            'section': request.form.get('section', '').strip(),
            'year_level': request.form.get('year_level', type=int)
        }
        
        # Validate data
        validation = validate_student_data(student_data)
        if not validation['valid']:
            for error in validation['errors']:
                flash(error, 'error')
            return render_template('students/add.html', student_data=student_data)
        
        # Check for existing student
        if Student.get_by_student_no(student_data['student_no']):
            flash('Student number already exists.', 'error')
            return render_template('students/add.html', student_data=student_data)
        
        if Student.query.filter_by(email=student_data['email']).first():
            flash('Email already exists.', 'error')
            return render_template('students/add.html', student_data=student_data)
        
        try:
            # Create student
            student = Student(**student_data)
            db.session.add(student)
            db.session.commit()
            
            # Generate QR code
            student.generate_qr_code()
            
            flash(f'Student {student.get_full_name()} added successfully!', 'success')
            return redirect(url_for('students.view_student', id=student.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
    
    return render_template('students/add.html', student_data={})

@student_bp.route('/<int:id>')
@login_required
@requires_professor_or_admin
def view_student(id):
    """View student details"""
    try:
        student = Student.query.get_or_404(id)
        
        # Get attendance statistics
        attendance_stats = student.get_attendance_stats()
        
        return render_template('students/view.html', 
                             student=student,
                             attendance_stats=attendance_stats)
    
    except Exception as e:
        flash(f'Error loading student: {str(e)}', 'error')
        return redirect(url_for('students.list_students'))

@student_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_professor_or_admin
def edit_student(id):
    """Edit student information"""
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        student_data = {
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'department': request.form.get('department', '').strip(),
            'section': request.form.get('section', '').strip(),
            'year_level': request.form.get('year_level', type=int)
        }
        
        # Validate data (use edit validation which doesn't require student_no)
        validation = validate_student_edit_data(student_data)
        if not validation['valid']:
            for error in validation['errors']:
                flash(error, 'error')
            return render_template('students/edit.html', student=student)
        
        # Check for duplicate email (excluding current student)
        existing_email = Student.query.filter(
            Student.email == student_data['email'],
            Student.id != student.id
        ).first()
        
        if existing_email:
            flash('Email already exists.', 'error')
            return render_template('students/edit.html', student=student)
        
        try:
            # Update student
            student.update_info(**student_data)
            
            flash(f'Student {student.get_full_name()} updated successfully!', 'success')
            return redirect(url_for('students.view_student', id=student.id))
        
        except Exception as e:
            flash(f'Error updating student: {str(e)}', 'error')
    
    return render_template('students/edit.html', student=student)

@student_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@requires_professor_or_admin
def delete_student(id):
    """Deactivate student"""
    try:
        student = Student.query.get_or_404(id)
        student.deactivate()
        
        flash(f'Student {student.get_full_name()} deactivated successfully!', 'success')
        return redirect(url_for('students.list_students'))
    
    except Exception as e:
        flash(f'Error deactivating student: {str(e)}', 'error')
        return redirect(url_for('students.view_student', id=id))

@student_bp.route('/<int:id>/qr-code')
@login_required
@requires_professor_or_admin
def download_qr_code(id):
    """Download student's QR code"""
    try:
        student = Student.query.get_or_404(id)
        
        if not student.qr_code_path:
            student.generate_qr_code()
        
        from flask import send_file, current_app
        import os
        
        # Get the absolute path to the QR code file
        static_folder = current_app.static_folder
        qr_path = os.path.join(static_folder, student.qr_code_path)
        
        # Check if file exists
        if not os.path.exists(qr_path):
            # Try to regenerate the QR code
            student.generate_qr_code()
            qr_path = os.path.join(static_folder, student.qr_code_path)
            
            if not os.path.exists(qr_path):
                flash('QR code file not found. Please try again.', 'error')
                return redirect(url_for('students.view_student', id=id))
        
        return send_file(qr_path, as_attachment=True, 
                        download_name=f"{student.student_no}_qr.png")
    
    except Exception as e:
        flash(f'Error downloading QR code: {str(e)}', 'error')
        return redirect(url_for('students.view_student', id=id))

@student_bp.route('/<int:id>/generate-qr', methods=['POST'])
@login_required
@requires_professor_or_admin
def generate_qr_code(id):
    """Generate QR code for a student"""
    try:
        student = Student.query.get_or_404(id)
        
        # Generate QR code
        student.generate_qr_code()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'QR code generated for {student.get_full_name()}',
            'qr_code_path': student.qr_code_path
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@student_bp.route('/api/search')
@login_required
@requires_professor_or_admin
def api_search():
    """API endpoint for student search"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify([])
        
        students = Student.search_students(query)[:limit]
        
        return jsonify([
            {
                'id': student.id,
                'student_no': student.student_no,
                'name': student.get_full_name(),
                'department': student.department,
                'section': student.section,
                'year_level': student.year_level
            }
            for student in students
        ])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/bulk-import', methods=['GET', 'POST'])
@login_required
@requires_professor_or_admin
def bulk_import():
    """Bulk import students from CSV/Excel"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return render_template('students/bulk_import.html')
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return render_template('students/bulk_import.html')
        
        try:
            import pandas as pd
            
            # Read file
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                flash('Invalid file format. Use CSV or Excel files.', 'error')
                return render_template('students/bulk_import.html')
            
            # Process students
            success_count = 0
            error_count = 0
            errors = []
            
            required_columns = ['student_no', 'first_name', 'last_name', 'email', 'department', 'section', 'year_level']
            
            if not all(col in df.columns for col in required_columns):
                flash(f'Missing required columns: {", ".join(required_columns)}', 'error')
                return render_template('students/bulk_import.html')
            
            for index, row in df.iterrows():
                try:
                    student_data = {col: row[col] for col in required_columns}
                    
                    # Validate
                    validation = validate_student_data(student_data)
                    if not validation['valid']:
                        errors.append(f"Row {index + 1}: {'; '.join(validation['errors'])}")
                        error_count += 1
                        continue
                    
                    # Check duplicates
                    if Student.get_by_student_no(student_data['student_no']):
                        errors.append(f"Row {index + 1}: Student number already exists")
                        error_count += 1
                        continue
                    
                    # Create student
                    student = Student(**student_data)
                    db.session.add(student)
                    success_count += 1
                
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
                    error_count += 1
            
            db.session.commit()
            
            flash(f'Import completed! {success_count} students added, {error_count} errors.', 
                  'success' if error_count == 0 else 'warning')
            
            if errors:
                # Show first 10 errors
                for error in errors[:10]:
                    flash(error, 'error')
                if len(errors) > 10:
                    flash(f'... and {len(errors) - 10} more errors', 'error')
        
        except Exception as e:
            db.session.rollback()
            flash(f'Import error: {str(e)}', 'error')
    
    return render_template('students/bulk_import.html')