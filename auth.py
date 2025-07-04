from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db


def register_user(username, password):
    """Register a new user with password validation"""
    # Input validation
    if not username or not password:
        return False
    if len(password) < 8:
        return False
    if len(username) < 3:
        return False

    # Check for existing user
    if User.query.filter_by(username=username).first():
        return False

    # Create and save new user
    try:
        user = User(username=username)
        user.set_password(password)  # Use the model's method
        db.session.add(user)
        db.session.commit()
        return user  # Return the user object for immediate login
    except Exception as e:
        db.session.rollback()
        return False


def login_user(username, password):
    """Authenticate an existing user"""
    if not username or not password:
        return None

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user  # Return user object instead of boolean
    return None