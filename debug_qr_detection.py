#!/usr/bin/env python3
"""
QR Code Detection Debugging Tool
Comprehensive testing and debugging for QR code detection issues
"""

import sys
import os
import qrcode
from io import BytesIO
from PIL import Image
import json

# Add app to path
sys.path.insert(0, '.')

def create_test_qr_codes():
    """Create various test QR codes for debugging"""
    test_cases = [
        {
            'name': 'Simple Student Number',
            'data': 'STU001',
            'filename': 'test_qr_stu001.png'
        },
        {
            'name': 'SCANME Format',
            'data': 'SCANME_d11a552c0e9f57f7be5c04a25146b27d',
            'filename': 'test_qr_scanme.png'
        },
        {
            'name': 'JSON Format',
            'data': json.dumps({'student_id': 123, 'student_no': 'STU123', 'name': 'Test Student'}),
            'filename': 'test_qr_json.png'
        },
        {
            'name': 'Johnrick Student',
            'data': 'STU588',
            'filename': 'test_qr_johnrick.png'
        }
    ]
    
    print("🔧 Creating Test QR Codes")
    print("=" * 40)
    
    created_files = []
    
    for test in test_cases:
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(test['data'])
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(test['filename'])
            
            print(f"✅ Created: {test['filename']} ({test['name']})")
            created_files.append({
                'file': test['filename'],
                'data': test['data'],
                'name': test['name']
            })
            
        except Exception as e:
            print(f"❌ Failed to create {test['filename']}: {e}")
    
    return created_files

def test_detection_methods():
    """Test different QR detection methods"""
    print("\n🧪 Testing QR Detection Methods")
    print("=" * 40)
    
    # Test library availability
    try:
        import cv2
        print("✅ OpenCV (cv2) available")
        cv2_available = True
    except ImportError:
        print("❌ OpenCV (cv2) not available")
        cv2_available = False
    
    try:
        from pyzbar import pyzbar
        print("✅ pyzbar available")
        pyzbar_available = True
    except ImportError:
        print("❌ pyzbar not available")
        pyzbar_available = False
    
    try:
        from PIL import Image
        print("✅ PIL/Pillow available")
    except ImportError:
        print("❌ PIL/Pillow not available")
        return False
    
    return cv2_available and pyzbar_available

def test_qr_service():
    """Test the QR image processing service"""
    print("\n🔍 Testing QR Image Processing Service")
    print("=" * 40)
    
    try:
        from app.services.qr_image_service import QRImageProcessingService
        print("✅ QR service imported successfully")
        
        # Check library flags
        try:
            import cv2
            print("✅ OpenCV available in service context")
        except ImportError:
            print("❌ OpenCV not available in service context")
        
        try:
            from pyzbar import pyzbar
            print("✅ pyzbar available in service context")
        except ImportError:
            print("❌ pyzbar not available in service context")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import QR service: {e}")
        return False

def test_qr_detection_on_files(created_files):
    """Test QR detection on created files"""
    print("\n🎯 Testing QR Detection on Test Files")
    print("=" * 40)
    
    try:
        from app.services.qr_image_service import QRImageProcessingService
        
        class MockFile:
            def __init__(self, file_path):
                with open(file_path, 'rb') as f:
                    self.data = f.read()
                self.filename = file_path
                self.content_type = "image/png"
            
            def read(self):
                return self.data
            
            def seek(self, pos, whence=0):
                if whence == 2:
                    return len(self.data)
                return pos
            
            def tell(self):
                return len(self.data)
        
        success_count = 0
        
        for test_file in created_files:
            print(f"\n📄 Testing: {test_file['name']}")
            print(f"   File: {test_file['file']}")
            print(f"   Expected: {test_file['data']}")
            
            try:
                mock_file = MockFile(test_file['file'])
                
                # Test validation
                validation = QRImageProcessingService.validate_image_file(mock_file)
                if not validation['valid']:
                    print(f"   ❌ Validation failed: {validation['error']}")
                    continue
                
                print("   ✅ File validation passed")
                
                # Test extraction
                result = QRImageProcessingService.extract_qr_codes(mock_file)
                
                if result['success']:
                    detected_data = result['qr_codes'][0]
                    print(f"   ✅ Detection successful!")
                    print(f"   📊 Detected: {detected_data}")
                    print(f"   🎯 Match: {'✅' if detected_data == test_file['data'] else '❌'}")
                    
                    if detected_data == test_file['data']:
                        success_count += 1
                else:
                    print(f"   ❌ Detection failed: {result['error']}")
                    if 'details' in result:
                        print(f"   📋 Details: {result['details']}")
                
            except Exception as e:
                print(f"   💥 Exception: {e}")
        
        print(f"\n📊 Success Rate: {success_count}/{len(created_files)} ({success_count/len(created_files)*100:.1f}%)")
        return success_count == len(created_files)
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

def test_manual_detection():
    """Test manual QR detection methods"""
    print("\n🔬 Testing Manual Detection Methods")
    print("=" * 40)
    
    try:
        from pyzbar import pyzbar
        from PIL import Image
        
        # Test direct detection on a test file
        test_file = 'test_qr_stu001.png'
        if os.path.exists(test_file):
            print(f"📄 Testing direct detection on {test_file}")
            
            # Method 1: PIL + pyzbar direct
            try:
                image = Image.open(test_file)
                detected = pyzbar.decode(image)
                if detected:
                    data = detected[0].data.decode('utf-8')
                    print(f"   ✅ PIL+pyzbar direct: {data}")
                else:
                    print("   ❌ PIL+pyzbar direct: No QR found")
            except Exception as e:
                print(f"   ❌ PIL+pyzbar direct failed: {e}")
            
            # Method 2: OpenCV if available
            try:
                import cv2
                import numpy as np
                
                image = Image.open(test_file)
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                detected = pyzbar.decode(opencv_image)
                if detected:
                    data = detected[0].data.decode('utf-8')
                    print(f"   ✅ OpenCV+pyzbar: {data}")
                else:
                    print("   ❌ OpenCV+pyzbar: No QR found")
            except Exception as e:
                print(f"   ❌ OpenCV+pyzbar failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual detection test failed: {e}")
        return False

def cleanup_test_files(created_files):
    """Clean up test files"""
    print("\n🧹 Cleaning up test files")
    print("=" * 40)
    
    for test_file in created_files:
        try:
            if os.path.exists(test_file['file']):
                os.remove(test_file['file'])
                print(f"✅ Removed: {test_file['file']}")
        except Exception as e:
            print(f"❌ Failed to remove {test_file['file']}: {e}")

def main():
    """Main debugging function"""
    print("🔍 QR CODE DETECTION DEBUGGING TOOL")
    print("="*50)
    print("This tool will help diagnose QR code detection issues")
    print()
    
    # Step 1: Create test QR codes
    created_files = create_test_qr_codes()
    
    # Step 2: Test detection methods
    libraries_ok = test_detection_methods()
    
    # Step 3: Test QR service
    service_ok = test_qr_service()
    
    # Step 4: Test detection on files
    detection_ok = False
    if created_files and libraries_ok and service_ok:
        detection_ok = test_qr_detection_on_files(created_files)
    
    # Step 5: Manual detection test
    manual_ok = test_manual_detection()
    
    # Summary
    print("\n" + "="*50)
    print("🎯 DEBUGGING SUMMARY")
    print("="*50)
    print(f"Libraries Available: {'✅' if libraries_ok else '❌'}")
    print(f"QR Service Working: {'✅' if service_ok else '❌'}")
    print(f"Detection Working: {'✅' if detection_ok else '❌'}")
    print(f"Manual Methods: {'✅' if manual_ok else '❌'}")
    
    if not libraries_ok:
        print("\n💡 SOLUTION: Install missing libraries:")
        print("   pip install opencv-python pyzbar")
    
    if not service_ok:
        print("\n💡 SOLUTION: Check QR service imports and dependencies")
    
    if not detection_ok:
        print("\n💡 SOLUTION: QR detection needs debugging")
        print("   - Check image quality")
        print("   - Verify QR code format")
        print("   - Test with different detection methods")
    
    # Cleanup
    if created_files:
        cleanup_test_files(created_files)
    
    print(f"\n🏁 Debugging complete!")

if __name__ == "__main__":
    main()