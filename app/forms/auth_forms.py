"""
Authentication Forms for ScanMe Attendance System
Flask-WTF forms for login, registration, and user management
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user_model import User
from app.utils.auth_utils import validate_username, validate_email, validate_password


class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username or Email', validators=[
        DataRequired(message='Username or email is required.')
    ], render_kw={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter username or email',
        'autocomplete': 'username'
    })
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ], render_kw={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter password',
        'autocomplete': 'current-password'
    })
    
    remember_me = BooleanField('Remember me', render_kw={
        'class': 'form-check-input'
    })


class RegisterForm(FlaskForm):
    """User registration form"""
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'),
        Length(min=1, max=50, message='First name must be 1-50 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter first name',
        'autocomplete': 'given-name'
    })
    
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'),
        Length(min=1, max=50, message='Last name must be 1-50 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter last name',
        'autocomplete': 'family-name'
    })
    
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=20, message='Username must be 3-20 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter username',
        'autocomplete': 'username'
    })
    
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter email address',
        'autocomplete': 'email'
    })
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=8, message='Password must be at least 8 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter password',
        'autocomplete': 'new-password'
    })
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Confirm password',
        'autocomplete': 'new-password'
    })
    
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('professor', 'Professor'),
        ('admin', 'Administrator')
    ], default='student', render_kw={
        'class': 'form-select'
    })
    
    agree_terms = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[
        DataRequired(message='You must agree to the terms and conditions.')
    ], render_kw={
        'class': 'form-check-input'
    })
    
    def validate_username(self, username):
        """Custom validator for username"""
        if not validate_username(username.data):
            raise ValidationError('Username must contain only letters, numbers, and underscores.')
        
        user = User.get_by_username(username.data)
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Custom validator for email"""
        if not validate_email(email.data):
            raise ValidationError('Please enter a valid email address.')
        
        user = User.get_by_email(email.data)
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')
    
    def validate_password(self, password):
        """Custom validator for password"""
        validation = validate_password(password.data)
        if not validation['valid']:
            raise ValidationError(validation['errors'][0])


class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter your email address',
        'autocomplete': 'email'
    })


class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter current password',
        'autocomplete': 'current-password'
    })
    
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        Length(min=8, message='Password must be at least 8 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter new password',
        'autocomplete': 'new-password'
    })
    
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password.'),
        EqualTo('new_password', message='Passwords must match.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Confirm new password',
        'autocomplete': 'new-password'
    })
    
    def validate_new_password(self, new_password):
        """Custom validator for new password"""
        validation = validate_password(new_password.data)
        if not validation['valid']:
            raise ValidationError(validation['errors'][0])


class EditProfileForm(FlaskForm):
    """Edit user profile form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=20, message='Username must be 3-20 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter username',
        'autocomplete': 'username'
    })
    
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Enter email address',
        'autocomplete': 'email'
    })
    
    def __init__(self, current_user, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.current_user = current_user
    
    def validate_username(self, username):
        """Custom validator for username"""
        if username.data != self.current_user.username:
            if not validate_username(username.data):
                raise ValidationError('Username must contain only letters, numbers, and underscores.')
            
            user = User.get_by_username(username.data)
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Custom validator for email"""
        if email.data != self.current_user.email:
            if not validate_email(email.data):
                raise ValidationError('Please enter a valid email address.')
            
            user = User.get_by_email(email.data)
            if user:
                raise ValidationError('Email already registered. Please choose a different one.')


class UserManagementForm(FlaskForm):
    """Admin form for user management"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=20, message='Username must be 3-20 characters long.')
    ], render_kw={
        'class': 'form-control'
    })
    
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ], render_kw={
        'class': 'form-control'
    })
    
    password = PasswordField('Password', validators=[
        Length(min=8, message='Password must be at least 8 characters long.')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Leave blank to keep current password'
    })
    
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('professor', 'Professor'),
        ('admin', 'Administrator')
    ], render_kw={
        'class': 'form-select'
    })
    
    is_active = BooleanField('Active', render_kw={
        'class': 'form-check-input'
    })
    
    notes = TextAreaField('Notes', render_kw={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'Optional notes about this user'
    })
    
    def __init__(self, user_id=None, *args, **kwargs):
        super(UserManagementForm, self).__init__(*args, **kwargs)
        self.user_id = user_id
    
    def validate_username(self, username):
        """Custom validator for username"""
        if not validate_username(username.data):
            raise ValidationError('Username must contain only letters, numbers, and underscores.')
        
        user = User.get_by_username(username.data)
        if user and str(user.id) != str(self.user_id):
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Custom validator for email"""
        if not validate_email(email.data):
            raise ValidationError('Please enter a valid email address.')
        
        user = User.get_by_email(email.data)
        if user and str(user.id) != str(self.user_id):
            raise ValidationError('Email already registered. Please choose a different one.')
    
    def validate_password(self, password):
        """Custom validator for password"""
        if password.data:  # Only validate if password is provided
            validation = validate_password(password.data)
            if not validation['valid']:
                raise ValidationError(validation['errors'][0])