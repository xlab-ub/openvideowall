"""
Authentication API endpoints.
"""

from flask import request, jsonify, session, Blueprint
from .auth_service import AuthService

# Create blueprint instance
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

auth_service = AuthService()


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and create session."""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400
        
        username = data['username']
        password = data['password']
        
        user = auth_service.authenticate_user(username, password)
        if user:
            # Create session
            session['user_id'] = user['username']
            session['user_role'] = user['role']
            
            # Update last login
            auth_service.update_last_login(username)
            
            return jsonify({
                'success': True,
                'user': {
                    'username': user['username'],
                    'role': user['role']
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clear user session."""
    try:
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/session', methods=['GET'])
def check_session():
    """Check if user is authenticated."""
    try:
        if 'user_id' in session:
            user = auth_service.get_user_by_username(session['user_id'])
            if user:
                return jsonify({
                    'authenticated': True,
                    'user': {
                        'username': user['username'],
                        'role': user['role']
                    }
                })
        
        return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False})


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information."""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = auth_service.get_user_by_username(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'username': user['username'],
            'role': user['role'],
            'created_at': user['created_at'],
            'last_login': user['last_login']
        })
    except Exception as e:
        return jsonify({'error': 'Failed to get user info'}), 500
