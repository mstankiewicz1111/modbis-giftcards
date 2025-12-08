# database/session.py

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------------------------
# Konfiguracja połączenia z bazą
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Lepiej wywalić się głośno przy starcie niż działać "po cichu" bez DB
    raise RuntimeError("ENV DATABASE_URL is not set")

# pre_ping = True – żeby szybciej wykrywać zerwane połączenia
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Klasyczna SessionLocal używana w całej aplikacji
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# Wspólna baza dla modeli (declarative base)
# ---------------------------------------------------------------------------

Base = declarative_base()
