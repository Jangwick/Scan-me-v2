#!/usr/bin/env python3
"""
Check for data type issues that might cause the modulo error
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
import traceback

def check_for_data_type_issues():
    """Check database for potential data type mismatches"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Checking for data type issues...")
            
            # Check for any malformed data that might cause issues
            
            # Check students table for any non-string names
            from app.models import Student
            students = Student.query.all()
            print(f"Checking {len(students)} students...")
            
            for student in students:
                try:
                    # Check if first_name and last_name are proper strings
                    if student.first_name is not None:
                        if not isinstance(student.first_name, str):
                            print(f"Student {student.id}: first_name is {type(student.first_name)}: {student.first_name}")
                        elif len(student.first_name) == 0:
                            print(f"Student {student.id}: first_name is empty string")
                            
                    if student.last_name is not None:
                        if not isinstance(student.last_name, str):
                            print(f"Student {student.id}: last_name is {type(student.last_name)}: {student.last_name}")
                        elif len(student.last_name) == 0:
                            print(f"Student {student.id}: last_name is empty string")
                            
                    # Test the first character access that happens in template
                    if student.first_name and student.last_name:
                        try:
                            first_char = student.first_name[0]
                            last_char = student.last_name[0]
                            print(f"Student {student.id}: {student.first_name} {student.last_name} -> {first_char}{last_char}")
                        except Exception as e:
                            print(f"Student {student.id}: ERROR accessing first character: {e}")
                            
                except Exception as e:
                    print(f"Student {student.id}: ERROR checking data: {e}")
                    traceback.print_exc()
            
            # Check attendance events
            from app.models import AttendanceEvent
            events = AttendanceEvent.query.limit(10).all()
            print(f"\nChecking {len(events)} attendance events...")
            
            for i, event in enumerate(events):
                print(f"Event {i}: ID={event.id}")
                print(f"  student_id: {event.student_id} (type: {type(event.student_id)})")
                print(f"  session_id: {event.session_id} (type: {type(event.session_id)})")
                
                # Test the loop index modulo operation that happens in template
                try:
                    index_result = i % 8
                    print(f"  Loop index {i} % 8 = {index_result}")
                except Exception as e:
                    print(f"  ERROR with modulo operation: {e}")
                    
                # Check if student exists and has proper data
                if event.student:
                    student = event.student
                    print(f"  Student: {student.first_name} {student.last_name}")
                else:
                    print(f"  No student linked to event {event.id}")
            
            # Check attendance sessions
            from app.models import AttendanceSession
            sessions = AttendanceSession.query.all()
            print(f"\nChecking {len(sessions)} attendance sessions...")
            
            for session in sessions:
                print(f"Session {session.id}: {session.subject}")
                print(f"  expected_students: {session.expected_students} (type: {type(session.expected_students)})")
                
                # Check if there are any string values where integers are expected
                if not isinstance(session.expected_students, int):
                    print(f"  WARNING: expected_students is not an integer!")
                    
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    check_for_data_type_issues()