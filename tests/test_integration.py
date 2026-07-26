import json
import pytest
from tests.conftest import login_as


@pytest.mark.integration
def test_login_valid_credentials(client, auth_admin):
    """Valid login should redirect to dashboard."""
    resp = login_as(client, 'admin_user', 'TestPass123!')
    assert resp.status_code == 200
    assert resp.request.path == '/dashboard'


@pytest.mark.integration
def test_login_invalid_credentials(client, auth_admin):
    """Invalid login should re-render login page with an error."""
    resp = client.post('/auth/login', data={
        'username': 'admin_user',
        'password': 'WrongPass123!',
        'remember_me': False
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid' in resp.data or b'invalid' in resp.data


@pytest.mark.integration
def test_register_new_user(client):
    """Registration should create a user and redirect to dashboard."""
    resp = client.post('/auth/register', data={
        'first_name': 'Test',
        'last_name': 'User',
        'username': 'newtestuser',
        'email': 'newtestuser@example.com',
        'password': 'SecureP@ss1',
        'confirm_password': 'SecureP@ss1',
        'role': 'student',
        'agree_terms': True
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/dashboard'


@pytest.mark.integration
def test_dashboard_requires_login(client):
    """Anonymous users should be redirected from dashboard."""
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302


@pytest.mark.integration
def test_admin_dashboard_access(client, auth_admin):
    """Admin should see admin dashboard."""
    login_as(client, 'admin_user', 'TestPass123!')
    resp = client.get('/admin/')
    assert resp.status_code == 200


@pytest.mark.integration
def test_professor_dashboard_access(client, professor_user):
    """Professor should see professor dashboard."""
    login_as(client, 'prof_user', 'TestPass123!')
    resp = client.get('/professor/')
    assert resp.status_code == 200


@pytest.mark.integration
def test_student_cannot_access_admin(client, student_user):
    """Student should be redirected from admin routes."""
    login_as(client, 'student_user', 'TestPass123!')
    resp = client.get('/admin/', follow_redirects=False)
    assert resp.status_code == 302


@pytest.mark.integration
def test_student_crud_flow(app, client, professor_user):
    """Professor should add, view, edit, and delete a student."""
    login_as(client, 'prof_user', 'TestPass123!')

    # Add student
    resp = client.post('/students/add', data={
        'student_no': 'ST2023TEST',
        'first_name': 'Testy',
        'last_name': 'McStudent',
        'email': 'testy@scanme.test',
        'department': 'Test Dept',
        'section': 'T-1A',
        'year_level': 1
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Testy' in resp.data or b'added successfully' in resp.data

    # Locate created student
    with app.app_context():
        from app.models.student_model import Student
        student = Student.get_by_student_no('ST2023TEST')
        assert student is not None
        student_id = student.id

    # View student
    resp = client.get(f'/students/{student_id}')
    assert resp.status_code == 200
    assert b'Testy' in resp.data

    # Edit student
    resp = client.post(f'/students/{student_id}/edit', data={
        'first_name': 'TestyUpdated',
        'last_name': 'McStudent',
        'email': 'testy2@scanme.test',
        'department': 'Updated Dept',
        'section': 'T-1B',
        'year_level': 2
    }, follow_redirects=True)
    assert resp.status_code == 200

    # Delete student (soft delete)
    resp = client.post(f'/students/{student_id}/delete', follow_redirects=True)
    assert resp.status_code == 200


@pytest.mark.integration
def test_dashboard_api_returns_json(client, auth_admin):
    """Dashboard stats API should return JSON for authenticated users."""
    login_as(client, 'admin_user', 'TestPass123!')
    resp = client.get('/api/dashboard/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)


@pytest.mark.integration
def test_attendance_api_records(client, professor_user):
    """Attendance API records should return JSON for professor/admin."""
    login_as(client, 'prof_user', 'TestPass123!')
    resp = client.get('/attendance/api/records')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


@pytest.mark.integration
def test_scanner_api_process_qr(app, client, professor_user, sample_student, sample_room):
    """Scanner QR endpoint should process a valid student QR code."""
    prof_id, _ = professor_user
    login_as(client, 'prof_user', 'TestPass123!')

    with app.app_context():
        from app.models.student_model import Student
        from app.models.attendance_model import AttendanceSession
        from app import db
        from datetime import datetime, timedelta

        student = Student.query.get(sample_student)
        session = AttendanceSession(
            room_id=sample_room,
            session_name='Test Session',
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now() + timedelta(hours=1),
            created_by=prof_id
        )
        db.session.add(session)
        db.session.commit()
        session_id = session.id

        qr_payload = {
            'type': 'student_attendance',
            'student_id': sample_student,
            'student_no': student.student_no,
            'name': student.get_full_name()
        }

    resp = client.post(
        '/scanner/api/scan-qr',
        data=json.dumps({'qr_data': json.dumps(qr_payload), 'room_id': sample_room, 'session_id': session_id}),
        content_type='application/json'
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'success' in data


@pytest.mark.integration
def test_logout(client, auth_admin):
    """Logout should clear session and redirect."""
    login_as(client, 'admin_user', 'TestPass123!')
    resp = client.get('/auth/logout', follow_redirects=True)
    assert resp.status_code == 200
    # After logout, dashboard should require login again
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302
