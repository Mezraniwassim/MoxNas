#!/usr/bin/env python3
"""
Production Environment Setup Script for MoxNAS LXC Deployment
Configures database, services, and system for production use
"""

import os
import sys
import subprocess
import json
import secrets
import string
from pathlib import Path

def run_command(cmd, shell=True, check=True, capture_output=True):
    """Run a command with error handling"""
    try:
        if shell and isinstance(cmd, list):
            cmd = ' '.join(cmd)
        
        result = subprocess.run(
            cmd, 
            shell=shell, 
            check=check, 
            capture_output=capture_output,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)

def log(message):
    """Log a message"""
    print(f"[INFO] {message}")

def error(message):
    """Log an error message"""
    print(f"[ERROR] {message}", file=sys.stderr)

def success(message):
    """Log a success message"""
    print(f"[SUCCESS] {message}")

def generate_secret_key():
    """Generate a secure secret key"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def setup_postgresql():
    """Setup PostgreSQL for production"""
    log("Setting up PostgreSQL...")
    
    # Generate secure password
    db_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    # Create database and user
    commands = [
        f"sudo -u postgres psql -c \"CREATE DATABASE moxnas;\"",
        f"sudo -u postgres psql -c \"CREATE USER moxnas WITH PASSWORD '{db_password}';\"",
        f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE moxnas TO moxnas;\"",
        f"sudo -u postgres psql -c \"ALTER USER moxnas CREATEDB;\"",
        f"sudo -u postgres psql -c \"ALTER DATABASE moxnas OWNER TO moxnas;\""
    ]
    
    for cmd in commands:
        success_flag, stdout, stderr = run_command(cmd)
        if not success_flag and "already exists" not in stderr:
            error(f"Failed to execute: {cmd}")
            error(f"Error: {stderr}")
            return None
    
    success("PostgreSQL database setup completed")
    return db_password

def create_env_file(db_password):
    """Create production environment file"""
    log("Creating production environment file...")
    
    secret_key = generate_secret_key()
    
    env_content = f"""# MoxNAS Production Environment Configuration
# Generated automatically - DO NOT COMMIT TO VERSION CONTROL

# Flask Configuration
FLASK_ENV=production
SECRET_KEY={secret_key}

# Database Configuration
DATABASE_URL=postgresql://moxnas:{db_password}@localhost/moxnas

# Redis Configuration  
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security Settings
SESSION_COOKIE_SECURE=true
WTF_CSRF_ENABLED=true

# Application Settings
MOXNAS_ADMIN_EMAIL=admin@moxnas.local
MOXNAS_STORAGE_ROOT=/mnt/storage
MOXNAS_BACKUP_ROOT=/mnt/backups
MOXNAS_LOG_LEVEL=INFO

# Mail Settings (configure as needed)
MAIL_SERVER=localhost
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
"""
    
    env_file = Path("/opt/moxnas/.env")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    # Set secure permissions
    os.chmod(env_file, 0o600)
    
    success(f"Environment file created: {env_file}")
    return env_file

def setup_directories():
    """Create required directories with proper permissions"""
    log("Setting up directories...")
    
    directories = [
        "/opt/moxnas",
        "/mnt/storage", 
        "/mnt/backups",
        "/var/log/moxnas",
        "/var/run/moxnas"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            # Set ownership to moxnas user if it exists
            run_command(f"chown moxnas:moxnas {directory}", check=False)
            success(f"Directory created: {directory}")
        except Exception as e:
            error(f"Failed to create directory {directory}: {e}")

def create_systemd_override():
    """Create systemd service override for LXC environment"""
    log("Creating systemd service override...")
    
    override_content = """[Unit]
# LXC Container optimizations
After=network-online.target postgresql.service redis-server.service

[Service]
# LXC-specific settings
Environment="FLASK_ENV=production"
EnvironmentFile=/opt/moxnas/.env

# Adjust for container environment
PrivateDevices=no
ProtectKernelTunables=no
ProtectKernelModules=no

# Resource limits for LXC
MemoryMax=1G
CPUQuota=100%

# Restart policy
Restart=always
RestartSec=10
"""
    
    override_dir = Path("/etc/systemd/system/moxnas.service.d")
    override_dir.mkdir(parents=True, exist_ok=True)
    
    override_file = override_dir / "lxc.conf"
    with open(override_file, 'w') as f:
        f.write(override_content)
    
    success(f"Systemd override created: {override_file}")
    
    # Reload systemd
    run_command("systemctl daemon-reload")

def initialize_database():
    """Initialize database with tables and admin user"""
    log("Initializing database...")
    
    # Change to MoxNAS directory
    os.chdir("/opt/moxnas")
    
    # Initialize database
    success_flag, stdout, stderr = run_command("python -c 'from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); db.create_all()'")
    
    if success_flag:
        success("Database tables created successfully")
    else:
        error(f"Failed to create database tables: {stderr}")
        return False
    
    # Create admin user
    admin_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    
    create_admin_script = f"""
from app import create_app, db
from app.models import User, UserRole
from werkzeug.security import generate_password_hash

app = create_app('production')
with app.app_context():
    # Check if admin exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@moxnas.local',
            role=UserRole.ADMIN,
            is_active=True,
            password_hash=generate_password_hash('{admin_password}')
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"""
    
    success_flag, stdout, stderr = run_command(f'python -c "{create_admin_script}"')
    
    if success_flag:
        success("Admin user setup completed")
        log(f"Admin credentials: admin / {admin_password}")
        
        # Save credentials to file
        creds_file = Path("/opt/moxnas/.admin_credentials")
        with open(creds_file, 'w') as f:
            f.write(f"Username: admin\nPassword: {admin_password}\n")
        os.chmod(creds_file, 0o600)
        
        return True
    else:
        error(f"Failed to create admin user: {stderr}")
        return False

def setup_nginx():
    """Setup nginx reverse proxy configuration"""
    log("Setting up nginx configuration...")
    
    nginx_config = """# MoxNAS Nginx Configuration
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL Configuration (self-signed for now)
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Proxy to MoxNAS application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static files
    location /static {
        alias /opt/moxnas/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
"""
    
    config_file = Path("/etc/nginx/sites-available/moxnas")
    with open(config_file, 'w') as f:
        f.write(nginx_config)
    
    # Enable site
    sites_enabled = Path("/etc/nginx/sites-enabled/moxnas")
    if not sites_enabled.exists():
        sites_enabled.symlink_to("../sites-available/moxnas")
    
    # Generate self-signed certificate
    run_command("openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/moxnas-selfsigned.key -out /etc/ssl/certs/moxnas-selfsigned.crt -subj '/CN=moxnas'", check=False)
    
    success("Nginx configuration created")

def main():
    """Main setup function"""
    print("🚀 MoxNAS Production Environment Setup")
    print("=" * 50)
    
    if os.geteuid() != 0:
        error("This script must be run as root")
        sys.exit(1)
    
    # Setup PostgreSQL
    db_password = setup_postgresql()
    if not db_password:
        error("Failed to setup PostgreSQL")
        sys.exit(1)
    
    # Create environment file
    env_file = create_env_file(db_password)
    
    # Setup directories
    setup_directories()
    
    # Create systemd override
    create_systemd_override()
    
    # Initialize database
    if not initialize_database():
        error("Failed to initialize database")
        sys.exit(1)
    
    # Setup nginx
    setup_nginx()
    
    print("\n" + "=" * 50)
    success("MoxNAS production environment setup completed!")
    print("\nNext steps:")
    print("1. Start services: systemctl start moxnas redis-server postgresql nginx")
    print("2. Enable services: systemctl enable moxnas redis-server postgresql nginx")
    print("3. Check admin credentials: cat /opt/moxnas/.admin_credentials")
    print("4. Access MoxNAS: https://your-container-ip")
    print("\n⚠️  Remember to:")
    print("   - Change the admin password on first login")
    print("   - Configure mail settings in .env file")
    print("   - Replace self-signed SSL certificate with proper certificate")

if __name__ == "__main__":
    main()