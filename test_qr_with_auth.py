#!/usr/bin/env python3
"""
Login and Test QR Scanner
Authenticate first, then test QR scanning
"""

import requests
import json
import sys
import os

class QRTester:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def login(self, username="admin", password="admin123"):
        """Login to get authentication"""
        print(f"Logging in as {username}")
        
        login_url = f"{self.base_url}/auth/login"
        
        # Get login page first (for CSRF if needed)
        try:
            login_page = self.session.get(login_url)
            print(f"Login page accessible: {login_page.status_code}")
        except Exception as e:
            print(f"Cannot access login page: {e}")
            return False
        
        # Attempt login
        login_data = {
            'username': username,
            'password': password
        }
        
        try:
            response = self.session.post(login_url, data=login_data, allow_redirects=False)
            
            if response.status_code == 302:  # Redirect means success
                print("Login successful!")
                return True
            else:
                print(f"Login failed: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def test_qr_scan(self, qr_data, session_id=1):
        """Test QR scanning with authentication"""
        print(f"\nTesting QR scan: {qr_data[:50]}...")
        
        scan_url = f"{self.base_url}/scanner/api/scan-qr"
        
        test_data = {
            'qr_data': qr_data,
            'session_id': session_id,
            'scan_type': 'auto'
        }
        
        try:
            response = self.session.post(scan_url, json=test_data)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("Response:")
                    print(json.dumps(result, indent=2))
                    
                    if result.get('success'):
                        print("QR scan successful!")
                    else:
                        print(f"QR scan failed: {result.get('message')}")
                        
                except ValueError:
                    print(f"Non-JSON Response: {response.text[:300]}...")
            else:
                print(f"HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:300]}...")
                
        except Exception as e:
            print(f"Scan test error: {e}")
    
    def test_image_upload(self, image_path, session_id=1):
        """Test image upload with authentication"""
        print(f"\nTesting image upload: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return
        
        upload_url = f"{self.base_url}/scanner/api/scan-image"
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': (image_path, f, 'image/png')}
                data = {'session_id': session_id}
                
                response = self.session.post(upload_url, files=files, data=data)
                
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print("Response:")
                        print(json.dumps(result, indent=2))
                        
                        if result.get('success'):
                            print("Image upload and QR detection successful!")
                        else:
                            print(f"QR detection failed: {result.get('message')}")
                            
                    except ValueError:
                        print(f"Non-JSON Response: {response.text[:300]}...")
                else:
                    print(f"HTTP Error: {response.status_code}")
                    print(f"Response: {response.text[:300]}...")
                    
        except Exception as e:
            print(f"Upload test error: {e}")

def main():
    """Main testing function"""
    print("COMPREHENSIVE QR TESTING TOOL")
    print("=" * 50)
    
    tester = QRTester()
    
    # Step 1: Login
    if not tester.login():
        print("Cannot proceed without authentication")
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
    
    print("\n" + "=" * 50)
    print("TESTING COMPLETE")
    print("Check the results above for any errors")

if __name__ == "__main__":
    main()
