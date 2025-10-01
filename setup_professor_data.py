#!/usr/bin/env python3
"""
Setup Professor Test Data
Creates a professor user and test sessions for testing the professor dashboard
"""

from app import create_app, db
from app.models import User, Room, AttendanceSession, Student
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import sys

def setup_professor_test_data():
    """Setup professor test data"""
    print("🧪 SETTING UP PROFESSOR TEST DATA")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create a professor user
            professor = User.query.filter_by(username='professor').first()
            if not professor:
                print("Creating professor user...")
                professor = User(
                    username='professor',
                    email='professor@scanme.system',
                    password=generate_password_hash('professor123'),
                    role='professor',
                    is_active=True
                )
                db.session.add(professor)
                db.session.commit()
                print("✅ Professor user created")
                print("   Username: professor")
                print("   Password: professor123")
            else:
                print("✅ Professor user already exists")
            
            # Get rooms for sessions
            rooms = Room.query.all()
            if not rooms:
                print("❌ No rooms found. Please create rooms first.")
                return False
            
            print(f"📍 Found {len(rooms)} rooms")
            
            # Create test sessions
            professor_name = professor.username  # Use username since no first_name/last_name fields
            
            # Current active session
            current_session = AttendanceSession.query.filter_by(
                instructor=professor_name,
                session_name="Computer Science 101"
            ).first()
            
            if not current_session:
                print("Creating active session...")
                now = datetime.now()
                start_time = now - timedelta(minutes=30)  # Started 30 minutes ago
                end_time = now + timedelta(minutes=60)    # Ends in 60 minutes
                
                current_session = AttendanceSession(
                    room_id=rooms[0].id,
                    session_name="Computer Science 101",
                    subject="Introduction to Programming",
                    instructor=professor_name,
                    start_time=start_time,
                    end_time=end_time,
                    expected_students=25,
                    created_by=professor.id
                )
                db.session.add(current_session)
                print("✅ Active session created")
            else:
                print("✅ Active session already exists")
            
            # Upcoming session
            upcoming_session = AttendanceSession.query.filter_by(
                instructor=professor_name,
                session_name="Database Systems"
            ).first()
            
            if not upcoming_session:
                print("Creating upcoming session...")
                tomorrow = datetime.now() + timedelta(days=1)
                start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)  # 2 PM tomorrow
                end_time = start_time + timedelta(hours=2)  # 2 hour session
                
                upcoming_session = AttendanceSession(
                    room_id=rooms[1 if len(rooms) > 1 else 0].id,
                    session_name="Database Systems",
                    subject="Advanced Database Management",
                    instructor=professor_name,
                    start_time=start_time,
                    end_time=end_time,
                    expected_students=20,
                    created_by=professor.id
                )
                db.session.add(upcoming_session)
                print("✅ Upcoming session created")
            else:
                print("✅ Upcoming session already exists")
            
            # Past session
            past_session = AttendanceSession.query.filter_by(
                instructor=professor_name,
                session_name="Software Engineering"
            ).first()
            
            if not past_session:
                print("Creating past session...")
                yesterday = datetime.now() - timedelta(days=1)
                start_time = yesterday.replace(hour=10, minute=0, second=0, microsecond=0)  # 10 AM yesterday
                end_time = start_time + timedelta(hours=1, minutes=30)  # 1.5 hour session
                
                past_session = AttendanceSession(
                    room_id=rooms[0].id,
                    session_name="Software Engineering",
                    subject="Agile Development Practices",
                    instructor=professor_name,
                    start_time=start_time,
                    end_time=end_time,
                    expected_students=18,
                    created_by=professor.id
                )
                db.session.add(past_session)
                print("✅ Past session created")
            else:
                print("✅ Past session already exists")
            
            db.session.commit()
            
            # Summary
            professor_sessions = AttendanceSession.query.filter_by(instructor=professor_name).all()
            print(f"\n📊 Summary:")
            print(f"   Professor: {professor_name}")
            print(f"   Total Sessions: {len(professor_sessions)}")
            
            for session in professor_sessions:
                status = session.get_session_status()
                print(f"   - {session.session_name}: {status}")
            
            print(f"\n🎉 Professor test data setup complete!")
            print(f"🌐 Login as professor and visit: http://127.0.0.1:5000/professor")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up test data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = setup_professor_test_data()
    if success:
        print("\n✅ Professor test data setup completed!")
    else:
        print("\n❌ Professor test data setup failed!")
        sys.exit(1)