#!/usr/bin/env python3
"""
Test script to manually render professor dashboard template
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, AttendanceSession
from datetime import datetime
import traceback

def test_professor_dashboard_render():
    """Test rendering the professor dashboard template directly"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing professor dashboard template rendering...")
            
            # Find professor user
            professor = User.query.filter_by(username='professor').first()
            if not professor:
                print("No professor user found!")
                return
            
            # Simulate Flask context
            from flask import g
            from flask_login import login_user
            
            # Simulate logged in user
            class MockUser:
                def __init__(self, user):
                    self.id = user.id
                    self.username = user.username
                    self.role = user.role
                    self.is_authenticated = True
                    
                def is_professor(self):
                    return self.role == 'professor'
                    
                def is_admin(self):
                    return self.role == 'admin'
            
            # Get sessions
            professor_name = professor.username
            
            professor_sessions = AttendanceSession.query.filter(
                db.or_(
                    AttendanceSession.instructor == professor_name,
                    AttendanceSession.created_by == professor.id
                ),
                AttendanceSession.is_active == True
            ).order_by(AttendanceSession.start_time.desc()).all()
            
            print(f"Found {len(professor_sessions)} sessions")
            
            # Categorize sessions
            today = datetime.now().date()
            current_sessions = []
            upcoming_sessions = []
            past_sessions = []
            
            for session in professor_sessions:
                try:
                    session_date = session.start_time.date()
                    session_status = session.get_session_status()
                    
                    print(f"Processing session {session.id}: {session.subject}")
                    print(f"  Status: {session_status}")
                    
                    if session_status == 'active':
                        current_sessions.append(session)
                    elif session_date >= today and session_status in ['scheduled']:
                        upcoming_sessions.append(session)
                    else:
                        past_sessions.append(session)
                        
                except Exception as e:
                    print(f"ERROR processing session {session.id}: {e}")
                    traceback.print_exc()
                    
            print(f"Categorized: {len(current_sessions)} current, {len(upcoming_sessions)} upcoming, {len(past_sessions)} past")
            
            # Test template rendering
            from flask import render_template
            
            with app.test_request_context():
                # Create a mock current_user
                import flask_login
                flask_login.current_user = MockUser(professor)
                
                try:
                    template_html = render_template('professor/dashboard.html',
                                                 current_sessions=current_sessions,
                                                 upcoming_sessions=upcoming_sessions,
                                                 past_sessions=past_sessions[:10],
                                                 stats={'total_classes_today': 0, 'total_students_today': 0, 'total_scans_today': 0, 'active_sessions': len(current_sessions)})
                    print("Template rendered successfully!")
                    print(f"Template length: {len(template_html)} characters")
                    
                except Exception as e:
                    print(f"ERROR rendering template: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_professor_dashboard_render()