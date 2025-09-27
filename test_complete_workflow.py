"""
Complete Time-In/Time-Out Workflow Test

This script tests the complete attendance workflow:
1. Student time-in when entering classroom
2. Student time-out when leaving classroom
3. Duration calculation
4. Status tracking
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_STUDENT_ID = "12345"
TEST_ROOM_ID = 1

def test_login():
    """Test login functionality"""
    print("🔐 Testing login...")
    
    login_data = {
        'email': 'teacher@example.com',
        'password': 'password'
    }
    
    session = requests.Session()
    response = session.post(f"{BASE_URL}/auth/login", data=login_data)
    
    if response.status_code == 200 and "dashboard" in response.url:
        print("✅ Login successful")
        return session
    else:
        print("❌ Login failed")
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        return None

def test_scanner_page(session):
    """Test scanner page access"""
    print("\n📱 Testing scanner page access...")
    
    response = session.get(f"{BASE_URL}/scanner/")
    
    if response.status_code == 200:
        print("✅ Scanner page accessible")
        return True
    else:
        print("❌ Scanner page not accessible")
        print(f"Status: {response.status_code}")
        return False

def test_time_in(session):
    """Test student time-in functionality"""
    print(f"\n⏰ Testing time-in for student {TEST_STUDENT_ID}...")
    
    scan_data = {
        'qr_data': TEST_STUDENT_ID,
        'scan_type': 'time_in'
    }
    
    response = session.post(f"{BASE_URL}/scanner/scan", 
                           data=scan_data,
                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"✅ Time-in response: {result}")
            
            if result.get('success'):
                print(f"✅ {result.get('student_name')} successfully timed in")
                print(f"   Action: {result.get('action')}")
                print(f"   Time: {result.get('time_in')}")
                if result.get('is_late'):
                    print("   ⚠️ Student was late")
                return True
            else:
                print(f"❌ Time-in failed: {result.get('message')}")
                return False
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            print(f"Response text: {response.text[:200]}")
            return False
    else:
        print(f"❌ Time-in request failed with status {response.status_code}")
        return False

def test_duplicate_time_in(session):
    """Test duplicate time-in detection"""
    print(f"\n🔄 Testing duplicate time-in detection...")
    
    scan_data = {
        'qr_data': TEST_STUDENT_ID,
        'scan_type': 'time_in'
    }
    
    response = session.post(f"{BASE_URL}/scanner/scan", 
                           data=scan_data,
                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"✅ Duplicate check response: {result}")
            
            if not result.get('success') and 'already timed in' in result.get('message', ''):
                print("✅ Duplicate time-in correctly detected and prevented")
                return True
            else:
                print(f"❌ Duplicate detection failed: {result}")
                return False
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Duplicate check request failed")
        return False

def test_time_out(session):
    """Test student time-out functionality"""
    print(f"\n🚪 Testing time-out for student {TEST_STUDENT_ID}...")
    
    scan_data = {
        'qr_data': TEST_STUDENT_ID,
        'scan_type': 'time_out'
    }
    
    response = session.post(f"{BASE_URL}/scanner/scan", 
                           data=scan_data,
                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"✅ Time-out response: {result}")
            
            if result.get('success'):
                print(f"✅ {result.get('student_name')} successfully timed out")
                print(f"   Action: {result.get('action')}")
                print(f"   Time-in: {result.get('time_in')}")
                print(f"   Time-out: {result.get('time_out')}")
                print(f"   Duration: {result.get('duration_minutes')} minutes")
                return True
            else:
                print(f"❌ Time-out failed: {result.get('message')}")
                return False
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Time-out request failed")
        return False

def test_auto_detection(session):
    """Test auto-detection functionality"""
    print(f"\n🤖 Testing auto-detection for new time-in...")
    
    # Use a different student ID for auto-detection test
    auto_test_student = "67890"
    
    scan_data = {
        'qr_data': auto_test_student,
        'scan_type': 'auto'
    }
    
    response = session.post(f"{BASE_URL}/scanner/scan", 
                           data=scan_data,
                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"✅ Auto-detection response: {result}")
            
            if result.get('success') and result.get('action') == 'time_in':
                print(f"✅ Auto-detection correctly identified need for time-in")
                
                # Now test auto-detection for time-out
                print(f"\n🤖 Testing auto-detection for time-out...")
                
                response2 = session.post(f"{BASE_URL}/scanner/scan", 
                                       data=scan_data,
                                       headers={'Content-Type': 'application/x-www-form-urlencoded'})
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    print(f"✅ Auto-detection time-out response: {result2}")
                    
                    if result2.get('success') and result2.get('action') == 'time_out':
                        print(f"✅ Auto-detection correctly identified need for time-out")
                        return True
                    else:
                        print(f"❌ Auto-detection time-out failed: {result2}")
                        return False
                else:
                    print("❌ Auto-detection time-out request failed")
                    return False
            else:
                print(f"❌ Auto-detection time-in failed: {result}")
                return False
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print("❌ Auto-detection request failed")
        return False

def main():
    print("🧪 Starting Complete Time-In/Time-Out Workflow Test")
    print("=" * 60)
    
    # Login first
    session = test_login()
    if not session:
        print("❌ Cannot continue without login")
        return
    
    # Test scanner page
    if not test_scanner_page(session):
        print("❌ Cannot continue without scanner access")
        return
    
    # Test complete workflow
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Time-in
    if test_time_in(session):
        tests_passed += 1
    
    # Test 2: Duplicate time-in detection
    if test_duplicate_time_in(session):
        tests_passed += 1
    
    # Test 3: Time-out
    if test_time_out(session):
        tests_passed += 1
    
    # Test 4: Auto-detection workflow
    if test_auto_detection(session):
        tests_passed += 1
    
    # Test 5: Edge case - time-out when not timed in
    print(f"\n🚫 Testing time-out when not timed in...")
    scan_data = {
        'qr_data': '99999',  # Different student
        'scan_type': 'time_out'
    }
    
    response = session.post(f"{BASE_URL}/scanner/scan", 
                           data=scan_data,
                           headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            if not result.get('success') and 'not currently timed in' in result.get('message', ''):
                print("✅ Correctly prevented time-out when student not timed in")
                tests_passed += 1
            else:
                print(f"❌ Should have prevented time-out: {result}")
        except:
            print("❌ Invalid response")
    else:
        print("❌ Request failed")
    
    print("\n" + "=" * 60)
    print(f"🎯 TEST RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Time-in/Time-out system is working correctly!")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()