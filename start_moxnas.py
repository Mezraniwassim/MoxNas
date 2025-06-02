#!/usr/bin/env python3
"""Start both frontend and backend servers for MoxNAS"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def start_backend():
    """Start Django backend server"""
    backend_dir = Path(__file__).parent / "backend"
    print(f"Starting Django backend server from {backend_dir}")
    
    return subprocess.Popen([
        sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"
    ], cwd=str(backend_dir))

def start_frontend():
    """Start frontend server"""
    frontend_script = Path(__file__).parent / "serve_frontend.py"
    print(f"Starting frontend server using {frontend_script}")
    
    return subprocess.Popen([sys.executable, str(frontend_script)])

def main():
    processes = []
    
    try:
        # Start backend
        backend_process = start_backend()
        processes.append(("Backend", backend_process))
        time.sleep(2)  # Give backend time to start
        
        # Start frontend
        frontend_process = start_frontend()
        processes.append(("Frontend", frontend_process))
        
        print("\n" + "="*50)
        print("🚀 MoxNAS is now running!")
        print("="*50)
        print("📡 Backend API: http://127.0.0.1:8000/")
        print("🖥️  Frontend UI: http://localhost:8080/")
        print("="*50)
        print("Press Ctrl+C to stop all servers")
        
        # Wait for processes
        while all(p.poll() is None for _, p in processes):
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        
    finally:
        # Clean up processes
        for name, process in processes:
            if process.poll() is None:
                print(f"Stopping {name} server...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

if __name__ == "__main__":
    main()
