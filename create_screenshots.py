#!/usr/bin/env python3
"""
Create placeholder screenshots for MoxNAS PWA
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_desktop_screenshot():
    """Create desktop screenshot (1280x720)"""
    img = Image.new('RGB', (1280, 720), '#f8f9fa')
    draw = ImageDraw.Draw(img)
    
    # Header bar
    draw.rectangle([0, 0, 1280, 60], fill='#343a40')
    
    # MoxNAS logo/title
    try:
        font = ImageFont.load_default()
        draw.text((20, 20), "MoxNAS Dashboard", fill='#ffffff', font=font)
    except:
        draw.text((20, 20), "MoxNAS Dashboard", fill='#ffffff')
    
    # Sidebar
    draw.rectangle([0, 60, 250, 720], fill='#495057')
    
    # Navigation items
    nav_items = ["Dashboard", "Storage", "Shares", "Backups", "Monitoring"]
    for i, item in enumerate(nav_items):
        y = 100 + (i * 50)
        color = '#007bff' if i == 0 else '#6c757d'
        draw.rectangle([10, y, 240, y + 40], fill=color)
        try:
            draw.text((20, y + 12), item, fill='#ffffff', font=font)
        except:
            draw.text((20, y + 12), item, fill='#ffffff')
    
    # Main content area
    draw.rectangle([250, 60, 1280, 720], fill='#ffffff')
    
    # Cards/widgets
    cards = [
        (280, 100, 500, 200, "CPU Usage", "#007bff"),
        (520, 100, 740, 200, "Memory", "#28a745"),
        (760, 100, 980, 200, "Storage", "#ffc107"),
        (1000, 100, 1220, 200, "Network", "#17a2b8")
    ]
    
    for x1, y1, x2, y2, title, color in cards:
        # Card background
        draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill='#ffffff', outline='#dee2e6', width=1)
        # Card header
        draw.rectangle([x1, y1, x2, y1 + 30], fill=color)
        try:
            draw.text((x1 + 10, y1 + 8), title, fill='#ffffff', font=font)
        except:
            draw.text((x1 + 10, y1 + 8), title, fill='#ffffff')
    
    # Chart area
    draw.rounded_rectangle([280, 250, 1220, 650], radius=8, fill='#ffffff', outline='#dee2e6', width=1)
    try:
        draw.text((300, 270), "System Performance Chart", fill='#495057', font=font)
    except:
        draw.text((300, 270), "System Performance Chart", fill='#495057')
    
    # Simulate chart lines
    import random
    points = []
    for i in range(0, 900, 10):
        x = 300 + i
        y = 400 + random.randint(-50, 50)
        points.append((x, y))
    
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill='#007bff', width=2)
    
    return img

def create_mobile_screenshot():
    """Create mobile screenshot (375x812)"""
    img = Image.new('RGB', (375, 812), '#f8f9fa')
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.rectangle([0, 0, 375, 80], fill='#343a40')
    try:
        font = ImageFont.load_default()
        draw.text((20, 30), "MoxNAS", fill='#ffffff', font=font)
        draw.text((320, 30), "☰", fill='#ffffff', font=font)
    except:
        draw.text((20, 30), "MoxNAS", fill='#ffffff')
        draw.text((320, 30), "Menu", fill='#ffffff')
    
    # Cards in mobile layout
    cards = [
        (20, 100, 355, 180, "System Status", "#007bff"),
        (20, 200, 355, 280, "Storage Pools", "#28a745"),
        (20, 300, 355, 380, "Active Shares", "#ffc107"),
        (20, 400, 355, 480, "Recent Backups", "#17a2b8")
    ]
    
    for x1, y1, x2, y2, title, color in cards:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill='#ffffff', outline='#dee2e6', width=1)
        draw.rectangle([x1, y1, x2, y1 + 25], fill=color)
        try:
            draw.text((x1 + 10, y1 + 5), title, fill='#ffffff', font=font)
        except:
            draw.text((x1 + 10, y1 + 5), title, fill='#ffffff')
    
    # Bottom navigation
    draw.rectangle([0, 750, 375, 812], fill='#343a40')
    nav_icons = ["📊", "💾", "📁", "📈"]
    for i, icon in enumerate(nav_icons):
        x = 20 + (i * 80)
        try:
            draw.text((x, 770), icon, fill='#ffffff', font=font)
        except:
            draw.text((x, 770), "•", fill='#ffffff')
    
    return img

def main():
    """Generate screenshots"""
    print("📸 Creating MoxNAS screenshots...")
    
    base_path = "app/static/images"
    
    # Desktop screenshot
    desktop = create_desktop_screenshot()
    desktop.save(f"{base_path}/screenshot-desktop.png", 'PNG', optimize=True)
    print("✅ Created desktop screenshot")
    
    # Mobile screenshot
    mobile = create_mobile_screenshot()
    mobile.save(f"{base_path}/screenshot-mobile.png", 'PNG', optimize=True)
    print("✅ Created mobile screenshot")
    
    print("📱 Screenshots generated successfully!")

if __name__ == '__main__':
    main()