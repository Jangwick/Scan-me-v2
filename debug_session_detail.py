#!/usr/bin/env python3
"""
Test script to debug the session detail error specifically
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, AttendanceSession, AttendanceEvent, AttendanceRecord, Student
from flask import render_template
import traceback

def test_session_detail_with_real_data():
    """Test the session detail route with actual data to find the modulo error"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing session detail rendering with real data...")
            
            # Get a session that exists
            session = AttendanceSession.query.first()
            if not session:
                print("No sessions found!")
                return
                
            print(f"Testing session {session.id}: {session.subject}")
            
            # Get the data exactly as the route does
            attendance_summary = session.get_attendance_summary()
            print(f"Attendance summary: {attendance_summary}")
            
            # Get recent events
            recent_events = AttendanceEvent.query.filter_by(
                session_id=session.id
            ).order_by(AttendanceEvent.event_time.desc()).limit(20).all()
            
            print(f"Found {len(recent_events)} recent events")
            
            # Check each event for potential issues
            for i, event in enumerate(recent_events):
                print(f"Event {i}: {event.id}")
                print(f"  Student ID: {event.student_id}")
                print(f"  Student: {event.student}")
                
                if event.student:
                    try:
                        first_name = event.student.first_name
                        last_name = event.student.last_name
                        print(f"  Student name: {first_name} {last_name}")
                        
                        if first_name and last_name:
                            initials = f"{first_name[0]}{last_name[0]}"
                            print(f"  Initials: {initials}")
                        else:
                            print(f"  Name issue: first='{first_name}', last='{last_name}'")
                            
                    except Exception as e:
                        print(f"  ERROR with student data: {e}")
                        traceback.print_exc()
            
            # Get active students
            active_students = db.session.query(AttendanceRecord, Student).join(Student).filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.is_active == True
            ).all()
            
            print(f"Found {len(active_students)} active students")
            
            # Test template rendering with the exact data
            with app.test_request_context(f'/professor/session/{session.id}'):
                # Mock current_user for template
                from flask_login import AnonymousUserMixin
                
                class MockUser:
                    def __init__(self):
                        self.is_authenticated = True
                        self.username = "test"
                        
                    def can_scan_attendance(self):
                        return True
                        
                    def can_manage_students(self):
                        return True
                        
                    def can_view_reports(self):
                        return True
                        
                    def is_professor(self):
                        return True
                        
                    def is_admin(self):
                        return False
                
                import flask_login
                flask_login.current_user = MockUser()
                
                try:
                    print("Attempting to render template...")
                    template_html = render_template('professor/session_detail.html',
                                                 session=session,
                                                 attendance_summary=attendance_summary,
                                                 recent_events=recent_events,
                                                 active_students=active_students)
                    
                    print("Template rendered successfully!")
                    print(f"HTML length: {len(template_html)} characters")
                    
                except Exception as e:
                    print(f"ERROR rendering template: {e}")
                    print(f"Error type: {type(e)}")
                    traceback.print_exc()
                    
                    # Try to identify if it's the modulo operation
                    if "unsupported operand type(s) for '%': 'int' and 'str'" in str(e):
                        print("\n*** FOUND THE MODULO ERROR! ***")
                        print("The error is in the template rendering.")
                        
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_session_detail_with_real_data()