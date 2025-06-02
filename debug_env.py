#!/usr/bin/env python3
"""Debug environment variable loading."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
print(f"Looking for .env file at: {env_path}")
print(f"File exists: {env_path.exists()}")

if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print("❌ .env file not found!")

# Check what we got
print("\n=== Environment Variables ===")
print(f"PROXMOX_HOST: {os.getenv('PROXMOX_HOST', 'NOT_SET')}")
print(f"PROXMOX_USER: {os.getenv('PROXMOX_USER', 'NOT_SET')}")
print(f"PROXMOX_PASSWORD: {os.getenv('PROXMOX_PASSWORD', 'NOT_SET')}")
print(f"PROXMOX_VERIFY_SSL: {os.getenv('PROXMOX_VERIFY_SSL', 'NOT_SET')}")
print(f"PROXMOX_PORT: {os.getenv('PROXMOX_PORT', 'NOT_SET')}")

# Try loading with verbose output
print("\n=== Trying to load .env with verbose output ===")
result = load_dotenv(env_path, verbose=True)
print(f"Load result: {result}")

# Check again after verbose load
print(f"PROXMOX_HOST after verbose load: {os.getenv('PROXMOX_HOST', 'NOT_SET')}")
