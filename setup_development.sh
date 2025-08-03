#!/bin/bash

# MoxNas Development Environment Setup
set -e

echo "🚀 Setting up MoxNas development environment..."

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r ../requirements.txt
echo "✅ Python dependencies installed"

# Generate migrations
python manage.py makemigrations proxmox
python manage.py makemigrations containers  
python manage.py makemigrations services
python manage.py makemigrations storage
echo "✅ Database migrations generated"

# Apply migrations
python manage.py migrate
echo "✅ Database migrations applied"

# Create superuser (optional)
echo "Creating superuser (optional)..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('✅ Superuser already exists')
"

cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Node.js dependencies installed"
else
    echo "✅ Node.js dependencies already installed"
fi

cd ..

echo "🎉 Development environment setup complete!"
echo ""
echo "To start development servers:"
echo "1. Backend: cd backend && source venv/bin/activate && python manage.py runserver"
echo "2. Frontend: cd frontend && npm start"
echo ""
echo "Or use: python start_moxnas.py"
