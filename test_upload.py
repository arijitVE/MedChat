import requests
import io
import json

# 1. Login or Signup to get token
# Try to login with the user we created in test_auth.py
login_data = {
    "email": "test2@gmail.com",
    "password": "password123"
}
res = requests.post("http://127.0.0.1:8000/auth/login", json=login_data)
token = res.json().get("access_token")
if not token:
    print("Login failed:", res.text)
    exit(1)

print("Got token")

# 2. Create a case
headers = {"Authorization": f"Bearer {token}"}
case_data = {"title": "Test Case", "description": "Test"}
res = requests.post("http://127.0.0.1:8000/api/v1/cases", json=case_data, headers=headers)
case_id = res.json().get("id")
if not case_id:
    print("Case creation failed:", res.text)
    exit(1)

print("Created case", case_id)

# 3. Upload a document
file_data = {"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
res = requests.post(f"http://127.0.0.1:8000/api/v1/cases/{case_id}/upload", files=file_data, headers=headers)
print("Upload status:", res.status_code)
print("Upload response:", res.text)

# 4. Check /users/me
res = requests.get("http://127.0.0.1:8000/users/me", headers=headers)
print("/users/me status:", res.status_code)
print("/users/me response:", res.text)
