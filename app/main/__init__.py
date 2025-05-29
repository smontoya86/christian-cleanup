from flask import Blueprint

main_bp = Blueprint('main', __name__)

# Note: Routes have been migrated to modular blueprints
# The main_bp is kept for backward compatibility but is no longer registered
