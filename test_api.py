"""
Test script to verify attendance trends API endpoint
"""
from app import create_app, db
from datetime import date, timedelta
from app.models.attendance_model import AttendanceRecord
from app.models.student_model import Student
from sqlalchemy import func

app = create_app()

with app.app_context():
    # Test the attendance trends query
    print("Testing Attendance Trends API...")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    
    print(f"Date range: {start_date} to {end_date}")
    
    # Count total records
    total_records = AttendanceRecord.query.count()
    print(f"Total attendance records in DB: {total_records}")
    
    # Test the query
    from datetime import datetime as dt
    start_datetime = dt.combine(start_date, dt.min.time())
    end_datetime = dt.combine(end_date, dt.max.time())
    
    daily_stats = db.session.query(
        func.date(AttendanceRecord.time_in).label('date'),
        func.count(AttendanceRecord.id).label('total_scans'),
        func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students')
    ).filter(
        AttendanceRecord.time_in >= start_datetime,
        AttendanceRecord.time_in <= end_datetime
    ).group_by(
        func.date(AttendanceRecord.time_in)
    ).order_by(
        func.date(AttendanceRecord.time_in)
    ).all()
    
    print(f"\nDaily stats found: {len(daily_stats)} days")
    for stat in daily_stats[:5]:  # Show first 5
        print(f"  {stat.date}: {stat.total_scans} scans, {stat.unique_students} students")
    
    # Test department breakdown
    print("\n\nTesting Department Breakdown API...")
    department_stats = db.session.query(
        Student.department,
        func.count(AttendanceRecord.id).label('total_records'),
        func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students')
    ).join(
        AttendanceRecord, Student.id == AttendanceRecord.student_id
    ).group_by(
        Student.department
    ).order_by(
        func.count(AttendanceRecord.id).desc()
    ).all()
    
    print(f"Departments found: {len(department_stats)}")
    for stat in department_stats:
        print(f"  {stat.department}: {stat.total_records} records, {stat.unique_students} students")

print("\nAPI test completed!")
