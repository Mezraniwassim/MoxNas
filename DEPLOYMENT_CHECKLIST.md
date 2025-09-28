# MoxNAS Deployment Checklist

## ✅ Pre-Deployment Security Checklist

### 🔒 Critical Security Items
- [ ] **SECRET_KEY**: Generate and set secure 32+ character secret key
- [ ] **Environment Variables**: Copy `.env.example` to `.env.local` and configure
- [ ] **Database Credentials**: Change default PostgreSQL passwords
- [ ] **SSL/TLS**: Configure HTTPS certificates
- [ ] **Firewall**: Configure appropriate port access (80, 443, 22)
- [ ] **Admin Account**: Create secure admin account with strong password

### 🛡️ Security Validation
- [ ] Run `./security_check.py` - all checks must pass
- [ ] Verify no development credentials in production
- [ ] Confirm CSRF protection enabled
- [ ] Validate session security settings
- [ ] Test rate limiting functionality

## 📊 Performance Optimization

### 🗄️ Database Optimization
- [ ] Run `./db_optimize.py` for performance tuning
- [ ] Verify all database indexes are created
- [ ] Configure connection pooling
- [ ] Set up automated VACUUM and ANALYZE

### ⚡ Application Performance
- [ ] Configure Redis for caching and sessions
- [ ] Set up Celery workers for background tasks
- [ ] Enable gzip compression in web server
- [ ] Configure static file caching

## 🚀 Deployment Steps

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y postgresql redis-server nginx supervisor
```

### 2. Application Setup
```bash
# Clone repository
git clone https://github.com/Mezraniwassim/MoxNas.git /opt/moxnas
cd /opt/moxnas

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Security Configuration
```bash
# Generate secure secret key
python3 -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env.local

# Set secure file permissions
chmod 600 .env.local
chmod 700 instance/

# Run security validation
./security_check.py
```

### 4. Database Setup
```bash
# Initialize database
python migrate.py init

# Create admin user
python migrate.py create-admin --username admin --email admin@yourdomain.com

# Optimize database
./db_optimize.py
```

### 5. Service Configuration
```bash
# Configure systemd services
sudo cp moxnas.service /etc/systemd/system/
sudo systemctl enable moxnas
sudo systemctl start moxnas

# Configure Nginx
sudo cp nginx.conf /etc/nginx/sites-available/moxnas
sudo ln -s /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

## 🧪 Post-Deployment Testing

### Functionality Tests
- [ ] **Authentication**: Test login/logout functionality
- [ ] **Storage Management**: Create and manage storage pools
- [ ] **Network Shares**: Configure SMB, NFS, and FTP shares
- [ ] **Backup System**: Create and test backup jobs
- [ ] **Monitoring**: Verify real-time monitoring dashboard
- [ ] **API Endpoints**: Test REST API functionality

### Performance Tests
- [ ] Run `./comprehensive_test.py` - must achieve 90+ score
- [ ] Verify page load times < 2 seconds
- [ ] Test concurrent user capacity (target: 100+ users)
- [ ] Validate backup performance
- [ ] Monitor memory usage (target: < 512MB base)

### Security Tests
- [ ] **Authentication Security**: Test failed login lockout
- [ ] **CSRF Protection**: Verify form submissions protected
- [ ] **Rate Limiting**: Test API rate limiting
- [ ] **Session Security**: Validate session timeout
- [ ] **HTTPS**: Confirm all traffic encrypted

## 📈 Monitoring Setup

### Application Monitoring
- [ ] Configure log rotation for `/logs/moxnas.log`
- [ ] Set up system metrics collection
- [ ] Configure alert thresholds
- [ ] Test notification delivery

### Storage Monitoring
- [ ] Enable SMART monitoring for all drives
- [ ] Configure RAID health checks
- [ ] Set up disk space alerts
- [ ] Test backup verification

## 🔧 Maintenance Tasks

### Daily
- [ ] Check system status dashboard
- [ ] Review security logs for anomalies
- [ ] Verify backup job completion

### Weekly
- [ ] Run database optimization
- [ ] Review performance metrics
- [ ] Check storage pool health
- [ ] Update system packages

### Monthly
- [ ] Security audit and penetration testing
- [ ] Capacity planning review
- [ ] Backup restoration testing
- [ ] Update MoxNAS to latest version

## 📚 Documentation

### Required Documentation
- [ ] **Network Diagram**: Document network topology
- [ ] **User Manual**: Create user guides for common tasks
- [ ] **Admin Guide**: Document administrative procedures
- [ ] **Disaster Recovery**: Document backup and recovery procedures
- [ ] **Security Policies**: Document security procedures and policies

### Training Materials
- [ ] Admin training for system management
- [ ] User training for basic operations
- [ ] Emergency procedures documentation

## 🆘 Emergency Procedures

### Backup Recovery
```bash
# Restore from backup
python backup_restore.py --backup-id <backup_id> --target /restore/path

# Database recovery
pg_restore -d moxnas backup.sql
```

### System Recovery
```bash
# Service restart
sudo systemctl restart moxnas moxnas-worker nginx postgresql redis

# Database maintenance
sudo -u postgres psql -d moxnas -c "VACUUM FULL; REINDEX DATABASE moxnas;"
```

### Security Incident Response
1. **Immediate**: Isolate affected systems
2. **Assessment**: Run security audit tools
3. **Recovery**: Restore from known good backup
4. **Analysis**: Review logs and identify root cause
5. **Prevention**: Update security measures

## 📞 Support Contacts

- **Primary Admin**: [Your Name] - [Email] - [Phone]
- **Backup Admin**: [Backup Name] - [Email] - [Phone]  
- **Security Team**: [Security Contact] - [Email]
- **Infrastructure Team**: [Infrastructure Contact] - [Email]

## ✅ Sign-off

- [ ] **Security Officer**: _________________ Date: _______
- [ ] **System Administrator**: _____________ Date: _______
- [ ] **Project Manager**: _________________ Date: _______
- [ ] **Business Owner**: __________________ Date: _______

---

**Deployment completed successfully when all items are checked and signed off.**
