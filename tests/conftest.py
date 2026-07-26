import pytest
from app import create_app, db
from app.models.user_model import User
from app.models.student_model import Student
from app.models.room_model import Room


TEST_PASSWORD = 'TestPass123!'


def _apply_test_config(app):
    """Override config for in-memory SQLite testing."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    app.config['DEBUG'] = False
    return app


@pytest.fixture(scope='function')
def app():
    """Create a fresh Flask app with an in-memory database for each test."""
    app = create_app('testing')
    _apply_test_config(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Flask test client for the current app."""
    return app.test_client()


@pytest.fixture(scope='function')
def auth_admin(app):
    """Create and log in an admin user in the current app context."""
    with app.app_context():
        user = User.create_user(
            username='admin_user',
            email='admin@scanme.test',
            password=TEST_PASSWORD,
            role='admin'
        )
        # Keep user object alive inside context for the client to use
        return user.id, TEST_PASSWORD


@pytest.fixture(scope='function')
def professor_user(app):
    """Create a professor user."""
    with app.app_context():
        user = User.create_user(
            username='prof_user',
            email='prof@scanme.test',
            password=TEST_PASSWORD,
            role='professor'
        )
        return user.id, TEST_PASSWORD


@pytest.fixture(scope='function')
def student_user(app):
    """Create a student user."""
    with app.app_context():
        user = User.create_user(
            username='student_user',
            email='student@scanme.test',
            password=TEST_PASSWORD,
            role='student'
        )
        return user.id, TEST_PASSWORD


@pytest.fixture(scope='function')
def sample_student(app):
    """Create a sample student record."""
    with app.app_context():
        student = Student(
            student_no='ST2023001',
            first_name='John',
            last_name='Doe',
            email='john.doe@scanme.test',
            department='Computer Science',
            section='CS-1A',
            year_level=2
        )
        db.session.add(student)
        db.session.commit()
        # Detach so it can be re-fetched later if needed
        db.session.refresh(student)
        return student.id


@pytest.fixture(scope='function')
def sample_room(app):
    """Create a sample room record."""
    with app.app_context():
        room = Room(
            room_number='101',
            room_name='Lecture Hall A',
            building='Main Building',
            floor=1,
            capacity=50,
            room_type='classroom'
        )
        db.session.add(room)
        db.session.commit()
        db.session.refresh(room)
        return room.id


def login_as(client, username, password=None):
    """Helper to log in through the web form."""
    return client.post(
        '/auth/login',
        data={
            'username': username,
            'password': password or TEST_PASSWORD,
            'remember_me': False
        },
        follow_redirects=True
    )
