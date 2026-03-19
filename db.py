import os
from typing import Generator

from pymongo import MongoClient
from pymongo.database import Database

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "charity")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client


def get_db() -> Generator[Database, None, None]:
    client = get_client()
    yield client[MONGODB_DB]
