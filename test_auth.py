from shared.db.session import SessionLocal
from product.schemas.auth import SignupRequest
from product.services.auth_service import signup
from product.auth.middleware import get_current_user
from product.auth.jwt_handler import decode_access_token
import asyncio

async def test():
    db = SessionLocal()
    req = SignupRequest(email="test2@gmail.com", password="password123", full_name="Test Two")
    res = signup(req, db)
    print("Signup Response Token:", res.access_token)
    print("Signup Response user_id:", res.user_id)
    
    payload = decode_access_token(res.access_token)
    print("Decoded payload:", payload)
    
    # Simulate get_current_user
    user_id = payload.get("sub")
    from shared.db.models.user import User
    db_user = db.query(User).filter(User.user_id == user_id).first()
    print("DB User found:", db_user)
    
    db.close()

if __name__ == "__main__":
    asyncio.run(test())
