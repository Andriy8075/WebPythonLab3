import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

_db_host = os.getenv("DB_HOST", "localhost")
_db_port = os.getenv("DB_PORT", "5432")
_db_name = os.getenv("DB_NAME", "charity")
_db_user = os.getenv("DB_USER", "postgres")
_db_pass = os.getenv("DB_PASSWORD", "postgres")

try:
    DATABASE_URL = f"postgresql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"
    connect_args = {}
except Exception as e:
    print(f"Error creating database engine: {e}")
    raise e

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
