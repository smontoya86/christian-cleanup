from flask import Blueprint

auth = Blueprint('auth', __name__, url_prefix='/auth')

# Import routes at the end to avoid circular dependencies
from . import routes
