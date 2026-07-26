import pytest
import flask


@pytest.mark.smoke
def test_app_factory_creates_app(app):
    """The application factory should produce a valid Flask app."""
    assert app is not None
    assert isinstance(app, flask.Flask)


@pytest.mark.smoke
def test_database_tables_created(app):
    """All model tables should exist after create_all."""
    from app import db
    with app.app_context():
        tables = db.inspect(db.engine).get_table_names()
        expected = {
            'users', 'students', 'rooms', 'attendance_records',
            'attendance_sessions', 'attendance_events', 'session_schedules'
        }
        assert expected.issubset(set(tables))


@pytest.mark.smoke
def test_public_routes_respond(client):
    """Public routes should return 200."""
    public_routes = [
        ('/', 200),
        ('/auth/login', 200),
        ('/auth/register', 200),
        ('/auth/forgot-password', 200),
    ]
    for route, expected_status in public_routes:
        resp = client.get(route)
        assert resp.status_code == expected_status, f"{route} returned {resp.status_code}"


@pytest.mark.smoke
def test_protected_routes_redirect_when_anonymous(client):
    """Protected routes should redirect anonymous users to login."""
    protected_routes = [
        '/dashboard',
        '/scanner/',
        '/students/',
        '/admin/',
        '/attendance/',
        '/schedule/',
        '/professor/',
    ]
    for route in protected_routes:
        resp = client.get(route, follow_redirects=False)
        assert resp.status_code in (302, 401), f"{route} did not protect resource ({resp.status_code})"


@pytest.mark.smoke
def test_404_for_unknown_route(client):
    """Unknown routes should return 404."""
    resp = client.get('/this-does-not-exist')
    assert resp.status_code == 404


@pytest.mark.smoke
def test_all_blueprints_registered(app):
    """All expected blueprints should be registered."""
    blueprint_names = {'main', 'auth', 'scanner', 'students', 'admin',
                       'attendance', 'schedule', 'professor', 'session_attendance'}
    assert blueprint_names.issubset(set(app.blueprints.keys()))
