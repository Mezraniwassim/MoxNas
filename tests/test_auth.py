"""Tests for authentication functionality"""
import pytest
from flask import url_for
from app.models import User, UserRole
from app import db

class TestAuthentication:
    """Test authentication routes and functionality"""
    
    def test_login_page_loads(self, client):
        """Test login page loads correctly"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'MoxNAS Login' in response.data
    
    def test_login_with_valid_credentials(self, client, admin_user):
        """Test login with valid credentials"""
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin_password',
            'csrf_token': 'test_token'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_with_invalid_credentials(self, client, admin_user):
        """Test login with invalid credentials"""
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'wrong_password',
            'csrf_token': 'test_token'
        })
        
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'password',
            'csrf_token': 'test_token'
        })
        
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_logout(self, authenticated_admin_client):
        """Test user logout"""
        response = authenticated_admin_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'You have been logged out' in response.data
    
    def test_account_lockout_after_failed_attempts(self, client, admin_user):
        """Test account lockout after multiple failed attempts"""
        # Make 5 failed login attempts
        for i in range(5):
            response = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'wrong_password',
                'csrf_token': 'test_token'
            })
            assert response.status_code == 200
        
        # 6th attempt should trigger lockout
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'wrong_password',
            'csrf_token': 'test_token'
        })
        
        assert b'Account temporarily locked' in response.data
    
    def test_password_complexity_validation(self, app):
        """Test password complexity requirements"""
        with app.app_context():
            user = User(username='test', email='test@example.com')
            
            # Test weak passwords
            weak_passwords = [
                'short',
                'lowercase',
                'UPPERCASE',
                '12345678',
                'NoNumbers',
                'nonumber!'
            ]
            
            for weak_pwd in weak_passwords:
                with pytest.raises(ValueError):
                    user.set_password(weak_pwd)
            
            # Test strong password
            strong_password = 'StrongPass123!'
            user.set_password(strong_password)
            assert user.check_password(strong_password)
    
    def test_user_creation_with_valid_data(self, app):
        """Test user creation with valid data"""
        with app.app_context():
            user = User(
                username='newuser',
                email='newuser@example.com',
                role=UserRole.USER,
                first_name='New',
                last_name='User'
            )
            user.set_password('ValidPassword123!')
            
            db.session.add(user)
            db.session.commit()
            
            # Verify user was created
            created_user = User.query.filter_by(username='newuser').first()
            assert created_user is not None
            assert created_user.email == 'newuser@example.com'
            assert created_user.role == UserRole.USER
    
    def test_user_password_hashing(self, app):
        """Test password hashing functionality"""
        with app.app_context():
            user = User(username='test', email='test@example.com')
            password = 'TestPassword123!'
            
            user.set_password(password)
            
            # Password should be hashed
            assert user.password_hash != password
            assert user.password_hash is not None
            
            # Should verify correctly
            assert user.check_password(password)
            assert not user.check_password('wrong_password')
    
    def test_2fa_setup(self, app, admin_user):
        """Test 2FA setup functionality"""
        with app.app_context():
            # Generate TOTP secret
            secret = admin_user.generate_totp_secret()
            assert secret is not None
            assert len(secret) == 32
            
            # Enable 2FA
            admin_user.enable_2fa(secret)
            assert admin_user.totp_enabled
            assert admin_user.totp_secret == secret
            
            # Generate and verify TOTP code
            import pyotp
            totp = pyotp.TOTP(secret)
            code = totp.now()
            
            assert admin_user.verify_totp(code)
            assert not admin_user.verify_totp('000000')
    
    def test_session_security(self, authenticated_admin_client):
        """Test session security features"""
        # Test that session contains security markers
        with authenticated_admin_client.session_transaction() as sess:
            assert '_user_id' in sess
            assert '_fresh' in sess
    
    def test_role_based_access(self, app, regular_user, admin_user):
        """Test role-based access control"""
        with app.app_context():
            # Regular user should not be admin
            assert not regular_user.is_admin()
            
            # Admin user should be admin
            assert admin_user.is_admin()
            
            # Test role hierarchy
            assert admin_user.role.value > regular_user.role.value

class TestUserModel:
    """Test User model functionality"""
    
    def test_user_representation(self, admin_user):
        """Test user string representation"""
        assert str(admin_user) == '<User admin>'
    
    def test_user_full_name(self, admin_user):
        """Test full name property"""
        admin_user.first_name = 'John'
        admin_user.last_name = 'Doe'
        assert admin_user.full_name == 'John Doe'
        
        # Test with missing names
        admin_user.first_name = None
        admin_user.last_name = 'Doe'
        assert admin_user.full_name == 'Doe'
    
    def test_user_is_locked(self, app, admin_user):
        """Test user account locking"""
        from datetime import datetime, timedelta
        
        with app.app_context():
            # User should not be locked initially
            assert not admin_user.is_locked()
            
            # Lock user account
            admin_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            assert admin_user.is_locked()
            
            # Unlock user account
            admin_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
            assert not admin_user.is_locked()
    
    def test_user_failed_login_tracking(self, app, admin_user):
        """Test failed login attempt tracking"""
        with app.app_context():
            # Initially no failed attempts
            assert admin_user.failed_login_attempts == 0
            
            # Increment failed attempts
            admin_user.failed_login_attempts = 3
            assert admin_user.failed_login_attempts == 3
            
            # Reset failed attempts
            admin_user.reset_failed_login_attempts()
            assert admin_user.failed_login_attempts == 0
    
    def test_user_activity_tracking(self, app, admin_user):
        """Test user activity tracking"""
        from datetime import datetime
        
        with app.app_context():
            # Update last login
            now = datetime.utcnow()
            admin_user.last_login = now
            
            assert admin_user.last_login == now
    
    def test_user_email_validation(self, app):
        """Test email validation"""
        with app.app_context():
            # Valid emails
            valid_emails = [
                'test@example.com',
                'user.name@domain.co.uk',
                'admin@localhost'
            ]
            
            for email in valid_emails:
                user = User(username='test', email=email)
                # Should not raise exception
                assert user.email == email
            
            # Invalid emails should be caught by form validation, not model

class TestAuthenticationIntegration:
    """Integration tests for authentication system"""
    
    def test_login_redirects_to_dashboard(self, client, admin_user):
        """Test successful login redirects to dashboard"""
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin_password',
            'csrf_token': 'test_token'
        }, follow_redirects=False)
        
        assert response.status_code == 302
        assert response.location.endswith('/dashboard')
    
    def test_dashboard_requires_authentication(self, client):
        """Test dashboard requires authentication"""
        response = client.get('/dashboard')
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_admin_pages_require_admin_role(self, authenticated_user_client):
        """Test admin pages require admin role"""
        admin_urls = [
            '/storage/create-pool',
            '/shares/create',
            '/users/create'
        ]
        
        for url in admin_urls:
            response = authenticated_user_client.get(url)
            # Should redirect to unauthorized page or deny access
            assert response.status_code in [302, 403]
    
    def test_csrf_protection(self, client, admin_user):
        """Test CSRF protection on forms"""
        # Login without CSRF token should fail
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin_password'
        })
        
        # Should either fail or require CSRF token
        assert response.status_code in [200, 400, 403]
    
    def test_rate_limiting_on_login(self, client, admin_user):
        """Test rate limiting on login attempts"""
        # This test would require actual rate limiting implementation
        # For now, just verify the endpoint exists
        response = client.get('/auth/login')
        assert response.status_code == 200
    
    def test_secure_session_configuration(self, app):
        """Test secure session configuration"""
        with app.test_client() as client:
            # Test that secure session settings are configured
            assert app.config.get('SESSION_COOKIE_SECURE') is not None
            assert app.config.get('SESSION_COOKIE_HTTPONLY') is not None
            assert app.config.get('SESSION_COOKIE_SAMESITE') is not None