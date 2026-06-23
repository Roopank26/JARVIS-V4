#!/usr/bin/env python3
"""
JARVIS Desktop - Icon Generator
Creates JARVIS application icon.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_icon(size: int = 256, output_dir: str = "resources") -> Path:
    """Create JARVIS application icon."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create base image with transparency
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    bg_color = (30, 60, 90, 255)       # Dark blue
    circle_color = (70, 130, 180, 255) # Light blue
    text_color = (255, 255, 255, 255)  # White
    
    # Draw rounded rectangle background
    margin = size // 16
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 8,
        fill=bg_color
    )
    
    # Draw circle
    circle_margin = size // 5
    draw.ellipse(
        [circle_margin, circle_margin, size - circle_margin, size - circle_margin],
        fill=circle_color
    )
    
    # Draw J letter (simplified, no font needed)
    center = size // 2
    letter_size = size // 3
    
    # Draw J as simple shapes
    # Vertical bar
    bar_width = size // 10
    bar_x = center - letter_size // 3
    bar_top = center - letter_size // 2
    bar_bottom = center + letter_size // 3
    draw.rectangle(
        [bar_x, bar_top, bar_x + bar_width, bar_bottom],
        fill=text_color
    )
    
    # Bottom curve (simplified as horizontal bar)
    draw.rectangle(
        [bar_x - letter_size // 4, bar_bottom - bar_width, bar_x + letter_size // 2, bar_bottom],
        fill=text_color
    )
    
    # Save as PNG
    png_path = output_path / "jarvis.png"
    img.save(png_path, format='PNG')
    print(f"Created: {png_path}")
    
    # Save as ICO (multiple sizes)
    ico_sizes = [16, 32, 48, 64, 128, 256]
    ico_images = []
    
    for ico_size in ico_sizes:
        resized = img.copy()
        resized.thumbnail((ico_size, ico_size), Image.Resampling.LANCZOS)
        ico_images.append(resized)
    
    ico_path = output_path / "jarvis.ico"
    ico_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in ico_sizes]
    )
    print(f"Created: {ico_path}")
    
    return ico_path


def create_icon_simple(size: int = 256, output_dir: str = "resources") -> Path:
    """Create a simpler icon without text."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    img = Image.new('RGBA', (size, size), color=(30, 60, 90, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(70, 130, 180, 255)
    )
    
    # Draw inner circle
    inner_margin = size // 4
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        fill=(100, 160, 210, 255)
    )
    
    # Save
    png_path = output_path / "jarvis.png"
    img.save(png_path, format='PNG')
    print(f"Created: {png_path}")
    
    return png_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate JARVIS icon")
    parser.add_argument("--size", type=int, default=256, help="Icon size")
    parser.add_argument("--output", default="resources", help="Output directory")
    parser.add_argument("--simple", action="store_true", help="Simple icon without text")
    
    args = parser.parse_args()
    
    if args.simple:
        create_icon_simple(args.size, args.output)
    else:
        create_icon(args.size, args.output)
    
    print("Icon generation complete!")
