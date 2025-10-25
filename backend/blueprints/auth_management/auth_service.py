"""
Authentication service for user management and password handling.
"""

import bcrypt
import time
from typing import Optional, Dict, Any

try:
    from ...db.mongo import get_mongo_db, upsert_one, find_one, find_all
except ImportError:
    from db.mongo import get_mongo_db, upsert_one, find_one, find_all


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self):
        self.collection_name = "users"
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def create_user(self, username: str, password: str, role: str) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = self.get_user_by_username(username)
            if existing_user:
                return None
            
            password_hash = self.hash_password(password)
            current_time = time.time()
            
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'role': role,
                'created_at': current_time,
                'last_login': None
            }
            
            # Save to MongoDB
            upsert_one(self.collection_name, {'username': username}, user_data)
            
            # Return user data without password hash
            return {
                'username': username,
                'role': role,
                'created_at': current_time,
                'last_login': None
            }
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            user = find_one(self.collection_name, {'username': username})
            if user:
                # Remove password hash from returned data
                user.pop('password_hash', None)
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password."""
        try:
            # Get user with password hash for verification
            db = get_mongo_db()
            if db is None:
                return None
            
            user = db[self.collection_name].find_one({'username': username}, {'_id': 0})
            if not user:
                return None
            
            password_hash = user.get('password_hash')
            if not password_hash or not self.verify_password(password, password_hash):
                return None
            
            # Return user data without password hash
            user.pop('password_hash', None)
            return user
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp."""
        try:
            current_time = time.time()
            upsert_one(self.collection_name, {'username': username}, {'last_login': current_time})
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    def get_all_users(self) -> list:
        """Get all users (for admin purposes)."""
        try:
            users = find_all(self.collection_name)
            # Remove password hashes from all users
            for user in users:
                user.pop('password_hash', None)
            return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def initialize_default_admin(self) -> bool:
        """Initialize default admin user if no users exist."""
        try:
            users = self.get_all_users()
            if not users:
                # Create default admin user
                admin_user = self.create_user('admin', 'admin', 'admin')
                if admin_user:
                    print("Default admin user created (username: admin, password: admin)")
                    return True
                else:
                    print("Failed to create default admin user")
                    return False
            else:
                print(f"Users already exist ({len(users)} users found), skipping default admin creation")
                return True
        except Exception as e:
            print(f"Error initializing default admin: {e}")
            return False
