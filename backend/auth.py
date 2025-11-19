"""
Super simple authentication (no JWT, no hashing)
Uses username instead of email for simplicity
"""
from database import get_all_users, user_exists_by_username, create_user, get_user

def register(username: str, password: str) -> dict:
    """Register new user with username"""
    exists, _ = user_exists_by_username(username)
    if exists:
        return {"error": "Username already registered"}
    
    username_result = create_user(username, password)
    
    return {
        "success": True,
        "username": username_result
    }

def login(username: str, password: str) -> dict:
    """Login user with username"""
    exists, username_found = user_exists_by_username(username)
    if not exists:
        return {"error": "Username not found"}
    
    user = get_user(username_found)
    if user['password'] != password:
        return {"error": "Wrong password"}
    
    return {
        "success": True,
        "username": username_found
    }