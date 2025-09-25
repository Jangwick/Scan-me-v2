"""
Authentication Routes for ScanMe Attendance System
Handles user login, logout, and registration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user_model import User
from app.utils.auth_utils import hash_password, validate_email, validate_username, validate_password
from app.forms.auth_forms import LoginForm, RegisterForm, ForgotPasswordForm, ChangePasswordForm, EditProfileForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        remember_me = form.remember_me.data
        
        try:
            # Find user by username or email
            user = User.get_by_username(username) or User.get_by_email(username)
            
            if user and user.is_active and user.check_password(password):
                # Update last login
                user.update_last_login()
                
                # Login user
                login_user(user, remember=remember_me)
                
                flash(f'Welcome back, {user.get_display_name()}!', 'success')
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid username/email or password.', 'error')
        
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    user_name = current_user.get_display_name()
    logout_user()
    flash(f'Goodbye, {user_name}!', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (admin only in production)"""
    # In production, this should be restricted to admins only
    # For demo purposes, allowing registration
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        try:
            # Create new user
            # Note: first_name and last_name are collected but not stored in current User model
            # They could be combined or stored in a separate profile table in the future
            user = User.create_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                role=form.role.data
            )
            
            flash(f'Account created successfully for {form.username.data}!', 'success')
            
            # Auto-login the new user
            login_user(user)
            return redirect(url_for('main.dashboard'))
        
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'error')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        try:
            user = User.get_by_email(form.email.data)
            
            if user and user.is_active:
                # In a real application, you would:
                # 1. Generate a password reset token
                # 2. Send reset email to user
                # 3. Store token in database with expiration
                
                # For demo purposes, just show a success message
                flash('If an account with that email exists, a password reset link has been sent.', 'info')
                return redirect(url_for('auth.login'))
            else:
                # Don't reveal if email exists or not for security
                flash('If an account with that email exists, a password reset link has been sent.', 'info')
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            flash('An error occurred. Please try again later.', 'error')
    
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password for logged-in user"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        try:
            # Change password
            current_user.change_password(form.current_password.data, form.new_password.data)
            flash('Password changed successfully!', 'success')
            return redirect(url_for('main.profile'))
        
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error changing password: {str(e)}', 'error')
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = EditProfileForm(current_user)
    
    if form.validate_on_submit():
        try:
            # Update profile
            current_user.update_profile(username=form.username.data, email=form.email.data)
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('main.profile'))
        
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    elif request.method == 'GET':
        # Populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('auth/edit_profile.html', form=form)

@auth_bp.route('/check-username')
def check_username():
    """AJAX endpoint to check username availability"""
    username = request.args.get('username', '').strip()
    
    if not username:
        return {'available': False, 'message': 'Username is required'}
    
    if not validate_username(username):
        return {
            'available': False, 
            'message': 'Username must be 3-20 characters, alphanumeric and underscores only'
        }
    
    existing_user = User.get_by_username(username)
    if existing_user and existing_user.id != getattr(current_user, 'id', None):
        return {'available': False, 'message': 'Username already exists'}
    
    return {'available': True, 'message': 'Username is available'}

@auth_bp.route('/check-email')
def check_email():
    """AJAX endpoint to check email availability"""
    email = request.args.get('email', '').strip()
    
    if not email:
        return {'available': False, 'message': 'Email is required'}
    
    if not validate_email(email):
        return {'available': False, 'message': 'Please enter a valid email address'}
    
    existing_user = User.get_by_email(email)
    if existing_user and existing_user.id != getattr(current_user, 'id', None):
        return {'available': False, 'message': 'Email already exists'}
    
    return {'available': True, 'message': 'Email is available'}