#!/usr/bin/env python3
"""
Test script to test professor session detail specifically
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, AttendanceSession, AttendanceEvent, AttendanceRecord, Student
import traceback

def test_session_detail_data():
    """Test the data used in session detail template"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing session detail data...")
            
            # Get a session
            session = AttendanceSession.query.first()
            if not session:
                print("No sessions found!")
                return
                
            print(f"Testing session {session.id}: {session.subject}")
            
            # Get recent events (what's used in the template)
            recent_events = AttendanceEvent.query.filter_by(
                session_id=session.id
            ).order_by(AttendanceEvent.event_time.desc()).limit(20).all()
            
            print(f"Found {len(recent_events)} recent events")
            
            for i, event in enumerate(recent_events):
                print(f"Event {i}: {event.id}")
                print(f"  Student: {event.student_id}")
                print(f"  Type: {event.event_type}")
                try:
                    # Test template expression that might be causing the issue
                    index_value = i % 8  # This simulates loop.index0 % 8
                    print(f"  Index value: {index_value} (type: {type(index_value)})")
                    
                    # Try to call the avatar_color filter manually
                    from app import app
                    with app.app_context():
                        filter_func = app.jinja_env.filters.get('avatar_color')
                        if filter_func:
                            color = filter_func(index_value)
                            print(f"  Color: {color}")
                        else:
                            print("  No avatar_color filter found!")
                            
                    # Test student name access
                    student = event.student
                    if student:
                        print(f"  Student name: {student.first_name} {student.last_name}")
                        first_initial = student.first_name[0] if student.first_name else 'X'
                        last_initial = student.last_name[0] if student.last_name else 'X'
                        print(f"  Initials: {first_initial}{last_initial}")
                    else:
                        print("  No student found!")
                        
                except Exception as e:
                    print(f"  ERROR: {e}")
                    traceback.print_exc()
                    
            # Test active students data
            active_students = db.session.query(AttendanceRecord, Student).join(Student).filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.is_active == True
            ).all()
            
            print(f"\nFound {len(active_students)} active students")
            
            for i, (record, student) in enumerate(active_students):
                print(f"Active student {i}: {student.id}")
                try:
                    index_value = i % 8
                    print(f"  Index value: {index_value} (type: {type(index_value)})")
                    
                    # Test student name access
                    first_initial = student.first_name[0] if student.first_name else 'X'
                    last_initial = student.last_name[0] if student.last_name else 'X'
                    print(f"  Initials: {first_initial}{last_initial}")
                    
                except Exception as e:
                    print(f"  ERROR: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_session_detail_data()