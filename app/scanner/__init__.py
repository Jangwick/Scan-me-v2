"""
Scanner blueprint initialization
"""
from flask import Blueprint

scanner = Blueprint('scanner_new', __name__, url_prefix='/scanner')

# Import routes after blueprint creation to avoid circular imports
from . import routes