#!/bin/bash

# MoxNAS Startup Script
# This script starts both the Django backend and frontend servers

echo "🚀 Starting MoxNAS..."

# Navigate to project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Start Django backend server
echo "🔧 Starting Django backend API server on http://127.0.0.1:8000/"
cd backend
python manage.py runserver 127.0.0.1:8000 --noreload &
DJANGO_PID=$!
cd ..

# Wait a moment for Django to start
sleep 2

# Start frontend server
echo "🌐 Starting frontend server on http://127.0.0.1:3000/"
cd frontend
python -m http.server 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ MoxNAS is now running!"
echo "   📱 Frontend Interface: http://127.0.0.1:3000/"
echo "   🔌 Backend API:        http://127.0.0.1:8000/"
echo ""
echo "🛑 To stop the servers, press Ctrl+C or run:"
echo "   kill $DJANGO_PID $FRONTEND_PID"
echo ""

# Wait for user interrupt
trap 'echo "🛑 Stopping MoxNAS servers..."; kill $DJANGO_PID $FRONTEND_PID 2>/dev/null; exit 0' INT

# Keep script running
wait
