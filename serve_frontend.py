#!/usr/bin/env python3
"""Simple server to serve the MoxNAS frontend"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Set the directory to serve
FRONTEND_DIR = Path(__file__).parent / "frontend"
PORT = 8081

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"Serving MoxNAS frontend at http://localhost:{PORT}/")
        print(f"Frontend directory: {FRONTEND_DIR}")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()
