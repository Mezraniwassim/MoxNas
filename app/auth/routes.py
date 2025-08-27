"""Authentication routes with security features"""
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pyotp
import qrcode
import io
import base64
from datetime import datetime
from app import db, limiter
from app.auth import bp
from app.auth.forms import (LoginForm, PasswordChangeForm, UserRegistrationForm, 
                           UserEditForm, TOTPSetupForm, TOTPDisableForm)
from app.models import User, SystemLog, LogLevel, UserRole

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    """Secure login with rate limiting and account lockout"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None:
            # Log failed login attempt
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'Login attempt with invalid username: {form.username.data}',
                ip_address=request.remote_addr,
                details={'user_agent': request.headers.get('User-Agent')}
            )
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
        
        if user.is_locked():
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'Login attempt on locked account: {user.username}',
                user_id=user.id,
                ip_address=request.remote_addr
            )
            flash('Account is temporarily locked due to multiple failed login attempts. Please try again later.', 'warning')
            return render_template('auth/login.html', form=form)
        
        if not user.is_active:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'Login attempt on disabled account: {user.username}',
                user_id=user.id,
                ip_address=request.remote_addr
            )
            flash('Account is disabled. Please contact your administrator.', 'warning')
            return render_template('auth/login.html', form=form)
        
        if not user.check_password(form.password.data):
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'Failed login attempt for user: {user.username}',
                user_id=user.id,
                ip_address=request.remote_addr
            )
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Check 2FA if enabled
        if user.totp_enabled:
            if not form.totp_code.data:
                flash('Two-factor authentication code is required', 'info')
                return render_template('auth/login.html', form=form, show_2fa=True)
            
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(form.totp_code.data):
                user.failed_login_attempts += 1
                db.session.commit()
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category='auth',
                    message=f'Invalid 2FA code for user: {user.username}',
                    user_id=user.id,
                    ip_address=request.remote_addr
                )
                flash('Invalid two-factor authentication code', 'danger')
                return render_template('auth/login.html', form=form, show_2fa=True)
        
        # Successful login
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='auth',
            message=f'User logged in successfully: {user.username}',
            user_id=user.id,
            ip_address=request.remote_addr
        )
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        
        # Check if password change is forced
        if user.force_password_change:
            flash('You must change your password before continuing', 'info')
            return redirect(url_for('auth.change_password'))
        
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    """Secure logout"""
    if current_user.is_authenticated:
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='auth',
            message=f'User logged out: {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
    
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password with security validation"""
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'Invalid current password during password change: {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            flash('Current password is incorrect', 'danger')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        current_user.force_password_change = False
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='auth',
            message=f'Password changed successfully: {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        
        flash('Your password has been changed successfully', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/change_password.html', form=form)

@bp.route('/users')
@login_required
def users():
    """List all users (admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('auth/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create new user (admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = UserRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=UserRole.ADMIN if form.role.data == 'admin' else UserRole.USER,
            force_password_change=form.force_password_change.data,
            created_by_id=current_user.id
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='auth',
            message=f'New user created: {user.username} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'created_user_id': user.id, 'role': user.role.value}
        )
        
        flash(f'User {user.username} created successfully', 'success')
        return redirect(url_for('auth.users'))
    
    return render_template('auth/create_user.html', form=form)

@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit user (admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(id)
    form = UserEditForm(user)
    
    if form.validate_on_submit():
        changes = []
        
        if user.username != form.username.data:
            changes.append(f'username: {user.username} -> {form.username.data}')
            user.username = form.username.data
        
        if user.email != form.email.data:
            changes.append(f'email: {user.email} -> {form.email.data}')
            user.email = form.email.data
        
        new_role = UserRole.ADMIN if form.role.data == 'admin' else UserRole.USER
        if user.role != new_role:
            changes.append(f'role: {user.role.value} -> {new_role.value}')
            user.role = new_role
        
        if user.is_active != form.is_active.data:
            changes.append(f'is_active: {user.is_active} -> {form.is_active.data}')
            user.is_active = form.is_active.data
        
        if form.force_password_change.data:
            changes.append('forced password change')
            user.force_password_change = True
        
        if form.unlock_account.data and user.is_locked():
            changes.append('account unlocked')
            user.unlock_account()
        
        db.session.commit()
        
        if changes:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='auth',
                message=f'User {user.username} updated by {current_user.username}: {";".join(changes)}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={'modified_user_id': user.id, 'changes': changes}
            )
        
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('auth.users'))
    
    # Pre-populate form
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role.value
        form.is_active.data = user.is_active
        form.force_password_change.data = user.force_password_change
    
    return render_template('auth/edit_user.html', form=form, user=user)

@bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    """Delete user (admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('auth.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    SystemLog.log_event(
        level=LogLevel.WARNING,
        category='auth',
        message=f'User {username} deleted by {current_user.username}',
        user_id=current_user.id,
        ip_address=request.remote_addr,
        details={'deleted_user_id': id}
    )
    
    flash(f'User {username} deleted successfully', 'success')
    return redirect(url_for('auth.users'))

@bp.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Setup two-factor authentication"""
    if current_user.totp_enabled:
        flash('Two-factor authentication is already enabled', 'info')
        return redirect(url_for('main.dashboard'))
    
    form = TOTPSetupForm()
    
    if request.method == 'GET':
        # Generate TOTP secret
        secret = pyotp.random_base32()
        session['totp_secret'] = secret
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name='MoxNAS'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        qr_code = base64.b64encode(img_io.getvalue()).decode()
        
        return render_template('auth/setup_2fa.html', form=form, 
                             qr_code=qr_code, secret=secret)
    
    if form.validate_on_submit():
        secret = session.get('totp_secret')
        if not secret:
            flash('Session expired. Please try again.', 'danger')
            return redirect(url_for('auth.setup_2fa'))
        
        totp = pyotp.TOTP(secret)
        if totp.verify(form.totp_code.data):
            current_user.totp_secret = secret
            current_user.totp_enabled = True
            db.session.commit()
            
            session.pop('totp_secret', None)
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='auth',
                message=f'Two-factor authentication enabled: {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            
            flash('Two-factor authentication has been enabled successfully', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')
    
    # Regenerate QR code if validation failed
    secret = session.get('totp_secret')
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name='MoxNAS'
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color='black', back_color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    qr_code = base64.b64encode(img_io.getvalue()).decode()
    
    return render_template('auth/setup_2fa.html', form=form, 
                         qr_code=qr_code, secret=secret)

@bp.route('/2fa/disable', methods=['GET', 'POST'])
@login_required
def disable_2fa():
    """Disable two-factor authentication"""
    if not current_user.totp_enabled:
        flash('Two-factor authentication is not enabled', 'info')
        return redirect(url_for('main.dashboard'))
    
    form = TOTPDisableForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('auth/disable_2fa.html', form=form)
        
        totp = pyotp.TOTP(current_user.totp_secret)
        if not totp.verify(form.totp_code.data):
            flash('Invalid two-factor authentication code', 'danger')
            return render_template('auth/disable_2fa.html', form=form)
        
        current_user.totp_secret = None
        current_user.totp_enabled = False
        current_user.backup_codes = None
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.WARNING,
            category='auth',
            message=f'Two-factor authentication disabled: {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        
        flash('Two-factor authentication has been disabled', 'warning')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/disable_2fa.html', form=form)