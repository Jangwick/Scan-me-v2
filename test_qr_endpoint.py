#!/usr/bin/env python3
"""
Test QR Upload Endpoint
Tests the actual Flask endpoint with a real QR code
"""

import requests
import sys
import os

def test_qr_upload():
    """Test the QR upload endpoint"""
    print("🔍 TESTING QR UPLOAD ENDPOINT")
    print("=" * 50)
    
    # Test with the first QR code we created
    qr_file = "student_qr_1_John_Smith.png"
    
    if not os.path.exists(qr_file):
        print(f"❌ Test file {qr_file} not found")
        print("Run create_test_qr_codes.py first to create test files")
        return
    
    # Test endpoint
    url = "http://127.0.0.1:5000/scanner/api/scan-image"
    
    try:
        # Check if server is running
        response = requests.get("http://127.0.0.1:5000", timeout=5)
        print("✅ Flask server is running")
    except requests.exceptions.RequestException:
        print("❌ Flask server is not running")
        print("Start the server with: python app.py")
        return
    
    # Test the upload
    print(f"\n📤 Testing upload with {qr_file}")
    
    try:
        with open(qr_file, 'rb') as f:
            files = {'image': (qr_file, f, 'image/png')}
            data = {'session_id': '1'}  # Assuming session 1 exists
            
            response = requests.post(url, files=files, data=data, timeout=10)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            
            try:
                result = response.json()
                print(f"📄 Response JSON:")
                import json
                print(json.dumps(result, indent=2))
                
                if result.get('success'):
                    print("✅ QR upload and detection successful!")
                else:
                    print(f"❌ QR upload failed: {result.get('message', 'Unknown error')}")
                    if 'details' in result:
                        print(f"📋 Details: {result['details']}")
                        
            except ValueError:
                print(f"📄 Response Text: {response.text}")
                
    except Exception as e:
        print(f"❌ Upload test failed: {e}")

def test_manual_qr_input():
    """Test manual QR input"""
    print("\n🖊️ TESTING MANUAL QR INPUT")
    print("=" * 50)
    
    url = "http://127.0.0.1:5000/scanner/api/scan"
    
    # Test data from our generated QR codes
    test_data = "SCANME_d11a552c0e9f57f7be5c04a25146b27d"  # John Smith's QR
    
    try:
        data = {
            'qr_data': test_data,
            'session_id': '1',
            'scan_type': 'auto'
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        
        try:
            result = response.json()
            print(f"📄 Response JSON:")
            import json
            print(json.dumps(result, indent=2))
            
            if result.get('success'):
                print("✅ Manual QR input successful!")
            else:
                print(f"❌ Manual QR input failed: {result.get('message', 'Unknown error')}")
                
        except ValueError:
            print(f"📄 Response Text: {response.text}")
            
    except Exception as e:
        print(f"❌ Manual input test failed: {e}")

def main():
    """Main testing function"""
    print("🧪 QR ENDPOINT TESTING TOOL")
    print("=" * 50)
    print("Testing actual Flask endpoints with real QR codes")
    print()
    
    # Test image upload
    test_qr_upload()
    
    # Test manual input
    test_manual_qr_input()
    
    print("\n" + "=" * 50)
    print("🎯 TESTING COMPLETE")
    print("If QR detection is failing, check:")
    print("1. Session ID exists (try session_id=1)")
    print("2. User is logged in")
    print("3. Flask server logs for errors")

if __name__ == "__main__":
    main()