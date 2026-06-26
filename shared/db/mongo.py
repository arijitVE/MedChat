# shared/db/mongo.py — MongoDB client singleton + collection access

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import certifi
import dns.resolver
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from shared.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient[dict[str, Any]]:
    """Return a cached singleton MongoClient instance."""
    settings = get_settings()
    
    # Fix for VM/cloud resolvers dropping SRV queries:
    if "+srv" in settings.MONGODB_URL:
        try:
            dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
            dns.resolver.default_resolver.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
        except Exception as e:
            logger.debug("Could not override DNS resolver: %s", e)
            
    kwargs = {}
    if "+srv" in settings.MONGODB_URL or "tls=true" in settings.MONGODB_URL.lower():
        kwargs["tlsCAFile"] = certifi.where()
    client: MongoClient[dict[str, Any]] = MongoClient(settings.MONGODB_URL, **kwargs)
    return client


def get_db() -> Database[dict[str, Any]]:
    """Return the MongoDB database object and ensure indexes exist."""
    settings = get_settings()
    client = get_mongo_client()
    db = client[settings.MONGODB_DB_NAME]
    _ensure_indexes(db)
    return db


def get_collection(name: str) -> Collection[dict[str, Any]]:
    """Return a named MongoDB collection."""
    db = get_db()
    return db[name]


_indexes_ensured = False


def _ensure_indexes(db: Database[dict[str, Any]]) -> None:
    """Ensure required unique indexes exist on core collections."""
    global _indexes_ensured
    if _indexes_ensured:
        return

    try:
        db["case_clinical_fields"].create_index("case_id", unique=True)
        db["case_metadata"].create_index("case_id", unique=True)
        db["case_insights"].create_index("case_id", unique=True)
        _indexes_ensured = True
        logger.info("MongoDB unique indexes ensured on case_id.")
    except Exception as e:
        logger.warning("Could not ensure MongoDB indexes: %s", e)
