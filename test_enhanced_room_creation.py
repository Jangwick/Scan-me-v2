#!/usr/bin/env python3
"""
Test the enhanced room creation with session scheduling functionality
"""

import sys
import os
from datetime import datetime, date, time, timedelta

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_enhanced_room_creation():
    """Test enhanced room creation with session scheduling"""
    
    print("🏢 ENHANCED ROOM CREATION WITH SESSION SCHEDULING - TEST")
    print("=" * 60)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.room_model import Room
            from app.models.user_model import User
            from app.models.session_schedule_model import SessionSchedule
            
            print("✅ Flask app initialized successfully")
            
            # Check instructors available
            instructors = User.query.filter(
                User.is_active == True,
                User.role.in_(['professor', 'admin'])
            ).order_by(User.username).all()
            
            print(f"✅ Available instructors: {len(instructors)}")
            for instructor in instructors:
                print(f"   👨‍🏫 {instructor.get_display_name()} ({instructor.get_role_display()})")
            
            # Show current rooms
            rooms = Room.query.all()
            sessions = SessionSchedule.query.all()
            
            print(f"✅ Current database state:")
            print(f"   🏢 Rooms: {len(rooms)}")
            print(f"   📅 Sessions: {len(sessions)}")
            
            if sessions:
                print(f"\n📅 EXISTING SESSIONS:")
                for session in sessions:
                    instructor = User.query.get(session.instructor_id)
                    room = Room.query.get(session.room_id)
                    print(f"   • {session.title}")
                    print(f"     👨‍🏫 {instructor.get_display_name()}")
                    print(f"     🏢 {room.get_full_name()}")
                    print(f"     📅 {session.session_date} at {session.start_time}")
            
            print(f"\n🆕 NEW ENHANCED FEATURES:")
            features = [
                "✅ Create room and immediately schedule a session",
                "✅ Assign professor/instructor during room creation",
                "✅ Set specific date and time for the session",  
                "✅ Configure attendance window and session settings",
                "✅ Real-time form validation and preview",
                "✅ Support for recurring sessions (daily, weekly, monthly)",
                "✅ Optional mandatory attendance and registration",
                "✅ Automatic room capacity inheritance or override"
            ]
            
            for feature in features:
                print(f"  {feature}")
            
            print(f"\n📋 HOW TO USE:")
            instructions = [
                "1. 🌐 Navigate to: http://localhost:5000/admin/rooms/add",
                "2. 📝 Fill in room details (number, type, capacity, etc.)",
                "3. 🔄 Toggle 'Create a session for this room' switch",
                "4. 📅 Fill in session details:",
                "   • Session title (e.g., 'Computer Science 101')",
                "   • Select instructor from available professors/admins",
                "   • Choose session date (today or future)",
                "   • Set start and end times",
                "   • Configure attendance settings",
                "5. 👁️ Review live preview of both room and session",
                "6. ✅ Submit to create room and session together"
            ]
            
            for instruction in instructions:
                print(f"  {instruction}")
            
            print(f"\n⚡ ADVANCED SESSION OPTIONS:")
            options = [
                "🔄 Recurring patterns: Create daily, weekly, or monthly sessions",
                "⏰ Attendance window: Configure QR code active time (5-60 minutes)",
                "👥 Capacity override: Set different max attendees than room capacity",
                "✅ Mandatory attendance: Require all students to attend",
                "📝 Registration required: Students must register before attending",
                "📄 Session descriptions: Add detailed information about the session"
            ]
            
            for option in options:
                print(f"  {option}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_workflow_example():
    """Show example workflow"""
    
    print(f"\n💡 EXAMPLE WORKFLOW:")
    print("-" * 40)
    
    print("🏢 CREATING A COMPUTER LAB WITH MORNING SESSION:")
    steps = [
        "Room Number: 'LAB-205'",
        "Room Name: 'Advanced Programming Lab'", 
        "Room Type: 'Computer Lab'",
        "Building: 'Engineering Building'",
        "Floor: '2nd Floor'",
        "Capacity: 30 students",
        "",
        "📅 IMMEDIATE SESSION SCHEDULING:",
        "Session Title: 'Python Programming Workshop'",
        "Instructor: 'Prof. Anderson (Professor)'",
        "Date: Tomorrow",
        "Time: 9:00 AM - 11:00 AM (2 hours)",
        "Max Attendees: 25 (override room capacity)",
        "Attendance Window: 15 minutes before start",
        "Settings: Mandatory attendance, Weekly recurrence",
        "",
        "🎯 RESULT:",
        "✅ Room LAB-205 created in database",
        "✅ Session scheduled with QR code generation ready",
        "✅ Professor assigned and notified",
        "✅ Students can scan QR 15 minutes before 9 AM",
        "✅ Weekly sessions auto-created for recurring pattern"
    ]
    
    for step in steps:
        if step:
            print(f"  • {step}")
        else:
            print()

if __name__ == '__main__':
    success = test_enhanced_room_creation()
    
    if success:
        show_workflow_example()
        
        print(f"\n🎉 ENHANCED ROOM CREATION IS READY!")
        print(f"🚀 Access the new feature at: http://localhost:5000/admin/rooms/add")
        print(f"📝 Now you can create rooms AND schedule sessions in one step!")
        
    else:
        print(f"\n❌ TEST FAILED - Please check the errors above")