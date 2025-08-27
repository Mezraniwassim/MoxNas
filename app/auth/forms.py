"""Authentication forms with security features"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from wtforms.widgets import PasswordInput
import re
from app.models import User

class LoginForm(FlaskForm):
    """Secure login form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    totp_code = StringField('2FA Code', validators=[Length(min=0, max=6)])
    submit = SubmitField('Sign In')

class PasswordChangeForm(FlaskForm):
    """Password change form with strength validation"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=128, message='Password must be between 8 and 128 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
    
    def validate_new_password(self, field):
        \"\"\"Validate password strength\"\"\"
        password = field.data
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'\"|,.<>?]', password):
            raise ValidationError('Password must contain at least one special character')
        
        # Check for common passwords (basic list)
        common_passwords = [
            'password', '123456', '12345678', 'qwerty', 'abc123',
            'admin', 'root', 'password123', 'administrator'
        ]
        if password.lower() in common_passwords:
            raise ValidationError('Password is too common. Please choose a stronger password')

class UserRegistrationForm(FlaskForm):
    """User registration form (admin only)"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters long')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=128, message='Password must be between 8 and 128 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Administrator')], default='user')
    force_password_change = BooleanField('Force password change on first login')
    submit = SubmitField('Create User')
    
    def validate_username(self, field):
        \"\"\"Check if username is available\"\"\"
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
        
        # Check for valid username characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', field.data):
            raise ValidationError('Username can only contain letters, numbers, hyphens, and underscores')
    
    def validate_email(self, field):
        \"\"\"Check if email is available\"\"\"
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email address.')
    
    def validate_password(self, field):
        \"\"\"Validate password strength\"\"\"
        password = field.data
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'\"|,.<>?]', password):
            raise ValidationError('Password must contain at least one special character')

class UserEditForm(FlaskForm):
    """User edit form (admin only)"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters long')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Administrator')])
    is_active = BooleanField('Account Active')
    force_password_change = BooleanField('Force password change on next login')
    unlock_account = BooleanField('Unlock account (if locked)')
    submit = SubmitField('Update User')
    
    def __init__(self, original_user, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
    
    def validate_username(self, field):
        \"\"\"Check if username is available (excluding current user)\"\"\"
        if field.data != self.original_user.username:
            user = User.query.filter_by(username=field.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, field):
        \"\"\"Check if email is available (excluding current user)\"\"\"
        if field.data != self.original_user.email:
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different email address.')

class TOTPSetupForm(FlaskForm):
    \"\"\"Two-factor authentication setup form\"\"\"
    totp_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6, message='Verification code must be 6 digits')
    ])
    submit = SubmitField('Enable 2FA')
    
    def validate_totp_code(self, field):
        \"\"\"Validate TOTP code format\"\"\"
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only digits')

class TOTPDisableForm(FlaskForm):
    \"\"\"Two-factor authentication disable form\"\"\"
    password = PasswordField('Current Password', validators=[DataRequired()])
    totp_code = StringField('Current 2FA Code', validators=[
        DataRequired(),
        Length(min=6, max=6, message='Verification code must be 6 digits')
    ])
    submit = SubmitField('Disable 2FA')
    
    def validate_totp_code(self, field):
        \"\"\"Validate TOTP code format\"\"\"
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only digits')

class PasswordResetRequestForm(FlaskForm):
    \"\"\"Password reset request form\"\"\"
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class PasswordResetForm(FlaskForm):
    \"\"\"Password reset form\"\"\"
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=128, message='Password must be between 8 and 128 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')
    
    def validate_password(self, field):
        \"\"\"Validate password strength\"\"\"
        password = field.data
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'\"|,.<>?]', password):
            raise ValidationError('Password must contain at least one special character')