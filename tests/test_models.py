import pytest
from app import db
from app.models.user_model import User
from app.models.student_model import Student
from app.models.room_model import Room
from app.models.attendance_model import AttendanceRecord
from app.utils.auth_utils import hash_password, verify_password


@pytest.mark.unit
def test_user_creation_and_password(app):
    with app.app_context():
        user = User.create_user('newuser', 'new@scanme.test', 'Password123!', 'student')
        assert user.id is not None
        assert user.check_password('Password123!') is True
        assert user.check_password('WrongPass!') is False
        assert user.is_student() is True
        assert user.is_admin() is False


@pytest.mark.unit
def test_user_get_by_username_and_email(app):
    with app.app_context():
        User.create_user('lookup', 'lookup@scanme.test', 'Password123!', 'professor')
        by_username = User.get_by_username('lookup')
        by_email = User.get_by_email('lookup@scanme.test')
        assert by_username is not None
        assert by_email is not None
        assert by_username.id == by_email.id


@pytest.mark.unit
def test_user_roles(app):
    with app.app_context():
        admin = User.create_user('admin', 'admin@scanme.test', 'Password123!', 'admin')
        prof = User.create_user('prof', 'prof@scanme.test', 'Password123!', 'professor')
        student = User.create_user('stud', 'stud@scanme.test', 'Password123!', 'student')

        assert admin.can_access_admin() is True
        assert prof.can_access_admin() is False
        assert prof.can_manage_students() is True
        assert student.can_view_reports() is False
        assert admin.get_role_display() == 'Administrator'


@pytest.mark.unit
def test_user_profile_update(app):
    with app.app_context():
        user = User.create_user('updater', 'update@scanme.test', 'Password123!', 'student')
        user.update_profile(username='newname', email='new@scanme.test')
        assert user.username == 'newname'
        assert user.email == 'new@scanme.test'


@pytest.mark.unit
def test_user_change_password(app):
    with app.app_context():
        user = User.create_user('pwduser', 'pwd@scanme.test', 'OldPass123!', 'student')
        user.change_password('OldPass123!', 'NewPass123!')
        assert user.check_password('NewPass123!') is True
        assert user.check_password('OldPass123!') is False

        with pytest.raises(ValueError):
            user.change_password('WrongOld!', 'AnotherPass123!')


@pytest.mark.unit
def test_user_deactivate_activate(app):
    with app.app_context():
        user = User.create_user('active_user', 'active@scanme.test', 'Password123!', 'student')
        user.deactivate()
        assert user.is_active is False
        user.activate()
        assert user.is_active is True


@pytest.mark.unit
def test_student_creation_and_qr_data(app):
    with app.app_context():
        student = Student(
            student_no='ST2023002',
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@scanme.test',
            department='Engineering',
            section='E-1B',
            year_level=3
        )
        db.session.add(student)
        db.session.commit()

        assert student.id is not None
        assert student.qr_code_data.startswith('SCANME_')
        assert student.get_full_name() == 'Jane Smith'


@pytest.mark.unit
def test_student_lookup_and_search(app):
    with app.app_context():
        student = Student(
            student_no='ST2023003',
            first_name='Alice',
            last_name='Wong',
            email='alice@scanme.test',
            department='Mathematics',
            section='M-2A',
            year_level=1
        )
        db.session.add(student)
        db.session.commit()

        by_no = Student.get_by_student_no('ST2023003')
        by_qr = Student.get_by_qr_code(student.qr_code_data)
        assert by_no is not None
        assert by_qr is not None

        results = Student.search_students('Alice')
        assert any(s.id == student.id for s in results)


@pytest.mark.unit
def test_student_update_and_deactivate(app):
    with app.app_context():
        student = Student(
            student_no='ST2023004',
            first_name='Bob',
            last_name='Tan',
            email='bob@scanme.test',
            department='Physics',
            section='P-3C',
            year_level=4
        )
        db.session.add(student)
        db.session.commit()

        student.update_info(first_name='Bobby', section='P-3D')
        assert student.first_name == 'Bobby'
        assert student.section == 'P-3D'

        student.deactivate()
        assert student.is_active is False


@pytest.mark.unit
def test_room_creation_and_helpers(app):
    with app.app_context():
        room = Room(
            room_number='201',
            room_name='Lab B',
            building='Science Hall',
            floor=2,
            capacity=30,
            room_type='laboratory'
        )
        db.session.add(room)
        db.session.commit()

        assert room.get_full_name() == '201 - Lab B'
        assert room.get_location() == 'Science Hall, 2nd Floor'
        assert '2nd' in room.get_location()


@pytest.mark.unit
def test_room_active_lookup(app):
    with app.app_context():
        active = Room(room_number='301', building='Main', floor=3, capacity=40)
        inactive = Room(room_number='302', building='Main', floor=3, capacity=40)
        inactive.deactivate()

        db.session.add(active)
        db.session.add(inactive)
        db.session.commit()

        active_rooms = Room.get_active_rooms()
        assert all(r.is_active for r in active_rooms)
        assert len(active_rooms) == 1


@pytest.mark.unit
def test_attendance_record_time_in_and_out(app, sample_student, sample_room):
    with app.app_context():
        scanner = User.create_user('scanner1', 'scanner@scanme.test', 'Password123!', 'professor')

        record = AttendanceRecord(
            student_id=sample_student,
            room_id=sample_room,
            scanned_by=scanner.id
        )
        db.session.add(record)
        db.session.commit()

        assert record.is_active is True
        assert record.time_in is not None

        success, message = record.time_out_student(scanner.id)
        assert success is True
        assert 'timed out' in message.lower()
        assert record.is_active is False
        assert record.time_out is not None


@pytest.mark.unit
def test_attendance_record_cannot_time_out_twice(app, sample_student, sample_room):
    with app.app_context():
        scanner = User.create_user('scanner2', 'scanner2@scanme.test', 'Password123!', 'professor')

        record = AttendanceRecord(
            student_id=sample_student,
            room_id=sample_room,
            scanned_by=scanner.id
        )
        db.session.add(record)
        db.session.commit()

        record.time_out_student(scanner.id)
        success, message = record.time_out_student(scanner.id)
        assert success is False
        assert 'already timed out' in message
