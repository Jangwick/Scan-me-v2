#!/usr/bin/env python3
"""
Complete QR Testing Guide
Step-by-step testing for QR detection issues
"""

import os
import json
from datetime import datetime

def create_test_session():
    """Create test data for QR scanning"""
    print("🔧 CREATING TEST SESSION DATA")
    print("=" * 50)
    
    test_session = {
        "id": 1,
        "session_name": "Test Session",
        "room_name": "Lab A",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_active": True
    }
    
    print("Test session data:")
    print(json.dumps(test_session, indent=2))
    print()
    
    return test_session

def test_manual_qr_data():
    """Test different QR data formats"""
    print("🧪 TESTING QR DATA FORMATS")
    print("=" * 50)
    
    test_qr_codes = [
        {
            "name": "Simple Student ID", 
            "data": "STU001",
            "description": "Basic student number format"
        },
        {
            "name": "SCANME Format", 
            "data": "SCANME_d11a552c0e9f57f7be5c04a25146b27d",
            "description": "Hash-based student identifier"
        },
        {
            "name": "JSON Format", 
            "data": '{"student_id": "STU001", "name": "John Smith"}',
            "description": "JSON with student details"
        },
        {
            "name": "Email Format", 
            "data": "johnsmith@university.edu",
            "description": "Student email address"
        },
        {
            "name": "Numeric ID", 
            "data": "123456",
            "description": "Numeric student ID"
        }
    ]
    
    for i, qr in enumerate(test_qr_codes, 1):
        print(f"{i}. {qr['name']}")
        print(f"   Data: {qr['data']}")
        print(f"   Description: {qr['description']}")
        print()
    
    return test_qr_codes

def create_login_script():
    """Create a script to login and test QR scanning"""
    print("🔐 CREATING LOGIN AND TEST SCRIPT")
    print("=" * 50)
    
    script_content = '''#!/usr/bin/env python3
"""
Login and Test QR Scanner
Authenticate first, then test QR scanning
"""

import requests
import json
import sys

class QRTester:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def login(self, username="admin", password="admin123"):
        """Login to get authentication"""
        print(f"🔐 Logging in as {username}")
        
        login_url = f"{self.base_url}/auth/login"
        
        # Get login page first (for CSRF if needed)
        try:
            login_page = self.session.get(login_url)
            print(f"✅ Login page accessible: {login_page.status_code}")
        except Exception as e:
            print(f"❌ Cannot access login page: {e}")
            return False
        
        # Attempt login
        login_data = {
            'username': username,
            'password': password
        }
        
        try:
            response = self.session.post(login_url, data=login_data, allow_redirects=False)
            
            if response.status_code == 302:  # Redirect means success
                print("✅ Login successful!")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_qr_scan(self, qr_data, session_id=1):
        """Test QR scanning with authentication"""
        print(f"\\n🔍 Testing QR scan: {qr_data[:50]}...")
        
        scan_url = f"{self.base_url}/scanner/api/scan-qr"
        
        test_data = {
            'qr_data': qr_data,
            'session_id': session_id,
            'scan_type': 'auto'
        }
        
        try:
            response = self.session.post(scan_url, json=test_data)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("📄 Response:")
                    print(json.dumps(result, indent=2))
                    
                    if result.get('success'):
                        print("✅ QR scan successful!")
                    else:
                        print(f"❌ QR scan failed: {result.get('message')}")
                        
                except ValueError:
                    print(f"📄 Non-JSON Response: {response.text[:300]}...")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:300]}...")
                
        except Exception as e:
            print(f"❌ Scan test error: {e}")
    
    def test_image_upload(self, image_path, session_id=1):
        """Test image upload with authentication"""
        print(f"\\n📤 Testing image upload: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return
        
        upload_url = f"{self.base_url}/scanner/api/scan-image"
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': (image_path, f, 'image/png')}
                data = {'session_id': session_id}
                
                response = self.session.post(upload_url, files=files, data=data)
                
                print(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print("📄 Response:")
                        print(json.dumps(result, indent=2))
                        
                        if result.get('success'):
                            print("✅ Image upload and QR detection successful!")
                        else:
                            print(f"❌ QR detection failed: {result.get('message')}")
                            
                    except ValueError:
                        print(f"📄 Non-JSON Response: {response.text[:300]}...")
                else:
                    print(f"❌ HTTP Error: {response.status_code}")
                    print(f"Response: {response.text[:300]}...")
                    
        except Exception as e:
            print(f"❌ Upload test error: {e}")

def main():
    """Main testing function"""
    print("🧪 COMPREHENSIVE QR TESTING TOOL")
    print("=" * 50)
    
    tester = QRTester()
    
    # Step 1: Login
    if not tester.login():
        print("❌ Cannot proceed without authentication")
        return
    
    # Step 2: Test manual QR data
    test_qr_codes = [
        "STU001",
        "SCANME_d11a552c0e9f57f7be5c04a25146b27d",
        '{"student_id": "STU001", "name": "John Smith"}',
        "johnsmith@university.edu"
    ]
    
    for qr_data in test_qr_codes:
        tester.test_qr_scan(qr_data)
    
    # Step 3: Test image uploads
    image_files = [
        "student_qr_1_John_Smith.png",
        "student_qr_2_Jane_Doe.png",
        "student_qr_3_Bob_Johnson.png"
    ]
    
    for image_file in image_files:
        if os.path.exists(image_file):
            tester.test_image_upload(image_file)
    
    print("\\n" + "=" * 50)
    print("🎯 TESTING COMPLETE")
    print("Check the results above for any errors")

if __name__ == "__main__":
    main()
'''
    
    with open("test_qr_with_auth.py", "w") as f:
        f.write(script_content)
    
    print("✅ Created test_qr_with_auth.py")
    print("Run this script to test QR scanning with proper authentication")
    print()

def check_image_files():
    """Check if test QR image files exist"""
    print("📁 CHECKING TEST IMAGE FILES")
    print("=" * 50)
    
    expected_files = [
        "student_qr_1_John_Smith.png",
        "student_qr_2_Jane_Doe.png", 
        "student_qr_3_Bob_Johnson.png",
        "student_qr_4_Alice_Williams.png",
        "student_qr_5_Michael_Davis.png"
    ]
    
    existing_files = []
    missing_files = []
    
    for file in expected_files:
        if os.path.exists(file):
            existing_files.append(file)
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")
    
    print(f"\\nSummary: {len(existing_files)} found, {len(missing_files)} missing")
    
    if missing_files:
        print("\\n🔧 To create missing files, run:")
        print("python create_test_qr_codes.py")
    
    return existing_files

def print_troubleshooting_steps():
    """Print step-by-step troubleshooting guide"""
    print("🛠️ TROUBLESHOOTING STEPS")
    print("=" * 50)
    
    steps = [
        "1. **Login Required**: QR scanning requires authentication",
        "   - Login at: http://127.0.0.1:5000/auth/login",
        "   - Use admin/admin123 or create an account",
        "",
        "2. **Test with Generated QR Codes**: Use high-quality test images",
        "   - Run: python create_test_qr_codes.py",
        "   - Test with: student_qr_1_John_Smith.png",
        "",
        "3. **Check Server Status**: Ensure Flask is running",
        "   - Visit: http://127.0.0.1:5000",
        "   - Run: python app.py",
        "",
        "4. **Test Manual QR Data**: Try different QR formats",
        "   - STU001 (simple)",
        "   - SCANME_d11a552c0e9f57f7be5c04a25146b27d (hash)",
        "   - JSON format",
        "",
        "5. **Check Image Quality**: QR detection requirements",
        "   - Good contrast (dark QR on light background)",
        "   - Adequate resolution (at least 200x200 pixels)",
        "   - No blur or distortion",
        "   - Supported formats: PNG, JPG, JPEG",
        "",
        "6. **Test with Authentication**: Use the test script",
        "   - Run: python test_qr_with_auth.py",
        "   - This handles login automatically",
        "",
        "7. **Check Browser Console**: For JavaScript errors",
        "   - Open Developer Tools (F12)",
        "   - Check Console tab for errors",
        "   - Check Network tab for failed requests",
        "",
        "8. **Verify Session Data**: Ensure test session exists",
        "   - Visit: http://127.0.0.1:5000/attendance/sessions",
        "   - Create a test session if needed"
    ]
    
    for step in steps:
        print(step)
    
    print()

def main():
    """Main function"""
    print("📋 COMPLETE QR TESTING GUIDE")
    print("=" * 60)
    print("Step-by-step guide to test and debug QR detection issues")
    print()
    
    # Create test session data
    create_test_session()
    
    # Show QR data formats
    test_manual_qr_data()
    
    # Create login script
    create_login_script()
    
    # Check image files
    check_image_files()
    
    # Print troubleshooting steps
    print_troubleshooting_steps()
    
    print("🎯 NEXT STEPS:")
    print("1. Run: python test_qr_with_auth.py")
    print("2. If that works, the issue is with your original image")
    print("3. If that fails, check server logs and authentication")
    print()
    print("📞 If you still get 'No QR code found', the issue is likely:")
    print("   - Image quality/format")
    print("   - Missing authentication")
    print("   - Wrong QR code format")

if __name__ == "__main__":
    main()