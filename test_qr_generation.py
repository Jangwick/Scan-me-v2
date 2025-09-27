"""
Test QR Code Generation for ScanMe System
This script tests the QR code generation functionality for all user types
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.qr_utils import generate_user_qr_code, create_qr_data
import json

def test_student_qr():
    """Test QR code generation for student"""
    print("=== Testing Student QR Code ===")
    
    student_data = {
        'id': 1,
        'student_no': 'ST001',
        'name': 'John Doe',
        'department': 'Computer Science',
        'section': 'CS-A',
        'year_level': 3
    }
    
    # Test QR data creation
    qr_data = create_qr_data(student_data, 'student')
    print(f"Student QR Data: {qr_data}")
    
    # Parse and display
    parsed_data = json.loads(qr_data)
    print("Parsed Student QR Code contains:")
    for key, value in parsed_data.items():
        print(f"  {key}: {value}")
    
    # Test QR code generation
    qr_base64 = generate_user_qr_code(student_data, 'student')
    print(f"QR Code generated successfully: {'Yes' if qr_base64 else 'No'}")
    
    if qr_base64:
        print(f"QR Code length: {len(qr_base64)} characters")
    print()

def test_professor_qr():
    """Test QR code generation for professor"""
    print("=== Testing Professor QR Code ===")
    
    professor_data = {
        'id': 10,
        'username': 'prof_smith',
        'email': 'smith@university.edu',
        'role': 'professor',
        'display_name': 'Prof. Smith'
    }
    
    # Test QR data creation
    qr_data = create_qr_data(professor_data, 'professor')
    print(f"Professor QR Data: {qr_data}")
    
    # Parse and display
    parsed_data = json.loads(qr_data)
    print("Parsed Professor QR Code contains:")
    for key, value in parsed_data.items():
        print(f"  {key}: {value}")
    
    # Test QR code generation
    qr_base64 = generate_user_qr_code(professor_data, 'professor')
    print(f"QR Code generated successfully: {'Yes' if qr_base64 else 'No'}")
    
    if qr_base64:
        print(f"QR Code length: {len(qr_base64)} characters")
    print()

def test_admin_qr():
    """Test QR code generation for admin"""
    print("=== Testing Admin QR Code ===")
    
    admin_data = {
        'id': 100,
        'username': 'admin',
        'email': 'admin@university.edu',
        'role': 'admin',
        'display_name': 'Administrator'
    }
    
    # Test QR data creation
    qr_data = create_qr_data(admin_data, 'admin')
    print(f"Admin QR Data: {qr_data}")
    
    # Parse and display
    parsed_data = json.loads(qr_data)
    print("Parsed Admin QR Code contains:")
    for key, value in parsed_data.items():
        print(f"  {key}: {value}")
    
    # Test QR code generation
    qr_base64 = generate_user_qr_code(admin_data, 'admin')
    print(f"QR Code generated successfully: {'Yes' if qr_base64 else 'No'}")
    
    if qr_base64:
        print(f"QR Code length: {len(qr_base64)} characters")
    print()

def test_qr_bytes():
    """Test QR code generation as bytes for download"""
    print("=== Testing QR Code Bytes Generation ===")
    
    test_data = {
        'id': 1,
        'username': 'test_user',
        'email': 'test@example.com',
        'role': 'student',
        'display_name': 'Test User'
    }
    
    qr_bytes = generate_user_qr_code(test_data, 'student', return_bytes=True)
    print(f"QR Bytes generated successfully: {'Yes' if qr_bytes else 'No'}")
    
    if qr_bytes:
        print(f"QR Bytes length: {len(qr_bytes)} bytes")
    print()

if __name__ == "__main__":
    print("QR Code Generation Test Suite")
    print("=" * 50)
    
    try:
        test_student_qr()
        test_professor_qr()
        test_admin_qr()
        test_qr_bytes()
        
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()