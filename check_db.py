from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:pass%40123@localhost:3306/documed')
with engine.connect() as conn:
    result = conn.execute(text('SELECT user_id, email FROM users')).fetchall()
    print("Users in DB:", result)
