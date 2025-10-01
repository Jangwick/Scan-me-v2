#!/usr/bin/env python3
"""
Debug Image Upload Endpoint
Test the scan-image endpoint specifically
"""

import requests
import json
import os

def test_image_upload_debug():
    """Test image upload with detailed debugging"""
    print("DEBUG: IMAGE UPLOAD ENDPOINT")
    print("=" * 50)
    
    # Create a session and login
    session = requests.Session()
    
    # Login first
    login_url = "http://127.0.0.1:5000/auth/login"
    login_data = {'username': 'admin', 'password': 'admin123'}
    
    login_response = session.post(login_url, data=login_data, allow_redirects=False)
    if login_response.status_code != 302:
        print("Login failed!")
        return
    
    print("✅ Login successful")
    
    # Test with different image files
    test_images = [
        "student_qr_1_John_Smith.png",
        "student_qr_2_Jane_Doe.png"
    ]
    
    for image_file in test_images:
        if not os.path.exists(image_file):
            print(f"❌ {image_file} not found")
            continue
            
        print(f"\n📤 Testing: {image_file}")
        
        upload_url = "http://127.0.0.1:5000/scanner/api/scan-image"
        
        try:
            with open(image_file, 'rb') as f:
                files = {'image': (image_file, f, 'image/png')}
                data = {'session_id': '1'}
                
                response = session.post(upload_url, files=files, data=data)
                
                print(f"📊 Status: {response.status_code}")
                print(f"📋 Headers: {dict(response.headers)}")
                
                # Try to parse as JSON
                try:
                    result = response.json()
                    print("📄 JSON Response:")
                    print(json.dumps(result, indent=2))
                except ValueError:
                    print("📄 Text Response:")
                    print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
                    
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🔍 IMAGE UPLOAD DEBUG TOOL")
    print("Testing the scan-image endpoint specifically")
    print()
    
    test_image_upload_debug()

if __name__ == "__main__":
    main()