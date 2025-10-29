"""
Simple test script for registration and login
"""
import requests
import json

# Backend URL
BASE_URL = "http://localhost:8000"

def print_header(text):
    print("\n" + "="*50)
    print(f"  {text}")
    print("="*50)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

# ============================================
# TEST 1: Register New User
# ============================================
print_header("TEST 1: REGISTER NEW USER")

email = "mudassir@test.com"
password = "pass123"

print(f"Registering: {email}")

try:
    response = requests.post(
        f"{BASE_URL}/register/",
        data={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Registration successful!")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Email: {data.get('email')}")
    else:
        error = response.json()
        print_error(f"Registration failed: {error.get('detail')}")
        
except Exception as e:
    print_error(f"Connection error: {e}")
    print("Make sure backend is running: uvicorn app:app --reload")

# ============================================
# TEST 2: Try to Register Same Email Again
# ============================================
print_header("TEST 2: REGISTER SAME EMAIL AGAIN (Should Fail)")

print(f"Trying to register: {email} again")

try:
    response = requests.post(
        f"{BASE_URL}/register/",
        data={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        print_error("Registration should have failed (email already exists)!")
    else:
        error = response.json()
        print_success(f"Registration blocked as expected: {error.get('detail')}")
        
except Exception as e:
    print_error(f"Connection error: {e}")

# ============================================
# TEST 3: Login with Correct Password
# ============================================
print_header("TEST 3: LOGIN WITH CORRECT PASSWORD")

print(f"Logging in: {email}")

try:
    response = requests.post(
        f"{BASE_URL}/login/",
        data={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Login successful!")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Email: {data.get('email')}")
    else:
        error = response.json()
        print_error(f"Login failed: {error.get('detail')}")
        
except Exception as e:
    print_error(f"Connection error: {e}")

# ============================================
# TEST 4: Login with Wrong Password
# ============================================
print_header("TEST 4: LOGIN WITH WRONG PASSWORD (Should Fail)")

wrong_password = "wrongpass"
print(f"Trying to login with wrong password")

try:
    response = requests.post(
        f"{BASE_URL}/login/",
        data={"email": email, "password": wrong_password}
    )
    
    if response.status_code == 200:
        print_error("Login should have failed (wrong password)!")
    else:
        error = response.json()
        print_success(f"Login blocked as expected: {error.get('detail')}")
        
except Exception as e:
    print_error(f"Connection error: {e}")

# ============================================
# TEST 5: Login with Non-existent Email
# ============================================
print_header("TEST 5: LOGIN WITH NON-EXISTENT EMAIL (Should Fail)")

fake_email = "nonexistent@test.com"
print(f"Trying to login with: {fake_email}")

try:
    response = requests.post(
        f"{BASE_URL}/login/",
        data={"email": fake_email, "password": "anypass"}
    )
    
    if response.status_code == 200:
        print_error("Login should have failed (email doesn't exist)!")
    else:
        error = response.json()
        print_success(f"Login blocked as expected: {error.get('detail')}")
        
except Exception as e:
    print_error(f"Connection error: {e}")

# ============================================
# SUMMARY
# ============================================
print_header("TEST COMPLETE")
print("\n✅ All tests completed!")
print("\nWhat was tested:")
print("  1. Register new user ✅")
print("  2. Block duplicate email ✅")
print("  3. Login with correct password ✅")
print("  4. Block wrong password ✅")
print("  5. Block non-existent email ✅")