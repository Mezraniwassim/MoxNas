# MoxNAS Development Setup Guide

## 🚀 Quick Start

### 1. Environment Configuration

Your MoxNAS project is now configured with secure environment variables. To get started with development:

#### Update your `.env` file with actual credentials

```bash
# Edit the .env file
nano .env
```

**Required changes:**

- Replace `your-proxmox-host-ip` with your actual Proxmox VE host IP
- Replace `your-proxmox-password-here` with your actual Proxmox root password
- Replace `your-secure-container-root-password` with a strong password for containers
- Replace `your-secure-default-container-password` with a strong default password

#### Example configuration

```bash
PROXMOX_HOST=192.168.1.100
PROXMOX_PASSWORD=your-actual-proxmox-password
CONTAINER_ROOT_PASSWORD=SecureContainerRoot123!
CONTAINER_DEFAULT_PASSWORD=SecureDefault456!
```

### 2. Start Development Server

```bash
# Navigate to backend directory
cd /home/wassim/Documents/MoxNas/backend

# Activate virtual environment (if not already active)
source ../venv/bin/activate

# Start Django development server
python manage.py runserver
```

### 3. Access the Interface

- **Backend API**: <http://localhost:8000/>
- **Frontend**: Open `/home/wassim/Documents/MoxNas/frontend/index.html` in your browser
- **API Configuration**: <http://localhost:8000/api/proxmox/api/config/> (provides safe config values)

### 4. Testing the Connection

1. Open the frontend interface
2. Click "Connect to Proxmox" - the form will be pre-filled with your configuration
3. Enter your password and click "Connect"

## 🔒 Security Features Implemented

✅ **Complete Credential Security**:

- All hardcoded passwords removed
- Environment variables for all sensitive data
- Secure file permissions (600) on `.env`
- `.gitignore` prevents credential exposure

✅ **Configuration Management**:

- Centralized `SecureConfig` class
- Frontend gets safe config values via API
- Production-ready separation of concerns

✅ **Validation & Monitoring**:

- Environment validation script
- Comprehensive logging
- Django system checks pass

## 🛠️ Development Commands

```bash
# Validate environment configuration
python validate_env.py

# Check Django configuration
python manage.py check

# Run tests
python test_proxmox_connection.py

# View logs
tail -f backend/logs/moxnas.log
```

## 📁 Project Structure

```
MoxNAS/
├── .env                    # Your secure configuration (never commit!)
├── .env.example           # Template for new setups
├── validate_env.py        # Environment validation
├── backend/
│   ├── secure_config.py   # Configuration utility
│   ├── manage.py          # Django management
│   └── proxmox_integration/
└── frontend/
    └── src/js/proxmox.js  # Frontend interface
```

## 🚨 Important Security Notes

1. **Never commit `.env`** - it contains sensitive credentials
2. **For production**:
   - Set `DEBUG=False`
   - Set `PROXMOX_VERIFY_SSL=True`
   - Use strong, unique passwords
   - Enable HTTPS
3. **Share `.env.example`** with team members for local setup

## 🎯 Next Steps

Your MoxNAS system is now secure and ready for development! The environment variable implementation ensures that:

- No sensitive data is hardcoded in source files
- Team members can set up their own local environments safely
- Production deployments are secure by default
- Configuration is centralized and manageable

**Ready to start developing!** 🚀
