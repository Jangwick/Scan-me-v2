"""
Create sample data for testing the scanner functionality
"""
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Student, Room, AttendanceSession, AttendanceRecord

app = create_app()

def create_sample_sessions():
    """Create sample sessions for today"""
    with app.app_context():
        # Get or create a room
        room = Room.query.first()
        if not room:
            room = Room(
                room_number="101",
                room_name="Computer Lab",
                building="Engineering Building",
                floor=1,
                capacity=40
            )
            db.session.add(room)
            db.session.flush()
        
        # Get or create an admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin', 
                email='admin@university.edu',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.flush()
        
        # Create sessions for today
        today = datetime.now().date()
        sessions_data = [
            {
                'name': 'Computer Science 101',
                'subject': 'Introduction to Programming',
                'start_time': datetime.combine(today, datetime.strptime('09:00', '%H:%M').time()),
                'end_time': datetime.combine(today, datetime.strptime('10:30', '%H:%M').time()),
                'expected_students': 25
            },
            {
                'name': 'Data Structures',
                'subject': 'Advanced Programming',
                'start_time': datetime.combine(today, datetime.strptime('11:00', '%H:%M').time()),
                'end_time': datetime.combine(today, datetime.strptime('12:30', '%H:%M').time()),
                'expected_students': 30
            },
            {
                'name': 'Web Development',
                'subject': 'Frontend Technologies',
                'start_time': datetime.combine(today, datetime.strptime('14:00', '%H:%M').time()),
                'end_time': datetime.combine(today, datetime.strptime('15:30', '%H:%M').time()),
                'expected_students': 20
            }
        ]
        
        for session_data in sessions_data:
            # Check if session already exists
            existing_session = AttendanceSession.query.filter_by(
                session_name=session_data['name'],
                room_id=room.id
            ).filter(
                db.func.date(AttendanceSession.start_time) == today
            ).first()
            
            if not existing_session:
                session = AttendanceSession(
                    room_id=room.id,
                    session_name=session_data['name'],
                    subject=session_data['subject'],
                    instructor="Prof. Smith",
                    start_time=session_data['start_time'],
                    end_time=session_data['end_time'],
                    expected_students=session_data['expected_students'],
                    created_by=admin.id
                )
                db.session.add(session)
        
        # Create some sample students
        sample_students = [
            {'student_no': 'STU001', 'first_name': 'John', 'last_name': 'Smith', 'email': 'john.smith@university.edu'},
            {'student_no': 'STU002', 'first_name': 'Alice', 'last_name': 'Johnson', 'email': 'alice.johnson@university.edu'},
            {'student_no': 'STU003', 'first_name': 'Bob', 'last_name': 'Williams', 'email': 'bob.williams@university.edu'},
            {'student_no': 'STU004', 'first_name': 'Emma', 'last_name': 'Brown', 'email': 'emma.brown@university.edu'},
            {'student_no': 'STU005', 'first_name': 'Michael', 'last_name': 'Davis', 'email': 'michael.davis@university.edu'},
        ]
        
        for student_data in sample_students:
            existing_student = Student.query.filter_by(student_no=student_data['student_no']).first()
            if not existing_student:
                student = Student(
                    student_no=student_data['student_no'],
                    first_name=student_data['first_name'],
                    last_name=student_data['last_name'],
                    email=student_data['email'],
                    department='Computer Science',
                    section='CS-A',
                    year_level=2
                )
                db.session.add(student)
        
        # Create some sample attendance records for testing
        first_session = AttendanceSession.query.filter(
            db.func.date(AttendanceSession.start_time) == today
        ).first()
        
        if first_session:
            students = Student.query.limit(3).all()
            for i, student in enumerate(students):
                # Check if attendance record already exists
                existing_record = AttendanceRecord.query.filter_by(
                    student_id=student.id,
                    session_id=first_session.id
                ).filter(
                    db.func.date(AttendanceRecord.scan_time) == today
                ).first()
                
                if not existing_record:
                    scan_time = first_session.start_time + timedelta(minutes=(i * 5))
                    record = AttendanceRecord(
                        student_id=student.id,
                        room_id=first_session.room_id,
                        session_id=first_session.id,
                        scanned_by=admin.id,
                        is_late=(i > 0)  # First student on time, others late
                    )
                    record.scan_time = scan_time
                    db.session.add(record)
        
        db.session.commit()
        print("Sample sessions and data created successfully!")

if __name__ == '__main__':
    create_sample_sessions()