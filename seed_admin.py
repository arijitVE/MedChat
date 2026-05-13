from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db.session import SessionLocal
from sqlalchemy import text
import bcrypt
import uuid

ADMIN_EMAIL = "admin@HDIMS.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_NAME = "System Admin"

db = SessionLocal()

# Check if admin already exists
existing = db.execute(
    text("SELECT user_id FROM users WHERE email = :email"),
    {"email": ADMIN_EMAIL}
).fetchone()

if existing:
    print(f"✅ Admin already exists: {ADMIN_EMAIL}")
    db.close()
    exit(0)

password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt(12)).decode()
user_id = str(uuid.uuid4())

db.execute(text("""
    INSERT INTO users (user_id, email, password_hash, role, full_name, is_active, is_registered)
    VALUES (:user_id, :email, :password_hash, 'admin', :full_name, TRUE, TRUE)
"""), {
    "user_id": user_id,
    "email": ADMIN_EMAIL,
    "password_hash": password_hash,
    "full_name": ADMIN_NAME
})
db.commit()
db.close()

print(f"✅ Admin created successfully")
print(f"   Email:    {ADMIN_EMAIL}")
print(f"   Password: {ADMIN_PASSWORD}")
print(f"   user_id:  {user_id}")
print(f"\n⚠️  Change the password after first login")
