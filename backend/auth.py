"""
Super simple authentication (no JWT, no hashing)
"""
from database import get_all_users, user_exists_by_email, create_user, get_user

def register(email: str, password: str) -> dict:
    """Register new user"""
    exists, _ = user_exists_by_email(email)
    if exists:
        return {"error": "Email already registered"}
    
    user_id = create_user(email, password)
    
    return {
        "success": True,
        "user_id": user_id,
        "email": email
    }

def login(email: str, password: str) -> dict:
    """Login user"""
    exists, user_id = user_exists_by_email(email)
    if not exists:
        return {"error": "Email not found"}
    
    user = get_user(user_id)
    if user['password'] != password:
        return {"error": "Wrong password"}
    
    return {
        "success": True,
        "user_id": user_id,
        "email": email
    }