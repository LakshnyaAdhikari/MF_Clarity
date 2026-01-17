import requests
import sys

BASE_URL = "http://localhost:8000"

def test_auth():
    email = "testuser@example.com"
    password = "securepassword123"
    
    # 1. Register
    print("Testing Registration...")
    try:
        resp = requests.post(f"{BASE_URL}/register", json={"email": email, "password": password})
        if resp.status_code == 201:
            print("Registration Success!")
        elif resp.status_code == 400 and "already registered" in resp.text:
            print("User already exists, proceeding...")
        else:
            print(f"Registration Failed: {resp.text}")
            return
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 2. Login
    print("\nTesting Login...")
    resp = requests.post(f"{BASE_URL}/token", data={"username": email, "password": password})
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        print(f"Login Success! Token obtained.")
    else:
        print(f"Login Failed: {resp.text}")
        return

    # 3. Access Protected Route
    print("\nTesting Protected Route (/funds)...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/funds", headers=headers)
    if resp.status_code == 200:
        print(f"Access Granted! Found {len(resp.json())} funds.")
    else:
        print(f"Access Denied: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    test_auth()
