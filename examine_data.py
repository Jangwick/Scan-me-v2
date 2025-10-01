#!/usr/bin/env python3
"""
Test script to examine actual data in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Room, AttendanceSession, Student, AttendanceEvent
import traceback

def examine_actual_data():
    """Examine actual data values and types"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Examining actual data values...")
            
            # Check rooms data
            print("\n--- ROOMS DATA ---")
            rooms = Room.query.limit(5).all()
            for room in rooms:
                print(f"Room {room.id}:")
                print(f"  floor: {room.floor} (type: {type(room.floor)})")
                print(f"  capacity: {room.capacity} (type: {type(room.capacity)})")
                
                # Test the method that uses floor
                try:
                    location = room.get_location()
                    print(f"  location: {location}")
                except Exception as e:
                    print(f"  ERROR in get_location(): {e}")
                    traceback.print_exc()
            
            # Check attendance sessions
            print("\n--- ATTENDANCE SESSIONS DATA ---")
            sessions = AttendanceSession.query.limit(5).all()
            for session in sessions:
                print(f"Session {session.id}:")
                print(f"  expected_students: {session.expected_students} (type: {type(session.expected_students)})")
                print(f"  room_id: {session.room_id} (type: {type(session.room_id)})")
                
                # Test the method that might cause issues
                try:
                    summary = session.get_attendance_summary()
                    print(f"  summary: {summary}")
                except Exception as e:
                    print(f"  ERROR in get_attendance_summary(): {e}")
                    traceback.print_exc()
            
            # Check students data 
            print("\n--- STUDENTS DATA ---")
            students = Student.query.limit(3).all()
            for student in students:
                print(f"Student {student.id}:")
                print(f"  year_level: {student.year_level} (type: {type(student.year_level)})")
            
            # Check attendance events
            print("\n--- ATTENDANCE EVENTS DATA ---")
            events = AttendanceEvent.query.limit(3).all()
            for event in events:
                print(f"Event {event.id}:")
                print(f"  student_id: {event.student_id} (type: {type(event.student_id)})")
                print(f"  session_id: {event.session_id} (type: {type(event.session_id)})")
                print(f"  duration_minutes: {event.duration_minutes} (type: {type(event.duration_minutes)})")
                
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    examine_actual_data()