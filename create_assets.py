#!/usr/bin/env python3
"""
Create missing assets for MoxNAS PWA
Generate favicons and icons programmatically
"""
from PIL import Image, ImageDraw, ImageFont
import os
import base64
from io import BytesIO

def create_moxnas_icon(size, bg_color="#007bff", text_color="#ffffff"):
    """Create MoxNAS icon with HDD stack symbol"""
    # Create image
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate proportions
    padding = size // 8
    icon_size = size - (2 * padding)
    
    # Draw HDD stack (simplified representation)
    # Main storage box
    box_height = icon_size // 3
    box_width = icon_size - (icon_size // 4)
    
    start_x = (size - box_width) // 2
    start_y = padding + (icon_size // 6)
    
    # Draw 3 stacked drives
    for i in range(3):
        y_offset = i * (box_height // 2 + 4)
        
        # Drive body
        drive_rect = [
            start_x, start_y + y_offset,
            start_x + box_width, start_y + y_offset + box_height
        ]
        draw.rounded_rectangle(drive_rect, radius=size//20, fill=text_color)
        
        # Drive details (LED indicator)
        led_size = size // 16
        led_x = start_x + box_width - led_size - (size // 20)
        led_y = start_y + y_offset + (box_height // 2) - (led_size // 2)
        
        led_color = "#28a745" if i == 0 else "#ffc107" if i == 1 else "#dc3545"
        draw.ellipse([led_x, led_y, led_x + led_size, led_y + led_size], fill=led_color)
    
    # Add "M" letter in corner for MoxNAS
    try:
        font_size = size // 6
        font = ImageFont.load_default()
        
        # Draw "M" in bottom right
        text = "M"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = size - text_width - (size // 20)
        text_y = size - text_height - (size // 20)
        
        # Background circle for text
        circle_radius = max(text_width, text_height) // 2 + 4
        circle_center_x = text_x + text_width // 2
        circle_center_y = text_y + text_height // 2
        
        draw.ellipse([
            circle_center_x - circle_radius,
            circle_center_y - circle_radius,
            circle_center_x + circle_radius,
            circle_center_y + circle_radius
        ], fill=bg_color, outline=text_color, width=2)
        
        draw.text((text_x, text_y), text, fill=text_color, font=font)
    except:
        pass  # Skip text if font issues
    
    return img

def create_simple_favicon():
    """Create simple 16x16 favicon"""
    img = Image.new('RGBA', (16, 16), '#007bff')
    draw = ImageDraw.Draw(img)
    
    # Simple HDD representation
    draw.rectangle([2, 4, 14, 12], fill='#ffffff')
    draw.rectangle([12, 6, 13, 7], fill='#28a745')  # Green LED
    draw.rectangle([12, 9, 13, 10], fill='#ffc107')  # Yellow LED
    
    return img

def save_icon(img, path):
    """Save icon to file"""
    img.save(path, 'PNG', optimize=True)
    print(f"✅ Created: {path}")

def main():
    """Generate all required icons"""
    print("🎨 Generating MoxNAS assets...")
    
    base_path = "app/static/images"
    os.makedirs(base_path, exist_ok=True)
    
    # Icon sizes needed
    sizes = [16, 32, 72, 96, 128, 144, 152, 192, 384, 512]
    
    # Generate icons
    for size in sizes:
        if size <= 32:
            # Use simple design for small sizes
            img = create_simple_favicon() if size == 16 else create_moxnas_icon(size)
        else:
            img = create_moxnas_icon(size)
        
        filename = f"icon-{size}x{size}.png"
        save_icon(img, f"{base_path}/{filename}")
    
    # Create favicons
    favicon_16 = create_simple_favicon()
    save_icon(favicon_16, f"{base_path}/favicon-16x16.png")
    
    favicon_32 = create_moxnas_icon(32)
    save_icon(favicon_32, f"{base_path}/favicon-32x32.png")
    
    # Create Apple touch icon
    apple_icon = create_moxnas_icon(180)
    save_icon(apple_icon, f"{base_path}/apple-touch-icon.png")
    
    # Create shortcut icons
    shortcut_icons = ['dashboard', 'storage', 'shares', 'monitoring']
    colors = ['#007bff', '#28a745', '#ffc107', '#17a2b8']
    
    for i, (name, color) in enumerate(zip(shortcut_icons, colors)):
        shortcut_img = create_moxnas_icon(96, bg_color=color)
        save_icon(shortcut_img, f"{base_path}/shortcut-{name}.png")
    
    print(f"\n🎉 Generated {len(sizes) + 6} icons successfully!")
    print("📱 PWA assets are now complete")

if __name__ == '__main__':
    main()