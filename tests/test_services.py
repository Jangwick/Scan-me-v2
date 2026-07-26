import pytest
from datetime import datetime, timedelta
from app import db
from app.models.user_model import User
from app.models.student_model import Student
from app.models.room_model import Room
from app.models.attendance_model import AttendanceSession
from app.services.new_attendance_service import NewAttendanceService
from app.services.attendance_state_service import AttendanceStateService


@pytest.fixture
def active_session(app, sample_room):
    """Create an active AttendanceSession for service tests."""
    with app.app_context():
        room = Room.query.get(sample_room)
        creator = User.create_user('session_creator', 'creator@scanme.test', 'Password123!', 'professor')
        session = AttendanceSession(
            room_id=room.id,
            session_name='Test Session',
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now() + timedelta(hours=1),
            created_by=creator.id
        )
        db.session.add(session)
        db.session.commit()
        db.session.refresh(session)
        return session.id


@pytest.mark.unit
def test_new_attendance_service_time_in(app, sample_student, sample_room, active_session):
    with app.app_context():
        scanner = User.create_user('svc_scanner', 'svc_scanner@scanme.test', 'Password123!', 'professor')
        service = NewAttendanceService()
        result = service.process_attendance_scan(
            student_id=sample_student,
            room_id=sample_room,
            session_id=active_session,
            scanned_by=scanner.id
        )
        assert result['success'] is True
        assert result['action'] == 'time_in'
        assert 'Welcome' in result['message']


@pytest.mark.unit
def test_new_attendance_service_duplicate_time_in(app, sample_student, sample_room, active_session):
    with app.app_context():
        scanner = User.create_user('svc_scanner2', 'svc_scanner2@scanme.test', 'Password123!', 'professor')
        service = NewAttendanceService()
        service.process_attendance_scan(
            student_id=sample_student,
            room_id=sample_room,
            session_id=active_session,
            scanned_by=scanner.id
        )

        result = service.process_attendance_scan(
            student_id=sample_student,
            room_id=sample_room,
            session_id=active_session,
            scanned_by=scanner.id
        )
        assert result['success'] is False
        assert result['action'] in ('already_timed_in', 'time_out')


@pytest.mark.unit
def test_new_attendance_service_invalid_student(app, sample_room, active_session):
    with app.app_context():
        scanner = User.create_user('svc_scanner3', 'svc_scanner3@scanme.test', 'Password123!', 'professor')
        service = NewAttendanceService()
        result = service.process_attendance_scan(
            student_id=99999,
            room_id=sample_room,
            session_id=active_session,
            scanned_by=scanner.id
        )
        assert result['success'] is False
        assert 'Student not found' in result['message']


@pytest.mark.unit
def test_attendance_state_service_invalid_input(app):
    with app.app_context():
        result = AttendanceStateService.process_attendance_scan_new_logic(
            student_id=99999,
            room_id=99999,
            session_id=None,
            scanned_by=99999
        )
        assert result['success'] is False
        assert result['action'] in ('error', 'validation_error')
