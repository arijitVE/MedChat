from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.db.models.user import User

engine = create_engine('mysql+pymysql://root:pass%40123@localhost:3306/documed')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()
user_id = '887d0755-debd-4f34-b1bc-14c2cbdb5598'
user = db.query(User).filter(User.user_id == user_id).first()
if user:
    print("Found user via SQLAlchemy!")
else:
    print("User NOT FOUND via SQLAlchemy!")
