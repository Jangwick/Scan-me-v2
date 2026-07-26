import pytest
from app.utils.auth_utils import (
    hash_password,
    verify_password,
    validate_email,
    validate_username,
    validate_password,
    validate_student_data,
    validate_room_data,
    get_user_permissions,
)
from app.models.user_model import User


@pytest.mark.unit
def test_hash_and_verify_password():
    hashed = hash_password('MySecureP@ss1')
    assert verify_password(hashed, 'MySecureP@ss1') is True
    assert verify_password(hashed, 'WrongPassword') is False


@pytest.mark.unit
def test_validate_email():
    assert validate_email('user@example.com') is True
    assert validate_email('first.last@domain.co.uk') is True
    assert validate_email('invalid-email') is False
    assert validate_email('@domain.com') is False
    assert validate_email('user@domain') is False
    assert validate_email('') is False


@pytest.mark.unit
def test_validate_username():
    assert validate_username('john_doe') is True
    assert validate_username('user123') is True
    assert validate_username('ab') is False  # too short
    assert validate_username('a' * 21) is False  # too long
    assert validate_username('user-name') is False  # hyphen not allowed
    assert validate_username('user name') is False
    assert validate_username('') is False


@pytest.mark.unit
def test_validate_password_strength():
    assert validate_password('StrongP@ss1')['valid'] is True
    assert validate_password('Sh0rt!')['valid'] is False
    assert validate_password('nouppercase1!')['valid'] is False
    assert validate_password('NOLOWERCASE1!')['valid'] is False
    assert validate_password('NoNumber!@#')['valid'] is False
    assert validate_password('NoSpecial1')['valid'] is False


@pytest.mark.unit
def test_validate_student_data():
    valid = {
        'student_no': 'ST2023001',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@scanme.test',
        'department': 'CS',
        'section': 'CS-1A',
        'year_level': '2'
    }
    assert validate_student_data(valid)['valid'] is True

    invalid = valid.copy()
    invalid['email'] = 'not-an-email'
    assert validate_student_data(invalid)['valid'] is False
    assert any('email' in e.lower() for e in validate_student_data(invalid)['errors'])

    missing = valid.copy()
    missing['first_name'] = ''
    assert validate_student_data(missing)['valid'] is False


@pytest.mark.unit
def test_validate_room_data():
    valid = {
        'room_number': '101',
        'building': 'Main',
        'floor': '1',
        'capacity': '40'
    }
    assert validate_room_data(valid)['valid'] is True

    invalid = valid.copy()
    invalid['capacity'] = '0'
    assert validate_room_data(invalid)['valid'] is False

    missing = valid.copy()
    missing['building'] = ''
    assert validate_room_data(missing)['valid'] is False


@pytest.mark.unit
def test_get_user_permissions(app):
    with app.app_context():
        admin = User.create_user('admin_perm', 'admin_perm@scanme.test', 'Password123!', 'admin')
        professor = User.create_user('prof_perm', 'prof_perm@scanme.test', 'Password123!', 'professor')
        student = User.create_user('stud_perm', 'stud_perm@scanme.test', 'Password123!', 'student')

        admin_perms = get_user_permissions(admin)
        assert admin_perms['can_manage_rooms'] is True
        assert admin_perms['can_manage_users'] is True
        assert admin_perms['can_view_dashboard'] is True

        prof_perms = get_user_permissions(professor)
        assert prof_perms['can_manage_students'] is True
        assert prof_perms['can_manage_rooms'] is False

        stud_perms = get_user_permissions(student)
        assert stud_perms['can_view_dashboard'] is True
        assert stud_perms['can_view_reports'] is False
