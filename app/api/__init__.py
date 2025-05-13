# app/api/__init__.py
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes at the end to avoid circular dependencies
from . import routes
