#!/usr/bin/env python3
"""
Simple QR Code Test
"""
import qrcode
from io import BytesIO
import sys
import os

# Add app to path
sys.path.insert(0, '.')

try:
    from app.services.qr_image_service import QRImageProcessingService
    print("✅ QR service imported successfully")
except Exception as e:
    print(f"❌ Failed to import QR service: {e}")
    exit(1)

class MockFile:
    def __init__(self, data, filename="test.png"):
        self.data = data
        self.filename = filename
        self.content_type = "image/png"
        self._position = 0
    
    def read(self):
        return self.data
    
    def seek(self, pos, whence=0):
        if whence == 2:  # SEEK_END
            self._position = len(self.data)
        else:
            self._position = pos
        return self._position
    
    def tell(self):
        return self._position

def test_basic_qr():
    print("\n🧪 Basic QR Code Test")
    print("-" * 30)
    
    # Create a simple QR code
    test_data = "STU001"
    print(f"Creating QR code with data: {test_data}")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(test_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    
    # Test file validation
    mock_file = MockFile(img_bytes.getvalue())
    
    print("Testing file validation...")
    validation = QRImageProcessingService.validate_image_file(mock_file)
    print(f"Validation: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
    if not validation['valid']:
        print(f"Error: {validation['error']}")
        return
    
    print("Testing QR extraction...")
    # Reset file position
    mock_file._position = 0
    result = QRImageProcessingService.extract_qr_codes(mock_file)
    
    if result['success']:
        print(f"✅ SUCCESS: Detected QR code: {result['qr_codes'][0]}")
        return True
    else:
        print(f"❌ FAILED: {result['error']}")
        print(f"Details: {result.get('details', {})}")
        return False

if __name__ == "__main__":
    print("🔍 QR Detection Test")
    print("=" * 40)
    success = test_basic_qr()
    print("\n" + "=" * 40)
    if success:
        print("🎉 QR detection is working!")
    else:
        print("⚠️  QR detection needs attention")