#!/usr/bin/env python3
"""
QR Code Generation Script for Students
Generates QR codes for all students and updates the database
"""

from app import create_app, db
from app.models import Student

def generate_all_qr_codes():
    """Generate QR codes for all students"""
    app = create_app()
    
    with app.app_context():
        try:
            students = Student.query.all()
            print(f"Found {len(students)} students")
            
            for student in students:
                print(f"Generating QR code for {student.get_full_name()} ({student.student_no})")
                
                # Generate QR code
                student.generate_qr_code()
                
                print(f"  QR path: {student.qr_code_path}")
                
            # Commit all changes
            db.session.commit()
            print("All QR codes generated successfully!")
            
            # Verify paths are saved
            print("\nVerifying saved paths:")
            for student in Student.query.all():
                print(f"  {student.student_no}: {student.qr_code_path}")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    generate_all_qr_codes()