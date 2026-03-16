"""
MongoDB document schemas (plain dicts).
Collections: users, charity_campaigns, donations, comments
"""
from datetime import datetime
from typing import Any


def doc_with_id(doc: dict[str, Any], id_field: str = "_id") -> dict[str, Any]:
    """Add 'id' field from _id for template compatibility."""
    d = dict(doc)
    if id_field in d:
        d["id"] = str(d[id_field])
    return d


def utc_now() -> datetime:
    return datetime.utcnow()
