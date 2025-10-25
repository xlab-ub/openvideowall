"""
Authentication utility functions and decorators.
"""

from functools import wraps
from flask import session, jsonify


def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(required_role):
    """Decorator to require a specific role for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = session.get('user_role')
            if user_role != required_role:
                return jsonify({'error': f'Role {required_role} required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Get current user from session."""
    if 'user_id' not in session:
        return None
    
    return {
        'username': session.get('user_id'),
        'role': session.get('user_role')
    }
