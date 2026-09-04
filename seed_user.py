import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import User, UserRole

load_dotenv()

DATABASE_URL = f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@localhost:5432/{os.environ['POSTGRES_DB']}"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.admin,
    )
    approver = User(
        email="approver@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.approver,
        approval_limit=500,
    )
    member = User(
        email="member@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.member,
    )
    session.add_all([admin, approver, member])
    session.commit()
    print(f"Created admin: {admin.email}")
    print(f"Created approver: {approver.email} with limit {approver.approval_limit}")
    print(f"Created member: {member.email}")