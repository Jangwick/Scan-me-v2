#!/usr/bin/env python3
"""
QR Code Detection Libraries Test
"""

print("🔍 Testing QR Code Detection Libraries")
print("=" * 50)

# Test OpenCV
try:
    import cv2
    print("✅ OpenCV (cv2) is available")
    opencv_available = True
except ImportError:
    print("❌ OpenCV (cv2) not installed")
    opencv_available = False

# Test pyzbar
try:
    from pyzbar import pyzbar
    print("✅ pyzbar is available")
    pyzbar_available = True
except ImportError:
    print("❌ pyzbar not installed")
    pyzbar_available = False

# Test PIL/Pillow
try:
    from PIL import Image
    print("✅ PIL/Pillow is available")
    pillow_available = True
except ImportError:
    print("❌ PIL/Pillow not installed")
    pillow_available = False

print("\n📊 Summary:")
if opencv_available and pyzbar_available and pillow_available:
    print("✅ All required libraries for QR detection are available")
elif pillow_available:
    print("⚠️  Basic image processing available, but QR detection libraries missing")
    print("   Install with: pip install opencv-python pyzbar")
else:
    print("❌ Missing required libraries")
    print("   Install with: pip install opencv-python pyzbar pillow")

print(f"\nRecommended setup for QR detection:")
print(f"pip install opencv-python pyzbar pillow")