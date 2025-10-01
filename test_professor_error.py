#!/usr/bin/env python3
"""
Test script to identify the professor session loading error
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, AttendanceSession
import traceback

def test_professor_session_loading():
    """Test loading professor sessions to identify the modulo error"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing professor session loading...")
            
            # Find a professor user
            professor = User.query.filter_by(username='professor').first()
            if not professor:
                print("No professor user found!")
                return
            
            print(f"Found professor: {professor.username}")
            
            # Get professor's sessions
            professor_name = professor.username
            print(f"Searching for sessions with instructor: {professor_name}")
            
            # This is the query from professor_routes.py
            professor_sessions = AttendanceSession.query.filter(
                db.or_(
                    AttendanceSession.instructor == professor_name,
                    AttendanceSession.created_by == professor.id
                ),
                AttendanceSession.is_active == True
            ).order_by(AttendanceSession.start_time.desc()).all()
            
            print(f"Found {len(professor_sessions)} sessions")
            
            # Test getting session status for each
            for session in professor_sessions:
                print(f"\nTesting session {session.id}: {session.subject}")
                try:
                    status = session.get_session_status()
                    print(f"  Status: {status}")
                    
                    summary = session.get_attendance_summary()
                    print(f"  Summary: {summary}")
                    
                    # Test room location display if room exists
                    if session.room:
                        location = session.room.get_location_display()
                        print(f"  Location: {location}")
                        
                except Exception as e:
                    print(f"  ERROR in session {session.id}: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_professor_session_loading()