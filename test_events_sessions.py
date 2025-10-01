#!/usr/bin/env python3
"""
Test script to find sessions with events and test them
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, AttendanceSession, AttendanceEvent, AttendanceRecord, Student
import traceback

def find_and_test_sessions_with_events():
    """Find sessions with events and test them"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Finding sessions with events...")
            
            # Find sessions that have events
            sessions_with_events = db.session.query(AttendanceSession)\
                .join(AttendanceEvent)\
                .distinct()\
                .all()
                
            print(f"Found {len(sessions_with_events)} sessions with events")
            
            for session in sessions_with_events:
                print(f"\nSession {session.id}: {session.subject}")
                
                # Get events for this session
                events = AttendanceEvent.query.filter_by(session_id=session.id).all()
                print(f"  Has {len(events)} events")
                
                for i, event in enumerate(events[:5]):  # Test first 5 events
                    print(f"  Event {i}: {event.id}")
                    try:
                        # Test the problematic template expression
                        index_value = i % 8  # This is loop.index0 % 8
                        print(f"    Index: {index_value} (type: {type(index_value)})")
                        
                        # Test calling the avatar_color filter
                        filter_func = app.jinja_env.filters.get('avatar_color')
                        if filter_func:
                            color = filter_func(index_value)
                            print(f"    Color result: {color}")
                        else:
                            print("    No avatar_color filter!")
                            
                        # Test student access
                        if event.student:
                            student = event.student
                            if student.first_name and student.last_name:
                                initials = f"{student.first_name[0]}{student.last_name[0]}"
                                print(f"    Student initials: {initials}")
                            else:
                                print(f"    Student name issue: first='{student.first_name}', last='{student.last_name}'")
                        else:
                            print("    No student linked!")
                            
                    except Exception as e:
                        print(f"    ERROR: {e}")
                        traceback.print_exc()
                        
            # Also test if we can create the exact scenario that might cause the error
            print("\n--- MANUAL FILTER TEST ---")
            try:
                # Test different types of values with the filter
                filter_func = app.jinja_env.filters.get('avatar_color')
                if filter_func:
                    print("Testing filter with different inputs:")
                    
                    # Test with int
                    result1 = filter_func(0)
                    print(f"  filter(0) = {result1}")
                    
                    result2 = filter_func(5)
                    print(f"  filter(5) = {result2}")
                    
                    # Test with string (this might cause the error)
                    try:
                        result3 = filter_func("5")
                        print(f"  filter('5') = {result3}")
                    except Exception as e:
                        print(f"  filter('5') ERROR: {e}")
                        
                    # Test with None
                    try:
                        result4 = filter_func(None)
                        print(f"  filter(None) = {result4}")
                    except Exception as e:
                        print(f"  filter(None) ERROR: {e}")
                        
                else:
                    print("No avatar_color filter found!")
                    
            except Exception as e:
                print(f"Manual filter test ERROR: {e}")
                traceback.print_exc()
                
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    find_and_test_sessions_with_events()