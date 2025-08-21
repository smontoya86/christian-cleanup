"""
Authentication and authorization utilities for the Christian Music Curation app.

This module provides decorators and utilities for securing admin endpoints
and ensuring proper access control throughout the application.
"""

from functools import wraps

from flask import jsonify
from flask_login import current_user


def admin_required(f):
    """
    Decorator to require admin privileges for accessing endpoints.

    This decorator should be used in conjunction with @login_required
    to ensure both authentication and admin authorization.

    Usage:
        @bp.route('/admin/endpoint')
        @login_required
        @admin_required
        def admin_endpoint():
            return jsonify({'message': 'Admin access granted'})

    Returns:
        - 401 if user is not authenticated
        - 403 if user is authenticated but not an admin
        - Original function result if user is an authenticated admin
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        # Check if user has admin privileges
        if not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        # User is authenticated and is admin - proceed with original function
        return f(*args, **kwargs)

    return decorated_function


def check_admin_access():
    """
    Utility function to check if current user has admin access.

    Returns:
        bool: True if user is authenticated and is admin, False otherwise
    """
    return current_user.is_authenticated and current_user.is_admin


def require_admin_or_self(user_id):
    """
    Check if current user is admin or is accessing their own data.

    Args:
        user_id (int): The user ID being accessed

    Returns:
        bool: True if access should be allowed
    """
    if not current_user.is_authenticated:
        return False

    # Admin can access any user's data
    if current_user.is_admin:
        return True

    # User can access their own data
    return current_user.id == user_id
