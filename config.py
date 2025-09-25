# Flask Application Configuration
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "instance", "scanme.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300
    }
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/static/uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # WTF Forms Configuration
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'
    WTF_CSRF_TIME_LIMIT = int(os.environ.get('WTF_CSRF_TIME_LIMIT', 3600))
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@scanme.system')
    
    # QR Code Settings
    QR_CODE_SIZE = int(os.environ.get('QR_CODE_SIZE', 10))
    QR_CODE_BORDER = int(os.environ.get('QR_CODE_BORDER', 4))
    QR_CODE_ERROR_CORRECTION = os.environ.get('QR_CODE_ERROR_CORRECTION', 'M')
    QR_CODE_FORMAT = 'PNG'
    QR_CODE_FILL_COLOR = 'black'
    QR_CODE_BACK_COLOR = 'white'
    
    # Attendance Settings
    LATE_THRESHOLD_MINUTES = int(os.environ.get('LATE_THRESHOLD_MINUTES', 15))
    ATTENDANCE_GRACE_PERIOD = int(os.environ.get('ATTENDANCE_GRACE_PERIOD', 5))
    AUTO_CREATE_SESSIONS = os.environ.get('AUTO_CREATE_SESSIONS', 'True').lower() == 'true'
    
    # Pagination Settings
    STUDENTS_PER_PAGE = int(os.environ.get('STUDENTS_PER_PAGE', 20))
    RECORDS_PER_PAGE = int(os.environ.get('RECORDS_PER_PAGE', 50))
    
    # Security Settings
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_NUMBERS = os.environ.get('PASSWORD_REQUIRE_NUMBERS', 'True').lower() == 'true'
    PASSWORD_REQUIRE_SYMBOLS = os.environ.get('PASSWORD_REQUIRE_SYMBOLS', 'False').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/scanme.log')
    
    # Cache Settings
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # API Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    WTF_CSRF_ENABLED = False  # Disable CSRF for development
    
    # Less strict password requirements for development
    BCRYPT_LOG_ROUNDS = 4
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_REQUIRE_UPPERCASE = False
    PASSWORD_REQUIRE_LOWERCASE = False
    PASSWORD_REQUIRE_NUMBERS = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Development-specific initialization
        print("Running in DEVELOPMENT mode")

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Stronger security settings
    BCRYPT_LOG_ROUNDS = 14
    PASSWORD_REQUIRE_SYMBOLS = True
    
    # Production database with connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30
    }
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler, SMTPHandler
        
        # File logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/scanme.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Email error logging
        if cls.MAIL_SERVER:
            auth = None
            if cls.MAIL_USERNAME or cls.MAIL_PASSWORD:
                auth = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            
            secure = None
            if cls.MAIL_USE_TLS:
                secure = ()
            
            mail_handler = SMTPHandler(
                mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
                fromaddr=cls.MAIL_DEFAULT_SENDER,
                toaddrs=['admin@scanme.system'],
                subject='ScanMe Application Error',
                credentials=auth,
                secure=secure
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('ScanMe startup - Production Mode')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Testing-specific settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database
    WTF_CSRF_ENABLED = False
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4
    
    # Disable email sending in tests
    MAIL_SUPPRESS_SEND = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print("Running in TESTING mode")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment variable"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, config['default'])