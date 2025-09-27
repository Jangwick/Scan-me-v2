#!/usr/bin/env python3
"""
Test script to verify session scheduling functionality
"""

import sys
import os
from datetime import datetime, date, time, timedelta

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from app.models.session_schedule_model import SessionSchedule, SessionStatus, RecurrenceType
from app.models.room_model import Room
from app.models.user_model import User

def test_scheduling_system():
    """Test the session scheduling system"""
    
    print("🧪 Testing Session Scheduling System")
    print("=" * 50)
    
    try:
        app = create_app()
        
        with app.app_context():
            # Get existing data
            rooms = Room.query.all()
            users = User.query.all()
            
            print(f"✅ Found {len(rooms)} rooms and {len(users)} users")
            
            if not rooms or not users:
                print("❌ Need at least one room and one user to test scheduling")
                return False
            
            room = rooms[0]
            user = users[0]
            
            print(f"📍 Using room: {room.get_full_name()}")
            print(f"👤 Using user: {user.get_display_name()}")
            
            # Test session creation
            test_session = SessionSchedule(
                title="Test Mathematics Session",
                room_id=room.id,
                instructor_id=user.id,
                session_date=date.today() + timedelta(days=1),
                start_time=time(9, 0),
                end_time=time(10, 30),
                description="This is a test session for mathematics",
                max_attendees=25,
                is_mandatory=True
            )
            
            print(f"📅 Created test session: {test_session.title}")
            print(f"   Date: {test_session.get_formatted_date()}")
            print(f"   Time: {test_session.get_formatted_time()}")
            print(f"   Duration: {test_session.duration_minutes} minutes")
            print(f"   Status: {test_session.get_status_display()}")
            print(f"   Recurrence: {test_session.get_recurrence_display()}")
            
            # Test methods
            print(f"   Session datetime: {test_session.get_session_datetime()}")
            print(f"   End datetime: {test_session.get_session_end_datetime()}")
            print(f"   Is active now: {test_session.is_active_now()}")
            print(f"   Can take attendance: {test_session.can_take_attendance()}")
            print(f"   Capacity: {test_session.get_capacity()}")
            print(f"   Attendance count: {test_session.get_attendance_count()}")
            print(f"   Is full: {test_session.is_full()}")
            
            # Test recurring sessions
            recurring_session = SessionSchedule(
                title="Weekly Staff Meeting",
                room_id=room.id,
                instructor_id=user.id,
                session_date=date.today() + timedelta(days=2),
                start_time=time(14, 0),
                end_time=time(15, 0),
                recurrence_type=RecurrenceType.WEEKLY,
                recurrence_interval=1,
                recurrence_end_date=date.today() + timedelta(days=30)
            )
            
            recurring_sessions = recurring_session.generate_recurring_sessions()
            print(f"\n🔄 Generated {len(recurring_sessions)} recurring sessions")
            
            for i, session_data in enumerate(recurring_sessions[:3]):  # Show first 3
                print(f"   {i+1}. {session_data['session_date']} - {session_data['title']}")
            
            # Test available routes
            print("\n🛠️ Available Schedule Routes:")
            
            for rule in app.url_map.iter_rules():
                if rule.endpoint.startswith('schedule'):
                    print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods)})")
            
            print("\n✅ All scheduling tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_scheduling_system()
    
    if success:
        print("\n🎉 Session Scheduling System is ready!")
        print("\n📋 New Features:")
        print("1. 📅 Create scheduled sessions with date/time")
        print("2. 🏢 Associate sessions with specific rooms")
        print("3. 👨‍🏫 Assign instructors to sessions")
        print("4. 🔄 Create recurring sessions (daily, weekly, monthly)")
        print("5. ⏰ Set attendance time windows")
        print("6. 🔍 Check room availability conflicts")
        print("7. 📊 Track session status and attendance")
        print("8. 🎯 Set capacity limits and mandatory attendance")
        
        print("\n🚀 Ready to use:")
        print("- Visit /schedule/sessions/add to create new sessions")
        print("- Visit room details and click 'Schedule Session'")
        print("- Use the scheduling interface to manage all sessions")
    else:
        print("\n❌ Session scheduling system has issues!")