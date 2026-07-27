# Database Initialization Script
# This script creates all database tables and sets up initial data

from app import create_app, db
from app.models import User, Room, AttendanceSession, Student, AttendanceRecord
from werkzeug.security import generate_password_hash
from datetime import datetime, time, timedelta
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
                    role='admin',
                    password=generate_password_hash('admin123'),
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
                        'room_number': '101',
                        'room_name': 'Room 101',
                        'building': 'Main Building',
                        'floor': 1,
                        'capacity': 50,
                        'room_type': 'classroom',
                        'description': 'General classroom for lectures'
                    },
                    {
                        'room_number': 'LAB-1',
                        'room_name': 'Computer Lab 1',
                        'building': 'IT Building',
                        'floor': 2,
                        'capacity': 30,
                        'room_type': 'laboratory',
                        'description': 'Computer laboratory with 30 workstations'
                    },
                    {
                        'room_number': 'CONF-A',
                        'room_name': 'Conference Room A',
                        'building': 'Admin Building',
                        'floor': 1,
                        'capacity': 25,
                        'room_type': 'classroom',
                        'description': 'Meeting room with presentation equipment'
                    },
                    {
                        'room_number': 'AUD',
                        'room_name': 'Auditorium',
                        'building': 'Main Building',
                        'floor': 1,
                        'capacity': 200,
                        'room_type': 'auditorium',
                        'description': 'Large auditorium for events and seminars'
                    },
                    {
                        'room_number': 'LAB-201',
                        'room_name': 'Laboratory 201',
                        'building': 'Science Building',
                        'floor': 2,
                        'capacity': 40,
                        'room_type': 'laboratory',
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
                
                # Get first room and user for the sessions
                first_room = Room.query.first()
                first_user = User.query.first()
                
                if first_room and first_user:
                    today = datetime.now().date()
                    sample_sessions = [
                        {
                            'room_id': first_room.id,
                            'session_name': 'Morning Session',
                            'start_time': datetime.combine(today, time(8, 0)),  # 8:00 AM
                            'end_time': datetime.combine(today, time(11, 30)),  # 11:30 AM
                            'created_by': first_user.id,
                            'subject': 'General',
                            'instructor': 'Default Instructor',
                            'expected_students': 30
                        },
                        {
                            'room_id': first_room.id,
                            'session_name': 'Afternoon Session',
                            'start_time': datetime.combine(today, time(13, 0)),  # 1:00 PM
                            'end_time': datetime.combine(today, time(16, 30)),   # 4:30 PM
                            'created_by': first_user.id,
                            'subject': 'General',
                            'instructor': 'Default Instructor',
                            'expected_students': 25
                        },
                        {
                            'room_id': first_room.id,
                            'session_name': 'Evening Session',
                            'start_time': datetime.combine(today, time(18, 0)),  # 6:00 PM
                            'end_time': datetime.combine(today, time(21, 0)),    # 9:00 PM
                            'created_by': first_user.id,
                            'subject': 'General',
                            'instructor': 'Default Instructor',
                            'expected_students': 20
                        }
                    ]
                    
                    for session_data in sample_sessions:
                        session = AttendanceSession(**session_data)
                        db.session.add(session)
                    
                    print(f"✓ Created {len(sample_sessions)} sample attendance sessions")
                else:
                    print("⚠ Skipping session creation - no rooms or users found")
            else:
                print(f"✓ Found {AttendanceSession.query.count()} existing attendance sessions")
            
            # Create sample students if none exist
            if Student.query.count() == 0:
                print("Creating sample students...")
                
                sample_students = [
                    {
                        'student_no': 'Std-001',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'email': 'john.doe@student.scanme',
                        'department': 'Information Technology',
                        'section': 'BSIT-101',
                        'year_level': 2
                    },
                    {
                        'student_no': 'Std-002',
                        'first_name': 'Jane',
                        'last_name': 'Smith',
                        'email': 'jane.smith@student.scanme',
                        'department': 'Computer Science',
                        'section': 'BSCS-201',
                        'year_level': 3
                    },
                    {
                        'student_no': 'Std-003',
                        'first_name': 'Michael',
                        'last_name': 'Johnson',
                        'email': 'michael.johnson@student.scanme',
                        'department': 'Engineering',
                        'section': 'BSENG-301',
                        'year_level': 4
                    },
                    {
                        'student_no': 'Std-004',
                        'first_name': 'Emily',
                        'last_name': 'Williams',
                        'email': 'emily.williams@student.scanme',
                        'department': 'Business',
                        'section': 'BSBA-101',
                        'year_level': 1
                    },
                    {
                        'student_no': 'Std-005',
                        'first_name': 'Daniel',
                        'last_name': 'Brown',
                        'email': 'daniel.brown@student.scanme',
                        'department': 'Information Technology',
                        'section': 'BSIT-101',
                        'year_level': 2
                    }
                ]
                
                for student_data in sample_students:
                    student = Student(**student_data)
                    db.session.add(student)
                
                print(f"✓ Created {len(sample_students)} sample students")
            else:
                print(f"✓ Found {Student.query.count()} existing students")
            
            # Create sample attendance records if none exist
            if AttendanceRecord.query.count() == 0:
                print("Creating sample attendance records...")
                
                sample_room = Room.query.first()
                sample_session = AttendanceSession.query.first()
                sample_user = User.query.first()
                sample_students = Student.query.all()
                
                if sample_room and sample_session and sample_user and sample_students:
                    now = datetime.utcnow()
                    base_offsets = [
                        (0, 8, False),   # today, 8 hours ago, on time
                        (0, 9, False),
                        (1, 10, True),   # yesterday, late
                        (1, 11, False),
                        (2, 8, False),
                        (3, 9, True),
                        (5, 8, False),
                        (7, 10, False),
                        (10, 9, False),
                        (14, 8, True),
                        (30, 9, False),
                        (60, 10, False),
                    ]
                    
                    created_count = 0
                    for i, (days_back, hours_back, is_late) in enumerate(base_offsets):
                        student = sample_students[i % len(sample_students)]
                        scan_time = now - timedelta(days=days_back, hours=hours_back)
                        
                        record = AttendanceRecord(
                            student_id=student.id,
                            room_id=sample_room.id,
                            scanned_by=sample_user.id,
                            session_id=sample_session.id,
                            is_late=is_late
                        )
                        record.time_in = scan_time
                        record.scan_time = scan_time
                        record.time_out = scan_time + timedelta(hours=1)
                        record.time_out_scanned_by = sample_user.id
                        record.is_active = False
                        record.is_duplicate = False
                        db.session.add(record)
                        created_count += 1
                    
                    print(f"✓ Created {created_count} sample attendance records")
                else:
                    print("⚠ Skipping attendance record creation - missing room, session, user or students")
            else:
                print(f"✓ Found {AttendanceRecord.query.count()} existing attendance records")
            
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