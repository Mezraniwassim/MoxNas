# MoxNAS Security Configuration Guide

## Overview

MoxNAS now uses environment variables stored in a `.env` file to manage all sensitive configuration data, including passwords, API keys, and connection details. This approach enhances security by:

- Removing hardcoded passwords from source code
- Enabling different configurations for development/production environments
- Centralizing sensitive configuration management
- Preventing accidental exposure of credentials in version control

## Environment Configuration

### 1. Initial Setup

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Required Configuration

Edit `.env` and set the following required variables:

```bash
# Essential Security Settings
SECRET_KEY=your-super-secret-django-key-here-make-it-very-long-and-random
PROXMOX_HOST=your-proxmox-host-ip
PROXMOX_PASSWORD=your-proxmox-password
CONTAINER_ROOT_PASSWORD=secure-container-root-password
```

### 3. Generate Secure Keys

For the Django `SECRET_KEY`, generate a secure random key:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Environment Variables Reference

### Django Configuration

- `SECRET_KEY`: Django secret key for cryptographic signing
- `DEBUG`: Enable/disable debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames

### Database Configuration

- `DATABASE_ENGINE`: Database backend (default: SQLite)
- `DATABASE_NAME`: Database name or file path
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password
- `DATABASE_HOST`: Database host
- `DATABASE_PORT`: Database port

### Proxmox Configuration

- `PROXMOX_HOST`: Proxmox server IP address or hostname
- `PROXMOX_USER`: Proxmox username (default: root@pam)
- `PROXMOX_PASSWORD`: Proxmox user password
- `PROXMOX_PORT`: Proxmox API port (default: 8006)
- `PROXMOX_VERIFY_SSL`: Verify SSL certificates (True/False)

### Container Configuration

- `CONTAINER_ROOT_PASSWORD`: Default root password for new containers
- `CONTAINER_DEFAULT_PASSWORD`: Default user password for containers

### Service Configuration

- `SMB_WORKGROUP`: SMB/CIFS workgroup name
- `NFS_EXPORT_OPTIONS`: Default NFS export options
- `FTP_PASSIVE_PORTS`: FTP passive port range
- `ISCSI_TARGET_PREFIX`: iSCSI target naming prefix

### Security Configuration

- `ENCRYPTION_KEY`: Key for encrypting sensitive data
- `API_SECRET_KEY`: Secret key for API authentication

### Logging Configuration

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE_PATH`: Path to log file

## Usage in Code

### Python/Django Code

Import and use the secure configuration:

```python
from django.conf import settings

# Access Proxmox configuration
proxmox_config = settings.PROXMOX_CONFIG
host = proxmox_config['HOST']
password = proxmox_config['PASSWORD']
```

### Test Scripts

Use the secure configuration utility:

```python
from secure_config import SecureConfig

# Get Proxmox configuration
config = SecureConfig.get_proxmox_config()
api = ProxmoxAPI(
    config['host'],
    user=config['user'],
    password=config['password'],
    verify_ssl=config['verify_ssl']
)
```

## Security Best Practices

### 1. File Permissions

Secure the `.env` file permissions:

```bash
chmod 600 .env
```

### 2. Version Control

- Never commit `.env` files to version control
- The `.gitignore` file is configured to exclude `.env` files
- Only commit `.env.example` as a template

### 3. Production Deployment

For production environments:

- Use stronger passwords (minimum 16 characters)
- Enable SSL verification for Proxmox connections
- Set `DEBUG=False`
- Use a production database (PostgreSQL/MySQL)
- Configure proper logging

### 4. Regular Security Maintenance

- Rotate passwords regularly
- Monitor access logs
- Update dependencies regularly
- Review and audit configuration changes

## Migration from Hardcoded Values

The following files have been updated to use environment variables:

### Core Django Files

- `backend/moxnas/settings.py` - Main Django configuration
- `backend/secure_config.py` - Configuration utility

### Test Files

- `backend/test_complete_workflow.py`
- `backend/test_proxmox_connection.py`
- `backend/check_containers.py`
- `backend/check_tasks.py`

### Application Files

- `backend/proxmox_integration/views.py`

## Troubleshooting

### Configuration Validation

Test your configuration:

```bash
cd backend
python secure_config.py
```

### Common Issues

1. **Missing .env file**: Copy `.env.example` to `.env`
2. **Permission denied**: Check file permissions with `ls -la .env`
3. **Connection failed**: Verify Proxmox host and credentials
4. **Import errors**: Ensure `python-dotenv` is installed

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
LOG_LEVEL=DEBUG
```

## Security Compliance

This configuration approach follows security best practices:

- **Principle of Least Privilege**: Each component only accesses required configuration
- **Defense in Depth**: Multiple layers of security (file permissions, .gitignore, etc.)
- **Separation of Concerns**: Configuration separated from code
- **Audit Trail**: All configuration changes are logged

## Support

For security-related questions or issues:

1. Check this documentation
2. Review the `.env.example` template
3. Test configuration with `secure_config.py`
4. Check application logs for detailed error messages
