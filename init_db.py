# Database Initialization Script
# This script creates all database tables and sets up initial data

from app import create_app, db
from app.models import User, Room, AttendanceSession
from werkzeug.security import generate_password_hash
from datetime import datetime, time
import sys
import os

def init_database():
    """Initialize the database with tables and default data"""
    print("Initializing ScanMe Attendance System Database...")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Check if admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                print("Creating default admin user...")
                admin_user = User(
                    username='admin',
                    email='admin@scanme.system',
                    first_name='System',
                    last_name='Administrator',
                    role='admin',
                    password_hash=generate_password_hash('admin123'),
                    is_active=True
                )
                db.session.add(admin_user)
                print("✓ Default admin user created")
                print("  Username: admin")
                print("  Password: admin123")
                print("  ⚠️  Please change this password after first login!")
            else:
                print("✓ Admin user already exists")
            
            # Create sample rooms if none exist
            if Room.query.count() == 0:
                print("Creating sample rooms...")
                
                sample_rooms = [
                    {
                        'name': 'Room 101',
                        'building': 'Main Building',
                        'capacity': 50,
                        'description': 'General classroom for lectures'
                    },
                    {
                        'name': 'Computer Lab 1',
                        'building': 'IT Building',
                        'capacity': 30,
                        'description': 'Computer laboratory with 30 workstations'
                    },
                    {
                        'name': 'Conference Room A',
                        'building': 'Admin Building',
                        'capacity': 25,
                        'description': 'Meeting room with presentation equipment'
                    },
                    {
                        'name': 'Auditorium',
                        'building': 'Main Building',
                        'capacity': 200,
                        'description': 'Large auditorium for events and seminars'
                    },
                    {
                        'name': 'Laboratory 201',
                        'building': 'Science Building',
                        'capacity': 40,
                        'description': 'Science laboratory with equipment'
                    }
                ]
                
                for room_data in sample_rooms:
                    room = Room(**room_data)
                    db.session.add(room)
                
                print(f"✓ Created {len(sample_rooms)} sample rooms")
            else:
                print(f"✓ Found {Room.query.count()} existing rooms")
            
            # Create sample attendance sessions if none exist
            if AttendanceSession.query.count() == 0:
                print("Creating sample attendance sessions...")
                
                sample_sessions = [
                    {
                        'name': 'Morning Session',
                        'start_time': time(8, 0),  # 8:00 AM
                        'end_time': time(11, 30),  # 11:30 AM
                        'is_active': True,
                        'description': 'Morning classes and lectures'
                    },
                    {
                        'name': 'Afternoon Session',
                        'start_time': time(13, 0),  # 1:00 PM
                        'end_time': time(16, 30),   # 4:30 PM
                        'is_active': True,
                        'description': 'Afternoon classes and laboratories'
                    },
                    {
                        'name': 'Evening Session',
                        'start_time': time(18, 0),  # 6:00 PM
                        'end_time': time(21, 0),    # 9:00 PM
                        'is_active': True,
                        'description': 'Evening classes for working students'
                    }
                ]
                
                for session_data in sample_sessions:
                    session = AttendanceSession(**session_data)
                    db.session.add(session)
                
                print(f"✓ Created {len(sample_sessions)} sample attendance sessions")
            else:
                print(f"✓ Found {AttendanceSession.query.count()} existing attendance sessions")
            
            # Commit all changes
            db.session.commit()
            print("\n" + "=" * 50)
            print("Database initialization completed successfully!")
            print("\nNext steps:")
            print("1. Run the application: python app.py")
            print("2. Open browser to: http://localhost:5000")
            print("3. Login with admin credentials")
            print("4. Add students and start taking attendance")
            
        except Exception as e:
            print(f"❌ Error initializing database: {str(e)}")
            db.session.rollback()
            sys.exit(1)

def reset_database():
    """Reset the database (drop all tables and recreate)"""
    print("⚠️  WARNING: This will delete all existing data!")
    confirm = input("Are you sure you want to reset the database? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Database reset cancelled.")
        return
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Dropping all database tables...")
            db.drop_all()
            print("✓ All tables dropped")
            
            # Reinitialize
            init_database()
            
        except Exception as e:
            print(f"❌ Error resetting database: {str(e)}")
            sys.exit(1)

def check_database():
    """Check database status and show statistics"""
    print("ScanMe Database Status")
    print("=" * 30)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if not tables:
                print("❌ No database tables found. Run initialization first.")
                return
            
            print(f"✓ Database tables: {len(tables)}")
            
            # Show counts
            from app.models import Student, AttendanceRecord
            
            user_count = User.query.count()
            student_count = Student.query.count()
            room_count = Room.query.count()
            session_count = AttendanceSession.query.count()
            attendance_count = AttendanceRecord.query.count()
            
            print(f"✓ Users: {user_count}")
            print(f"✓ Students: {student_count}")
            print(f"✓ Rooms: {room_count}")
            print(f"✓ Attendance Sessions: {session_count}")
            print(f"✓ Attendance Records: {attendance_count}")
            
            # Check admin user
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print(f"✓ Admin user exists: {admin.email}")
            else:
                print("❌ Admin user not found")
            
            print("\nDatabase is ready!")
            
        except Exception as e:
            print(f"❌ Error checking database: {str(e)}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ScanMe Database Management')
    parser.add_argument('--reset', action='store_true', help='Reset database (WARNING: Deletes all data)')
    parser.add_argument('--check', action='store_true', help='Check database status')
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    elif args.check:
        check_database()
    else:
        init_database()