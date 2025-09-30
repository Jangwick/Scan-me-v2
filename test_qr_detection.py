#!/usr/bin/env python3
"""
QR Code Image Detection Test
Tests the QRImageProcessingService with real QR code generation and detection
"""

import sys
import os
import qrcode
from io import BytesIO
from PIL import Image

# Add the app directory to the path
sys.path.insert(0, os.path.abspath('.'))

from app.services.qr_image_service import QRImageProcessingService

class MockFile:
    """Mock file object for testing"""
    def __init__(self, image_data, filename="test.png", content_type="image/png"):
        self.data = image_data
        self.filename = filename
        self.content_type = content_type
        self.position = 0
    
    def read(self):
        return self.data
    
    def seek(self, position, whence=0):
        if whence == 0:  # SEEK_SET
            self.position = position
        elif whence == 2:  # SEEK_END
            self.position = len(self.data)
        return self.position
    
    def tell(self):
        return self.position if hasattr(self, 'position') else len(self.data)

def create_test_qr_image(data: str) -> bytes:
    """Create a QR code image with the given data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def test_qr_detection():
    """Test QR code detection with various scenarios"""
    print("🧪 QR CODE IMAGE DETECTION TEST")
    print("=" * 50)
    
    # Test Case 1: Valid student QR code
    print("\n1. Testing valid student QR code (SCANME_ format)...")
    test_data_1 = "SCANME_d11a552c0e9f57f7be5c04a25146b27d"
    image_data_1 = create_test_qr_image(test_data_1)
    mock_file_1 = MockFile(image_data_1)
    
    result_1 = QRImageProcessingService.extract_qr_codes(mock_file_1)
    print(f"   Result: {'✅ SUCCESS' if result_1['success'] else '❌ FAILED'}")
    if result_1['success']:
        print(f"   Detected: {result_1['qr_codes'][0]}")
    else:
        print(f"   Error: {result_1['error']}")
    
    # Test Case 2: Valid student number format
    print("\n2. Testing student number format...")
    test_data_2 = "STU588"
    image_data_2 = create_test_qr_image(test_data_2)
    mock_file_2 = MockFile(image_data_2)
    
    result_2 = QRImageProcessingService.extract_qr_codes(mock_file_2)
    print(f"   Result: {'✅ SUCCESS' if result_2['success'] else '❌ FAILED'}")
    if result_2['success']:
        print(f"   Detected: {result_2['qr_codes'][0]}")
    else:
        print(f"   Error: {result_2['error']}")
    
    # Test Case 3: JSON format
    print("\n3. Testing JSON format...")
    test_data_3 = '{"student_id": 123, "student_no": "STU123", "name": "Test Student"}'
    image_data_3 = create_test_qr_image(test_data_3)
    mock_file_3 = MockFile(image_data_3)
    
    result_3 = QRImageProcessingService.extract_qr_codes(mock_file_3)
    print(f"   Result: {'✅ SUCCESS' if result_3['success'] else '❌ FAILED'}")
    if result_3['success']:
        print(f"   Detected: {result_3['qr_codes'][0][:50]}...")
    else:
        print(f"   Error: {result_3['error']}")
    
    # Test Case 4: Empty image (no QR code)
    print("\n4. Testing image without QR code...")
    # Create a plain white image
    plain_image = Image.new('RGB', (200, 200), 'white')
    img_byte_arr = BytesIO()
    plain_image.save(img_byte_arr, format='PNG')
    mock_file_4 = MockFile(img_byte_arr.getvalue())
    
    result_4 = QRImageProcessingService.extract_qr_codes(mock_file_4)
    print(f"   Result: {'✅ CORRECTLY FAILED' if not result_4['success'] else '❌ UNEXPECTED SUCCESS'}")
    print(f"   Message: {result_4['error']}")
    
    # Test Case 5: File validation tests
    print("\n5. Testing file validation...")
    
    # Empty file
    empty_file = MockFile(b"")
    validation_result = QRImageProcessingService.validate_image_file(empty_file)
    print(f"   Empty file: {'✅ CORRECTLY REJECTED' if not validation_result['valid'] else '❌ INCORRECTLY ACCEPTED'}")
    print(f"   Message: {validation_result['error']}")
    
    # Large file simulation
    large_data = b"x" * (6 * 1024 * 1024)  # 6MB
    large_file = MockFile(large_data)
    validation_result = QRImageProcessingService.validate_image_file(large_file)
    print(f"   Large file: {'✅ CORRECTLY REJECTED' if not validation_result['valid'] else '❌ INCORRECTLY ACCEPTED'}")
    print(f"   Message: {validation_result['error']}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    success_count = sum([
        result_1['success'],
        result_2['success'], 
        result_3['success'],
        not result_4['success'],  # Should fail
        not validation_result['valid']  # Should be invalid
    ])
    print(f"   Passed: {success_count}/5 tests")
    
    if success_count == 5:
        print("✅ All tests passed! QR detection is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the results above.")

if __name__ == "__main__":
    test_qr_detection()