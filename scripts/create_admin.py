#!/usr/bin/env python3
"""CLI Script to create super administrator accounts in the database."""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.db.session import SessionLocal
from shared.db.models.user import User
from product.auth.password import hash_password

def create_admin_user(email: str, password: str, full_name: str):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Updating existing user '{email}' to ADMIN role...")
            existing.role = "admin"
            existing.password_hash = hash_password(password)
            existing.full_name = full_name
            db.commit()
            print(f"User '{email}' successfully updated to super administrator.")
            return

        new_admin = User(
            user_id=str(uuid4()),
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role="admin",
        )
        db.add(new_admin)
        db.commit()
        print(f"Successfully created super administrator: {email} ({full_name})")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a super administrator user.")
    parser.add_argument("--email", required=True, help="Email address of the admin account")
    parser.add_argument("--password", required=True, help="Password for the account")
    parser.add_argument("--name", default="System Administrator", help="Full name of the admin")
    args = parser.parse_args()

    create_admin_user(args.email, args.password, args.name)
