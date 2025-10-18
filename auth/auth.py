# auth/auth.py

# Simple in-memory user store for demo purposes
_users = {}

def register_user(username: str, password: str) -> bool:
    """
    Register a new user.
    Returns True if registration successful, False if username already exists.
    """
    if username in _users:
        return False
    _users[username] = password
    return True

def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user credentials.
    Returns True if credentials match, False otherwise.
    """
    return _users.get(username) == password
